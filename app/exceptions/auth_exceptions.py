from fastapi import HTTPException, status


class UnauthorizedException(HTTPException):
    """Exception for unauthorized access"""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class InvalidCredentialsException(HTTPException):
    """Exception for invalid login credentials"""
    def __init__(self, detail: str = "Invalid username or password"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class TokenExpiredException(HTTPException):
    """Exception when token is expired"""
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class InvalidTokenException(HTTPException):
    """Exception for invalid token"""
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(HTTPException):
    """Exception for forbidden access"""
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class AccountLockedException(HTTPException):
    """Exception when account is locked"""
    def __init__(self, detail: str = "Account is locked"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)