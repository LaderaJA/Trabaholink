# Generated manually for Experience model changes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_add_order_to_education'),
    ]

    operations = [
        migrations.AddField(
            model_name='experience',
            name='year_ended',
            field=models.CharField(
                blank=True,
                help_text="Year ended or 'Present' if currently working",
                max_length=10,
                null=True
            ),
        ),
        
        # Make start_date and end_date nullable for backward compatibility
        migrations.AlterField(
            model_name='experience',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='experience',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
