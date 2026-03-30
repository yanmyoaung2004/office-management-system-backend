"""Utility functions and helpers."""
import re


def generate_id(prefix: str, model_class) -> str:
    """Generate ID like U001, STU001, MAJ001."""
    last = model_class.objects.filter(
        id__startswith=prefix
    ).order_by('-id').first()
    if last:
        match = re.search(r'(\d+)$', last.id)
        num = int(match.group(1)) + 1 if match else 1
    else:
        num = 1
    return f"{prefix}{num:03d}"


def custom_exception_handler(exc, context):
    """Custom exception handler for consistent API response format."""
    from rest_framework.views import exception_handler

    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data.get('detail', response.data)
        if isinstance(detail, list):
            custom_response = {
                'success': False,
                'error': detail[0] if detail else 'Validation failed',
                'code': 'VALIDATION_ERROR',
                'details': detail
            }
        elif isinstance(detail, dict):
            custom_response = {'success': False, 'error': detail, 'code': 'VALIDATION_ERROR'}
        else:
            custom_response = {
                'success': False,
                'error': str(detail),
                'code': {401: 'UNAUTHORIZED', 403: 'FORBIDDEN', 404: 'NOT_FOUND'}.get(
                    response.status_code, 'BAD_REQUEST'
                )
            }
        response.data = custom_response
    return response
