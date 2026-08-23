from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError, APIException

def custom_exception_handler(exc, context):
    """
    Standardized Enterprise API Error Envelope.
    Format:
    {
        "success": false,
        "message": "Human readable error message",
        "code": "error_code_string",
        "errors": { ... } or null
    }
    """
    if isinstance(exc, DjangoValidationError):
        msgs = list(exc.messages) if hasattr(exc, 'messages') else [str(exc)]
        exc = DRFValidationError(msgs)
    elif isinstance(exc, IntegrityError):
        msg_str = str(exc)
        if 'unique' in msg_str.lower() or 'already exists' in msg_str.lower():
            exc = DRFValidationError({'detail': 'A record with these unique details already exists for this tenant/property.'})
        else:
            exc = DRFValidationError({'detail': 'Database constraint failure.'})

    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, 'default_code', 'error')

        if isinstance(exc, DRFValidationError):
            error_code = 'validation_error'
            message = 'Invalid input parameters.'
            errors = response.data
        elif hasattr(response, 'data') and isinstance(response.data, dict):
            # Extract clean message string from detail or first error
            raw_detail = response.data.get('detail')
            if raw_detail:
                message = str(raw_detail)
                errors = None
            else:
                message = 'An error occurred while processing your request.'
                errors = response.data
        else:
            message = str(exc)
            errors = response.data

        response.data = {
            'success': False,
            'message': message,
            'code': str(error_code),
            'errors': errors
        }
    else:
        # Unhandled 500 backend exceptions
        response = Response(
            {
                'success': False,
                'message': 'An unexpected server error occurred.',
                'code': 'internal_server_error',
                'errors': str(exc)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response


