"""AI Assistant Views"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..permissions import IsSuperAdmin
import logging

logger = logging.getLogger('crypto_access.system')

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperAdmin])
def ai_status(request):
    """Check if AI service is available."""
    from ..services.ai_policy_service import ai_policy_service
    return Response({
        'enabled': ai_policy_service.enabled,
        'available': ai_policy_service.is_available(),
        'model': ai_policy_service.model,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSuperAdmin])
def generate_policy(request):
    """Generate ABAC + CP-ABE policy from natural language."""
    from ..services.ai_policy_service import ai_policy_service
    
    prompt = request.data.get('prompt', '').strip()
    if not prompt:
        return Response({'error': 'Prompt is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not ai_policy_service.is_available():
        return Response({'error': 'AI service is not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        result = ai_policy_service.generate_policy(prompt)
        
        # Validate the generated policy using existing test_policy logic
        validation = _validate_generated_policy(result.get('subject_condition', ''))
        result['validation'] = validation
        
        logger.info(f"AI policy generated for prompt: '{prompt[:50]}...'",
                     extra={"user.name": request.user.username, "user.id": request.user.id})
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"AI policy generation failed: {e}")
        return Response({'error': f'Generation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _validate_generated_policy(condition: str) -> dict:
    """Validate generated policy using existing AST parser + CP-ABE compiler."""
    import ast
    from crypto_access.models import AccessPolicy
    
    result = {'abac_valid': False, 'cpabe_valid': False, 'cpabe_policy': None, 'error': None}
    
    if not condition:
        result['error'] = 'Empty condition'
        return result
    
    # Test ABAC syntax
    try:
        expr = condition.replace('&&', ' and ').replace('||', ' or ')
        ast.parse(expr, mode='eval')
        result['abac_valid'] = True
    except SyntaxError as e:
        result['error'] = f'ABAC Syntax Error: {str(e)}'
        return result
    
    # Test CP-ABE compilation
    try:
        dummy = AccessPolicy(subject_condition=condition)
        cpabe_str = dummy._generate_cpabe_policy()
        result['cpabe_policy'] = cpabe_str
        if cpabe_str:
            result['cpabe_valid'] = True
    except Exception as e:
        result['error'] = f'CP-ABE Error: {str(e)}'
    
    return result
