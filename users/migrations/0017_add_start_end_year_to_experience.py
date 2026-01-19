# Generated manually for Experience start_year and end_year fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_add_start_end_year_to_education'),
    ]

    operations = [
        migrations.AddField(
            model_name='experience',
            name='start_year',
            field=models.CharField(
                blank=True,
                help_text="Year started",
                max_length=10,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='experience',
            name='end_year',
            field=models.CharField(
                blank=True,
                help_text="Year ended or 'Present' if currently working",
                max_length=10,
                null=True
            ),
        ),
        migrations.AlterModelOptions(
            name='experience',
            options={'ordering': ['order', '-end_year', '-start_year']},
        ),
    ]
