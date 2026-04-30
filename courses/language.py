"""Language helpers used across retrieval and prompt building."""
from __future__ import annotations

import re

# Bidirectional Turkish ↔ English keyword map. Used for two purposes:
#   1) Search-query expansion (so an English question still matches the
#      Turkish data in the database).
#   2) UniversityInfo recall (matching "telephone" → category 'contact').
#
# Keys are lower-case, ASCII-folded English terms. Values are the Turkish
# synonyms a question might use. The reverse direction is built lazily.
EN_TO_TR: dict[str, list[str]] = {
    # general academic vocabulary
    "course": ["ders"],
    "courses": ["ders", "dersler", "dersleri"],
    "elective": ["seçmeli"],
    "electives": ["seçmeli", "seçmeliler"],
    "mandatory": ["zorunlu"],
    "credit": ["kredi"],
    "ects": ["ects", "kredi"],
    "semester": ["dönem", "yarıyıl"],
    "year": ["yıl", "sınıf"],
    "department": ["bölüm", "bölümü", "bölümünde"],
    "faculty": ["fakülte", "fakültesi"],
    "program": ["program", "programı"],
    "curriculum": ["müfredat"],
    "internship": ["staj"],
    "thesis": ["tez", "bitirme"],
    "graduation": ["mezuniyet"],
    "project": ["proje"],
    "lecture": ["ders"],
    "lab": ["laboratuvar", "laboratuar"],
    # subjects
    "programming": ["programlama"],
    "algorithm": ["algoritma", "algoritmalar"],
    "algorithms": ["algoritma", "algoritmalar"],
    "math": ["matematik"],
    "mathematics": ["matematik"],
    "calculus": ["kalkülüs"],
    "physics": ["fizik"],
    "chemistry": ["kimya"],
    "biology": ["biyoloji"],
    "english": ["i̇ngilizce", "ingilizce"],
    "turkish": ["türk", "türkçe"],
    "history": ["tarih", "i̇nkılap", "inkılap"],
    "data": ["veri"],
    "database": ["veritabanı"],
    "databases": ["veritabanı"],
    "web": ["web"],
    "network": ["ağ", "ağlar"],
    "networks": ["ağlar", "ağ"],
    "operating": ["i̇şletim", "işletim"],
    "system": ["sistem"],
    "systems": ["sistem", "sistemler"],
    "software": ["yazılım"],
    "engineering": ["mühendisliği", "mühendislik"],
    "computer": ["bilgisayar"],
    "science": ["bilim"],
    "introduction": ["giriş"],
    "electronics": ["elektronik"],
    "statistics": ["istatistik"],
    "probability": ["olasılık"],
    "linear": ["lineer", "doğrusal"],
    "algebra": ["cebir"],
    "discrete": ["ayrık"],
    "artificial": ["yapay"],
    "intelligence": ["zeka"],
    "machine": ["makine"],
    "learning": ["öğrenme"],
    "cloud": ["bulut"],
    "computing": ["bilişim"],
    "architecture": ["mimari", "mimarisi"],
    "ethics": ["etik"],
    "economics": ["ekonomi"],
    "management": ["yönetim", "yönetimi"],
    "design": ["tasarım"],
    "graduation_project": ["bitirme", "tasarım", "projesi"],
    # university / contact
    "phone": ["telefon", "tel"],
    "telephone": ["telefon"],
    "email": ["eposta", "e-posta", "mail"],
    "address": ["adres"],
    "location": ["konum", "yer", "adres"],
    "campus": ["kampüs"],
    "contact": ["iletişim", "iletisim"],
    "admission": ["kayıt", "başvuru", "giriş", "kabul"],
    "tuition": ["ücret", "ücreti", "harç"],
    "fee": ["ücret", "harç"],
    "scholarship": ["burs"],
    "library": ["kütüphane"],
    "dormitory": ["yurt"],
    "transportation": ["ulaşım"],
    "rector": ["rektör"],
    "founder": ["kurucu"],
    "history_of": ["tarihçe"],
    # faculties
    "medicine": ["tıp", "tıbbı"],
    "medical": ["tıp", "tıbbı", "tıbbi"],
    "dentistry": ["diş", "dişçilik", "diş hekimliği"],
    "pharmacy": ["eczacılık"],
    "nursing": ["hemşirelik"],
    "health": ["sağlık", "sağlığı"],
    "biomedical": ["biyomedikal"],
    "industrial": ["endüstri"],
    "molecular": ["moleküler"],
    "psychology": ["psikoloji"],
    "physiotherapy": ["fizyoterapi"],
    "rehabilitation": ["rehabilitasyon"],
    "nutrition": ["beslenme"],
    "dietetics": ["diyetetik"],
}

# Build reverse map (tr → [en synonyms]) once at import time.
_TR_TO_EN: dict[str, list[str]] = {}
for en, tr_list in EN_TO_TR.items():
    for tr in tr_list:
        _TR_TO_EN.setdefault(tr, []).append(en)


# Turkish-only characters; presence of any is a strong signal the text is Turkish.
_TR_CHARS = set("çğıöşüÇĞİÖŞÜ")

# Turkish stop-words / markers used to detect Turkish input that contains no
# Turkish-specific letter (a typed-in-haste "merhaba acu nedir" or "telefon
# nedir"). The set is intentionally tight: only words that are unambiguously
# Turkish AND not proper nouns. Words like "acibadem" or "ders" are excluded
# because they occur in English questions too ("What courses does Acibadem
# University offer?").
_TR_WORDS = {
    # greetings / discourse markers
    "merhaba", "selam", "evet", "hayır", "lütfen", "teşekkür", "teşekkürler",
    # interrogatives / function words
    "nedir", "nerede", "nereden", "nasıl", "hangi", "kimdir", "neyin",
    # particles
    "mı", "mi", "mu", "mü", "değil",
    # very common verbs / connectives
    "var", "yok", "için", "ile",
}


def detect_language(text: str) -> str:
    """Return 'tr' if the text is Turkish, otherwise 'en'.

    The chatbot only formally distinguishes between Turkish and English. Any
    other language is treated as English so the LLM still has a safe default.
    """
    if not text:
        return "en"
    if any(ch in _TR_CHARS for ch in text):
        return "tr"
    tokens = set(re.findall(r"\b[\wçğıöşüÇĞİÖŞÜ]+\b", text.lower()))
    if tokens & _TR_WORDS:
        return "tr"
    return "en"


def expand_query(query: str) -> str:
    """Expand a user query with synonyms in the *other* language.

    The expansion is purely additive — every original token is preserved — and
    is intended to be fed to PostgreSQL full-text/trigram search, never to the
    LLM. This way an English question can still hit Turkish course names and
    vice-versa.
    """
    if not query:
        return query
    lower = query.lower()
    extras: list[str] = []
    for en, tr_list in EN_TO_TR.items():
        if re.search(rf"\b{re.escape(en)}\b", lower):
            extras.extend(tr_list)
    for tr, en_list in _TR_TO_EN.items():
        if re.search(rf"\b{re.escape(tr)}\b", lower):
            extras.extend(en_list)
    if not extras:
        return query
    # de-duplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for term in extras:
        if term not in seen:
            seen.add(term)
            deduped.append(term)
    return f"{query} {' '.join(deduped)}"
