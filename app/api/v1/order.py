from fastapi import APIRouter, Depends, status, Query, Body, Request, HTTPException
from typing import Optional
from decimal import Decimal
from datetime import datetime, date, timedelta

from app.models import Customer
from app.schemas.request.order_req import CreateOrderRequest, UpdateOrderStatusRequest, BuyNowRequest
from app.schemas.response.order_resp import (
    OrderResponse, OrderDetailResponse,
    OrderListResponse, OrderWithPaymentResponse
)
from app.schemas.response.auth_resp import MessageResponse
from app.services.order_service import OrderService
from app.Dependencies import get_current_customer, get_admin_or_employee, get_order_service
from app.models.user import User
from app.models.order import Order
from app.enum import OrderStatusEnum, PaymentStatusEnum
from app.exceptions import ForbiddenException
from fastapi.responses import StreamingResponse
from app.services.export_service import ExportService, ExportFormat
import io

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== CUSTOMER ROUTES ====================

@router.post("", response_model=OrderWithPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
        request: CreateOrderRequest,
        current_user: User = Depends(get_current_customer),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Create new order (Customer only)
    """
    customer_id = current_user.id
    result = order_service.create_order(customer_id, request, {})
    return {
        "order": result["order"],
        "payment_result": result.get("payment_result")
    }


@router.get("/my-orders", response_model=OrderListResponse)
async def get_my_orders(
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        search: Optional[str] = Query(None, description="Search by order code"),
        order_status: Optional[str] = Query(None, description="Filter by order status"),
        current_user: User = Depends(get_current_customer),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get customer's orders with pagination
    """
    return order_service.get_customer_orders(
        customer_id=current_user.id,
        page=page,
        limit=limit,
        search=search,
        order_status=order_status
    )


@router.get("/my-orders/{order_id}", response_model=OrderDetailResponse)
async def get_my_order_detail(
        order_id: int,
        current_user: User = Depends(get_current_customer),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get order detail by ID (Customer only)
    """
    order = order_service.get_order_by_id(order_id)

    # Verify ownership
    if order.customer_id != current_user.id:
        raise ForbiddenException("You don't have permission to view this order")

    return order


@router.get("/my-orders/code/{order_code}", response_model=OrderDetailResponse)
async def get_my_order_by_code(
        order_code: str,
        current_user: User = Depends(get_current_customer),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get order detail by order code (Customer only)
    """
    order = order_service.get_order_by_code(order_code)

    # Verify ownership
    if order.customer_id != current_user.id:
        raise ForbiddenException("You don't have permission to view this order")

    return order


@router.put("/my-orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_my_order(
        order_id: int,
        reason: Optional[str] = Body(None, embed=True),
        current_user: User = Depends(get_current_customer),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Cancel order (Customer only)
    """
    return order_service.cancel_order(order_id, current_user.id, reason)


@router.post("/my-orders/{order_id}/request-return", response_model=MessageResponse)
async def request_order_return(
        order_id: int,
        reason: str = Body(..., embed=True, min_length=1),  # Giảm min_length để dễ test
        current_user: User = Depends(get_current_customer),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Request order return/refund (Customer only)
    """
    return order_service.request_order_return(order_id, current_user.id, reason)


# ==================== NEW CUSTOMER ENDPOINTS ====================

@router.put("/my-orders/{order_id}/confirm-receipt", response_model=OrderResponse)
async def confirm_order_receipt(
        order_id: int,
        current_user: User = Depends(get_current_customer),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Customer confirms order receipt
    """
    return order_service.confirm_order_receipt(order_id, current_user.id)


@router.get("/my-orders/{order_id}/payment-status")
async def get_payment_status(
        order_id: int,
        current_user: User = Depends(get_current_customer),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Check payment status
    """
    return order_service.check_payment_status(order_id, current_user.id)


# ==================== PAYMENT WEBHOOK ====================

@router.post("/payment/webhook/{gateway}")
async def payment_webhook(
        gateway: str,
        request: Request,
        order_service: OrderService = Depends(get_order_service)
):
    """
    Payment gateway webhook (VNPay/Momo)
    """
    try:
        # VNPay dùng query params, Momo dùng JSON body
        if gateway.lower() == "vnpay":
            data = dict(request.query_params)
        else:  # momo
            data = await request.json()

        logger.info(f"📩 {gateway} webhook received: {data}")
        result = order_service.process_payment_webhook(gateway, data)

        # Trả response theo chuẩn từng gateway
        if gateway.lower() == "vnpay":
            return {"RspCode": "00" if result.get("success") else "99"}
        else:  # momo
            return {"resultCode": 0 if result.get("success") else 1}

    except Exception as e:
        logger.error(f"❌ {gateway} webhook error: {str(e)}")

        # Trả lỗi theo chuẩn gateway
        if gateway.lower() == "vnpay":
            return {"RspCode": "99", "Message": "Error"}
        else:
            return {"resultCode": 1, "message": "Error"}


# ==================== AUTO CANCELLATION ====================

@router.post("/auto-cancel-unpaid")
async def auto_cancel_unpaid_orders(
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Auto cancel unpaid orders (Admin/Employee only)
    """
    return order_service.auto_cancel_unpaid_orders()


# ==================== ADMIN/EMPLOYEE ROUTES ====================

@router.get("", response_model=OrderListResponse)
async def get_all_orders(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        search: Optional[str] = Query(None, description="Search by order code or customer info"),
        order_status: Optional[str] = Query(None, description="Filter by order status"),
        payment_status: Optional[str] = Query(None, description="Filter by payment status"),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get all orders (Admin/Employee only)
    """
    return order_service.get_all_orders(page, limit, search, order_status, payment_status)


@router.get("/statistics")
async def get_order_statistics(
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get order statistics (Admin/Employee only)
    """
    return order_service.get_order_statistics()


@router.get("/pending-count")
async def get_pending_orders_count(
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get count of pending orders (Admin/Employee only)
    """
    from sqlalchemy import func
    count = order_service.db.query(func.count(Order.id)).filter_by(order_status=OrderStatusEnum.PENDING).scalar()
    return {"pending_orders_count": count}


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order_detail(
        order_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get order detail by ID (Admin/Employee only)
    """
    return order_service.get_order_by_id(order_id)


@router.get("/code/{order_code}", response_model=OrderDetailResponse)
async def get_order_by_code(
        order_code: str,
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get order detail by order code (Admin/Employee only)
    """
    return order_service.get_order_by_code(order_code)


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
        order_id: int,
        request: UpdateOrderStatusRequest,
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Update order status (Admin/Employee only)
    """
    return order_service.update_order_status(order_id, request)


@router.put("/{order_id}/confirm", response_model=OrderResponse)
async def confirm_order(
        order_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Confirm order (Admin/Employee only)
    """
    return order_service.confirm_order(order_id)


@router.put("/{order_id}/ship", response_model=OrderResponse)
async def ship_order(
        order_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Mark order as shipped (Admin/Employee only)
    """
    return order_service.ship_order(order_id)


@router.put("/{order_id}/deliver", response_model=OrderResponse)
async def deliver_order(
        order_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Mark order as delivered (Admin/Employee only)
    """
    return order_service.deliver_order(order_id)


# ==================== NEW ADMIN CANCEL ENDPOINT ====================

@router.put("/{order_id}/admin-cancel", response_model=OrderResponse)
async def admin_cancel_order(
        order_id: int,
        reason: Optional[str] = Body(None, embed=True),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Cancel order as admin (Admin/Employee only) - with extended privileges
    """
    return order_service.admin_cancel_order(order_id, reason)


@router.put("/{order_id}/approve-return", response_model=OrderResponse)
async def approve_order_return(
        order_id: int,
        approved: bool = Body(..., embed=True),
        note: Optional[str] = Body(None, embed=True),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Approve/Reject order return request (Admin/Employee only)
    """
    return order_service.approve_order_return(order_id, approved, note)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
        order_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Delete order (Admin only)
    """
    order_service.delete_order(order_id)
    return None


# ==================== REPORTS ====================

@router.get("/reports/revenue")
async def get_revenue_report(
        start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get revenue report (Admin/Employee only)
    """
    return order_service.get_revenue_report(start_date, end_date)


@router.get("/reports/best-selling")
async def get_best_selling_products(
        limit: int = Query(10, ge=1, le=100),
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get best selling products (Admin/Employee only)
    """
    return order_service.get_best_selling_products(limit, start_date, end_date)


@router.get("/reports/customer-orders")
async def get_customer_orders_report(
        limit: int = Query(10, ge=1, le=100),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get customers with most orders (Admin/Employee only)
    """
    return order_service.get_customer_orders_report(limit)


@router.post("/buy-now", response_model=OrderWithPaymentResponse, status_code=status.HTTP_201_CREATED)
async def buy_now_product(
        request: BuyNowRequest,
        current_user: User = Depends(get_current_customer),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Mua ngay sản phẩm (không qua giỏ hàng)
    """
    try:
        result = order_service.buy_now(
            customer_id=current_user.id,
            product_id=request.product_id,
            quantity=request.quantity,
            shipping_info={
                "shipping_address": request.shipping_address,
                "shipping_phone": request.shipping_phone,
                "payment_method": request.payment_method,
                "shipping_fee": request.shipping_fee or Decimal('0'),
                "customer_note": request.customer_note
            },
            color_id=request.color_id,
            size_id=request.size_id
        )

        return {
            "order": result["order"],
            "payment_result": result.get("payment_result")
        }

    except Exception as e:
        logger.error(f"Buy now failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export")
async def export_orders(
        format_type: str = Query(..., description="excel, pdf, csv, or txt"),
        start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
        end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
        order_status: Optional[str] = Query(None),
        payment_status: Optional[str] = Query(None),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Export orders report (Admin/Employee only)
    """
    try:
        export_format = ExportFormat(format_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid format. Use: excel, pdf, csv, or txt")

    # Lấy orders theo filter
    query = order_service.db.query(Order)

    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(Order.created_at >= start_dt)

    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.filter(Order.created_at <= end_dt)

    if order_status:
        query = query.filter_by(order_status=OrderStatusEnum(order_status))

    if payment_status:
        query = query.filter_by(payment_status=PaymentStatusEnum(payment_status))

    orders = query.order_by(Order.created_at.desc()).all()

    # Export
    export_service = ExportService(order_service.db)
    result = export_service.export_orders_report(
        format_type=export_format,
        orders=orders,
        start_date=start_date,
        end_date=end_date,
        filter_status=order_status
    )

    return StreamingResponse(
        io.BytesIO(result["content"]),
        media_type=result["content_type"],
        headers={
            "Content-Disposition": f"attachment; filename={result['filename']}"
        }
    )


@router.get("/export/statistics")
async def export_statistics(
        format_type: str = Query(..., description="excel, csv, or txt"),
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Export statistics report (Admin/Employee only)
    """
    try:
        export_format = ExportFormat(format_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid format")

    # Lấy dữ liệu thống kê
    statistics = order_service.get_order_statistics()
    revenue_report = order_service.get_revenue_report(start_date, end_date)
    best_sellers = order_service.get_best_selling_products(limit=20, start_date=start_date, end_date=end_date)

    # Export
    export_service = ExportService(order_service.db)
    result = export_service.export_statistics_report(
        format_type=export_format,
        statistics=statistics,
        revenue_report=revenue_report,
        best_sellers=best_sellers
    )

    return StreamingResponse(
        io.BytesIO(result["content"]),
        media_type=result["content_type"],
        headers={
            "Content-Disposition": f"attachment; filename={result['filename']}"
        }
    )


# ==================== BULK OPERATIONS ====================

from pydantic import BaseModel
from typing import List as TypingList


class BulkUpdateStatusRequest(BaseModel):
    order_ids: TypingList[int]
    new_status: str


@router.put("/bulk-update-status")
async def bulk_update_order_status(
        request: BulkUpdateStatusRequest,
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Bulk update order status (Admin/Employee only)
    """
    updated_count = 0
    failed_orders = []

    for order_id in request.order_ids:
        try:
            order_service.update_order_status(
                order_id,
                UpdateOrderStatusRequest(order_status=request.new_status)
            )
            updated_count += 1
        except Exception as e:
            failed_orders.append({
                "order_id": order_id,
                "error": str(e)
            })

    return {
        "updated_count": updated_count,
        "failed_count": len(failed_orders),
        "failed_orders": failed_orders
    }


@router.post("/bulk-cancel")
async def bulk_cancel_orders(
        order_ids: TypingList[int] = Body(...),
        reason: Optional[str] = Body(None),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Bulk cancel orders (Admin/Employee only)
    """
    cancelled_count = 0
    failed_orders = []

    for order_id in order_ids:
        try:
            order_service.admin_cancel_order(order_id, reason)
            cancelled_count += 1
        except Exception as e:
            failed_orders.append({
                "order_id": order_id,
                "error": str(e)
            })

    return {
        "cancelled_count": cancelled_count,
        "failed_count": len(failed_orders),
        "failed_orders": failed_orders
    }


# ==================== ORDER SEARCH ====================

@router.get("/search")
async def search_orders(
        q: str = Query(..., min_length=1, description="Search query"),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Advanced search orders (Admin/Employee only)
    """
    from sqlalchemy import or_

    query = order_service.db.query(Order).join(Customer).join(User)

    # Search trong multiple fields
    search_filter = or_(
        Order.order_code.ilike(f"%{q}%"),
        User.fullname.ilike(f"%{q}%"),
        User.email.ilike(f"%{q}%"),
        Order.shipping_address.ilike(f"%{q}%"),
        Order.shipping_phone.ilike(f"%{q}%")
    )

    query = query.filter(search_filter).order_by(Order.created_at.desc())

    total = query.count()
    orders = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "query": q,
        "data": orders
    }


# ==================== ORDER ANALYTICS ====================

@router.get("/analytics/daily")
async def get_daily_analytics(
        days: int = Query(7, ge=1, le=90, description="Number of days"),
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get daily order analytics (Admin/Employee only)
    """
    from datetime import timedelta

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Lấy orders trong khoảng thời gian
    orders = order_service.db.query(Order).filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).all()

    # Group by date
    daily_data = {}
    for order in orders:
        date_key = order.created_at.strftime("%Y-%m-%d")

        if date_key not in daily_data:
            daily_data[date_key] = {
                "date": date_key,
                "total_orders": 0,
                "total_revenue": 0,
                "orders_by_status": {}
            }

        daily_data[date_key]["total_orders"] += 1

        if order.payment_status == PaymentStatusEnum.PAID:
            daily_data[date_key]["total_revenue"] += float(order.total_amount)

        status = order.order_status.value
        daily_data[date_key]["orders_by_status"][status] = \
            daily_data[date_key]["orders_by_status"].get(status, 0) + 1

    return {
        "period": f"Last {days} days",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "data": list(daily_data.values())
    }


@router.get("/analytics/overview")
async def get_analytics_overview(
        _current_user: User = Depends(get_admin_or_employee),
        order_service: OrderService = Depends(get_order_service)
):
    """
    Get comprehensive analytics overview (Admin/Employee only)
    """
    from sqlalchemy import func

    today = date.today()
    yesterday = today - timedelta(days=1)
    this_month_start = datetime(today.year, today.month, 1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

    # Today vs Yesterday
    today_orders = order_service.db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == today
    ).scalar() or 0

    yesterday_orders = order_service.db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == yesterday
    ).scalar() or 0

    # This month vs Last month
    this_month_orders = order_service.db.query(func.count(Order.id)).filter(
        Order.created_at >= this_month_start
    ).scalar() or 0

    last_month_orders = order_service.db.query(func.count(Order.id)).filter(
        Order.created_at >= last_month_start,
        Order.created_at < this_month_start
    ).scalar() or 0

    # Revenue
    this_month_revenue = order_service.db.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= this_month_start,
        Order.payment_status == PaymentStatusEnum.PAID
    ).scalar() or 0

    # Average order value
    avg_order_value = order_service.db.query(func.avg(Order.total_amount)).filter(
        Order.payment_status == PaymentStatusEnum.PAID
    ).scalar() or 0

    return {
        "today": {
            "orders": today_orders,
            "change_from_yesterday": today_orders - yesterday_orders
        },
        "this_month": {
            "orders": this_month_orders,
            "revenue": float(this_month_revenue),
            "change_from_last_month": this_month_orders - last_month_orders
        },
        "averages": {
            "order_value": float(avg_order_value)
        },
        "statistics": order_service.get_order_statistics()
    }