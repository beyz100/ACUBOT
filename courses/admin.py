from django.contrib import admin

from .models import Course, Department, Faculty, UniversityInfo


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'website')
    search_fields = ('name', 'name_en', 'description')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'faculty')
    list_filter = ('faculty',)
    search_fields = ('name', 'name_en', 'description')
    autocomplete_fields = ('faculty',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'name_en', 'ects', 'semester', 'department')
    list_filter = ('department__faculty', 'department', 'semester')
    search_fields = ('code', 'name', 'name_en')
    autocomplete_fields = ('department',)


@admin.register(UniversityInfo)
class UniversityInfoAdmin(admin.ModelAdmin):
    list_display = ('category', 'key', 'short_value')
    list_filter = ('category',)
    search_fields = ('key', 'value', 'keywords')

    @admin.display(description='Value')
    def short_value(self, obj):
        return obj.value if len(obj.value) <= 80 else obj.value[:77] + '...'
