"""
Storage Views - API endpoints for file operations
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
import uuid

from ..models import StorageBucket, UploadedFile
from ..serializers import (
    StorageBucketSerializer,
    UploadedFileSerializer,
    FileUploadSerializer,
    SignedUrlRequestSerializer
)
from ..services.storage_service import get_storage_service


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
    parser_classes = [MultiPartParser, FormParser]
    
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
        try:
            file_data = file.read()
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
