"""LLM service — talks to Ollama, handles prompt engineering and language."""
from __future__ import annotations

import json
import logging
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
7. Yorum, tahmin veya "bu ders şunu sağlar" gibi açıklama EKLEME. Sadece bilgi tabanındaki olguları aktar.""",
    "en": """You are "ACUBOT", an assistant that answers questions for Acıbadem University students and visitors.

STRICT RULES:
1. Use ONLY the information in the "Knowledge Base" section below. Do not rely on outside knowledge or assumptions.
2. Answer ENTIRELY in ENGLISH. Never switch languages, even though the source data is in Turkish — translate course names if helpful.
3. If the knowledge base does not contain the answer, say plainly: "I don't have that information; please check the university's website."
4. When asked for ALL courses of a department or faculty, list every entry from the knowledge base verbatim — do not summarise or skip rows.
5. Preserve course codes, ECTS values, and original Turkish names exactly as shown in the knowledge base.
6. Keep replies concise, clear, and use bullet points when listing items. Skip filler intros and outros.
7. Do NOT add commentary, interpretations, or filler like "this course covers ..." — relay only the facts present in the knowledge base.""",
}


@dataclass
class LLMReply:
    text: str
    language: str
    context_size: int
    error: bool = False


def _build_prompt(
    user_message: str,
    context_text: str,
    history: list[tuple[str, str]],
    language: str,
) -> str:
    system_prompt = SYSTEM_PROMPTS[language]
    parts = [system_prompt, "", "Knowledge Base:", context_text]
    if history:
        parts.append("")
        parts.append("Conversation so far:")
        for role, content in history:
            label = "User" if role == "user" else "Assistant"
            parts.append(f"{label}: {content}")
    parts.append("")
    parts.append(f"User: {user_message}")
    parts.append("Assistant:")
    return "\n".join(parts)


def _call_ollama(prompt: str) -> tuple[str | None, str | None]:
    """Return (text, error). Exactly one of them is None."""
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        # Keep the model in RAM between requests; without this Ollama unloads
        # after 5 min of inactivity and the next call eats a 10–30 s reload.
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0.0,
            "top_p": 0.9,
            # Context window kept small (4096) so 3B-class models stay snappy
            # on CPU-only machines. Bump to 8192 if you switch to a larger
            # model on a workstation with a GPU.
            "num_ctx": 4096,
            # Up to ~50 course rows can need >1.5k tokens to render.
            "num_predict": 2048,
        },
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
    text = (data.get("response") or "").strip()
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

    result = retrieve(user_message)
    context_text = format_for_llm(result, language)

    trimmed_history: list[tuple[str, str]] = []
    if history:
        trimmed_history = list(history)[-HISTORY_TURNS * 2 :]

    prompt = _build_prompt(user_message, context_text, trimmed_history, language)
    logger.debug("LLM prompt (%d chars):\n%s", len(prompt), prompt)

    text, error = _call_ollama(prompt)
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
    result = retrieve(user_message)
    context_text = format_for_llm(result, language)
    context_size = result.total()

    trimmed_history: list[tuple[str, str]] = []
    if history:
        trimmed_history = list(history)[-HISTORY_TURNS * 2 :]

    prompt = _build_prompt(user_message, context_text, trimmed_history, language)

    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0.0,
            "top_p": 0.9,
            "num_ctx": 4096,
            "num_predict": 2048,
        },
    }

    chunks: list[str] = []
    error_code: str | None = None
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
                    piece = obj.get("response", "")
                    if piece:
                        chunks.append(piece)
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

    full_text = "".join(chunks).strip()
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
