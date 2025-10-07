# core/migrations/0002_add_note_title.py

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='title',
            field=models.CharField(default='Untitled Note', max_length=200),
        ),
    ]