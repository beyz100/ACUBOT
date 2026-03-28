from django.db import migrations, models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0004_enable_trigram_extension'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='course',
            index=GinIndex(
                fields=['name', 'code'],
                opclasses=['gin_trgm_ops', 'gin_trgm_ops'],
                name='course_search_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='department',
            index=GinIndex(
                fields=['name'],
                opclasses=['gin_trgm_ops'],
                name='department_search_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='universityinfo',
            index=GinIndex(
                fields=['key', 'value'],
                opclasses=['gin_trgm_ops', 'gin_trgm_ops'],
                name='universityinfo_search_idx',
            ),
        ),
    ]

