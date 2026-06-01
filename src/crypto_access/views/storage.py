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

from ..models import StorageBucket, UploadedFile, FileAccessPolicy, AccessPolicy
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
import os

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
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def _decrypt_file_if_needed(self, file_data, bucket_name, file_path, user):
        """Helper to decrypt file if it has a CP-ABE policy"""
        file_policies = FileAccessPolicy.get_policies_for_file(bucket_name, file_path)
        is_encrypted = any(p.cpabe_policy for p in file_policies)
        
        if not is_encrypted:
            return file_data
            
        user_attrs = casbin_service.get_user_attributes(user)
        
        with tempfile.NamedTemporaryFile(delete=False) as f_key, \
             tempfile.NamedTemporaryFile(delete=False) as f_in:
            key_name = f_key.name
            f_in.write(file_data)
            temp_in_name = f_in.name
            
        temp_out_name = temp_in_name + ".dec"
        
        try:
            cpabe_service.generate_user_key(user_attrs, key_name)
            cpabe_service.decrypt_file(key_name, temp_in_name, temp_out_name)
            with open(temp_out_name, 'rb') as f_out:
                return f_out.read()
        finally:
            if os.path.exists(key_name): os.remove(key_name)
            if os.path.exists(temp_in_name): os.remove(temp_in_name)
            if os.path.exists(temp_out_name): os.remove(temp_out_name)
    
    def get_queryset(self):
        """Filter files by user or bucket"""
        queryset = super().get_queryset()
        
        # Filter by bucket
        bucket_name = self.request.query_params.get('bucket', None)
        if bucket_name:
            queryset = queryset.filter(bucket__name=bucket_name)
        
        # Filter by file type
        file_type = self.request.query_params.get('type', None)
        if file_type:
            queryset = queryset.filter(file_type=file_type)
        
        # Filter by user
        my_files = self.request.query_params.get('my_files', None)
        if my_files and self.request.user.is_authenticated:
            queryset = queryset.filter(uploaded_by=self.request.user)
        
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
        policy_id = serializer.validated_data.get('policy_id')
        
        policy_obj = None
        cpabe_policy_str = None
        if policy_id:
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
        
        # Generate unique file path
        file_path = serializer.validated_data.get('file_path')
        if not file_path:
            ext = file.name.split('.')[-1] if '.' in file.name else ''
            unique_name = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
            file_path = f"{timezone.now().strftime('%Y/%m/%d')}/{unique_name}"
        
        # Upload to Supabase
        storage = get_storage_service()
        
        # Check inherited policies from folders if no direct policy_id was provided
        if not cpabe_policy_str:
            inherited_policies = FileAccessPolicy.get_policies_for_file(bucket_name, file_path)
            for p in inherited_policies:
                if p.policy and p.policy.cpabe_policy:
                    cpabe_policy_str = p.policy.cpabe_policy
                    logger.info(f"Inheriting CP-ABE policy from folder: {cpabe_policy_str}")
                    break
        
        try:
            file_data = file.read()
            
            # Encrypt if policy has cpabe_policy
            if cpabe_policy_str:
                logger.info(f"Encrypting file with CP-ABE policy: {cpabe_policy_str}")
                with tempfile.NamedTemporaryFile(delete=False) as f_in:
                    f_in.write(file_data)
                    temp_in_name = f_in.name
                
                temp_out_name = temp_in_name + ".enc"
                try:
                    cpabe_service.encrypt_file(temp_in_name, temp_out_name, cpabe_policy_str)
                    with open(temp_out_name, 'rb') as f_out:
                        file_data = f_out.read()
                finally:
                    if os.path.exists(temp_in_name): os.remove(temp_in_name)
                    if os.path.exists(temp_out_name): os.remove(temp_out_name)

            upload_result = storage.upload_file(
                bucket_name=bucket_name,
                file_path=file_path,
                file_data=file_data,
                content_type=file.content_type
            )
            
            # Get URL
            if bucket.bucket_type == 'public':
                file_url = storage.get_public_url(bucket_name, file_path)
                signed_url = None
                signed_url_expires_at = None
            else:
                file_url = None
                signed_url = storage.create_signed_url(bucket_name, file_path, expires_in=3600)
                signed_url_expires_at = timezone.now() + timedelta(seconds=3600)
            
            # Save to database
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
                tags=tags
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
        
        try:
            file_data = storage.download_file(
                bucket_name=uploaded_file.bucket.name,
                file_path=uploaded_file.file_path
            )
            
            # Decrypt if necessary
            file_data = self._decrypt_file_if_needed(
                file_data, 
                uploaded_file.bucket.name, 
                uploaded_file.file_path, 
                request.user
            )
            
            response = HttpResponse(file_data, content_type=uploaded_file.mime_type)
            response['Content-Disposition'] = f'attachment; filename="{uploaded_file.file_name}"'
            return response
            
        except Exception as e:
            return Response(
                {'error': f"Download failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
        """Delete file from both Supabase Storage and database"""
        uploaded_file = self.get_object()
        storage = get_storage_service()
        
        try:
            # Delete from Supabase
            storage.delete_file(
                bucket_name=uploaded_file.bucket.name,
                file_paths=[uploaded_file.file_path]
            )
            
            # Delete from database
            file_name = uploaded_file.file_name
            uploaded_file.delete()
            
            return Response({
                'message': f"File '{file_name}' deleted successfully"
            })
            
        except Exception as e:
            return Response(
                {'error': f"Delete failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get storage statistics"""
        user = request.user
        
        stats = {
            'total_files': UploadedFile.objects.count(),
            'my_files': UploadedFile.objects.filter(uploaded_by=user).count() if user.is_authenticated else 0,
            'total_size': sum(f.file_size for f in UploadedFile.objects.all()),
            'by_type': {}
        }
        
        # Count by file type
        for file_type, _ in UploadedFile.FILE_TYPE_CHOICES:
            count = UploadedFile.objects.filter(file_type=file_type).count()
            stats['by_type'][file_type] = count
        
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
            files = storage.list_files(
                bucket_name=bucket_name,
                path=path,
                limit=100
            )
            
            # Transform to standard format
            result = []
            for f in files:
                is_folder = f.get('id') is None  # Folders don't have id
                result.append({
                    'name': f.get('name', ''),
                    'type': 'folder' if is_folder else 'file',
                    'size': f.get('metadata', {}).get('size', 0) if not is_folder else None,
                    'id': f.get('id'),
                    'created_at': f.get('created_at'),
                    'updated_at': f.get('updated_at'),
                    'path': f"{path}/{f.get('name', '')}" if path else f.get('name', '')
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
        uploaded_file = UploadedFile.objects.filter(
            bucket__name=bucket_name,
            file_path=file_path
        ).first()
        
        is_owner = uploaded_file and uploaded_file.uploaded_by == request.user
        
        try:
            file_data = storage.download_file(bucket_name, file_path)
            
            # Decrypt if necessary
            file_data = self._decrypt_file_if_needed(
                file_data, 
                bucket_name, 
                file_path, 
                request.user
            )
            
            file_name = file_path.split('/')[-1]
            
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
                {'error': f"Download failed: {str(e)}"},
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
            # Delete from Supabase Storage
            storage.delete_file(bucket_name, [file_path])
            
            # Also delete from database if exists
            UploadedFile.objects.filter(
                bucket__name=bucket_name,
                file_path=file_path
            ).delete()
            
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
        file_record = UploadedFile.objects.filter(
            bucket=bucket,
            file_path=file_path
        ).first()
        
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
        folder_path = ''
        
        if target_type == 'file':
            file_record = UploadedFile.objects.filter(
                bucket=bucket,
                file_path=file_path
            ).first()
            
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
        
        if existing.exists():
            return Response(
                {'error': 'This policy is already assigned to this file/folder'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the assignment
        file_access_policy = FileAccessPolicy.objects.create(
            uploaded_file=file_record if target_type == 'file' else None,
            folder_path=folder_path if target_type == 'folder' else '',
            bucket=bucket,
            target_type=target_type,
            policy=policy,
            assigned_by=request.user,
            notes=data.get('notes', '')
        )
        
        # Add granted users if specified
        if data.get('grant_user_ids'):
            from django.contrib.auth.models import User
            users = User.objects.filter(id__in=data['grant_user_ids'])
            file_access_policy.granted_users.set(users)
            
        # Retroactive Encryption for File Assignment
        if target_type == 'file' and policy.cpabe_policy:
            storage = get_storage_service()
            try:
                # Check if it was already encrypted by another policy
                other_policies = FileAccessPolicy.objects.filter(
                    uploaded_file=file_record
                ).exclude(id=file_access_policy.id)
                
                was_already_encrypted = any(p.policy.cpabe_policy for p in other_policies)
                
                if not was_already_encrypted:
                    # Download plaintext
                    file_data = storage.download_file(bucket_name, file_path)
                    
                    # Encrypt it
                    logger.info(f"Retroactively encrypting file {file_path} with policy: {policy.cpabe_policy}")
                    with tempfile.NamedTemporaryFile(delete=False) as f_in:
                        f_in.write(file_data)
                        temp_in_name = f_in.name
                    
                    temp_out_name = temp_in_name + ".enc"
                    try:
                        cpabe_service.encrypt_file(temp_in_name, temp_out_name, policy.cpabe_policy)
                        with open(temp_out_name, 'rb') as f_out:
                            enc_data = f_out.read()
                            
                        # Re-upload to overwrite the plaintext in Supabase
                        storage.upload_file(
                            bucket_name=bucket_name,
                            file_path=file_path,
                            file_data=enc_data,
                            content_type=file_record.mime_type or 'application/octet-stream',
                            upsert=True
                        )
                    finally:
                        if os.path.exists(temp_in_name): os.remove(temp_in_name)
                        if os.path.exists(temp_out_name): os.remove(temp_out_name)
            except Exception as e:
                logger.error(f"Failed to retroactively encrypt file {file_path}: {e}")
        
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

