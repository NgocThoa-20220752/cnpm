from enum import Enum

class PaymentStatusEnum(str, Enum):
    PENDING = "Chưa thanh toán"
    PAID = "đã thanh toán"
    FAILED = "thanh toán thất bại"
    REFUNDED = "đã hoàn tiền"