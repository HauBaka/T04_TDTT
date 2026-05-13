class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)

        self.message = message
        self.status_code = status_code

class NotFoundError(AppException):
    def __init__(self, message: str = "Data not found"):
        super().__init__(message, status_code=404)

class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, status_code=400)

class ValidationError(AppException):
    def __init__(self, message: str = "Invalid input data"):
        super().__init__(message, status_code=422)

class InternalServerError(AppException):
    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=500)

class DatabaseError(InternalServerError):
    def __init__(self, message: str = "Database connection error"):
        super().__init__(message)

class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)

class ConflictError(AppException):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, status_code=409)

class DuplicateEntryError(ConflictError):
    def __init__(self, message: str = "Duplicate entry"):
        super().__init__(message)

class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)
    
class RateLimitExceededError(AppException):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)

class ServiceUnavailableError(AppException):
    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message, status_code=503)