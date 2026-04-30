from django.db import models


class Faculty(models.Model):
    name = models.CharField(max_length=255, unique=True)
    name_en = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Faculties"

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    program_url = models.URLField(blank=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='departments')

    class Meta:
        ordering = ["name"]
        unique_together = [("faculty", "name")]

    def __str__(self):
        return f"{self.name} ({self.faculty.name})"


class Course(models.Model):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True)
    ects = models.PositiveIntegerField(default=0)
    semester = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')

    class Meta:
        ordering = ["code"]
        unique_together = [("department", "code")]

    def __str__(self):
        return f"{self.code} - {self.name}"


class UniversityInfo(models.Model):
    CATEGORY_CHOICES = [
        ('contact', 'Contact Information'),
        ('admission', 'Admission'),
        ('campus', 'Campus Life'),
        ('academic', 'Academic / General'),
        ('faq', 'Frequently Asked Question'),
        ('navigation', 'Ana Menü / Navigasyon'),
        ('general', 'Genel Bilgi'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    key = models.CharField(max_length=255)
    value = models.TextField()
    keywords = models.TextField(
        blank=True,
        help_text="Comma-separated synonyms (TR/EN) used to boost search recall.",
    )

    class Meta:
        ordering = ["category", "key"]
        verbose_name = "University Info"
        verbose_name_plural = "University Info"
        unique_together = ('category', 'key')

    def __str__(self):
        return f"[{self.get_category_display()}] {self.key}: {self.value[:80]}"
