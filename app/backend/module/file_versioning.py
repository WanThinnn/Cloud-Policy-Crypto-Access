"""
File Version Manager for handling file versioning and approval workflow
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from google.cloud.firestore_v1 import FieldFilter, Query
from google.cloud import firestore
from .database import db  # Import the db client directly
from .file_integrity import FileIntegrityManager
from .central_authority import central_authority # Import for decryption
import uuid

logger = logging.getLogger(__name__)

class FileVersionManager:
    """
    Manages file versioning, approval workflow, and version history
    """
    
    @staticmethod
    def create_version(file_id: str, 
                      file_data: bytes, 
                      uploader_id: str,
                      version_type: str = 'MINOR',
                      change_description: Optional[str] = None,
                      access_policy: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new version of a file.
        The new version's data is encrypted and stored in the version document.
        If activation is successful, the main file's encrypted data is replaced.
        
        Args:
            file_id: Original file ID
            file_data: New raw, unencrypted file data
            uploader_id: User creating the version
            version_type: MAJOR, MINOR, PATCH
            change_description: Description of changes
            access_policy: Access policy to use (if None, uses original file's policy)
            
        Returns:
            Version creation result
        """
        try:
            # Use the correct collection name: 'shared_files'
            file_ref = db.collection('shared_files').document(file_id)
            file_doc = file_ref.get()
            
            if not file_doc.exists:
                return {
                    'success': False,
                    'error': 'Original file not found'
                }
            
            original_file_metadata = file_doc.to_dict()
            
            # IMPORTANT: Save the current file data BEFORE any modifications
            # This is critical for proper version comparison
            old_encrypted_data = original_file_metadata.get('encrypted_data')
            old_decrypted_data = b""
            old_file_size = original_file_metadata.get('original_size', 0)
            
            if old_encrypted_data:
                decrypt_result = central_authority.decrypt_file_for_user(
                    old_encrypted_data,
                    uploader_id
                )
                if decrypt_result.get('success'):
                    old_decrypted_data = decrypt_result['decrypted_data']
                else:
                    logger.warning(f"User {uploader_id} could not decrypt file {file_id} for integrity check. Proceeding without comparison.")

            # Create the integrity report comparing old (decrypted) and new (raw) data
            integrity_analysis = FileIntegrityManager.create_integrity_report(
                old_decrypted_data,
                file_data, # new raw file data
                {
                    'version': original_file_metadata.get('current_version', '0.0.0'),
                    'upload_time': original_file_metadata.get('upload_time'),
                    'owner_id': original_file_metadata.get('owner_id')
                }
            )
            integrity_report = integrity_analysis.get('report') if integrity_analysis.get('success') else None

            # Get current version info and increment it
            current_version = original_file_metadata.get('current_version', '1.0.0')
            new_version = FileVersionManager._increment_version(current_version, version_type)
            
            # Generate version ID
            version_id = str(uuid.uuid4())
            
            # Generate integrity hashes for the new version's raw data
            new_hashes = FileIntegrityManager.generate_integrity_hashes(file_data)
            
            # Encrypt the new file data for this version using a temporary file
            import tempfile
            import os
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, f"{version_id}-{original_file_metadata.get('filename', 'temp')}")
            with open(temp_file_path, 'wb') as f:
                f.write(file_data)

            # Use the provided access policy or fall back to original file's policy
            effective_access_policy = access_policy or original_file_metadata.get('access_policy')
            if not effective_access_policy:
                return {'success': False, 'error': 'No access policy available for version encryption'}
                
            encrypt_result = central_authority.encrypt_file_for_policy(temp_file_path, effective_access_policy)
            
            import shutil
            shutil.rmtree(temp_dir)

            if not encrypt_result.get('success'):
                return {'success': False, 'error': f"Failed to encrypt new version: {encrypt_result.get('error')}"}

            # Simplified workflow: new versions are approved automatically.
            # A more complex system could use PENDING_APPROVAL and the approve_version method.
            approval_required = False
            
            # Create the version document in Firestore
            version_data = {
                'version_id': version_id,
                'file_id': file_id,
                'version_number': new_version,
                'version_type': version_type,
                'uploader_id': uploader_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'status': 'PENDING_ACTIVATION', # Status before it replaces the main file
                'change_description': change_description or '',
                'integrity_hashes': new_hashes,
                'integrity_report': integrity_report,
                'encrypted_data': encrypt_result['encrypted_data'], # Store encrypted data for this version
                'file_size': len(file_data),
                'metadata': {
                    'original_filename': original_file_metadata.get('filename'),
                    'content_type': original_file_metadata.get('file_type')
                }
            }
            
            db.collection('file_versions').document(version_id).set(version_data)
            
            # If no approval is required, activate this version immediately
            if not approval_required:
                activation_result = FileVersionManager._activate_version(file_id, version_id, version_data, uploader_id)
                if not activation_result['success']:
                    return activation_result
            
            logger.info(f"Version {new_version} created and activated for file {file_id} by user {uploader_id}")
            
            return {
                'success': True,
                'version_id': version_id,
                'version_number': new_version,
                'status': 'ACTIVE',
                'approval_required': approval_required,
                'integrity_report': integrity_report
            }
            
        except Exception as e:
            logger.error(f"Version creation failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to create version: {str(e)}'
            }
    
    @staticmethod
    def approve_version(version_id: str, approver_id: str, approval_notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Approve a pending file version
        
        Args:
            version_id: Version to approve
            approver_id: User approving the version
            approval_notes: Optional approval notes
            
        Returns:
            Approval result
        """
        try:
            
            
            # Get version document
            version_ref = db.collection('file_versions').document(version_id)
            version_doc = version_ref.get()
            
            if not version_doc.exists:
                return {
                    'success': False,
                    'error': 'Version not found'
                }
            
            version_data = version_doc.to_dict()
            
            # Check if approval is required
            if not version_data.get('approval_required', False):
                return {
                    'success': False,
                    'error': 'Version does not require approval'
                }
            
            # Check if already approved
            if version_data.get('status') == 'APPROVED':
                return {
                    'success': False,
                    'error': 'Version already approved'
                }
            
            # Check approver permissions
            file_id = version_data['file_id']
            approver_permissions = FileVersionManager._get_user_file_permissions(approver_id, file_id)
            if not approver_permissions.get('can_approve_versions', False):
                return {
                    'success': False,
                    'error': 'Insufficient permissions to approve versions'
                }
            
            # Update version status
            version_ref.update({
                'status': 'APPROVED',
                'approved_by': approver_id,
                'approved_at': firestore.SERVER_TIMESTAMP,
                'approval_notes': approval_notes or ''
            })
            
            # Activate the approved version
            activation_result = FileVersionManager._activate_version(file_id, version_id, version_data, approver_id)
            if not activation_result['success']:
                return activation_result
            
            logger.info(f"Version {version_id} approved by {approver_id}")
            
            return {
                'success': True,
                'version_id': version_id,
                'approved_by': approver_id,
                'activated': True
            }
            
        except Exception as e:
            logger.error(f"Version approval failed: {e}")
            return {
                'success': False,
                'error': f'Failed to approve version: {str(e)}'
            }
    
    @staticmethod
    def reject_version(version_id: str, rejector_id: str, rejection_reason: str) -> Dict[str, Any]:
        """
        Reject a pending file version
        
        Args:
            version_id: Version to reject
            rejector_id: User rejecting the version
            rejection_reason: Reason for rejection
            
        Returns:
            Rejection result
        """
        try:
            
            
            # Get version document
            version_ref = db.collection('file_versions').document(version_id)
            version_doc = version_ref.get()
            
            if not version_doc.exists:
                return {
                    'success': False,
                    'error': 'Version not found'
                }
            
            version_data = version_doc.to_dict()
            
            # Check rejector permissions
            file_id = version_data['file_id']
            rejector_permissions = FileVersionManager._get_user_file_permissions(rejector_id, file_id)
            if not rejector_permissions.get('can_approve_versions', False):
                return {
                    'success': False,
                    'error': 'Insufficient permissions to reject versions'
                }
            
            # Update version status
            version_ref.update({
                'status': 'REJECTED',
                'rejected_by': rejector_id,
                'rejected_at': firestore.SERVER_TIMESTAMP,
                'rejection_reason': rejection_reason
            })
            
            logger.info(f"Version {version_id} rejected by {rejector_id}")
            
            return {
                'success': True,
                'version_id': version_id,
                'rejected_by': rejector_id,
                'rejection_reason': rejection_reason
            }
            
        except Exception as e:
            logger.error(f"Version rejection failed: {e}")
            return {
                'success': False,
                'error': f'Failed to reject version: {str(e)}'
            }
    
    @staticmethod
    def get_version_history(file_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get version history for a file
        
        Args:
            file_id: File to get history for
            limit: Maximum number of versions to return
            
        Returns:
            Version history
        """
        try:
            
            
            # Query versions for this file
            versions_ref = db.collection('file_versions')
            query = versions_ref.where(filter=FieldFilter('file_id', '==', file_id))
            query = query.order_by('created_at', direction=Query.DESCENDING)
            query = query.limit(limit)
            
            versions = []
            for doc in query.stream():
                version_data = doc.to_dict()
                versions.append({
                    'version_id': version_data['version_id'],
                    'version_number': version_data['version_number'],
                    'version_type': version_data['version_type'],
                    'uploader_id': version_data['uploader_id'],
                    'created_at': version_data['created_at'],
                    'status': version_data['status'],
                    'change_description': version_data.get('change_description', ''),
                    'approved_by': version_data.get('approved_by'),
                    'approved_at': version_data.get('approved_at'),
                    'file_size': version_data.get('file_size', 0),
                    'integrity_report': version_data.get('integrity_report')
                })
            
            return {
                'success': True,
                'file_id': file_id,
                'versions': versions,
                'total_versions': len(versions)
            }
            
        except Exception as e:
            logger.error(f"Failed to get version history: {e}")
            return {
                'success': False,
                'error': f'Failed to get version history: {str(e)}'
            }
    
    @staticmethod
    def get_pending_approvals(approver_id: str) -> Dict[str, Any]:
        """
        Get versions pending approval for a specific approver
        
        Args:
            approver_id: User ID of the approver
            
        Returns:
            List of pending versions
        """
        try:
            
            
            # Get versions pending approval
            versions_ref = db.collection('file_versions')
            query = versions_ref.where(filter=FieldFilter('status', '==', 'PENDING_APPROVAL'))
            query = query.order_by('created_at', direction=Query.DESCENDING)
            
            pending_versions = []
            for doc in query.stream():
                version_data = doc.to_dict()
                file_id = version_data['file_id']
                
                # Check if user can approve this version
                permissions = FileVersionManager._get_user_file_permissions(approver_id, file_id)
                if permissions.get('can_approve_versions', False):
                    pending_versions.append({
                        'version_id': version_data['version_id'],
                        'file_id': file_id,
                        'version_number': version_data['version_number'],
                        'version_type': version_data['version_type'],
                        'uploader_id': version_data['uploader_id'],
                        'created_at': version_data['created_at'],
                        'change_description': version_data.get('change_description', ''),
                        'integrity_report': version_data.get('integrity_report'),
                        'file_metadata': version_data.get('metadata', {})
                    })
            
            return {
                'success': True,
                'pending_versions': pending_versions,
                'total_pending': len(pending_versions)
            }
            
        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            return {
                'success': False,
                'error': f'Failed to get pending approvals: {str(e)}'
            }
    
    @staticmethod
    def _increment_version(current_version: str, version_type: str) -> str:
        """
        Increment version number based on type
        
        Args:
            current_version: Current version (e.g., "1.2.3")
            version_type: MAJOR, MINOR, or PATCH
            
        Returns:
            New version number
        """
        try:
            parts = current_version.split('.')
            major = int(parts[0]) if len(parts) > 0 else 1
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            
            if version_type == 'MAJOR':
                major += 1
                minor = 0
                patch = 0
            elif version_type == 'MINOR':
                minor += 1
                patch = 0
            else:  # PATCH
                patch += 1
            
            return f"{major}.{minor}.{patch}"
            
        except Exception:
            return "1.0.1"
    
    @staticmethod
    def _requires_approval(version_type: str, 
                          integrity_report: Optional[Dict],
                          user_permissions: Dict[str, Any]) -> bool:
        """
        Determine if version requires approval
        
        Args:
            version_type: Type of version change
            integrity_report: File integrity analysis
            user_permissions: User's permissions
            
        Returns:
            True if approval required
        """
        # Always require approval for major versions
        if version_type == 'MAJOR':
            return True
        
        # Check if user has auto-approval permissions
        if user_permissions.get('auto_approve_minor', False) and version_type == 'MINOR':
            return False
        
        if user_permissions.get('auto_approve_patch', False) and version_type == 'PATCH':
            return False
        
        # Check integrity report for suspicious changes
        if integrity_report:
            security_analysis = integrity_report.get('security_analysis', {})
            risk_level = security_analysis.get('risk_level', 'LOW')
            
            if risk_level in ['HIGH', 'CRITICAL']:
                return True
        
        # Default: require approval for non-patch versions
        return version_type != 'PATCH'
    
    @staticmethod
    def _activate_version(file_id: str, version_id: str, version_data: Dict[str, Any], activator_id: str) -> Dict[str, Any]:
        """
        Activate an approved version as the current version.
        This replaces the main file's encrypted data and metadata.
        IMPORTANT: Before updating, we save the current version as a historical record.
        
        Args:
            file_id: File to update
            version_id: Version to activate
            version_data: The data from the version document
            activator_id: User activating the version
            
        Returns:
            Activation result
        """
        try:
            file_ref = db.collection('shared_files').document(file_id)
            current_file_data = file_ref.get().to_dict()
            
            # Save the current file state as a historical version before overwriting
            current_version_id = current_file_data.get('current_version_id')
            if current_version_id and current_version_id != version_id:
                # Create historical version record
                historical_version_data = {
                    'version_id': current_version_id or f"historical_{file_id}_{datetime.utcnow().timestamp()}",
                    'file_id': file_id,
                    'version_number': current_file_data.get('current_version', '1.0.0'),
                    'version_type': 'HISTORICAL',
                    'uploader_id': current_file_data.get('owner_id'),
                    'created_at': current_file_data.get('upload_time') or firestore.SERVER_TIMESTAMP,
                    'status': 'HISTORICAL',
                    'change_description': 'Historical version saved before activation',
                    'integrity_hashes': current_file_data.get('integrity_hashes', {}),
                    'encrypted_data': current_file_data.get('encrypted_data'),
                    'file_size': current_file_data.get('original_size', 0),
                    'metadata': {
                        'original_filename': current_file_data.get('filename'),
                        'content_type': current_file_data.get('file_type')
                    }
                }
                
                # Save historical version
                historical_doc_id = current_version_id or f"historical_{file_id}_{int(datetime.utcnow().timestamp())}"
                db.collection('file_versions').document(historical_doc_id).set(historical_version_data)
                logger.info(f"Saved historical version {current_file_data.get('current_version')} before activating {version_data['version_number']}")
            
            # Update main file document with ONLY version metadata (DO NOT overwrite content)
            # Main file should be metadata-only container, actual content stays in file_versions
            file_ref.update({
                'current_version': version_data['version_number'],
                'current_version_id': version_id,
                'last_modified_at': firestore.SERVER_TIMESTAMP,
                'last_modified_by': activator_id
                # NOTE: DO NOT update encrypted_data or original_size - content stays in versions collection
            })
            
            # Mark version as active in its own document
            version_ref = db.collection('file_versions').document(version_id)
            version_ref.update({
                'status': 'ACTIVE',
                'activated_at': firestore.SERVER_TIMESTAMP,
                'activated_by': activator_id
            })
            
            return {
                'success': True,
                'activated_version': version_data['version_number']
            }
            
        except Exception as e:
            logger.error(f"Version activation failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to activate version: {str(e)}'
            }
    
    @staticmethod
    def _get_user_file_permissions(user_id: str, file_id: str) -> Dict[str, Any]:
        """
        Get user's permissions for a specific file
        
        Args:
            user_id: User ID
            file_id: File ID
            
        Returns:
            Permission dictionary
        """
        try:
            
            
            # Get user info
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return {}
            
            user_data = user_doc.to_dict()
            role = user_data.get('role', 'EMPLOYEE')
            department = user_data.get('department', '')
            
            # Get file info
            file_ref = db.collection('shared_files').document(file_id)
            file_doc = file_ref.get()
            
            if not file_doc.exists:
                return {}
            
            file_data = file_doc.to_dict()
            file_owner = file_data.get('owner_id', '')
            
            # Determine permissions based on role and ownership
            permissions = {
                'can_create_version': False,
                'can_approve_versions': False,
                'auto_approve_minor': False,
                'auto_approve_patch': False
            }
            
            # File owner permissions
            if user_id == file_owner:
                permissions.update({
                    'can_create_version': True,
                    'auto_approve_patch': True
                })
            
            # Role-based permissions
            if role == 'MANAGER':
                permissions.update({
                    'can_create_version': True,
                    'can_approve_versions': True,
                    'auto_approve_minor': True,
                    'auto_approve_patch': True
                })
            elif role == 'SENIOR_EMPLOYEE':
                permissions.update({
                    'can_create_version': True,
                    'auto_approve_patch': True
                })
            elif role == 'EMPLOYEE':
                permissions.update({
                    'can_create_version': True
                })
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return {}
