from enum import Enum

class RoleEnum(str, Enum):
    CUSTOMER = "khách hàng"
    ADMIN = "admin"
    EMPLOYEE = "nhân viên"