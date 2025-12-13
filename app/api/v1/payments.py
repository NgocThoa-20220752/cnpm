# app/api/payments.py
from decimal import Decimal
from fastapi import APIRouter, Query
from app.core.config import get_settings
from app.services.payment_service import RealPaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("/create")
async def create_payment(
        order_id: int,
        amount: float,
        method: str = "vnpay"
):
    """API endpoint cho frontend"""
    settings = get_settings()

    payment_service = RealPaymentService(
        settings=settings,
        is_production=False
    )

    result = payment_service.create_payment(
        method=method,
        order_id=order_id,
        order_code=f"ORDER_{order_id}",
        amount=Decimal(str(amount)),
        order_info=f"Thanh toán đơn hàng #{order_id}"
    )

    return result


@router.get("/vnpay/callback")
async def vnpay_callback(
    vnp_response_code: str = Query(None, alias="vnp_ResponseCode"),
    vnp_transaction_no: str = Query(None, alias="vnp_TransactionNo"),
    order_id: int = Query(None, alias="order_id")
):
    """Endpoint VNPay redirect về"""
    return {
        "success": vnp_response_code == "00",
        "message": "Payment successful" if vnp_response_code == "00" else "Payment failed",
        "order_id": order_id,
        "transaction_id": vnp_transaction_no
    }


@router.get("/momo/callback")
async def momo_callback(
        result_code: str = Query(None, alias="resultCode"),
        message: str = Query(None),
        order_id: str = Query(None, alias="orderId"),
        trans_id: str = Query(None, alias="transId"),
        amount: str = Query(None),
        extra_data: str = Query(None, alias="extraData")
):
    """Endpoint Momo redirect về"""

    # Extract order_id từ extraData nếu có
    extracted_order_id = None
    if extra_data and "order_id:" in extra_data:
        try:
            # Tìm vị trí order_id: trong extra_data
            start_idx = extra_data.find("order_id:") + len("order_id:")
            # Lấy phần sau order_id: cho đến khi gặp ; hoặc hết
            end_idx = extra_data.find(";", start_idx)
            if end_idx == -1:
                end_idx = len(extra_data)

            order_id_str = extra_data[start_idx:end_idx].strip()
            extracted_order_id = int(order_id_str)
        except (ValueError, IndexError, AttributeError):
            # Bỏ qua nếu không parse được
            pass

    return {
        "success": result_code == "0",
        "message": message,
        "order_id": extracted_order_id,
        "order_code": order_id,
        "transaction_id": trans_id,
        "amount": amount,
        "extra_data": extra_data
    }