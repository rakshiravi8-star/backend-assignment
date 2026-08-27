from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class ApplicationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'An error occurred.'
    default_code = 'error'


class EmailAlreadyRegistered(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'This email is already registered and verified.'
    default_code = 'email_already_registered'


class ResendCooldownActive(ApplicationError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Please wait before requesting another verification code.'
    default_code = 'otp_resend_cooldown'


class InvalidOTP(ApplicationError):
    default_detail = 'Invalid verification code.'
    default_code = 'invalid_otp'


class OTPExpired(ApplicationError):
    default_detail = 'Verification code has expired. Please request a new one.'
    default_code = 'otp_expired'


class OTPLocked(ApplicationError):
    default_detail = 'Too many failed attempts. Please request a new verification code.'
    default_code = 'otp_locked'


class InvalidCredentials(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Invalid email or password.'
    default_code = 'invalid_credentials'


class EmailNotVerified(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Email is not verified.'
    default_code = 'email_not_verified'


class EventFull(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'This event has reached its capacity.'
    default_code = 'event_full'


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ApplicationError):
        message = str(exc.detail)
        code = exc.default_code
    elif isinstance(response.data, dict):
        detail = response.data
        if 'detail' in detail and len(detail) == 1:
            message, code = str(detail['detail']), getattr(exc, 'default_code', 'error')
        else:
            field = next(iter(detail))
            first_error = detail[field]
            if isinstance(first_error, list) and first_error:
                first_error = first_error[0]
            message, code = f'{field}: {first_error}', 'validation_error'
    elif response.data:
        message, code = str(response.data[0]), getattr(exc, 'default_code', 'error')
    else:
        message, code = str(response.data), getattr(exc, 'default_code', 'error')
    response.data = {'detail': message, 'code': code}
    return response