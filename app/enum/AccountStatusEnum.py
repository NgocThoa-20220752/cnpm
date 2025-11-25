from enum import Enum

class AccountStatusEnum(str, Enum):
    PENDING = "chờ kích hoạt"
    ACTIVE = "hoạt động"
    INACTIVE = "tạm ngừng"
    LOCKED = "khóa tài khoản"
    SUSPENDED = "tạm khóa"
    BANNED = "cấm vĩnh viễn"
    DELETED = "đã xóa"