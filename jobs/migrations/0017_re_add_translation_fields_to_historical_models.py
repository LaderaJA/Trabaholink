# Generated migration to re-add translation fields to historical models
# These were removed by migration 0016 but are required by modeltranslation
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0016_remove_historicalcontract_job_description_en_and_more'),
    ]

    operations = [
        # Re-add translation fields to HistoricalJob
        migrations.AddField(
            model_name='historicaljob',
            name='title_en',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='historicaljob',
            name='title_tl',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='historicaljob',
            name='description_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljob',
            name='description_tl',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljob',
            name='tasks_en',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='historicaljob',
            name='tasks_tl',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='historicaljob',
            name='required_skills_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljob',
            name='required_skills_tl',
            field=models.TextField(blank=True, null=True),
        ),
        
        # Re-add translation fields to HistoricalContract
        migrations.AddField(
            model_name='historicalcontract',
            name='job_title_en',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='job_title_tl',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='job_description_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='job_description_tl',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='terms_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='terms_tl',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='notes_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='notes_tl',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='termination_reason_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='termination_reason_tl',
            field=models.TextField(blank=True, null=True),
        ),
        
        # Re-add translation fields to HistoricalJobApplication
        migrations.AddField(
            model_name='historicaljobapplication',
            name='message_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljobapplication',
            name='message_tl',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljobapplication',
            name='cover_letter_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljobapplication',
            name='cover_letter_tl',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljobapplication',
            name='experience_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljobapplication',
            name='experience_tl',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljobapplication',
            name='certifications_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljobapplication',
            name='certifications_tl',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljobapplication',
            name='additional_notes_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicaljobapplication',
            name='additional_notes_tl',
            field=models.TextField(blank=True, null=True),
        ),
    ]
