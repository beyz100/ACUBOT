from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0006_remove_course_course_search_idx_and_more'),
    ]

    operations = [
        # --- Faculty: bilingual + description + website ---
        migrations.AddField(
            model_name='faculty',
            name='name_en',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='faculty',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='faculty',
            name='website',
            field=models.URLField(blank=True),
        ),
        migrations.AlterModelOptions(
            name='faculty',
            options={'ordering': ['name'], 'verbose_name_plural': 'Faculties'},
        ),

        # --- Department: bilingual + description + program URL + (faculty,name) unique ---
        migrations.AddField(
            model_name='department',
            name='name_en',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='department',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='department',
            name='program_url',
            field=models.URLField(blank=True),
        ),
        migrations.AlterModelOptions(
            name='department',
            options={'ordering': ['name']},
        ),
        migrations.AlterUniqueTogether(
            name='department',
            unique_together={('faculty', 'name')},
        ),

        # --- Course: bilingual + semester + description; relax unique code ---
        migrations.AlterField(
            model_name='course',
            name='code',
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name='course',
            name='ects',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='course',
            name='name_en',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='course',
            name='semester',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterModelOptions(
            name='course',
            options={'ordering': ['code']},
        ),
        migrations.AlterUniqueTogether(
            name='course',
            unique_together={('department', 'code')},
        ),

        # --- UniversityInfo: keywords + extended categories ---
        migrations.AddField(
            model_name='universityinfo',
            name='keywords',
            field=models.TextField(
                blank=True,
                help_text='Comma-separated synonyms (TR/EN) used to boost search recall.',
            ),
        ),
        migrations.AlterField(
            model_name='universityinfo',
            name='category',
            field=models.CharField(
                choices=[
                    ('contact', 'Contact Information'),
                    ('admission', 'Admission'),
                    ('campus', 'Campus Life'),
                    ('academic', 'Academic / General'),
                    ('faq', 'Frequently Asked Question'),
                    ('navigation', 'Ana Menü / Navigasyon'),
                    ('general', 'Genel Bilgi'),
                ],
                max_length=50,
            ),
        ),
        migrations.AlterModelOptions(
            name='universityinfo',
            options={
                'ordering': ['category', 'key'],
                'verbose_name': 'University Info',
                'verbose_name_plural': 'University Info',
            },
        ),
    ]
