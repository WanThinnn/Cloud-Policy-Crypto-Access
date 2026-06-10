"""
Storage Views - API endpoints for file operations
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
import uuid
import logging
import hashlib
import json
from django.core.cache import cache
from django.db.models import Q
import tempfile
import os

from ..models import StorageBucket, UploadedFile, FileAccessPolicy, AccessPolicy, FileVersion
from ..serializers import (
    StorageBucketSerializer,
    UploadedFileSerializer,
    FileUploadSerializer,
    SignedUrlRequestSerializer
)
from ..serializers.storage import (
    FileAccessPolicySerializer,
    AssignPolicyToFileSerializer,
    PolicyListForAssignmentSerializer
)
from ..services.storage_service import get_storage_service
from ..services.cpabe_service import cpabe_service
from ..services.casbin_service import casbin_service
import tempfile
import time

def get_db_file_by_path(bucket_name, file_path):
    from crypto_access.models import UploadedFile
    from django.conf import settings
    field_encryption = getattr(settings, 'FIELD_ENCRYPTION', False)
    
    if field_encryption:
        from crypto_access.models.fields import get_encryption_key
        import hmac
        import hashlib
        key = get_encryption_key(info=b"blind_index")
        h = hmac.new(key, str(file_path).encode('utf-8'), hashlib.sha3_256)
        hash_value = h.hexdigest()
        return UploadedFile.objects.filter(bucket__name=bucket_name, file_path_hash=hash_value).first()
    else:
        return UploadedFile.objects.filter(bucket__name=bucket_name, file_path=file_path).first()

logger = logging.getLogger(__name__)


class StorageBucketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing storage buckets
    """
    queryset = StorageBucket.objects.all()
    serializer_class = StorageBucketSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def create_in_supabase(self, request, pk=None):
        """Create bucket in Supabase Storage"""
        bucket = self.get_object()
        storage = get_storage_service()
        
        try:
            result = storage.create_bucket(
                bucket_name=bucket.name,
                public=(bucket.bucket_type == 'public'),
                allowed_mime_types=bucket.allowed_mime_types if bucket.allowed_mime_types else None,
                file_size_limit=bucket.max_file_size
            )
            return Response({
                'message': f"Bucket '{bucket.name}' created in Supabase",
                'result': result
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def list_supabase_buckets(self, request):
        """List all buckets from Supabase"""
        storage = get_storage_service()
        try:
            buckets = storage.list_buckets()
            return Response({'buckets': buckets})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UploadedFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing uploaded files
    """
    queryset = UploadedFile.objects.select_related('bucket', 'uploaded_by').all()
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def _decrypt_file_if_needed(self, file_data, bucket_name, file_path, user, is_owner=False, cpabe_policy_str=None):
        """Helper to decrypt file if it has a CP-ABE policy"""

        if cpabe_policy_str is not None:
            is_encrypted = bool(cpabe_policy_str)
            policies_to_parse = [cpabe_policy_str] if is_encrypted else []
        else:
            file_policies = FileAccessPolicy.get_policies_for_file(bucket_name, file_path)
            is_encrypted = any(p.cpabe_policy for p in file_policies)
            policies_to_parse = [p.cpabe_policy for p in file_policies if p.cpabe_policy]
        
        if not is_encrypted:
            return file_data
            
        user_attrs = casbin_service.get_user_attributes(user)
        
        # CP-ABE Bypass for SuperAdmin and File Owner
        # We mathematically satisfy the policy by extracting required attributes from the policy string
        if user.is_superuser or is_owner:
            import re
            for p_str in policies_to_parse:
                if p_str:
                    tokens = re.findall(r'[a-zA-Z0-9_]+:[a-zA-Z0-9_]+', p_str)
                    for token in tokens:
                        k, v = token.split(':', 1)
                        if k not in user_attrs:
                            user_attrs[k] = []
                        if isinstance(user_attrs[k], list):
                            if v not in user_attrs[k]:
                                user_attrs[k].append(v)
                        else:
                            if user_attrs[k] != v:
                                user_attrs[k] = [user_attrs[k], v]
        
        # Calculate cache key based on attributes
        attrs_str = json.dumps(user_attrs, sort_keys=True)
        attrs_hash = hashlib.sha256(attrs_str.encode('utf-8')).hexdigest()
        cache_key = f"cpabe_key_{user.id}_{attrs_hash}"
        cached_key_data = cache.get(cache_key)
        
        try:
            if not cached_key_data:
                import tempfile
                import os
                # Generate key requires a file output due to C library constraints
                with tempfile.NamedTemporaryFile(delete=False) as f_key:
                    key_name = f_key.name
                
                try:
                    cpabe_service.generate_user_key(user_attrs, key_name)
                    # Read the generated key immediately and delete the file
                    with open(key_name, 'rb') as f:
                        cached_key_data = f.read()
                    
                    # Cache the generated key for 1 hour
                    cache.set(cache_key, cached_key_data, timeout=3600)
                finally:
                    if os.path.exists(key_name):
                        os.remove(key_name)
                    
            try:
                # Decrypt passing the raw bytes directly (No TempFile)
                decrypted_data = cpabe_service.decrypt_buffer(cached_key_data, file_data)
                logger.info(f"CP-ABE Decryption successful for file: {file_path}")
                # We DO NOT cache decrypted_data for security reasons.
                # Decrypted data should strictly reside in RAM during the request life cycle.
                return decrypted_data
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Decryption failed: {error_msg}")
                # If the error is about unsupported format (-7 or 101), the file might actually be plaintext
                if "(-7)" in error_msg or "(-8)" in error_msg or "101" in error_msg or "format" in error_msg.lower():
                    logger.warning("Assuming file is plaintext due to format error. Returning original data.")
                    return file_data
                # Otherwise (e.g. -4 Crypto failed), it is a real decryption failure
                raise Exception("Bạn không có đủ thuộc tính (quyền) để giải mã tài liệu này!")
        except Exception as e:
            raise e
    
    def get_queryset(self):
        """Filter files by user, bucket, and ABAC policies"""
        from crypto_access.models.storage import UploadedFile, StorageBucket, FileAccessPolicy, FileVersion
        from crypto_access.services.casbin_service import casbin_service
        
        queryset = super().get_queryset().filter(is_deleted=False)
        
        # Filter by bucket
        bucket_name = self.request.query_params.get('bucket', None)
        if bucket_name:
            queryset = queryset.filter(bucket__name=bucket_name)
        
        # Filter by file type
        file_type = self.request.query_params.get('type', None)
        if file_type:
            queryset = queryset.filter(file_type=file_type)
            
        # Secure Search by file_name (via Blind Index)
        search_name = self.request.query_params.get('search_name', None)
        if search_name:
            from django.conf import settings
            if getattr(settings, 'FIELD_ENCRYPTION', False):
                from crypto_access.models.fields import get_encryption_key
                import hmac
                import hashlib
                key = get_encryption_key(info=b"blind_index")
                h = hmac.new(key, str(search_name).encode('utf-8'), hashlib.sha3_256)
                hash_value = h.hexdigest()
                queryset = queryset.filter(file_name_hash=hash_value)
            else:
                queryset = queryset.filter(file_name__icontains=search_name)
        
        # Filter by user
        my_files = self.request.query_params.get('my_files', None)
        if my_files and self.request.user.is_authenticated:
            queryset = queryset.filter(uploaded_by=self.request.user)
        
        # ABAC Post-filtering: only return files the user is allowed to see
        if self.request.user.is_authenticated and not self.request.user.is_superuser:
            # Step 1: Pre-evaluate which policies this user satisfies
            allowed_policy_ids = casbin_service.get_allowed_policies_for_user(
                self.request.user, 'read'
            )
            
            # Step 2: Check if user has general read access via ABAC
            has_general_read = casbin_service.check_access(
                self.request.user, 'document', 'read'
            )
            
            # Step 3: Build Q filter conditions
            # Condition A: User is the file owner (always allowed)
            condition = Q(uploaded_by=self.request.user)
            
            # Condition B: File has a policy that matches user's allowed policies
            if allowed_policy_ids:
                condition |= Q(access_policies__policy_id__in=allowed_policy_ids)
            
            # Condition C: File has no policy assigned AND user has general read access
            if has_general_read:
                condition |= Q(access_policies__isnull=True)
            
            queryset = queryset.filter(condition).distinct()
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Upload file to Supabase Storage
        Protected by ABAC middleware - requires 'upload' permission on 'document'
        
        POST /api/files/upload/
        Content-Type: multipart/form-data
        
        Body:
        - file: File to upload
        - bucket_name: Target bucket name
        - file_path: Optional custom path (auto-generated if not provided)
        - description: Optional description
        - tags: Optional tags (JSON array)
        - is_public: Boolean (default: False)
        """
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data['file']
        bucket_name = serializer.validated_data['bucket_name']
        description = serializer.validated_data.get('description', '')
        tags = serializer.validated_data.get('tags', [])
        is_public = serializer.validated_data.get('is_public', False)
        
        # Metadata extraction
        custom_metadata = request.data.get('metadata', '{}')
        if isinstance(custom_metadata, str):
            import json
            try:
                custom_metadata = json.loads(custom_metadata)
            except:
                custom_metadata = {}
        
        # Auto-detect context
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0]
            
        uploader_info = {}
        if request.user.is_authenticated:
            uploader_info['uploader_username'] = request.user.username
            uploader_info['uploader_email'] = request.user.email
            try:
                profile = getattr(request.user, 'profile', None)
                if profile:
                    uploader_info['uploader_name'] = profile.full_name
                    uploader_info['uploader_role'] = profile.get_user_type_code()
            except Exception:
                pass
            
        file_metadata = {
            'original_filename': file.name,
            'client_ip': client_ip,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'upload_source': 'web_api',
            'file_size_bytes': file.size,
            'mime_type': file.content_type,
            **uploader_info,
            **custom_metadata
        }
        policy_id = serializer.validated_data.get('policy_id')
        policy_obj = None
        cpabe_policy_str = None
        
        if serializer.validated_data.get('create_new_policy'):
            policy_obj = AccessPolicy.objects.create(
                name=serializer.validated_data['new_policy_name'],
                description=serializer.validated_data.get('new_policy_description', ''),
                subject_condition=serializer.validated_data['new_policy_subject_condition'],
                resource=serializer.validated_data.get('new_policy_resource', 'document'),
                action=serializer.validated_data.get('new_policy_action', 'read'),
                effect=serializer.validated_data.get('new_policy_effect', 'allow'),
                priority=serializer.validated_data.get('new_policy_priority', 100),
                created_by=request.user if request.user.is_authenticated else None
            )
            cpabe_policy_str = policy_obj.cpabe_policy
            logger.info(f"Created new policy '{policy_obj.name}' during upload")
        elif policy_id:
            try:
                policy_obj = AccessPolicy.objects.get(id=policy_id)
                cpabe_policy_str = policy_obj.cpabe_policy
            except AccessPolicy.DoesNotExist:
                pass
        
        # Get or create bucket
        try:
            bucket = StorageBucket.objects.get(name=bucket_name)
        except StorageBucket.DoesNotExist:
            return Response(
                {'error': f"Bucket '{bucket_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Determine logical file_path
        file_path = serializer.validated_data.get('file_path')
        if not file_path:
            ext = file.name.split('.')[-1] if '.' in file.name else ''
            unique_name = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
            file_path = f"{timezone.now().strftime('%Y/%m/%d')}/{unique_name}"
            
        # Check if file exists for versioning
        from django.conf import settings
        field_encryption = getattr(settings, 'FIELD_ENCRYPTION', False)
        
        if field_encryption:
            from crypto_access.models.fields import get_encryption_key
            import hmac
            import hashlib
            key = get_encryption_key(info=b"blind_index")
            h = hmac.new(key, str(file_path).encode('utf-8'), hashlib.sha3_256)
            hash_value = h.hexdigest()
            existing_file = UploadedFile.objects.filter(bucket=bucket, file_path_hash=hash_value).first()
        else:
            existing_file = UploadedFile.objects.filter(bucket=bucket, file_path=file_path).first()
            
        is_new_version_val = request.data.get('is_new_version', 'false')
        print(f"DEBUG: is_new_version received = {is_new_version_val} (type: {type(is_new_version_val)})")
        is_new_version = str(is_new_version_val).lower() == 'true'
        print(f"DEBUG: is_new_version parsed = {is_new_version}")
        
        version_number = 1
        
        # Obfuscate physical path if encryption is enabled
        parts = file_path.split('/')
        folder_path = '/'.join(parts[:-1]) if len(parts) > 1 else ''
        ext = parts[-1].split('.')[-1] if '.' in parts[-1] else ''
        
        if field_encryption:
            unique_name = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
            physical_path = f"{folder_path}/{unique_name}" if folder_path else unique_name
        else:
            physical_path = file_path
        
        if existing_file:
            if not is_new_version:
                return Response(
                    {'error': 'This file already exists. Please rename the file before uploading a new one, or right-click the existing file and select "Upload New Version".'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            latest_version = existing_file.get_latest_version()
            version_number = (latest_version.version_number + 1) if latest_version else 2
            if not field_encryption:
                physical_path = f"{file_path}_v{version_number}"
        
        # Upload to Supabase
        storage = get_storage_service()
        
        # Check inherited policies from folders if no direct policy_id was provided
        if not cpabe_policy_str:
            inherited_policies = FileAccessPolicy.get_policies_for_file(bucket_name, file_path)
            for p in inherited_policies:
                if p.cpabe_policy:
                    cpabe_policy_str = p.cpabe_policy
                    logger.info(f"Inheriting CP-ABE policy from folder: {cpabe_policy_str}")
                    break
        
        try:
            file_data = file.read()
            
            # Encrypt if policy has cpabe_policy
            if cpabe_policy_str:
                logger.info(f"Encrypting file with CP-ABE policy: {cpabe_policy_str}")
                file_data = cpabe_service.encrypt_buffer(file_data, cpabe_policy_str)

            upload_result = storage.upload_file(
                bucket_name=bucket_name,
                file_path=physical_path,
                file_data=file_data,
                content_type=file.content_type,
                upsert=True
            )
            
            # Get URL (Note: For public files, we use the physical path)
            if bucket.bucket_type == 'public':
                file_url = storage.get_public_url(bucket_name, physical_path)
                signed_url = None
                signed_url_expires_at = None
            else:
                file_url = None
                signed_url = storage.create_signed_url(bucket_name, physical_path, expires_in=3600)
                signed_url_expires_at = timezone.now() + timedelta(seconds=3600)
            
            # Save to database
            if existing_file:
                uploaded_file = existing_file
                uploaded_file.file_size = file.size
                uploaded_file.is_deleted = False
                uploaded_file.deleted_at = None
                
                # Merge existing metadata with new metadata
                if not isinstance(uploaded_file.metadata, dict):
                    uploaded_file.metadata = {}
                uploaded_file.metadata.update(file_metadata)
                
                uploaded_file.save(update_fields=['file_size', 'updated_at', 'is_deleted', 'deleted_at', 'metadata'])
            else:
                uploaded_file = UploadedFile.objects.create(
                    bucket=bucket,
                    file_path=file_path,
                    file_name=file.name,
                    file_type=UploadedFile.detect_file_type(file.content_type),
                    mime_type=file.content_type,
                    file_size=file.size,
                    public_url=file_url,
                    signed_url=signed_url,
                    signed_url_expires_at=signed_url_expires_at,
                    uploaded_by=request.user if request.user.is_authenticated else None,
                    description=description,
                    tags=tags,
                    metadata=file_metadata
                )
            
            # Create FileVersion
            FileVersion.objects.create(
                file=uploaded_file,
                version_number=version_number,
                physical_path=physical_path,
                file_size=file.size,
                cpabe_policy=cpabe_policy_str,
                uploaded_by=request.user if request.user.is_authenticated else None
            )
            
            if policy_obj:
                FileAccessPolicy.objects.create(
                    uploaded_file=uploaded_file,
                    bucket=bucket,
                    target_type='file',
                    policy=policy_obj,
                    assigned_by=request.user
                )
            
            return Response(
                UploadedFileSerializer(uploaded_file).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': f"Upload failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download file from Supabase Storage"""
        uploaded_file = self.get_object()
        storage = get_storage_service()
        version_param = request.query_params.get('version')
        
        try:
            # Determine which version to serve
            if version_param:
                file_version = uploaded_file.versions.filter(version_number=version_param).first()
                if not file_version:
                    return Response({'error': f'Version {version_param} not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                file_version = uploaded_file.get_latest_version()
                
            physical_path = file_version.physical_path if file_version else uploaded_file.file_path
            cpabe_policy_str = file_version.cpabe_policy if file_version else None
            
            file_data = storage.download_file(
                bucket_name=uploaded_file.bucket.name,
                file_path=physical_path
            )
            
            # Check if user is owner
            is_owner = uploaded_file.uploaded_by == request.user
            
            # Decrypt if necessary
            file_data = self._decrypt_file_if_needed(
                file_data, 
                uploaded_file.bucket.name, 
                uploaded_file.file_path, 
                request.user,
                is_owner=is_owner,
                cpabe_policy_str=cpabe_policy_str
            )
            
            response = HttpResponse(file_data, content_type=uploaded_file.mime_type)
            # Add version to filename if not latest
            if version_param and file_version and file_version != uploaded_file.get_latest_version():
                ext = uploaded_file.file_name.split('.')[-1] if '.' in uploaded_file.file_name else ''
                base = uploaded_file.file_name[:-(len(ext)+1)] if ext else uploaded_file.file_name
                file_name = f"{base}_v{version_param}.{ext}" if ext else f"{base}_v{version_param}"
            else:
                file_name = uploaded_file.file_name
                
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
            
        except Exception as e:
            return Response(
                {'error': f"Download failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get version history for a file"""
        uploaded_file = self.get_object()
        
        try:
            # Auto-create v1 for legacy files that have no version records
            if uploaded_file.versions.count() == 0:
                # Try to get existing CP-ABE policy from FileAccessPolicy
                existing_policy = None
                file_policy = uploaded_file.access_policies.first()
                if file_policy and file_policy.policy and file_policy.policy.cpabe_policy:
                    existing_policy = file_policy.policy.cpabe_policy
                    
                FileVersion.objects.create(
                    file=uploaded_file,
                    version_number=1,
                    physical_path=uploaded_file.file_path,
                    file_size=uploaded_file.file_size,
                    cpabe_policy=existing_policy,
                    uploaded_by=uploaded_file.uploaded_by
                )
                logger.info(f"Auto-created v1 FileVersion for legacy file: {uploaded_file.file_name} (id={uploaded_file.id})")
            
            versions = uploaded_file.versions.all().order_by('-version_number')
            result = []
            for v in versions:
                result.append({
                    'version_number': v.version_number,
                    'file_size': v.file_size,
                    'cpabe_policy': v.cpabe_policy,
                    'uploaded_by': v.uploaded_by.username if v.uploaded_by else 'Unknown',
                    'created_at': v.created_at
                })
            return Response({'versions': result})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def create_signed_url(self, request, pk=None):
        """Create a temporary signed URL for private file"""
        uploaded_file = self.get_object()
        
        if uploaded_file.bucket.bucket_type == 'public':
            return Response(
                {'public_url': uploaded_file.public_url},
                status=status.HTTP_200_OK
            )
        
        expires_in = request.data.get('expires_in', 3600)
        storage = get_storage_service()
        
        try:
            signed_url = storage.create_signed_url(
                bucket_name=uploaded_file.bucket.name,
                file_path=uploaded_file.file_path,
                expires_in=expires_in
            )
            
            # Update database
            uploaded_file.signed_url = signed_url
            uploaded_file.signed_url_expires_at = timezone.now() + timedelta(seconds=expires_in)
            uploaded_file.save()
            
            return Response({
                'signed_url': signed_url,
                'expires_at': uploaded_file.signed_url_expires_at,
                'expires_in': expires_in
            })
            
        except Exception as e:
            return Response(
                {'error': f"Failed to create signed URL: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['delete'])
    def delete_from_storage(self, request, pk=None):
        """Soft delete file (move to trash)"""
        uploaded_file = self.get_object()
        
        try:
            # Soft delete in database
            file_name = uploaded_file.file_name
            uploaded_file.is_deleted = True
            uploaded_file.deleted_at = timezone.now()
            uploaded_file.save()
            
            return Response({
                'message': f"File '{file_name}' moved to trash successfully"
            })
            
        except Exception as e:
            return Response(
                {'error': f"Delete failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=False, methods=['get'])
    def trash(self, request):
        """List soft-deleted files (Admin only)"""
        if not request.user.profile.is_admin():
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
        trashed_files = UploadedFile.objects.filter(is_deleted=True).select_related('bucket', 'uploaded_by')
        return Response(UploadedFileSerializer(trashed_files, many=True).data)
        
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore soft-deleted file (Admin only)"""
        if not request.user.profile.is_admin():
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            uploaded_file = UploadedFile.objects.get(pk=pk, is_deleted=True)
            uploaded_file.is_deleted = False
            uploaded_file.deleted_at = None
            uploaded_file.save()
            
            return Response({
                'message': f"File '{uploaded_file.file_name}' restored successfully"
            })
        except UploadedFile.DoesNotExist:
            return Response({'error': 'File not found in trash'}, status=status.HTTP_404_NOT_FOUND)
            
    @action(detail=True, methods=['delete'])
    def hard_delete(self, request, pk=None):
        """Permanently delete file from DB and Supabase (SuperAdmin only)"""
        if not request.user.profile.is_super_admin():
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            uploaded_file = UploadedFile.objects.get(pk=pk, is_deleted=True)
            file_name = uploaded_file.file_name
            # This will trigger post_delete signal to remove from Supabase
            uploaded_file.delete()
            
            return Response({
                'message': f"File '{file_name}' permanently deleted"
            })
        except UploadedFile.DoesNotExist:
            return Response({'error': 'File not found in trash'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get storage statistics"""
        from django.db.models import Sum, Count
        
        user = request.user
        
        size_result = UploadedFile.objects.aggregate(total_size=Sum('file_size'))
        
        stats = {
            'total_files': UploadedFile.objects.count(),
            'my_files': UploadedFile.objects.filter(uploaded_by=user).count() if user.is_authenticated else 0,
            'total_size': size_result['total_size'] or 0,
            'by_type': {}
        }
        
        # Count by file type in a single query
        type_counts = UploadedFile.objects.values('file_type').annotate(count=Count('id'))
        for entry in type_counts:
            stats['by_type'][entry['file_type']] = entry['count']
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def browse(self, request):
        """
        Browse files directly from Supabase storage bucket
        GET /api/storage/files/browse/?path=public
        """
        storage = get_storage_service()
        bucket_name = request.query_params.get('bucket', 'documents')
        path = request.query_params.get('path', '')
        
        try:
            # 1. Get folders from Supabase (to preserve empty folders)
            supabase_items = storage.list_files(
                bucket_name=bucket_name,
                path=path,
                limit=100
            )
            folders = [f for f in supabase_items if f.get('id') is None]
            
            result = []
            for f in folders:
                f_path = f"{path}/{f.get('name', '')}" if path else f.get('name', '')
                result.append({
                    'name': f.get('name', ''),
                    'type': 'folder',
                    'size': None,
                    'id': None,
                    'created_at': f.get('created_at'),
                    'updated_at': f.get('updated_at'),
                    'path': f_path
                })
                
            # 2. Get files from Database for THIS path (using ABAC filtered queryset)
            db_files = self.get_queryset().filter(
                bucket__name=bucket_name
            )
            
            for db_file in db_files:
                # Get the directory part of the file_path
                parts = db_file.file_path.split('/')
                file_dir = '/'.join(parts[:-1]) if len(parts) > 1 else ''
                
                # Only include files exactly in the current path (not subdirectories)
                if file_dir == path:
                    result.append({
                        'name': db_file.file_name,
                        'type': 'file',
                        'size': db_file.file_size,
                        'id': db_file.id,
                        'created_at': db_file.uploaded_at,
                        'updated_at': db_file.updated_at,
                        'path': db_file.file_path,
                        'metadata': db_file.metadata
                    })
            
            return Response({
                'path': path,
                'bucket': bucket_name,
                'files': result
            })
            
        except Exception as e:
            return Response(
                {'error': f"Failed to list files: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def download_by_path(self, request):
        """
        Download file by path from Supabase
        GET /api/storage/files/download_by_path/?path=public/company-policy.md
        Protected by ABAC middleware - requires 'download' permission on 'document'
        
        Note: File owner can always download their own files regardless of ABAC policy
        """
        storage = get_storage_service()
        bucket_name = request.query_params.get('bucket', 'documents')
        file_path = request.query_params.get('path', '')
        
        if not file_path:
            return Response(
                {'error': 'path parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is owner of this file (can bypass ABAC for their own files)
        # This is already passed ABAC middleware, but we track ownership for audit
        uploaded_file = get_db_file_by_path(bucket_name, file_path)
        
        is_owner = uploaded_file and uploaded_file.uploaded_by == request.user
        
        version_param = request.query_params.get('version')
        
        try:
            physical_path = file_path
            cpabe_policy_str = None
            
            if uploaded_file:
                if version_param:
                    file_version = uploaded_file.versions.filter(version_number=version_param).first()
                    if not file_version:
                        return Response({'error': f'Version {version_param} not found'}, status=status.HTTP_404_NOT_FOUND)
                else:
                    file_version = uploaded_file.get_latest_version()
                    
                if file_version:
                    physical_path = file_version.physical_path
                    cpabe_policy_str = file_version.cpabe_policy
                    
            file_data = storage.download_file(bucket_name, physical_path)
            
            # Decrypt if necessary
            file_data = self._decrypt_file_if_needed(
                file_data, 
                bucket_name, 
                file_path, 
                request.user,
                is_owner=is_owner,
                cpabe_policy_str=cpabe_policy_str
            )
            
            file_name = file_path.split('/')[-1]
            if version_param and file_version and file_version != uploaded_file.get_latest_version():
                ext = file_name.split('.')[-1] if '.' in file_name else ''
                base = file_name[:-(len(ext)+1)] if ext else file_name
                file_name = f"{base}_v{version_param}.{ext}" if ext else f"{base}_v{version_param}"
            
            # Guess content type
            ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
            content_types = {
                'md': 'text/markdown',
                'txt': 'text/plain',
                'pdf': 'application/pdf',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg', 
                'png': 'image/png',
                'gif': 'image/gif',
            }
            content_type = content_types.get(ext, 'application/octet-stream')
            
            response = HttpResponse(file_data, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=False, methods=['get'])
    def preview_by_path(self, request):
        """
        Preview file by path from Supabase (displays in browser instead of downloading)
        GET /api/storage/files/preview_by_path/?path=public/company-policy.md
        Protected by ABAC middleware - requires 'read' permission on 'document'
        """
        storage = get_storage_service()
        bucket_name = request.query_params.get('bucket', 'documents')
        file_path = request.query_params.get('path', '')
        
        if not file_path:
            return Response(
                {'error': 'path parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is owner of this file (can bypass ABAC for their own files)
        uploaded_file = get_db_file_by_path(bucket_name, file_path)
        is_owner = uploaded_file and uploaded_file.uploaded_by == request.user
        
        version_param = request.query_params.get('version')
        
        try:
            physical_path = file_path
            cpabe_policy_str = None
            
            if uploaded_file:
                if version_param:
                    file_version = uploaded_file.versions.filter(version_number=version_param).first()
                    if not file_version:
                        return Response({'error': f'Version {version_param} not found'}, status=status.HTTP_404_NOT_FOUND)
                else:
                    file_version = uploaded_file.get_latest_version()
                    
                if file_version:
                    physical_path = file_version.physical_path
                    cpabe_policy_str = file_version.cpabe_policy
                    
            file_data = storage.download_file(bucket_name, physical_path)
            
            # Decrypt if necessary
            file_data = self._decrypt_file_if_needed(
                file_data, 
                bucket_name, 
                file_path, 
                request.user,
                is_owner=is_owner,
                cpabe_policy_str=cpabe_policy_str
            )
            file_name = file_path.split('/')[-1]
            if version_param and file_version and file_version != uploaded_file.get_latest_version():
                ext = file_name.split('.')[-1] if '.' in file_name else ''
                base = file_name[:-(len(ext)+1)] if ext else file_name
                file_name = f"{base}_v{version_param}.{ext}" if ext else f"{base}_v{version_param}"
            
            # Guess content type
            ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
            content_types = {
                'md': 'text/markdown',
                'txt': 'text/plain',
                'pdf': 'application/pdf',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg', 
                'png': 'image/png',
                'gif': 'image/gif',
            }
            content_type = content_types.get(ext, 'application/octet-stream')
            
            response = HttpResponse(file_data, content_type=content_type)
            # Use inline instead of attachment for preview
            response['Content-Disposition'] = f'inline; filename="{file_name}"'
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['delete'])
    def delete_by_path(self, request):
        """
        Delete file by path from Supabase
        DELETE /api/storage/files/delete_by_path/?path=public/file.md&bucket=documents
        Protected by ABAC middleware - requires 'delete' permission on 'document'
        """
        storage = get_storage_service()
        bucket_name = request.query_params.get('bucket', 'documents')
        file_path = request.query_params.get('path', '')
        
        if not file_path:
            return Response(
                {'error': 'path parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Soft delete logic
            uploaded_file = get_db_file_by_path(bucket_name, file_path)
            
            if uploaded_file:
                uploaded_file.is_deleted = True
                uploaded_file.deleted_at = timezone.now()
                uploaded_file.save(update_fields=['is_deleted', 'deleted_at'])
            else:
                # Fallback if not in database but somehow exists in Supabase
                # Or just do nothing, assuming we want soft delete to mean marking db records.
                # Actually, we shouldn't touch Supabase storage until Hard Delete
                pass
            
            return Response({
                'message': f"File '{file_path}' deleted successfully"
            })
            
        except Exception as e:
            return Response(
                {'error': f"Delete failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_folder(self, request):
        """
        Create a folder in Supabase Storage
        POST /api/storage/files/create_folder/
        Body: { "folder_name": "hr", "bucket_name": "documents", "parent_path": "" }
        """
        bucket_name = request.data.get('bucket_name', 'documents')
        folder_name = request.data.get('folder_name', '')
        parent_path = request.data.get('parent_path', '')
        
        if not folder_name:
            return Response(
                {'error': 'folder_name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate folder name
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', folder_name):
            return Response(
                {'error': 'Folder name can only contain letters, numbers, underscore and hyphen'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        storage = get_storage_service()
        
        try:
            # Create folder by uploading a placeholder file
            # Supabase creates folders implicitly when files are uploaded
            folder_path = f"{parent_path}/{folder_name}/.folder" if parent_path else f"{folder_name}/.folder"
            
            storage.upload_file(
                bucket_name=bucket_name,
                file_path=folder_path,
                file_data=b'',  # Empty placeholder
                content_type='text/plain'
            )
            
            return Response({
                'message': f"Folder '{folder_name}' created successfully",
                'path': folder_path.replace('/.folder', '')
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f"Failed to create folder: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ============= FILE ACCESS POLICY MANAGEMENT =============
    
    @action(detail=False, methods=['get'])
    def available_policies(self, request):
        """
        Get list of available policies for assignment.
        Filters policies that are applicable to documents/files.
        """
        policies = AccessPolicy.objects.filter(
            is_active=True,
            resource__in=['document', '*']  # Only document-related policies
        ).order_by('priority', 'name')
        
        serializer = PolicyListForAssignmentSerializer(policies, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def file_policies(self, request):
        """
        Get policies assigned to a specific file or folder.
        Query params: path, bucket (default: documents)
        """
        file_path = request.GET.get('path', '')
        bucket_name = request.GET.get('bucket', 'documents')
        
        if not file_path:
            return Response(
                {'error': 'File path is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            bucket = StorageBucket.objects.get(name=bucket_name)
        except StorageBucket.DoesNotExist:
            return Response(
                {'error': f"Bucket '{bucket_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get direct file policies
        file_record = get_db_file_by_path(bucket.name, file_path)
        
        file_policies = []
        if file_record:
            file_policies = FileAccessPolicy.objects.filter(
                uploaded_file=file_record
            ).select_related('policy', 'assigned_by')
        
        # Get folder policies that apply to this path
        folder_policies = []
        path_parts = file_path.split('/')
        for i in range(len(path_parts)):
            folder_path = '/'.join(path_parts[:i+1]) + '/'
            fp = FileAccessPolicy.objects.filter(
                bucket=bucket,
                folder_path=folder_path,
                target_type='folder'
            ).select_related('policy', 'assigned_by')
            folder_policies.extend(list(fp))
        
        return Response({
            'file_path': file_path,
            'bucket': bucket_name,
            'direct_policies': FileAccessPolicySerializer(file_policies, many=True).data,
            'inherited_folder_policies': FileAccessPolicySerializer(folder_policies, many=True).data
        })
    
    @action(detail=False, methods=['post'])
    def assign_policy(self, request):
        """
        Assign a policy to a file or folder.
        Can use existing policy or create a new one.
        """
        serializer = AssignPolicyToFileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        file_path = data['file_path']
        bucket_name = data['bucket_name']
        target_type = data['target_type']
        
        try:
            bucket = StorageBucket.objects.get(name=bucket_name)
        except StorageBucket.DoesNotExist:
            return Response(
                {'error': f"Bucket '{bucket_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create the policy
        policy = None
        if data.get('policy_id'):
            try:
                policy = AccessPolicy.objects.get(id=data['policy_id'])
            except AccessPolicy.DoesNotExist:
                return Response(
                    {'error': f"Policy ID {data['policy_id']} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif data.get('create_new_policy'):
            # Create new policy for this file with all fields from Policy Builder
            policy = AccessPolicy.objects.create(
                name=data['new_policy_name'],
                description=data.get('new_policy_description', ''),
                subject_condition=data['new_policy_subject_condition'],
                resource=data.get('new_policy_resource', 'document'),
                action=data.get('new_policy_action', 'read'),
                effect=data['new_policy_effect'],
                priority=data.get('new_policy_priority', 100),
                created_by=request.user
            )
            logger.info(f"Created new policy '{policy.name}' for file assignment")
        
        # Create FileAccessPolicy
        file_record = None
        folder_path = None
        
        if target_type == 'file':
            file_record = get_db_file_by_path(bucket.name, file_path)
            
            if not file_record:
                return Response(
                    {'error': f"File '{file_path}' not found in bucket '{bucket_name}'"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:  # folder
            folder_path = file_path if file_path.endswith('/') else file_path + '/'
        
        # Check if policy already assigned
        existing = FileAccessPolicy.objects.filter(
            policy=policy,
            bucket=bucket,
        )
        if target_type == 'file':
            existing = existing.filter(uploaded_file=file_record)
        else:
            existing = existing.filter(folder_path=folder_path)
        
        # Determine replace mode
        replace_policies = self.request.data.get('replace', False) or self.request.query_params.get('replace', 'false').lower() == 'true'
        
        # Check ownership/admin rights for modifying policies
        is_admin = getattr(request.user, 'is_superuser', False)
        if hasattr(request.user, 'profile') and request.user.profile.user_type_ref:
            if request.user.profile.user_type_ref.code in ['super_admin', 'admin']:
                is_admin = True
                
        is_owner = file_record and file_record.uploaded_by == request.user
        
        if not (is_owner or is_admin):
            return Response(
                {'error': 'Only the file owner or an administrator can modify its policy.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if existing.exists() and not replace_policies:
            return Response(
                {'error': 'This policy is already assigned to this file/folder'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Handle Encryption / Re-encryption
        if target_type == 'file':
            storage = get_storage_service()
            try:
                # Find all existing policies to check if already encrypted
                existing_all = FileAccessPolicy.objects.filter(
                    uploaded_file=file_record
                )
                was_already_encrypted = any(p.policy.cpabe_policy for p in existing_all)
                
                needs_encryption_update = False
                file_data = None
                
                if replace_policies:
                    # If replacing, we must download, decrypt, and re-encrypt
                    needs_encryption_update = True
                    latest_version = file_record.get_latest_version()
                    physical_path = latest_version.physical_path if latest_version else file_path
                    cpabe_policy_str = latest_version.cpabe_policy if latest_version else None
                    
                    # Get plaintext bytes
                    file_data = storage.download_file(bucket_name, physical_path)
                    if was_already_encrypted:
                        file_data = self._decrypt_file_if_needed(
                            file_data, bucket_name, file_path, request.user, is_owner=True, cpabe_policy_str=cpabe_policy_str
                        )
                    
                    # Delete old policies
                    existing_all.delete()
                    policy_to_encrypt = policy.cpabe_policy

                else:
                    latest_version = file_record.get_latest_version()
                    physical_path = latest_version.physical_path if latest_version else file_path
                    cpabe_policy_str = latest_version.cpabe_policy if latest_version else None
                    
                    if policy.cpabe_policy:
                        needs_encryption_update = True
                        if was_already_encrypted:
                            # Add operation: Combine all existing CP-ABE policies with the new one
                            all_cpabe = [p.policy.cpabe_policy for p in existing_all if p.policy.cpabe_policy]
                            all_cpabe.append(policy.cpabe_policy)
                            policy_to_encrypt = " or ".join(f"({p})" for p in all_cpabe)
                            
                            # Decrypt existing file data first
                            enc_data = storage.download_file(bucket_name, physical_path)
                            file_data = self._decrypt_file_if_needed(
                                enc_data, bucket_name, file_path, request.user, is_owner=True, cpabe_policy_str=cpabe_policy_str
                            )
                        else:
                            file_data = storage.download_file(bucket_name, physical_path)
                            policy_to_encrypt = policy.cpabe_policy
                        
                # Create the assignment
                file_access_policy = FileAccessPolicy.objects.create(
                    uploaded_file=file_record,
                    bucket=bucket,
                    target_type=target_type,
                    policy=policy,
                    assigned_by=request.user,
                    notes=data.get('notes', '')
                )
                
                if needs_encryption_update:
                    if policy_to_encrypt:
                        # Encrypt plaintext
                        logger.info(f"Encrypting file {physical_path} with policy: {policy_to_encrypt}")
                        try:
                            enc_data = cpabe_service.encrypt_buffer(file_data, policy_to_encrypt)
                            
                            storage.upload_file(
                                bucket_name=bucket_name,
                                file_path=physical_path,
                                file_data=enc_data,
                                content_type=file_record.mime_type or 'application/octet-stream',
                                upsert=True
                            )
                            # Update FileVersion cpabe_policy
                            if latest_version:
                                latest_version.cpabe_policy = policy_to_encrypt
                                latest_version.save(update_fields=['cpabe_policy'])
                        except Exception as e:
                            logger.error(f"Failed to encrypt file data during policy assignment: {e}")
                            raise
                    elif replace_policies:
                        # Policy has no CP-ABE, and we are replacing -> Upload plaintext
                        logger.info(f"Removing encryption for file {physical_path}")
                        storage.upload_file(
                            bucket_name=bucket_name,
                            file_path=physical_path,
                            file_data=file_data,
                            content_type=file_record.mime_type or 'application/octet-stream',
                            upsert=True
                        )
                        if latest_version:
                            latest_version.cpabe_policy = ''
                            latest_version.save(update_fields=['cpabe_policy'])
            except Exception as e:
                logger.error(f"Failed to update encryption for file {file_path}: {e}")
                return Response({'error': f"Failed to update encryption: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Create the assignment for folder
            if replace_policies:
                FileAccessPolicy.objects.filter(
                    folder_path=folder_path,
                    bucket=bucket,
                    target_type=target_type
                ).delete()
                
            file_access_policy = FileAccessPolicy.objects.create(
                folder_path=folder_path,
                bucket=bucket,
                target_type=target_type,
                policy=policy,
                assigned_by=request.user,
                notes=data.get('notes', '')
            )
        
        return Response({
            'message': 'Policy assigned successfully',
            'assignment': FileAccessPolicySerializer(file_access_policy).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['delete'])
    def remove_policy(self, request):
        """
        Remove a policy assignment from a file/folder.
        Query params: assignment_id
        """
        assignment_id = request.GET.get('assignment_id')
        
        if not assignment_id:
            return Response(
                {'error': 'assignment_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            assignment = FileAccessPolicy.objects.get(id=assignment_id)
            
            # Check if user is owner or admin
            file_owner = None
            if assignment.uploaded_file:
                file_owner = assignment.uploaded_file.uploaded_by
            
            if not (request.user.is_superuser or 
                    assignment.assigned_by == request.user or 
                    file_owner == request.user):
                return Response(
                    {'error': 'You do not have permission to remove this policy assignment'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            assignment.delete()
            return Response({'message': 'Policy assignment removed successfully'})
            
        except FileAccessPolicy.DoesNotExist:
            return Response(
                {'error': f"Assignment ID {assignment_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

