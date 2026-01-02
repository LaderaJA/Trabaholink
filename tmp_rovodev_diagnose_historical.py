#!/usr/bin/env python
"""
Diagnostic script to check HistoricalJob table structure
Run with: docker-compose exec web python manage.py shell < tmp_rovodev_diagnose_historical.py
"""

from django.db import connection

print("=" * 70)
print("CHECKING HISTORICALJOB TABLE STRUCTURE")
print("=" * 70)

with connection.cursor() as cursor:
    # Get all columns from jobs_historicaljob table
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name='jobs_historicaljob' 
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    
    print(f"\nTotal columns in jobs_historicaljob: {len(columns)}")
    print("\nColumn List:")
    print("-" * 70)
    
    translation_fields = []
    for col_name, data_type, nullable in columns:
        print(f"{col_name:40} {data_type:20} NULL={nullable}")
        if col_name.endswith('_en') or col_name.endswith('_tl'):
            translation_fields.append(col_name)
    
    print("\n" + "=" * 70)
    print(f"Translation fields (_en, _tl) found: {len(translation_fields)}")
    print("=" * 70)
    
    if translation_fields:
        print("\n✓ Translation fields exist:")
        for field in translation_fields:
            print(f"  - {field}")
    else:
        print("\n❌ NO translation fields found!")
        print("\nExpected fields:")
        print("  - title_en, title_tl")
        print("  - description_en, description_tl")
        print("  - tasks_en, tasks_tl")
        print("  - required_skills_en, required_skills_tl")
        print("\n⚠️  Migration 0013 may not have been applied correctly!")

print("\n" + "=" * 70)
print("CHECKING MIGRATION STATUS")
print("=" * 70)

from django.db.migrations.recorder import MigrationRecorder
recorder = MigrationRecorder(connection)
applied_migrations = recorder.applied_migrations()

jobs_migrations = [m for m in applied_migrations if m[0] == 'jobs']
jobs_migrations.sort(key=lambda x: x[1])

print(f"\nApplied migrations for 'jobs' app: {len(jobs_migrations)}")
print("\nLast 5 migrations:")
for app, name in jobs_migrations[-5:]:
    print(f"  - {name}")

migration_0013_applied = ('jobs', '0013_add_translation_fields_to_historical_models') in applied_migrations
print(f"\nMigration 0013 applied: {migration_0013_applied}")

if not migration_0013_applied:
    print("\n❌ Migration 0013 has NOT been applied!")
    print("   Run: docker-compose exec web python manage.py migrate jobs")
