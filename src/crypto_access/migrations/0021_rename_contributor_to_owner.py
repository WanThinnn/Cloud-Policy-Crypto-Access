# Standardize: Rename data_contributor -> data_owner

from django.db import migrations

def rename_user_types(apps, schema_editor):
    UserType = apps.get_model('crypto_access', 'UserType')
    
    # Rename data_contributor -> data_owner
    try:
        ut = UserType.objects.get(code='data_contributor')
        ut.code = 'data_owner'
        ut.name = 'Data Owner'
        ut.description = 'Data Owner - Can upload files, create policies, encrypt, and view/download other files'
        ut.save()
    except UserType.DoesNotExist:
        pass

def reverse_rename(apps, schema_editor):
    UserType = apps.get_model('crypto_access', 'UserType')
    
    try:
        ut = UserType.objects.get(code='data_owner')
        ut.code = 'data_contributor'
        ut.name = 'Data Contributor'
        ut.description = 'Data contributor - Can upload files, create policies, encrypt, and view/download other files'
        ut.save()
    except UserType.DoesNotExist:
        pass

class Migration(migrations.Migration):

    dependencies = [
        ("crypto_access", "0020_uploadedfile_file_path_hash_and_more"),
    ]

    operations = [
        migrations.RunPython(rename_user_types, reverse_rename),
    ]
