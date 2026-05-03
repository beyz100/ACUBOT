"""Language helpers used across retrieval and prompt building."""
from __future__ import annotations

import re

EN_TO_TR: dict[str, list[str]] = {
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
    "dean": ["dekan"],
    "founder": ["kurucu"],
    "history_of": ["tarihçe"],
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

_TR_TO_EN: dict[str, list[str]] = {}
for en, tr_list in EN_TO_TR.items():
    for tr in tr_list:
        _TR_TO_EN.setdefault(tr, []).append(en)


_TR_CHARS = set("çğıöşüÇĞİÖŞÜ")

_PROPER_NOUNS = (
    "acıbadem", "acibadem", "acu",
    "atatürk", "ataturk",
    "ataşehir", "atasehir", "i̇stanbul", "istanbul",
    "kayışdağı", "kayisdagi", "kerem", "aydınlar", "aydinlar",
)
_PROPER_NOUNS_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(n) for n in _PROPER_NOUNS) + r")\b",
    re.IGNORECASE,
)

_EN_STARTERS = {
    "what", "which", "where", "when", "how", "who", "whose", "whom", "why",
    "is", "are", "was", "were", "am", "be", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "can", "could", "would", "should", "may", "might", "must", "shall", "will",
    "tell", "list", "show", "give", "provide", "explain", "describe",
    "i", "we", "you", "they", "he", "she", "it",
}

_TR_WORDS = {
    "merhaba", "selam", "evet", "hayır", "lütfen", "teşekkür", "teşekkürler",
    "nedir", "nerede", "nereden", "nasıl", "hangi", "kimdir", "neyin",
    "mı", "mi", "mu", "mü", "değil",
    "var", "yok", "için", "ile",
    "üniversite", "üniversitesi", "üniversitesinde",
    "fakülte", "fakültesi", "fakülteleri",
    "bölüm", "bölümü", "bölümünde", "bölümleri",
    "ders", "dersi", "dersler", "dersleri",
    "öğrenci", "öğretim", "kayıt", "burs",
}

_EN_WORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "from",
    "by", "and", "or", "but", "if", "as", "that", "this", "these", "those",
    "university", "faculty", "department", "course", "courses", "student",
    "address", "phone", "campus", "contact",
}


def _word_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b[\wçğıöşüÇĞİÖŞÜ]+\b", text.lower()))


def detect_language(text: str) -> str:
    """Detect language from user input.
    
    Turkish has special characters (ç, ğ, ı, ö, ş, ü) and specific words.
    English queries typically start with question words or auxiliaries.
    """
    if not text:
        return "en"

    lower = text.strip().lower()

    first_match = re.match(r"[\wçğıöşüÇĞİÖŞÜ]+", lower)
    first_token = first_match.group(0) if first_match else ""
    if first_token in _TR_WORDS:
        return "tr"
    if first_token in _EN_STARTERS:
        return "en"

    cleaned = _PROPER_NOUNS_RE.sub(" ", lower)
    tr_char_count = sum(1 for ch in cleaned if ch in _TR_CHARS)

    tokens = _word_tokens(cleaned)
    tr_word_count = len(tokens & _TR_WORDS)
    en_word_count = len(tokens & _EN_WORDS)

    # Heavily weight Turkish characters and English words at start
    tr_score = tr_char_count * 2 + tr_word_count * 3
    en_score = en_word_count * 2
    
    # If more than 30% of words are detected English, default to English
    total_words = len(tokens)
    if total_words > 0 and en_word_count / total_words > 0.3:
        return "en"
    
    if tr_score == 0 and en_score == 0:
        return "en"
    return "tr" if tr_score > en_score else "en"


def expand_query(query: str) -> str:
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
    seen: set[str] = set()
    deduped: list[str] = []
    for term in extras:
        if term not in seen:
            seen.add(term)
            deduped.append(term)
    return f"{query} {' '.join(deduped)}"
