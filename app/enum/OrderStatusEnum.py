from enum import Enum

class OrderStatusEnum(str, Enum):
    PENDING = "chờ xác nhận"
    CONFIRMED = "đã xác nhận"
    PROCESSING = "đang xử lý"
    SHIPPED = "đã giao hàng"
    DELIVERED = "đã nhận hàng"
    CANCELLED = "đã hủy"
    REFUNDED = "đã hoàn tiền"

    # Thêm trạng thái cho trả hàng
    RETURN_REQUESTED = "yêu cầu trả hàng"
    RETURN_APPROVED = "đã chấp nhận trả hàng"
    RETURN_REJECTED = "từ chối trả hàng"
    RETURNED = "đã trả hàng"