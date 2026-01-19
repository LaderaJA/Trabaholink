# Generated manually for Education order field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_add_title_to_education'),
    ]

    operations = [
        migrations.AddField(
            model_name='education',
            name='order',
            field=models.IntegerField(default=0, help_text='Display order (lower numbers appear first)'),
        ),
        migrations.AlterModelOptions(
            name='education',
            options={'ordering': ['order', '-year_graduated']},
        ),
    ]
