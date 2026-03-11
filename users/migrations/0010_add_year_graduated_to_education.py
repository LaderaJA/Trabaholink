# Generated manually for Education model changes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_notificationpreference'),
    ]

    operations = [
        # Add year_graduated field
        migrations.AddField(
            model_name='education',
            name='year_graduated',
            field=models.CharField(
                blank=True, 
                help_text="Year graduated or 'Present' if currently studying", 
                max_length=10, 
                null=True
            ),
        ),
        
        # Make start_date and end_date nullable for backward compatibility
        migrations.AlterField(
            model_name='education',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='education',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
        
        # Add Meta ordering
        migrations.AlterModelOptions(
            name='education',
            options={'ordering': ['-year_graduated']},
        ),
    ]
