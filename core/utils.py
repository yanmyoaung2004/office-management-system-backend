"""Utility functions and helpers."""
import re
from rest_framework.response import Response


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

def paginate_response(data, serializer_class, request, extra_data=None):
    """
    Helper for paginated list responses.
    Supports both Django QuerySets and pre-serialized Python Lists.
    """
    page = max(1, int(request.query_params.get('page', 1)))
    limit = min(max(1, int(request.query_params.get('limit', 10))), 100)
    offset = (page - 1) * limit
    is_list = isinstance(data, list)
    total = len(data) if is_list else data.count()
    items = data[offset:offset + limit]
    if is_list:
        serialized_data = items
    else:
        if serializer_class:
            serialized_data = serializer_class(items, many=True).data
        else:
            serialized_data = items

    return Response({
        'success': True,
        'data': serialized_data,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'totalPages': (total + limit - 1) // limit
        },
        **(extra_data or {})
    })

def success_response(data=None, message=None, status_code=200):
    """Standard success response."""
    resp = {'success': True}
    if message:
        resp['message'] = message
    if data is not None:
        resp['data'] = data
    return Response(resp, status=status_code)


def error_response(error, code='BAD_REQUEST', status_code=400):
    """Standard error response."""
    return Response({
        'success': False,
        'error': error,
        'code': code
    }, status=status_code)

