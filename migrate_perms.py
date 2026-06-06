import sys
import django
import os

from crypto_access.models import UserType, AccessPolicy

prefix_to_res = {
    'file_': 'document',
    'key_': 'key',
    'policy_': 'policy',
    'user_': 'user',
    'attribute_': 'attribute',
    'logs_': 'audit'
}

print("Starting data migration...")

for ut in UserType.objects.all():
    perms = ut.permissions or []
    if not perms:
        continue
        
    res_actions = {}
    
    for perm in perms:
        if perm == '*':
            if '*' not in res_actions:
                res_actions['*'] = set()
            res_actions['*'].add('*')
            continue
            
        found = False
        for prefix, res in prefix_to_res.items():
            if perm.startswith(prefix):
                action = perm[len(prefix):]
                if res not in res_actions:
                    res_actions[res] = set()
                res_actions[res].add(action)
                found = True
                break
        
        if not found:
            print(f"Skipping unknown perm {perm} for {ut.code}")
            
    if res_actions:
        print(f"Creating policies for {ut.code}...")
        for res, actions in res_actions.items():
            action_str = ",".join(actions)
            # Check if exists
            policy_name = f"Auto: {ut.name} ({res})"[:50]
            condition = f"r.sub.user_type == '{ut.code}'"
            if not AccessPolicy.objects.filter(subject_condition=condition, resource=res, effect='allow').exists():
                AccessPolicy.objects.create(
                    name=policy_name,
                    description=f"Auto migrated from UserType {ut.code}",
                    subject_condition=condition,
                    resource=res,
                    action=action_str,
                    effect='allow',
                    is_active=True,
                    priority=10
                )
                print(f"  Created: {res} -> {action_str}")
            else:
                print(f"  Skipped (already exists): {res}")

print("Data migration completed.")
