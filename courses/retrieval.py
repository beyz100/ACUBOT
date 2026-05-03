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
    residual = query
    for entity in (dept, fac):
        if not entity:
            continue
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

_TOPIC_FILLER_WORDS: set[str] = {
    "ders", "dersi", "dersler", "dersleri",
    "course", "courses", "class", "classes",
    "bölüm", "bölümü", "bölümünde", "bölümündeki", "bölümleri",
    "department", "departments",
    "fakülte", "fakültesi", "fakültesinde", "fakülteleri",
    "faculty", "faculties",
    "müfredat", "müfredatı", "curriculum", "katalog", "kataloğu",
    "program", "programı", "programları",
    "tüm", "bütün", "hepsi", "all", "every", "any",
    "list", "show", "give", "tell",
    "neler", "ne", "nedir", "hangi", "kaç", "what", "which", "are", "is", "there",
    "var", "mı", "mi", "mu", "mü", "ile", "için",
    "the", "a", "an", "of", "in", "at", "on", "to",
}


def _detect_semesters(query: str) -> set[int] | None:
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
    base = Course.objects.select_related("department__faculty")
    if department is not None:
        base = base.filter(department=department)
    elif faculty is not None:
        base = base.filter(department__faculty=faculty)

    exclude_keywords = [
        'seçmeli', 'secmeli', 'elective',
        'staj', 'internship',
        'mezuniyet', 'graduation',
        'seminer', 'seminar',
    ]
    exclude_q = Q()
    for keyword in exclude_keywords:
        exclude_q |= Q(name__icontains=keyword)
    base = base.exclude(exclude_q)

    semesters = _detect_semesters(query)
    if semesters is not None:
        base = base.filter(semester__in=semesters)

    expanded = expand_query(query)
    residual = _residual_query(query, department, faculty)
    residual_tokens = set(re.findall(r"\w+", residual.lower()))
    non_filler = residual_tokens - _TOPIC_FILLER_WORDS
    has_topical = bool(non_filler)

    if (department is not None or faculty is not None) and not has_topical:
        return list(base.order_by("semester", "code")[:limit])
    if semesters is not None:
        return list(base.order_by("semester", "code")[:limit])

    full_text_query = expand_query(residual) if has_topical else expanded
    full_text = _course_full_text(full_text_query, base, limit * 2)
    trigram = _course_trigram(residual or query, base, limit * 2)
    merged = _merge_courses(full_text, trigram, limit)

    if not merged and (department is not None or faculty is not None):
        return list(base.order_by("semester", "code")[:limit])
    return merged


def _retrieve_university_info(query: str, limit: int) -> list[UniversityInfo]:
    if not query:
        return []
    expanded = expand_query(query)

    lower = query.lower()
    intent_categories = {
        cat for word, cat in INTENT_TO_INFO_CATEGORY.items() if word in lower
    }
    intent_matches: list[UniversityInfo] = []
    if intent_categories:
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

    fuzzy_matches = list(
        UniversityInfo.objects.annotate(
            key_sim=TrigramSimilarity("key", expanded),
            val_sim=TrigramSimilarity("value", expanded),
            kw_sim=TrigramSimilarity("keywords", expanded),
        )
        .filter(Q(key_sim__gt=0.15) | Q(val_sim__gt=0.12) | Q(kw_sim__gt=0.15))
        .order_by("-key_sim", "-kw_sim", "-val_sim")[: limit * 2]
    )

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
    "fakulte", "fakulteler", "fakulteleri",
}
_LIST_ALL_DEPARTMENT_HINTS = {
    "department", "departments",
    "bölüm", "bölümler", "bölümleri",
    "bolum", "bolumler", "bolumleri",
    "program", "programs", "programlar", "programları", "programlari",
}


def _wants_full_list(query: str, hints: set[str]) -> bool:
    lower = query.lower()
    return any(h in lower for h in hints)


def retrieve(query: str) -> RetrievalResult:
    department = _detect_department(query)
    faculty = _detect_faculty(query) if department is None else department.faculty

    courses = _retrieve_courses(query, department, faculty, limit=150)

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
    if result.is_empty():
        if language == "tr":
            return "BİLGİ TABANI BOŞ. (DİKKAT: Kullanıcıya SADECE şu cümleyi kur: 'Üniversitemizde bu bölüm/fakülte bulunmamaktadır veya bu konuda elimde bilgi yok. Web sitemizi kontrol edebilirsiniz.')"
        return "KNOWLEDGE BASE IS EMPTY. (WARNING: Tell the user ONLY this: 'We do not have this department/faculty, or I don't have that information. Please check our website.')"



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
        course_groups: dict[str, list[tuple[int, Course]]] = {}

        for c in result.courses:
            name_match = re.match(r'^(.+?)\s+([12])$', c.name.strip())
            if name_match:
                base_name = name_match.group(1)
                part_num = int(name_match.group(2))
            else:
                base_name = c.name
                part_num = 0

            if base_name not in course_groups:
                course_groups[base_name] = []
            course_groups[base_name].append((part_num, c))

        for base_name in sorted(course_groups.keys()):
            group = course_groups[base_name]

            has_part_1 = any(p == 1 for p, _ in group)
            has_part_2 = any(p == 2 for p, _ in group)

            if len(group) == 2 and has_part_1 and has_part_2:
                c1 = next(c for p, c in group if p == 1)
                c2 = next(c for p, c in group if p == 2)

                row = f"- {c1.code}/{c2.code} {base_name} 1-2"
                if c1.name_en or c2.name_en:
                    en_name = c1.name_en or c2.name_en
                    row += f" / {en_name}"

                ects_str = f"{c1.ects}" if c1.ects else ""
                if c2.ects and c1.ects and c1.ects != c2.ects:
                    ects_str = f"{c1.ects}+{c2.ects}"

                extras: list[str] = []
                if ects_str:
                    extras.append(f"{ects_str} ECTS")
                if c1.semester:
                    extras.append(f"semester {c1.semester}")
                extras.append(f"dept: {c1.department.name}")
                row += f" ({', '.join(extras)})"
                rows.append(row)
            else:
                for part_num, c in sorted(group, key=lambda x: x[0] if x[0] > 0 else 999):
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
