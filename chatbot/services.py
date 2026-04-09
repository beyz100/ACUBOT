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
from requests.exceptions import ConnectionError, Timeout, RequestException


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


SYSTEM_PROMPT = """Answer in the student's language. Use only the provided courses list.
CRITICAL: If the user asks to list all courses or asks a broad question, you MUST list EVERY SINGLE matching course from the provided context. Do NOT abbreviate, summarize, or truncate the list. Do NOT say that you only have some of the courses."""


def _build_context_text(user_message: str) -> str:
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
            "num_predict": 2048,
        },
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=45)

        if response.status_code != 200:
            logger.error(f"Ollama API hata kodu: {response.status_code}")
            return "Şu an sunucu kaynaklı bir gecikme yaşıyoruz. Lütfen kısa süre sonra tekrar deneyin."

        data = response.json()
        return data.get("response", "").strip()

    except Timeout:
        logger.warning("Ollama API yanıt vermedi (Timeout).")
        return "Yanıt çok uzun sürdü. Sunucumuz şu an meşgul, lütfen tekrar deneyin."

    except ConnectionError:
        logger.error("Ollama API bağlantı hatası.")
        return "Sistem bağlantısı şu an kurulamadı. Sunucu servisi durmuş olabilir."

    except RequestException as e:
        logger.critical(f"Beklenmedik bir Request hatası: {str(e)}")
        return "İşlem sırasında beklenmedik bir hata oluştu."
