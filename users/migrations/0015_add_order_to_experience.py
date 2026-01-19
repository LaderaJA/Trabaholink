# Generated manually for Experience order field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_add_title_to_experience'),
    ]

    operations = [
        migrations.AddField(
            model_name='experience',
            name='order',
            field=models.IntegerField(default=0, help_text='Display order (lower numbers appear first)'),
        ),
        migrations.AlterModelOptions(
            name='experience',
            options={'ordering': ['order', '-year_ended']},
        ),
    ]
