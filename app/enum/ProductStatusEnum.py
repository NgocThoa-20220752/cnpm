from enum import Enum

class ProductStatusEnum(str, Enum):
    ACTIVE = "active"
    HIDDEN = "hidden"