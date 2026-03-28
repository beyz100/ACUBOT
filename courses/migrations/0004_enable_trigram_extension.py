from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0003_universityinfo'),
    ]

    operations = [
        TrigramExtension(),
    ]

