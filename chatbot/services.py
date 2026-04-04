from __future__ import annotations

import re
import requests
import logging
from courses.models import Course
from courses.retrieval import (
    get_retrieval_context,
    format_context_for_llm,
    retrieve_courses_hybrid,
    retrieve_university_info,
)

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://llm:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"


EN_TR_KEYWORDS: dict[str, list[str]] = {
    "programming":  ["programlama", "programlamaya"],
    "program":      ["programlama"],
    "course":       ["ders"],
    "courses":      ["ders", "dersleri"],
    "math":         ["matematik", "kalkülüs"],
    "mathematics":  ["matematik", "kalkülüs"],
    "calculus":     ["kalkülüs"],
    "physics":      ["fizik"],
    "chemistry":    ["kimya"],
    "english":      ["ingilizce"],
    "turkish":      ["türk dili"],
    "history":      ["tarih", "inkılap"],
    "data":         ["veri"],
    "database":     ["veritabanı"],
    "algorithm":    ["algoritma"],
    "web":          ["web"],
    "network":      ["ağ", "bilgisayar ağları"],
    "operating":    ["işletim"],
    "system":       ["sistem"],
    "software":     ["yazılım"],
    "engineering":  ["mühendisliği", "mühendislik"],
    "computer":     ["bilgisayar"],
    "science":      ["bilim"],
    "introduction": ["giriş"],
    "electronics":  ["elektronik"],
    "statistics":   ["istatistik", "olasılık"],
    "probability":  ["olasılık"],
    "linear":       ["lineer", "doğrusal"],
    "algebra":      ["cebir"],
    "discrete":     ["ayrık"],
    "artificial":   ["yapay"],
    "intelligence": ["zeka"],
    "machine":      ["makine"],
    "learning":     ["öğrenme"],
    "elective":     ["seçmeli"],
    "faculty":      ["fakülte"],
    "department":   ["bölüm", "bölümü", "bölümünde"],
    "contact":      ["iletişim"],
    "address":      ["adres"],
    "phone":        ["telefon"],
    "campus":       ["kampüs"],
    "semester":     ["dönem", "yarıyıl"],
    "credit":       ["kredi", "ects"],
    "internship":   ["staj"],
    "thesis":       ["tez", "bitirme"],
    "graduation":   ["mezuniyet"],
    "project":      ["proje"],
}


def _expand_query_to_turkish(query: str) -> str:
    added: list[str] = []
    lower = query.lower()
    for en_word, tr_words in EN_TR_KEYWORDS.items():
        if re.search(rf'\b{re.escape(en_word)}\b', lower):
            added.extend(tr_words)

    if added:
        return f"{query} {' '.join(dict.fromkeys(added))}"
    return query


SYSTEM_PROMPT = "Answer in the student's language. Use only the provided courses list."


def _build_context_text(user_message: str) -> str:
    """
    Use Mirket07's retrieval pipeline to fetch relevant data.
    The query is first expanded with Turkish keywords so that English
    questions can still find Turkish course names.
    Falls back gracefully on errors.
    """
    search_query = _expand_query_to_turkish(user_message)
    logger.debug(f"Expanded query: {search_query}")

    try:
        context = get_retrieval_context(search_query, search_method='hybrid')
        logger.debug(f"Retrieved context: {len(context.get('courses', []))} courses, "
                    f"{len(context.get('departments', []))} departments, "
                    f"{len(context.get('university_info', []))} info items")
    except Exception as exc:
        logger.warning("Primary retrieval failed (%s). Trying fallback.", exc)
        try:
            courses = retrieve_courses_hybrid(search_query, limit=50)
            uni_info = retrieve_university_info(search_query, limit=5)
            context = {
                'courses': courses,
                'departments': [],
                'university_info': uni_info,
                'faculties': [],
            }
            logger.debug(f"Fallback retrieval succeeded: {len(courses)} courses, {len(uni_info)} info items")
        except Exception as inner_exc:
            logger.error("Fallback retrieval also failed (%s).", inner_exc)
            context = {
                'courses': [],
                'departments': [],
                'university_info': [],
                'faculties': [],
            }


    total = (len(context.get('courses', []))
             + len(context.get('departments', []))
             + len(context.get('university_info', []))
             + len(context.get('faculties', [])))
    if total == 0:
        logger.warning("No context found for query, attempting fallback to contact info")
        try:
            context['university_info'] = list(
                __import__('courses.models', fromlist=['UniversityInfo'])
                .UniversityInfo.objects.filter(category='contact')[:3]
            )
        except Exception:
            pass

    return format_context_for_llm(context)


def _build_prompt(user_message: str, context_text: str,
                  conversation_history: list | None = None) -> str:
    """Build minimal prompt to maximize space for courses."""
    return f"{SYSTEM_PROMPT}\n\nCourses:\n{context_text}\n\nQuestion: {user_message}\n\nAnswer:"



def ask_acubot(user_message: str,
               conversation_history: list | None = None) -> str:

    context_text = _build_context_text(user_message)
    prompt = _build_prompt(user_message, context_text, conversation_history)

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.5,
            "top_p": 0.9,
            "num_predict": 8192,
        },
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)

        if response.status_code == 200:
            data = response.json()
            return data.get("response", "").strip()
        else:
            logger.error("Ollama returned status %s: %s",
                         response.status_code, response.text[:300])
            return (
                "The AI server returned an error. "
                f"Status Code: {response.status_code}"
            )

    except requests.exceptions.ConnectionError:
        return (
            "I can't connect to my brain (Qwen model) right now. "
            "The model might still be downloading, or there's a Docker "
            "network issue."
        )
    except requests.exceptions.Timeout:
        return (
            "The AI model took too long to respond. "
            "Please try again in a moment."
        )
    except requests.exceptions.RequestException as exc:
        logger.error("Ollama request failed: %s", exc)
        return (
            "An unexpected error occurred while communicating with the "
            "AI server. Please try again later."
        )