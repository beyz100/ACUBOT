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


HISTORY_TURNS = 4


SYSTEM_PROMPTS = {
    "tr": """Sen "ACUBOT"sun: Acıbadem Üniversitesi için soruları yanıtlayan resmi bir yapay zeka asistanısın.

KESİN KURALLAR:
1. SADECE aşağıdaki "Bilgi Tabanı" metninde yer alan bilgileri kullanarak cevap ver. Kendi bilgini ekleme.
2. Eğer kullanıcının sorduğu bölüm veya fakülte (örneğin Hukuk, Mimarlık, Diş Hekimliği vb.) Bilgi Tabanı'nda YOKSA, asla uydurma! Doğrudan şunu söyle: "Üniversitemizde bu bölüm/fakülte bulunmamaktadır."
3. Diğer cevapsız konular için: "Bu konuda elimde bilgi yok, üniversitenin web sitesini kontrol edebilirsiniz." de.
4. Cevapların tamamen Türkçe, net ve kısa olsun. Halüsinasyon (olmayan bir şeyi varmış gibi göstermek) KESİNLİKLE YASAKTIR.""",
    "en": """You are "ACUBOT", the official AI assistant for Acıbadem University.

STRICT RULES:
1. Base your answer ONLY on the "Knowledge Base" text provided below. Do not use outside knowledge.
2. If the department or faculty (e.g., Law, Architecture, Dentistry) asked by the user is NOT in the Knowledge Base, DO NOT hallucinate! Simply say: "We do not have this department/faculty at our university."
3. For other unknown topics, say: "I don't have that information, please check the university's website."
4. Answer entirely in English, keep it short and clear. Inventing facts is STRICTLY FORBIDDEN."""
}


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
                line = rest
                continue
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


def _build_messages(
    user_message: str,
    context_text: str,
    history: list[tuple[str, str]],
    language: str,
) -> list[dict]:
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
        "num_ctx": 4096,
        "num_predict": 2048,
    }


def _call_ollama(messages: list[dict]) -> tuple[str | None, str | None]:
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
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
    language = detect_language(user_message)
    result = retrieve(user_message)
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
    language = detect_language(user_message)
    result = retrieve(user_message)
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
    label_scrubbed = False 

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
                        if not label_scrubbed:
                            joined = "".join(chunks)
                            cleaned = _scrub_labels(joined)
                            if cleaned != joined:
                                chunks = [cleaned]
                                if cleaned:
                                    yield {"type": "chunk", "text": cleaned}
                                    label_scrubbed = True
                                continue
                            if any(ch.isalpha() for ch in joined) and len(joined) >= 8:
                                label_scrubbed = True
                                yield {"type": "chunk", "text": piece}
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
