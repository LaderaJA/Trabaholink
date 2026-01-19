# Generated manually for Education title field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_add_year_graduated_to_education'),
    ]

    operations = [
        migrations.AddField(
            model_name='education',
            name='title',
            field=models.CharField(
                blank=True,
                help_text="Custom title for this education entry (e.g., 'Bachelor's Degree', 'High School')",
                max_length=100
            ),
        ),
    ]
