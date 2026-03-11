# Generated manually for Experience title field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_add_year_ended_to_experience'),
    ]

    operations = [
        migrations.AddField(
            model_name='experience',
            name='title',
            field=models.CharField(
                blank=True,
                help_text="Custom title for this experience entry",
                max_length=100
            ),
        ),
    ]
