from fastapi import HTTPException, status


class InsufficientStockException(HTTPException):
    """Exception when product stock is insufficient"""
    def __init__(self, detail: str = "Insufficient stock"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class PaymentFailedException(HTTPException):
    """Exception when payment fails"""
    def __init__(self, detail: str = "Payment failed"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class OrderCancellationException(HTTPException):
    """Exception when order cannot be cancelled"""
    def __init__(self, detail: str = "Cannot cancel this order"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)