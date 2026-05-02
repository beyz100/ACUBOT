"""Hybrid retrieval over the knowledge base.

Strategy:
    1. Detect whether the user mentioned a specific department / faculty.
       If yes, restrict the candidate pool to that department but STILL apply
       any extra topical filter ("web", "math", ...) — previously a department
       match would short-circuit any further topic filtering.
    2. Run two parallel searches (full-text + trigram) and merge by score.
    3. Look up `UniversityInfo` rows using both trigram similarity and a
       category hint derived from intent words ("contact", "admission", ...)
       so that "telefon numarası" reliably matches `category='contact'`.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.db.models import F, Q

from .language import expand_query
from .models import Course, Department, Faculty, UniversityInfo

logger = logging.getLogger(__name__)


# Maps intent words found in the user's question to the UniversityInfo
# category that almost certainly contains the answer. This is a deterministic
# fallback for cases where trigram similarity is too weak (e.g. "telefon"
# vs. key="phone").
INTENT_TO_INFO_CATEGORY: dict[str, str] = {
    "telefon": "contact", "tel": "contact", "phone": "contact", "telephone": "contact",
    "eposta": "contact", "e-posta": "contact", "email": "contact", "mail": "contact",
    "adres": "contact", "address": "contact", "location": "contact", "konum": "contact",
    "iletişim": "contact", "contact": "contact",
    "kayıt": "admission", "başvuru": "admission", "kabul": "admission",
    "admission": "admission", "apply": "admission", "register": "admission",
    "kontenjan": "admission", "puan": "admission",
    "kampüs": "campus", "campus": "campus", "kütüphane": "campus", "library": "campus",
    "yurt": "campus", "dormitory": "campus", "ulaşım": "campus", "transportation": "campus",
    "yemekhane": "campus", "cafeteria": "campus", "gidilir": "campus", "nasıl": "campus",
    "neresi": "campus", "yön": "campus", "directions": "campus",
    "rektör": "academic", "rector": "academic",
    "kurucu": "academic", "founder": "academic",
    "tarihçe": "academic", "history": "academic",
    "burs": "academic", "scholarship": "academic",
    "ücret": "academic", "tuition": "academic", "fee": "academic", "harç": "academic",
    "başkanı": "academic", "başkan": "academic", "head": "academic", "department head": "academic",
}


@dataclass
class RetrievalResult:
    courses: list[Course] = field(default_factory=list)
    departments: list[Department] = field(default_factory=list)
    faculties: list[Faculty] = field(default_factory=list)
    university_info: list[UniversityInfo] = field(default_factory=list)
    matched_department: Department | None = None
    matched_faculty: Faculty | None = None

    def is_empty(self) -> bool:
        return not (
            self.courses
            or self.departments
            or self.faculties
            or self.university_info
        )

    def total(self) -> int:
        return (
            len(self.courses)
            + len(self.departments)
            + len(self.faculties)
            + len(self.university_info)
        )


def _best_token_window(query: str, name: str) -> str:
    """Return the contiguous token window of `query` that best matches `name`.

    Long user sentences dilute trigram similarity against short entity names.
    Sliding a window the size of `name`'s token count over the query and
    keeping the highest-overlap span makes detection robust to extra words.
    """
    name_tokens = name.lower().split()
    q_tokens = query.split()
    if len(q_tokens) <= len(name_tokens):
        return query
    name_set = set(name_tokens)
    best_score = -1
    best_span = " ".join(q_tokens[: len(name_tokens)])
    for i in range(len(q_tokens) - len(name_tokens) + 1):
        span_tokens = q_tokens[i : i + len(name_tokens)]
        score = sum(1 for t in span_tokens if t.lower() in name_set)
        if score > best_score:
            best_score = score
            best_span = " ".join(span_tokens)
    return best_span


def _detect_department(query: str) -> Department | None:
    """Return the Department whose name is the closest trigram match to the
    query, scoring against the best-matching token window so long sentences
    do not dilute the similarity below the threshold."""
    if not query.strip():
        return None
    best: tuple[float, Department] | None = None
    for dept in Department.objects.select_related("faculty").all():
        window = _best_token_window(query, dept.name)
        sim = (
            Department.objects.filter(pk=dept.pk)
            .annotate(s=TrigramSimilarity("name", window))
            .values_list("s", flat=True)
            .first()
        ) or 0.0
        if sim > 0.45 and (best is None or sim > best[0]):
            best = (sim, dept)
    return best[1] if best else None


def _detect_faculty(query: str) -> Faculty | None:
    if not query.strip():
        return None
    best: tuple[float, Faculty] | None = None
    for fac in Faculty.objects.all():
        window = _best_token_window(query, fac.name)
        sim = (
            Faculty.objects.filter(pk=fac.pk)
            .annotate(s=TrigramSimilarity("name", window))
            .values_list("s", flat=True)
            .first()
        ) or 0.0
        if sim > 0.45 and (best is None or sim > best[0]):
            best = (sim, fac)
    return best[1] if best else None


def _residual_query(query: str, dept: Department | None, fac: Faculty | None) -> str:
    """Strip the matched department / faculty name from the query so the
    remaining tokens can be used for topical filtering."""
    residual = query
    for entity in (dept, fac):
        if not entity:
            continue
        # Remove the full name and each word longer than 3 chars.
        residual = re.sub(re.escape(entity.name), " ", residual, flags=re.IGNORECASE)
        for token in entity.name.split():
            if len(token) > 3:
                residual = re.sub(re.escape(token), " ", residual, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", residual).strip()


def _course_full_text(query: str, base_qs, limit: int) -> list[Course]:
    if not query:
        return []
    sq = SearchQuery(query, search_type="websearch")
    vector = (
        SearchVector("code", weight="A")
        + SearchVector("name", weight="A")
        + SearchVector("name_en", weight="B")
        + SearchVector("department__name", weight="C")
    )
    return list(
        base_qs.annotate(search=vector, rank=SearchRank(vector, sq))
        .filter(search=sq)
        .order_by("-rank", "code")[:limit]
    )


def _course_trigram(query: str, base_qs, limit: int) -> list[Course]:
    if not query:
        return []
    return list(
        base_qs.annotate(
            name_sim=TrigramSimilarity("name", query),
            code_sim=TrigramSimilarity("code", query),
        )
        .filter(Q(name_sim__gt=0.15) | Q(code_sim__gt=0.20))
        .order_by("-name_sim", "-code_sim", "code")[:limit]
    )


def _merge_courses(
    primary: list[Course], secondary: list[Course], limit: int
) -> list[Course]:
    """Score-merge two ranked course lists, keeping primary order as tie-break."""
    score: dict[int, float] = {}
    rank_a: dict[int, int] = {c.id: i for i, c in enumerate(primary)}
    rank_b: dict[int, int] = {c.id: i for i, c in enumerate(secondary)}
    courses_by_id: dict[int, Course] = {c.id: c for c in primary + secondary}
    for cid in courses_by_id:
        s = 0.0
        if cid in rank_a:
            s += 2.0 * (1.0 - rank_a[cid] / max(len(primary), 1))
        if cid in rank_b:
            s += 1.0 * (1.0 - rank_b[cid] / max(len(secondary), 1))
        score[cid] = s
    ordered_ids = sorted(score, key=lambda i: (-score[i], courses_by_id[i].code))
    return [courses_by_id[i] for i in ordered_ids[:limit]]


_SEMESTER_PATTERNS = [
    (re.compile(r"\b(\d{1,2})\.\s*yar[ıi]y[ıi]l\b", re.IGNORECASE), int),
    (re.compile(r"\b(\d{1,2})\.\s*d[öo]nem\b", re.IGNORECASE), int),
    (re.compile(r"\bsemester\s*(\d{1,2})\b", re.IGNORECASE), int),
]
_SEMESTER_WORD = {
    "birinci": 1, "first": 1, "1st": 1,
    "ikinci": 2, "second": 2, "2nd": 2,
    "üçüncü": 3, "ucuncu": 3, "third": 3, "3rd": 3,
    "dördüncü": 4, "dorduncu": 4, "fourth": 4, "4th": 4,
    "beşinci": 5, "besinci": 5, "fifth": 5, "5th": 5,
    "altıncı": 6, "altinci": 6, "sixth": 6, "6th": 6,
    "yedinci": 7, "seventh": 7, "7th": 7,
    "sekizinci": 8, "eighth": 8, "8th": 8,
}
_FALL_WORDS = {"güz", "guz", "fall"}
_SPRING_WORDS = {"bahar", "spring"}
_FIRST_YEAR_WORDS = {"birinci sınıf", "1. sınıf", "first year", "1st year"}


def _detect_semesters(query: str) -> set[int] | None:
    """Return the set of semester numbers the user is asking about, or None
    if no semester hint is present. Supports '1. yarıyıl', 'semester 2',
    'birinci sınıf güz' (= 1), 'birinci sınıf' (= 1 and 2), etc."""
    lower = query.lower()
    found: set[int] = set()
    for pattern, conv in _SEMESTER_PATTERNS:
        for m in pattern.finditer(lower):
            n = conv(m.group(1))
            if 1 <= n <= 12:
                found.add(n)
    for word, n in _SEMESTER_WORD.items():
        if word in lower and "yarıyıl" in lower or word in lower and "dönem" in lower or word in lower and "semester" in lower:
            found.add(n)

    year_n: int | None = None
    for word, n in _SEMESTER_WORD.items():
        if word in lower and ("sınıf" in lower or "year" in lower):
            year_n = n
            break
    if year_n is not None:
        is_fall = any(w in lower for w in _FALL_WORDS)
        is_spring = any(w in lower for w in _SPRING_WORDS)
        if is_fall:
            found.add(year_n * 2 - 1)
        elif is_spring:
            found.add(year_n * 2)
        else:
            found.update({year_n * 2 - 1, year_n * 2})
    return found or None


def _retrieve_courses(
    query: str,
    department: Department | None,
    faculty: Faculty | None,
    limit: int,
) -> list[Course]:
    """Find the courses most relevant to the query, optionally pre-filtered to
    a department or faculty."""
    base = Course.objects.select_related("department__faculty")
    if department is not None:
        base = base.filter(department=department)
    elif faculty is not None:
        base = base.filter(department__faculty=faculty)

    semesters = _detect_semesters(query)
    if semesters is not None:
        base = base.filter(semester__in=semesters)

    expanded = expand_query(query)
    residual = _residual_query(query, department, faculty)
    has_topical = len(residual) >= 3 and not residual.lower() in {
        "ders", "dersler", "dersleri", "courses", "course",
    }

    # If the user is asking *exclusively* about a department's catalogue and
    # gave no topical hint, return the entire catalogue ordered by code.
    if (department is not None or faculty is not None) and not has_topical:
        return list(base.order_by("semester", "code")[:limit])
    if semesters is not None:
        return list(base.order_by("semester", "code")[:limit])

    full_text_query = expand_query(residual) if has_topical else expanded
    full_text = _course_full_text(full_text_query, base, limit * 2)
    trigram = _course_trigram(residual or query, base, limit * 2)
    merged = _merge_courses(full_text, trigram, limit)

    return merged


def _retrieve_university_info(query: str, limit: int) -> list[UniversityInfo]:
    if not query:
        return []
    expanded = expand_query(query)

    # 1) Intent-based exact category match — most reliable for "phone", etc.
    lower = query.lower()
    intent_categories = {
        cat for word, cat in INTENT_TO_INFO_CATEGORY.items() if word in lower
    }
    intent_matches: list[UniversityInfo] = []
    if intent_categories:
        # Score each row by how many intent words appear in its key/keywords —
        # this surfaces "scholarship" for "burs" instead of letting alphabetic
        # ordering bury it behind unrelated rows in the same category.
        intent_words = {
            word for word in INTENT_TO_INFO_CATEGORY if word in lower
        }
        query_tokens = set(expanded.lower().split())
        scored: list[tuple[int, UniversityInfo]] = []
        for info in UniversityInfo.objects.filter(category__in=intent_categories):
            haystack = (info.key + " " + info.keywords).lower()
            intent_score = sum(1 for w in intent_words if w in haystack)
            overlap_score = sum(1 for w in query_tokens if w in haystack)
            scored.append((intent_score * 10 + overlap_score, info))
        scored.sort(key=lambda t: (-t[0], t[1].key))
        intent_matches = [info for _, info in scored]

    # 2) Fuzzy match against key / value / keywords using trigram similarity.
    fuzzy_matches = list(
        UniversityInfo.objects.annotate(
            key_sim=TrigramSimilarity("key", expanded),
            val_sim=TrigramSimilarity("value", expanded),
            kw_sim=TrigramSimilarity("keywords", expanded),
        )
        .filter(Q(key_sim__gt=0.15) | Q(val_sim__gt=0.12) | Q(kw_sim__gt=0.15))
        .order_by("-key_sim", "-kw_sim", "-val_sim")[: limit * 2]
    )

    # Merge, preferring intent matches first, then fuzzy.
    seen: set[int] = set()
    merged: list[UniversityInfo] = []
    for info in intent_matches + fuzzy_matches:
        if info.id in seen:
            continue
        seen.add(info.id)
        merged.append(info)
        if len(merged) >= limit:
            break
    return merged


def _retrieve_departments(query: str, limit: int) -> list[Department]:
    if not query:
        return []
    expanded = expand_query(query)
    sq = SearchQuery(expanded, search_type="websearch")
    vector = SearchVector("name", weight="A") + SearchVector("name_en", weight="B")
    fts = list(
        Department.objects.annotate(search=vector, rank=SearchRank(vector, sq))
        .filter(search=sq)
        .select_related("faculty")
        .order_by("-rank")[:limit]
    )
    if fts:
        return fts
    return list(
        Department.objects.annotate(sim=TrigramSimilarity("name", expanded))
        .filter(sim__gt=0.20)
        .select_related("faculty")
        .order_by("-sim")[:limit]
    )


def _retrieve_faculties(query: str, limit: int) -> list[Faculty]:
    if not query:
        return []
    expanded = expand_query(query)
    return list(
        Faculty.objects.annotate(sim=TrigramSimilarity("name", expanded))
        .filter(sim__gt=0.20)
        .order_by("-sim")[:limit]
    )


_LIST_ALL_FACULTY_HINTS = {
    "faculty", "faculties",
    "fakülte", "fakülteler", "fakülteleri",
    "fakulte", "fakulteler", "fakulteleri",  # ASCII fallbacks
}
_LIST_ALL_DEPARTMENT_HINTS = {
    "department", "departments",
    "bölüm", "bölümler", "bölümleri",
    "bolum", "bolumler", "bolumleri",  # ASCII fallbacks
    "program", "programs", "programlar", "programları", "programlari",
}


def _wants_full_list(query: str, hints: set[str]) -> bool:
    """Heuristic: did the user ask for *all* of an entity type?"""
    lower = query.lower()
    return any(h in lower for h in hints)


def retrieve(query: str) -> RetrievalResult:
    """Top-level entry point used by the chat service."""
    department = _detect_department(query)
    faculty = _detect_faculty(query) if department is None else department.faculty

    # Limits are intentionally modest so the prompt stays inside the LLM's
    # context window (~4096 tokens for the default 3B model). When the user
    # asks for "all courses of department X" the department-scoping branch
    # already returns the full catalogue, so this cap rarely bites.
    courses = _retrieve_courses(query, department, faculty, limit=50)

    # When the user asks "what faculties" / "list all faculties" we cannot
    # rely on trigram similarity (the literal word "faculties" doesn't match
    # the Turkish faculty names). In that case return EVERY faculty — there
    # are only ~10 rows so the context cost is negligible.
    #
    # We deliberately skip the "list all" expansion when a specific
    # department or faculty was already detected — the user is scoping
    # ("Bilgisayar Mühendisliği bölümündeki ..."), not browsing.
    if faculty is None and _wants_full_list(query, _LIST_ALL_FACULTY_HINTS):
        faculties = list(Faculty.objects.order_by("name"))
    elif faculty is None:
        faculties = _retrieve_faculties(query, limit=2)
    else:
        faculties = []

    if department is None and _wants_full_list(query, _LIST_ALL_DEPARTMENT_HINTS):
        departments = list(
            Department.objects.select_related("faculty").order_by("name")
        )
    elif department is None:
        departments = _retrieve_departments(query, limit=3)
    else:
        departments = []

    university_info = _retrieve_university_info(query, limit=10)

    result = RetrievalResult(
        courses=courses,
        departments=departments,
        faculties=faculties,
        university_info=university_info,
        matched_department=department,
        matched_faculty=faculty if department is None else None,
    )
    logger.info(
        "retrieval | dept=%s fac=%s courses=%d depts=%d facs=%d info=%d",
        department.name if department else "-",
        faculty.name if faculty else "-",
        len(result.courses),
        len(result.departments),
        len(result.faculties),
        len(result.university_info),
    )
    return result


def format_for_llm(result: RetrievalResult, language: str) -> str:
    """Format retrieval output as plain text the LLM can read.

    The output is bilingual-friendly: course rows show the original Turkish
    name plus the English name in parentheses when available, so the model
    can answer in either language without losing fidelity.
    """
    if result.is_empty():
        if language == "tr":
            return "(Bilgi tabanı bu soru için ilgili bir kayıt döndürmedi.)"
        return "(The knowledge base returned no relevant entries for this query.)"

    blocks: list[str] = []

    if result.matched_faculty or result.matched_department:
        scope_lines: list[str] = []
        if result.matched_faculty:
            fac = result.matched_faculty
            line = f"Faculty: {fac.name}"
            if fac.name_en:
                line += f" ({fac.name_en})"
            scope_lines.append(line)
        if result.matched_department:
            dep = result.matched_department
            line = f"Department: {dep.name}"
            if dep.name_en:
                line += f" ({dep.name_en})"
            line += f" — Faculty: {dep.faculty.name}"
            scope_lines.append(line)
        blocks.append("Scope:\n" + "\n".join(scope_lines))

    if result.faculties:
        rows = []
        for fac in result.faculties:
            row = f"- {fac.name}"
            if fac.name_en:
                row += f" / {fac.name_en}"
            if fac.description:
                row += f" — {fac.description}"
            rows.append(row)
        blocks.append("Faculties:\n" + "\n".join(rows))

    if result.departments:
        rows = []
        for dep in result.departments:
            row = f"- {dep.name}"
            if dep.name_en:
                row += f" / {dep.name_en}"
            row += f" (Faculty: {dep.faculty.name})"
            rows.append(row)
        blocks.append("Departments:\n" + "\n".join(rows))

    if result.courses:
        rows = []
        for c in result.courses:
            row = f"- {c.code} {c.name}"
            if c.name_en:
                row += f" / {c.name_en}"
            extras: list[str] = []
            if c.ects:
                extras.append(f"{c.ects} ECTS")
            if c.semester:
                extras.append(f"semester {c.semester}")
            extras.append(f"dept: {c.department.name}")
            row += f" ({', '.join(extras)})"
            rows.append(row)
        blocks.append("Courses:\n" + "\n".join(rows))

    if result.university_info:
        rows = []
        for info in result.university_info:
            rows.append(f"- {info.value}")
        blocks.append("University Info:\n" + "\n".join(rows))

    return "\n\n".join(blocks)
