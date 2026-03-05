import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Finalty.settings')
django.setup()

from django.db import connection
with connection.cursor() as cursor:
    # Drop collections
    tables_to_drop = [
        'base_calendlycredentials',
        'base_prefillmapping',
        'base_bookingemailtemplate',
        'base_zohotoken',
        'base_settings',
        'base_smtpsettings',
        'base_profile'
    ]
    
    for table in tables_to_drop:
        try:
            cursor.execute(f"DROP TABLE {table}")
            print(f"Dropped {table}")
        except Exception as e:
            print(f"Could not drop {table}: {e}")

    # Clear migration history for 'base'
    try:
        cursor.execute("DELETE FROM django_migrations WHERE app = 'base'")
        print(f"Cleared migration history for 'base' ({cursor.rowcount} rows)")
    except Exception as e:
        print(f"Could not clear migration history: {e}")
        # Try to see if table exists
        try:
            cursor.execute("SELECT app FROM django_migrations LIMIT 1")
            print("django_migrations exists but DELETE failed")
        except:
             print("django_migrations does not seem to exist")
