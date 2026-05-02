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


# Turkish-only characters; their presence is a Turkish signal — but a single
# proper noun (e.g. "Acıbadem", "Ataşehir") in an otherwise English sentence
# can fool a naive char check, so the detector also strips known proper nouns
# and weighs Turkish vs English signals.
_TR_CHARS = set("çğıöşüÇĞİÖŞÜ")

# Proper nouns that contain Turkish-specific characters but appear in English
# questions too. They are stripped before the language vote.
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

# Question/imperative starters that strongly indicate English. If the very
# first token of the text is one of these, classify as English regardless of
# any Turkish-flavoured proper nouns later in the sentence.
_EN_STARTERS = {
    "what", "which", "where", "when", "how", "who", "whose", "whom", "why",
    "is", "are", "was", "were", "am", "be", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "can", "could", "would", "should", "may", "might", "must", "shall", "will",
    "tell", "list", "show", "give", "provide", "explain", "describe",
    "i", "we", "you", "they", "he", "she", "it",
}

# Turkish stop-words / markers used to detect Turkish input even when there
# are no Turkish-specific letters. The list is intentionally narrow but also
# includes domain words ("üniversite", "fakülte", "bölüm", "ders") whose
# spelling is unambiguously Turkish — their English equivalents are spelt
# differently ("university", "faculty", ...).
_TR_WORDS = {
    # greetings / discourse markers
    "merhaba", "selam", "evet", "hayır", "lütfen", "teşekkür", "teşekkürler",
    # interrogatives / function words
    "nedir", "nerede", "nereden", "nasıl", "hangi", "kimdir", "neyin",
    # particles
    "mı", "mi", "mu", "mü", "değil",
    # very common verbs / connectives
    "var", "yok", "için", "ile",
    # university-domain Turkish forms
    "üniversite", "üniversitesi", "üniversitesinde",
    "fakülte", "fakültesi", "fakülteleri",
    "bölüm", "bölümü", "bölümünde", "bölümleri",
    "ders", "dersi", "dersler", "dersleri",
    "öğrenci", "öğretim", "kayıt", "burs",
}

# Common English content words; presence boosts the English score.
_EN_WORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "from",
    "by", "and", "or", "but", "if", "as", "that", "this", "these", "those",
    "university", "faculty", "department", "course", "courses", "student",
    "address", "phone", "campus", "contact",
}


def _word_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b[\wçğıöşüÇĞİÖŞÜ]+\b", text.lower()))


def detect_language(text: str) -> str:
    """Return ``'tr'`` if the text is Turkish, otherwise ``'en'``.

    Three-stage decision so a single Turkish-flavoured proper noun (e.g.
    ``"Acıbadem"``) inside an otherwise English sentence does not flip the
    answer language:

      1. **First-token shortcut.** If the leading word is an unmistakable
         English starter (``what``, ``which`` …) or Turkish marker
         (``hangi``, ``nedir`` …), use that.
      2. **Proper-noun aware character count.** Strip the well-known proper
         nouns and *then* count Turkish-specific letters; the remaining tally
         feeds a Turkish-vs-English score.
      3. **Score vote.** TR signals (TR-only chars × 2 + TR words × 3) vs EN
         signals (EN words × 2). The higher score wins; ties resolve to EN.
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

    tr_score = tr_char_count * 2 + tr_word_count * 3
    en_score = en_word_count * 2
    if tr_score == 0 and en_score == 0:
        return "en"
    return "tr" if tr_score > en_score else "en"


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
