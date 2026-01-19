# Generated migration to fix missing time fields in HistoricalContract

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0023_merge_20260114_1943'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalcontract',
            name='start_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Start Time'),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='end_time',
            field=models.TimeField(blank=True, null=True, verbose_name='End Time'),
        ),
    ]
