# Generated manually for video field addition
from django.db import migrations, models
import jobs.validators


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0020_merge_20260104_1031'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobprogress',
            name='video',
            field=models.FileField(blank=True, help_text='Optional progress video (max 30 seconds, 25MB)', null=True, upload_to='progress_videos/', validators=[jobs.validators.validate_video_file]),
        ),
    ]
