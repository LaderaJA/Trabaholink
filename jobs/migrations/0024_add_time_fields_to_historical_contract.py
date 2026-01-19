# Generated migration to fix missing time fields in HistoricalContract

from django.db import migrations, models


def check_and_add_time_fields(apps, schema_editor):
    """Add time fields only if they don't exist"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='jobs_historicalcontract' 
            AND column_name IN ('start_time', 'end_time')
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        
        # Add start_time if it doesn't exist
        if 'start_time' not in existing_columns:
            cursor.execute("""
                ALTER TABLE jobs_historicalcontract 
                ADD COLUMN start_time TIME NULL
            """)
        
        # Add end_time if it doesn't exist
        if 'end_time' not in existing_columns:
            cursor.execute("""
                ALTER TABLE jobs_historicalcontract 
                ADD COLUMN end_time TIME NULL
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0023_merge_20260114_1943'),
    ]

    operations = [
        migrations.RunPython(check_and_add_time_fields, migrations.RunPython.noop),
    ]
