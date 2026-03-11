# Generated manually for Education start_year and end_year fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_add_order_to_experience'),
    ]

    operations = [
        migrations.AddField(
            model_name='education',
            name='start_year',
            field=models.CharField(
                blank=True,
                help_text="Year started",
                max_length=10,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='education',
            name='end_year',
            field=models.CharField(
                blank=True,
                help_text="Year ended or 'Present' if currently studying",
                max_length=10,
                null=True
            ),
        ),
        migrations.AlterModelOptions(
            name='education',
            options={'ordering': ['order', '-end_year', '-start_year']},
        ),
    ]
