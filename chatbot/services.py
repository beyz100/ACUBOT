from __future__ import annotations

import re
import requests
import logging
from collections import Counter
from courses.retrieval import (
    get_retrieval_context,
    format_context_for_llm)
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


SYSTEM_PROMPT = """You are an ACUBOT assistant for Acıbadem University. 
- ALWAYS answer in the student's language.
- If the student asks in English, translate the course names and context into English.
- When asked for department courses: 
    - Identify the technical course codes in the context (e.g., CSE for Computer Eng, BME for Biomedical).
    - Prioritize those technical codes. Exclude internships, projects, theses, and electives.
    - Keep answers brief. 
- IMPORTANT: Provide the official course list link ONLY ONCE at the end of your response: https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=04&curSunit=6166#"""


def ask_acubot(user_message: str, _conversation_history: list | None = None) -> str:

    search_query = _expand_query_to_turkish(user_message)
    context = get_retrieval_context(search_query, search_method='hybrid')
    query_lower = user_message.lower()
    if any(k in query_lower for k in ["ders", "course", "bölüm", "department"]):
        context['university_info'] = []

    if context.get('courses'):
        unwanted = ['staj', 'tez', 'bitirme', 'proje', 'genel', 'seçmeli', 'etiği', 'yaz']
        filtered = [
            c for c in context['courses']
            if not any(k in c.name.lower() for k in unwanted)
        ]
        prefixes = [c.code.split(' ')[0] for c in filtered if ' ' in c.code]
        most_common = Counter(prefixes).most_common(1)
        priority_code = most_common[0][0] if most_common else 'XXX'

        def course_priority(c):
            if c.code.upper().startswith(priority_code): return 0
            if any(c.code.upper().startswith(p) for p in ['MAT', 'PHY', 'BME']): return 1
            return 2
        context['courses'] = sorted(filtered, key=course_priority)[:10]

    context_text = format_context_for_llm(context)
    prompt = f"{SYSTEM_PROMPT}\n\nCourses/Context:\n{context_text}\n\nQuestion: {user_message}\n\nAnswer:"

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "top_p": 0.9,
            "num_predict": 1024,
        },
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            logger.error(f"Ollama returned {response.status_code}")
            return "Şu an sunucu kaynaklı bir gecikme yaşıyoruz."



    except Timeout:
        return "Yanıt çok uzun sürdü. Tamamı için: https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=04&curSunit=6166#"
    except ConnectionError:
        return "Sistem bağlantısı kurulamadı."
    except RequestException as e:
        logger.error(f"Ollama request error: {e}")
        return "İşlem sırasında bir hata oluştu."
