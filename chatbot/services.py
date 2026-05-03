"""LLM service — talks to Ollama, handles prompt engineering and language."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Iterator

import requests
from django.conf import settings

from courses.language import detect_language
from courses.retrieval import format_for_llm, retrieve

logger = logging.getLogger(__name__)


# How many previous turns to include when building the prompt. Each "turn" is
# one user/assistant exchange. The LLM sees at most HISTORY_TURNS pairs.
HISTORY_TURNS = 4


SYSTEM_PROMPTS = {
    "tr": """Sen "ACUBOT"sun: Acıbadem Üniversitesi öğrencileri ve ziyaretçileri için soruları yanıtlayan bir asistansın.

KESİN KURALLAR:
1. SADECE aşağıdaki "Bilgi Tabanı" bölümündeki bilgileri kullan. Kendi bilgini ya da varsayımlarını kullanma.
2. Yanıtını TAMAMEN TÜRKÇE ver. Asla başka bir dile geçme.
3. Bilgi tabanında cevap yoksa açıkça şunu söyle: "Bu konuda elimde bilgi yok; üniversitenin web sitesini kontrol etmenizi öneririm."
4. Kullanıcı bir bölümün ya da fakültenin TÜM derslerini istediğinde, bilgi tabanındaki tüm dersleri TAM olarak listele; özet geçme, atlama yapma.
5. Ders kodlarını, ECTS değerlerini ve isimleri bilgi tabanındaki haliyle aynen kullan.
6. Yanıtların kısa, net ve madde işaretli olsun. Gereksiz girişlere ya da kapanışlara yer verme.
7. Yorum, tahmin veya "bu ders şunu sağlar" gibi açıklama EKLEME. Sadece bilgi tabanındaki olguları aktar.
8. Yanıtının başına ASLA "User:", "Assistant:", "Kullanıcı:", "Asistan:", "Bilgi Tabanı:" gibi etiketler koyma. Doğrudan cevapla.
9. Bölüm, fakülte ve ders isimlerini bilgi tabanında yazıldığı şekilde HARF HARF AYNEN yaz; harf düşürme/ekleme/değiştirme yapma. Örneğin "İnsan ve Toplum Bilimleri Fakültesi" yerine "İnsa ve Toplum Bilimleri" yazma; "Bilgisayar Mühendisliği" yerine "Bilgisayar Müh." yazma. Aynı ismi listede iki kez tekrarlama.
10. ASLA uydurma isimler (örn: [Adı], [Name], "Doç. Dr.") veya varsayımsal bilgiler ekleme. Bilgi tabanında bir liste eksikse (örneğin sadece Bölüm Başkanı var ama tüm akademik kadro soruluyorsa), SADECE elindeki bilgiyi ver ve eksik kısımlar için "Diğer akademik kadro hakkında elimde bilgi yok." şeklinde belirt.""",
    "en": """You are "ACUBOT", an assistant that answers questions for Acıbadem University students and visitors.

STRICT RULES:
1. Use ONLY the information in the "Knowledge Base" section below. Do not rely on outside knowledge or assumptions.
2. Answer ENTIRELY in ENGLISH. Never switch languages, even though the source data is in Turkish — translate course names if helpful.
3. If the knowledge base does not contain the answer, say plainly: "I don't have that information; please check the university's website."
4. When asked for ALL courses of a department or faculty, list every entry from the knowledge base verbatim — do not summarise or skip rows.
5. Preserve course codes, ECTS values, and original Turkish names exactly as shown in the knowledge base.
6. Keep replies concise, clear, and use bullet points when listing items. Skip filler intros and outros.
7. Do NOT add commentary, interpretations, or filler like "this course covers ..." — relay only the facts present in the knowledge base.
8. NEVER prefix your reply with labels like "User:", "Assistant:", or "Knowledge Base:". Reply directly.
9. Copy department, faculty and course names from the knowledge base LETTER FOR LETTER; do not drop, add, or change a single character. For example, never shorten "İnsan ve Toplum Bilimleri Fakültesi" to "İnsa ve Toplum Bilimleri", and never abbreviate "Bilgisayar Mühendisliği" to "Bilgisayar Eng.". Never list the same name twice.
10. NEVER invent names (e.g., [Name], [Adı]) or hypothetical information. If the knowledge base only has partial information (e.g., only the Department Head when asked for the full academic staff), state ONLY what you have and add "I don't have information about the rest of the staff." Do not hallucinate to complete a list.""",
}


# Prefixes the model occasionally echoes back from the chat scaffolding.
# Stripped before the answer is shown to the user.
_LABEL_RE = re.compile(
    r"^\s*(?:user|assistant|kullanıcı|kullanici|asistan|bilgi\s*tabanı|knowledge\s*base)\s*[:：]\s*",
    re.IGNORECASE,
)


_USER_LABEL_TOKENS = {"user", "kullanıcı", "kullanici"}


def _label_word(line: str) -> str | None:
    match = _LABEL_RE.match(line)
    if not match:
        return None
    return match.group(0).strip().rstrip(":：").strip().lower()


def _has_following_assistant_label(lines: list[str], user_idx: int) -> bool:
    for j in range(user_idx + 1, len(lines)):
        if not lines[j].strip():
            continue
        word = _label_word(lines[j])
        if word is None:
            return False
        if word not in _USER_LABEL_TOKENS:
            return True
    return False


def _scrub_labels(text: str) -> str:
    """Strip prompt-scaffolding leakage from the model's reply.

    Smaller models leak labels in two distinct ways:

      1. **Conversation echo** — the model parrots the entire turn:
         ``User: <prior question>\\nAssistant: <answer>``.
         In this case the User line is the user's question and must be
         dropped entirely.
      2. **Mislabeling** — the model just prefixes its own answer with the
         wrong tag, e.g. ``User: +90 216 ...``.
         In this case we must NOT drop the line; only the bogus prefix.

    We disambiguate per user-labelled line: if a non-user label appears on a
    later line, treat it as case (1) and drop the user line; otherwise treat
    it as case (2) and keep the content after the label.
    """
    lines = text.splitlines()
    out: list[str] = []
    for i, raw_line in enumerate(lines):
        line = raw_line
        drop_line = False
        while True:
            match = _LABEL_RE.match(line)
            if not match:
                break
            label_word = (
                match.group(0).strip().rstrip(":：").strip().lower()
            )
            rest = line[match.end():]
            if label_word in _USER_LABEL_TOKENS:
                if _has_following_assistant_label(lines, i):
                    drop_line = True
                    break
                # Mislabeling: peel off the prefix, keep the answer.
                line = rest
                continue
            # Assistant / knowledge-base header — strip and keep going.
            line = rest
        if drop_line:
            continue
        if line.strip():
            out.append(line)
    return "\n".join(out).strip()


@dataclass
class LLMReply:
    text: str
    language: str
    context_size: int
    error: bool = False


def _get_contextual_query(user_message: str, history: list[tuple[str, str]] | None) -> str:
    if not history:
        return user_message

    last_user_msg = ""
    for role, text in reversed(history):
        if role == "user":
            last_user_msg = text
            break

    if last_user_msg:
        return f"{last_user_msg} {user_message}"

    return user_message


def _build_messages(
    user_message: str,
    context_text: str,
    history: list[tuple[str, str]],
    language: str,
) -> list[dict]:
    """Build the structured message list expected by Ollama's /api/chat
    endpoint. Using role-based messages lets the model rely on its own chat
    template — so it never echoes labels like "User:" or "Assistant:" back
    to the user."""
    if language == "tr":
        kb_header = "Bilgi Tabanı:"
    else:
        kb_header = "Knowledge Base:"

    system_content = (
        f"{SYSTEM_PROMPTS[language]}\n\n{kb_header}\n{context_text}"
    )
    messages: list[dict] = [{"role": "system", "content": system_content}]
    for role, content in history:
        if role not in {"user", "assistant"}:
            continue
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


def _ollama_options() -> dict:
    return {
        "temperature": 0.0,
        "top_p": 0.9,
        # Context window kept small (2048) for faster inference on CPU.
        # Most queries need <1000 tokens context for courses.
        "num_ctx": 2048,
        # Limit output to 1024 tokens (usually <500 needed).
        "num_predict": 1024,
    }


def _call_ollama(messages: list[dict]) -> tuple[str | None, str | None]:
    """Return (text, error). Exactly one of them is None."""
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        # Keep the model in RAM between requests; without this Ollama unloads
        # after 5 min of inactivity and the next call eats a 10–30 s reload.
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "options": _ollama_options(),
    }
    try:
        response = requests.post(
            url, json=payload, timeout=settings.OLLAMA_TIMEOUT_SECONDS
        )
    except requests.exceptions.ConnectionError:
        return None, "connection"
    except requests.exceptions.Timeout:
        return None, "timeout"
    except requests.exceptions.RequestException as exc:
        logger.exception("Ollama request failed: %s", exc)
        return None, "request"

    if response.status_code != 200:
        logger.error(
            "Ollama returned %s: %s", response.status_code, response.text[:300]
        )
        return None, f"status_{response.status_code}"

    try:
        data = response.json()
    except ValueError:
        return None, "decode"
    text = (data.get("message", {}).get("content") or "").strip()
    text = _scrub_labels(text)
    if not text:
        return None, "empty"
    return text, None


_FRIENDLY_ERRORS = {
    "tr": {
        "connection": "Yapay zekâ sunucusuna şu an bağlanamıyorum. Model hâlâ indiriliyor olabilir; lütfen birkaç dakika sonra tekrar deneyin.",
        "timeout": "Yapay zekâ yanıt vermesi çok uzun sürdü. Lütfen tekrar deneyin.",
        "request": "Yapay zekâ servisinde beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.",
        "decode": "Yapay zekâ yanıtı çözümlenemedi. Lütfen tekrar deneyin.",
        "empty": "Yapay zekâ boş bir yanıt döndürdü. Lütfen tekrar deneyin.",
    },
    "en": {
        "connection": "I cannot reach the AI server right now. The model may still be downloading; please try again in a few minutes.",
        "timeout": "The AI took too long to respond. Please try again.",
        "request": "Unexpected error while contacting the AI service. Please try again.",
        "decode": "The AI response could not be parsed. Please try again.",
        "empty": "The AI returned an empty response. Please try again.",
    },
}


def _friendly_error(code: str, language: str) -> str:
    return _FRIENDLY_ERRORS[language].get(
        code,
        _FRIENDLY_ERRORS[language]["request"],
    ) + (
        " (Status: " + code + ")"
        if code.startswith("status_")
        else ""
    )


def ask(
    user_message: str,
    history: list[tuple[str, str]] | None = None,
) -> LLMReply:
    """Generate a reply for `user_message`.

    `history` is a list of (role, content) tuples in chronological order. Only
    the most recent HISTORY_TURNS exchanges are forwarded to the LLM.
    """
    language = detect_language(user_message)

    contextual_query = _get_contextual_query(user_message, history)
    result = retrieve(contextual_query)
    context_text = format_for_llm(result, language)

    trimmed_history: list[tuple[str, str]] = []
    if history:
        trimmed_history = list(history)[-HISTORY_TURNS * 2 :]

    messages = _build_messages(user_message, context_text, trimmed_history, language)
    logger.debug("LLM messages (%d):\n%s", len(messages), messages)

    text, error = _call_ollama(messages)
    if error is not None:
        return LLMReply(
            text=_friendly_error(error, language),
            language=language,
            context_size=result.total(),
            error=True,
        )

    return LLMReply(
        text=text,
        language=language,
        context_size=result.total(),
        error=False,
    )


def ask_stream(
    user_message: str,
    history: list[tuple[str, str]] | None = None,
) -> Iterator[dict]:
    """Stream a reply token-by-token. Yields dicts:
        {"type": "chunk", "text": "..."}      — partial output
        {"type": "done",  "text": "...full...", "language": ..., "context_size": ..., "error": bool}
    Always finishes with exactly one "done" event.
    """
    language = detect_language(user_message)
    contextual_query = _get_contextual_query(user_message, history)
    result = retrieve(contextual_query)
    context_text = format_for_llm(result, language)
    context_size = result.total()

    trimmed_history: list[tuple[str, str]] = []
    if history:
        trimmed_history = list(history)[-HISTORY_TURNS * 2 :]

    messages = _build_messages(user_message, context_text, trimmed_history, language)

    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "options": _ollama_options(),
    }

    chunks: list[str] = []
    error_code: str | None = None
    label_scrubbed = False  # only scrub the very first user-visible chunk

    try:
        with requests.post(
            url,
            json=payload,
            stream=True,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        ) as response:
            if response.status_code != 200:
                error_code = f"status_{response.status_code}"
            else:
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        continue
                    piece = obj.get("message", {}).get("content", "")
                    if piece:
                        chunks.append(piece)
                        # Scrub leading labels on the first non-empty emit.
                        if not label_scrubbed:
                            joined = "".join(chunks)
                            cleaned = _scrub_labels(joined)
                            if cleaned != joined:
                                # Re-seed chunks with the scrubbed text so
                                # subsequent emissions don't re-introduce it.
                                chunks = [cleaned]
                                if cleaned:
                                    yield {"type": "chunk", "text": cleaned}
                                    label_scrubbed = True
                                continue
                            # Wait for more text before deciding.
                            if any(ch.isalpha() for ch in joined) and len(joined) >= 8:
                                label_scrubbed = True
                                yield {"type": "chunk", "text": piece}
                            # else: still buffering, do not yield yet
                        else:
                            yield {"type": "chunk", "text": piece}
                    if obj.get("done"):
                        break
    except requests.exceptions.ConnectionError:
        error_code = "connection"
    except requests.exceptions.Timeout:
        error_code = "timeout"
    except requests.exceptions.RequestException as exc:
        logger.exception("Ollama stream failed: %s", exc)
        error_code = "request"

    full_text = _scrub_labels("".join(chunks).strip())
    if error_code is not None and not full_text:
        yield {
            "type": "done",
            "text": _friendly_error(error_code, language),
            "language": language,
            "context_size": context_size,
            "error": True,
        }
        return

    if not full_text:
        yield {
            "type": "done",
            "text": _friendly_error("empty", language),
            "language": language,
            "context_size": context_size,
            "error": True,
        }
        return

    yield {
        "type": "done",
        "text": full_text,
        "language": language,
        "context_size": context_size,
        "error": False,
    }
