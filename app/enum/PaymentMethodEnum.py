from enum import Enum

class PaymentMethodEnum(str, Enum):
    MOMO = "momo"
    VNPAY = "vnp"
    CASH = "thanh toán trực tiếp"