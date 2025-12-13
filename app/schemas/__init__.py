from app.schemas.request.auth_req import (
LoginRequest,
RegisterRequest,
ResetPasswordRequest,
ForgotPasswordRequest,
ChangePasswordRequest
)

from app.schemas.response.auth_resp import (
LoginResponse,
TokenResponse,
MessageResponse
)

from app.schemas.request.user_req import (
UpdateUserRequest,
UpdateEmployeeRequest,
CreateEmployeeRequest
)

from app.schemas.response.user_resp import (
UserResponse,
EmployeeResponse,
AccountResponse
)

from app.schemas.request.product_req import (
CreateProductRequest,
CreateProductColorRequest,
CreateProductImageRequest,
CreateProductSizeRequest,
CreateProductDetailRequest,
UpdateProductDetailRequest,
CreatePackagingTypeRequest,
UpdateProductRequest
)

from app.schemas.response.product_resp import (
ProductImageResponse,
LowStockProductResponse,
ProductFullDetailResponse,
ProductSizeResponse,
ProductListResponse,
ProductDetailResponse,
ProductColorResponse,
ProductResponse,
PackagingTypeResponse,
ProductCategoryResponse
)

from app.schemas.request.category_req import (
UpdateCategoryRequest,
CreateCategoryRequest
)

from app.schemas.response.category_resp import (
CategoryResponse,
CategoryListResponse,
CategoryWithChildrenResponse
)

from app.schemas.request.cart_req import (
AddToCartRequest,
UpdateCartItemRequest
)

from app.schemas.response.cart_resp import (
CartResponse,
CartItemProductResponse,
CartItemResponse
)

from app.schemas.request.order_req import (
CreateOrderRequest,
UpdateOrderStatusRequest,
OrderItemRequest
)

from app.schemas.response.order_resp import (
OrderResponse,
OrderItemProductResponse,
OrderItemResponse,
OrderListResponse,
OrderDetailResponse
)

from app.schemas.request.ai_req import AIChatRequest,TestAIRequest

from app.schemas.response.ai_resp import (
HealthResponse,
TestAIResponse,
ErrorResponse,
ProductRecommendation,
AIChatResponse
)

__all__ = {

    # auth req
    "ChangePasswordRequest",
    "RegisterRequest",
    "ResetPasswordRequest",
    "LoginRequest",
    "ForgotPasswordRequest",

    #auth resp
    "MessageResponse",
    "TokenResponse",
    "LoginResponse",

    # user req
    "UpdateUserRequest",
    "UpdateEmployeeRequest",
    "CreateEmployeeRequest",

    #user resp
    "UserResponse",
    "AccountResponse",
    "EmployeeResponse",

    # product req
    "UpdateProductRequest",
    "CreateProductRequest",
    "CreateProductColorRequest",
    "CreateProductImageRequest",
    "CreateProductSizeRequest",
    "CreateProductDetailRequest",
    "UpdateProductDetailRequest",
    "CreatePackagingTypeRequest",

    # product resp
    "ProductResponse",
    "ProductCategoryResponse",
    "ProductColorResponse",
    "ProductSizeResponse",
    "ProductListResponse",
    "ProductDetailResponse",
    "PackagingTypeResponse",
    "LowStockProductResponse",
    "ProductFullDetailResponse",
    "ProductImageResponse",

    # category req
    "CreateCategoryRequest",
    "UpdateCategoryRequest",

    #category resp
    "CategoryListResponse",
    "CategoryWithChildrenResponse",
    "CategoryResponse",

    # cart req
    "AddToCartRequest",
    "UpdateCartItemRequest",

    # cart resp
    "CartResponse",
    "CartItemResponse",
    "CartItemProductResponse",

    # order req
    "OrderItemRequest",
    "CreateOrderRequest",
    "UpdateOrderStatusRequest",

    # order resp
    "OrderResponse",
    "OrderListResponse",
    "OrderDetailResponse",
    "OrderItemResponse",
    "OrderItemProductResponse",

    # ai req
    "AIChatRequest",
    "TestAIRequest",

    # ai resp
    "AIChatResponse",
    "ErrorResponse",
    "HealthResponse",
    "TestAIResponse",
    "ProductRecommendation",



}