from django.core.management.base import BaseCommand
from courses.retrieval import (
    get_retrieval_context,
    format_context_for_llm,
    retrieve_courses_full_text,
    retrieve_courses_trigram,
    retrieve_courses_hybrid
)


class Command(BaseCommand):
    help = 'Test full-text search retrieval functions'

    def add_arguments(self, parser):
        parser.add_argument('query', type=str, help='Search query')
        parser.add_argument(
            '--method',
            type=str,
            default='hybrid',
            choices=['hybrid', 'full_text', 'trigram', 'all'],
            help='Search method to use'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of results'
        )
        parser.add_argument(
            '--format',
            action='store_true',
            help='Show formatted context for LLM'
        )

    def handle(self, *args, **options):
        query = options['query']
        method = options['method']
        limit = options['limit']
        show_format = options['format']

        self.stdout.write(
            self.style.SUCCESS(f"\n{'='*70}\n")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Search Query: {query}\n")
        )
        self.stdout.write(
            self.style.SUCCESS(f"{'='*70}\n")
        )

        if method == 'all':
            methods = ['hybrid', 'full_text', 'trigram']
        else:
            methods = [method]

        for m in methods:
            self._search_with_method(query, m, limit)

        if show_format:
            self._show_formatted_context(query)

    def _search_with_method(self, query, method, limit):
        self.stdout.write(f"\n--- {method.upper()} Search ---\n")

        if method == 'hybrid':
            courses = retrieve_courses_hybrid(query, limit=limit)
        elif method == 'full_text':
            courses = retrieve_courses_full_text(query, limit=limit)
        elif method == 'trigram':
            courses = retrieve_courses_trigram(query, limit=limit)
        else:
            courses = []

        if not courses:
            self.stdout.write(
                self.style.WARNING(f"No results found for {method} search")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(courses)} course(s):\n")
        )

        for idx, course in enumerate(courses, 1):
            self.stdout.write(f"{idx}. {course.code} - {course.name}")
            self.stdout.write(f"   ECTS: {course.ects}")
            self.stdout.write(f"   Department: {course.department.name}")
            self.stdout.write(f"   Faculty: {course.department.faculty.name}\n")

    def _show_formatted_context(self, query):
        self.stdout.write(f"\n{'='*70}\n")
        self.stdout.write(
            self.style.SUCCESS("Formatted Context for LLM:\n")
        )
        self.stdout.write(f"{'='*70}\n")

        context = get_retrieval_context(query, search_method='hybrid')
        formatted = format_context_for_llm(context)

        self.stdout.write(formatted)

