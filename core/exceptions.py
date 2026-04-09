class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

class NotFoundError(AppException):
    def __init__(self, message: str = "Data not found"):
        super().__init__(message, status_code=404)

class ValidationError(AppException):
    def __init__(self, message: str = "Invalid input data"):
        super().__init__(message, status_code=422)

class DatabaseError(AppException):
    def __init__(self, message: str = "Database connection error"):
        super().__init__(message, status_code=500)