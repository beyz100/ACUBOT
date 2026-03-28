from django.db import models

class Faculty(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = "Faculties"

    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=255)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='departments')

    def __str__(self):
        return f"{self.name} ({self.faculty.name})"

class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    ects = models.IntegerField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')

    def __str__(self):
        return f"{self.code} - {self.name}"


class UniversityInfo(models.Model):
    CATEGORY_CHOICES = [
        ('contact', 'İletişim Bilgileri'),
        ('navigation', 'Ana Menü / Navigasyon'),
        ('general', 'Genel Bilgi'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    key = models.CharField(max_length=255)
    value = models.TextField()

    class Meta:
        verbose_name = "Üniversite Bilgisi"
        verbose_name_plural = "Üniversite Bilgileri"
        unique_together = ('category', 'key')

    def __str__(self):
        return f"[{self.get_category_display()}] {self.key}: {self.value[:80]}"
