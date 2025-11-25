from enum import Enum

class OrderStatusEnum(str, Enum):
    PENDING = "chờ xác nhận"
    CONFIRMED = "đã xác nhận"
    PROCESSING = "đang xử lý"
    SHIPPED = "đã giao hàng"
    DELIVERED = "đã nhận hàng"
    CANCELLED = "đã hủy"
    REFUNDED = "đã hoàn tiền"
