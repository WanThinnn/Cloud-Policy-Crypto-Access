import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from crypto_access.models import AccessLog
from django.db import transaction

@transaction.atomic
def update_hashes():
    logs = AccessLog.objects.all().order_by('timestamp', 'id')
    prev_hash = "GENESIS_BLOCK"
    
    for log in logs:
        log.previous_hash = prev_hash
        log.log_hash = log.calculate_hash()
        log.save(update_fields=['previous_hash', 'log_hash'])
        prev_hash = log.log_hash
        
    print(f"Updated hashes for {logs.count()} logs.")

if __name__ == '__main__':
    update_hashes()
