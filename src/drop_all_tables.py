import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

with connection.cursor() as cursor:
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"Dropping table {table[0]}...")
        cursor.execute(f"DROP TABLE IF EXISTS \"{table[0]}\" CASCADE")
print("All tables dropped.")
