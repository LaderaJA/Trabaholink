# Generated manually for report_category field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_delete_bannedword_alter_report_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='report_category',
            field=models.CharField(
                blank=True,
                choices=[
                    ('harassment', 'Harassment or Bullying'),
                    ('scam', 'Scam or Fraud'),
                    ('fake_profile', 'Fake Profile'),
                    ('inappropriate_content', 'Inappropriate Content'),
                    ('spam', 'Spam or Advertising'),
                    ('impersonation', 'Impersonation'),
                    ('other', 'Other Issues'),
                    ('misleading', 'Misleading Information'),
                    ('inappropriate', 'Inappropriate Content'),
                    ('duplicate', 'Duplicate Posting'),
                    ('illegal', 'Illegal Activity'),
                ],
                help_text='Category of the report',
                max_length=50,
                null=True
            ),
        ),
    ]
