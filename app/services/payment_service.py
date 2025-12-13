import logging
import hmac
import hashlib
from typing import Dict, Optional, Tuple
from decimal import Decimal
import uuid
import requests
from datetime import datetime
import time

from app.core import Settings

logger = logging.getLogger(__name__)


class RealPaymentService:
    def __init__(self, settings: Settings, is_production: bool = False, request_ip: Optional[str] = None):
        """
        Khởi tạo dịch vụ thanh toán
        """
        self.is_production = is_production
        self.settings = settings
        self.client_ip = request_ip or "127.0.0.1"

        # QUAN TRỌNG: ĐỂ CỨNG TEST CREDENTIALS KHI KHÔNG CÓ SETTINGS
        # Nếu settings trống, dùng test credentials
        if not hasattr(settings, 'VNP_TMN_CODE') or not settings.VNP_TMN_CODE:
            settings.VNP_TMN_CODE = "DEMOV210"
            settings.VNP_HASH_SECRET = "TEST_SECRET"

        # Load settings với defaults
        self.store_name = getattr(settings, 'STORE_NAME', 'Your Store')
        self.store_id = getattr(settings, 'STORE_ID', 'default_store')
        self.base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')

        # Validate settings
        self._validate_settings()

        self.config = self._load_config()
        logger.info(f"Payment service initialized - {'PRODUCTION' if is_production else 'SANDBOX'}")

    def _validate_settings(self):
        """Validate required settings"""
        required_vnpay = ['VNP_TMN_CODE', 'VNP_HASH_SECRET', 'VNP_RETURN_URL']
        required_momo = ['MOMO_PARTNER_CODE', 'MOMO_ACCESS_KEY', 'MOMO_SECRET_KEY', 'MOMO_REDIRECT_URL']

        missing_vnpay = []
        missing_momo = []

        for attr in required_vnpay:
            if not hasattr(self.settings, attr) or not getattr(self.settings, attr):
                missing_vnpay.append(attr)

        for attr in required_momo:
            if not hasattr(self.settings, attr) or not getattr(self.settings, attr):
                missing_momo.append(attr)

        if missing_vnpay:
            logger.warning(f"⚠️ VNPay settings missing: {', '.join(missing_vnpay)}")

        if missing_momo:
            logger.warning(f"⚠️ Momo settings missing: {', '.join(missing_momo)}")

    def _load_config(self) -> Dict:
        """Load configuration for payment gateways"""
        base = "sandbox." if not self.is_production else ""

        # QUAN TRỌNG: Định nghĩa webhook_base
        webhook_base = f"{self.base_url}/api/orders/payment/webhook"

        return {
            "vnpay": {
                "base_url": f"https://{base}vnpayment.vn/paymentv2/vpcpay.html",
                "terminal_id": getattr(self.settings, 'VNP_TMN_CODE', ''),
                "secret_key": getattr(self.settings, 'VNP_HASH_SECRET', ''),
                "return_url": getattr(self.settings, 'VNP_RETURN_URL', ''),
                "ipn_url": f"{webhook_base}/vnpay"
            },
            "momo": {
                "base_url": f"https://{base}payment.momo.vn/v2/gateway/api/create",
                "partner_code": getattr(self.settings, 'MOMO_PARTNER_CODE', ''),
                "access_key": getattr(self.settings, 'MOMO_ACCESS_KEY', ''),
                "secret_key": getattr(self.settings, 'MOMO_SECRET_KEY', ''),
                "return_url": getattr(self.settings, 'MOMO_REDIRECT_URL', ''),
                "ipn_url": f"{webhook_base}/momo",
                "store_id": self.store_id,
                "store_name": self.store_name
            }
        }

    def _create_hmac_signature(self, data: str, secret_key: str, algorithm: str = 'sha256') -> str:

        if algorithm == 'sha256':
            algo = hashlib.sha256
        elif algorithm == 'sha512':
            algo = hashlib.sha512
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        return hmac.new(
            secret_key.encode('utf-8'),
            data.encode('utf-8'),
            algo
        ).hexdigest()

    def _get_client_ip(self) -> str:
        """Lấy IP của client"""
        return self.client_ip

    def _is_valid_bank_code(self, bank_code: str) -> bool:
        """Validate VNPay bank code"""
        valid_banks = [
            "VCB", "BIDV", "VIB", "ACB", "MB", "TCB",
            "TECHCOMBANK", "VPB", "HDB", "MSB", "OCB",
            "SCB", "EXIMBANK", "AGRIBANK", "VIETINBANK",
            "NAB", "SHB", "PG", "SEA", "VP"
        ]
        return bank_code.upper() in valid_banks

    def _error_response(self, order_id: int, method: str, amount: Decimal, error_msg: str) -> Dict:
        """Tạo response lỗi"""
        return {
            "success": False,
            "error": error_msg,
            "order_id": order_id,
            "gateway": method.lower(),
            "amount": float(amount),
            "timestamp": datetime.now().isoformat()
        }

    def create_payment(self, method: str, order_id: int, order_code: str,
                       amount: Decimal, order_info: str = "",
                       bank_code: Optional[str] = None, **kwargs) -> Dict:
        """
        Tạo payment request
        """
        try:
            logger.info(f"Creating {method} payment for order {order_id}")

            # Validate amount
            if amount <= 0:
                return self._error_response(order_id, method, amount, "Invalid amount")

            # Validate method
            method_lower = method.lower()
            if method_lower not in ["vnpay", "momo"]:
                return self._error_response(order_id, method, amount, "Unsupported payment method")

            # Validate bank code if provided
            if method_lower == "vnpay" and bank_code and not self._is_valid_bank_code(bank_code):
                return self._error_response(order_id, method, amount, f"Invalid bank code: {bank_code}")

            # Set default order info
            order_info = order_info.strip() or f"Payment for order {order_code}"

            # Create payment based on method
            if method_lower == "vnpay":
                return self._create_vnpay_payment(order_id, order_code, amount, order_info, bank_code)
            elif method_lower == "momo":
                return self._create_momo_payment(order_id, order_code, amount, order_info, **kwargs)

        except Exception as e:
            logger.error(f"Payment creation failed for order {order_id}: {str(e)}")
            return self._error_response(order_id, method, amount, str(e))

    def _create_vnpay_payment(self, order_id: int, order_code: str, amount: Decimal,
                              order_info: str, bank_code: Optional[str] = None) -> Dict:
        config = self.config["vnpay"]

        # Prepare parameters
        params = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": config["terminal_id"],
            "vnp_Amount": str(int(amount * 100)),
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": order_code,
            "vnp_OrderInfo": order_info[:255],  # Tối đa 255 ký tự
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": config["return_url"],  # URL đơn giản, không thêm params
            "vnp_IpAddr": self._get_client_ip(),
            "vnp_CreateDate": datetime.now().strftime("%Y%m%d%H%M%S")
        }

        # Add bank code if valid
        if bank_code and self._is_valid_bank_code(bank_code):
            params["vnp_BankCode"] = bank_code.upper()

        # Tạo signature ĐÚNG CÁCH
        # 1. Tạo chuỗi query sắp xếp A-Z
        sorted_params = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params])

        # 2. QUAN TRỌNG: SHA512(secret_key + query_string)
        raw_signature = config["secret_key"] + query_string
        secure_hash = hashlib.sha512(raw_signature.encode('utf-8')).hexdigest()

        # 3. Thêm signature vào URL
        payment_url = f"{config['base_url']}?{query_string}&vnp_SecureHash={secure_hash}"

        logger.info(f"✅ VNPay payment created for order {order_id}")

        return {
            "success": True,
            "payment_url": payment_url,
            "transaction_id": order_code,
            "order_id": order_id,
            "gateway": "vnpay",
            "amount": float(amount),
            "message": "VNPay payment created successfully",
            "expires_in": "15 minutes",
            "timestamp": datetime.now().isoformat()
        }

    def _create_momo_payment(self, order_id: int, order_code: str, amount: Decimal,
                             order_info: str, **kwargs) -> Dict:

        config = self.config["momo"]
        request_id = str(uuid.uuid4())

        # Validate config
        if not all([config["partner_code"], config["access_key"], config["secret_key"]]):
            return self._error_response(order_id, "momo", amount, "Momo configuration missing")

        # Build extra data
        extra_parts = [f"order_id:{order_id}", f"order_code:{order_code}"]
        if email := kwargs.get('customer_email'):
            extra_parts.append(f"email:{email}")
        if phone := kwargs.get('customer_phone'):
            extra_parts.append(f"phone:{phone}")

        # Prepare parameters
        params = {
            "partnerCode": config["partner_code"],
            "partnerName": config["store_name"],
            "storeId": config["store_id"],
            "requestId": request_id,
            "amount": str(int(amount)),  # Momo expects amount in VND (not cents)
            "orderId": order_code,
            "orderInfo": f"{order_info} - OrderID:{order_id}",
            "redirectUrl": f"{config['return_url']}?order_id={order_id}&order_code={order_code}&gateway=momo",
            "ipnUrl": config["ipn_url"],
            "requestType": "captureWallet",
            "extraData": ";".join(extra_parts),
            "lang": "vi"
        }

        # Generate signature for Momo
        sig_data = "&".join([
            f"accessKey={config['access_key']}",
            f"amount={params['amount']}",
            f"extraData={params['extraData']}",
            f"ipnUrl={params['ipnUrl']}",
            f"orderId={params['orderId']}",
            f"orderInfo={params['orderInfo']}",
            f"partnerCode={params['partnerCode']}",
            f"redirectUrl={params['redirectUrl']}",
            f"requestId={params['requestId']}",
            f"requestType={params['requestType']}"
        ])

        params["signature"] = self._create_hmac_signature(sig_data, config["secret_key"], 'sha256')

        # Call Momo API with retry logic
        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                logger.info(f"Momo API attempt {attempt + 1} for order {order_id}")

                response = requests.post(
                    config["base_url"],
                    json=params,
                    timeout=30,
                    headers={"Content-Type": "application/json"}
                )

                response.raise_for_status()
                result = response.json()

                if result.get("resultCode") == 0:
                    logger.info(f"✅ Momo payment created for order {order_id}")
                    return {
                        "success": True,
                        "payment_url": result["payUrl"],
                        "transaction_id": request_id,
                        "deep_link": result.get("deeplink"),
                        "qr_code": result.get("qrCodeUrl"),
                        "order_id": order_id,
                        "gateway": "momo",
                        "amount": float(amount),
                        "message": "Momo payment created successfully",
                        "expires_in": "15 minutes",
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    error_code = result.get("resultCode", "UNKNOWN")
                    last_error = Exception(f"Momo error {error_code}: {error_msg}")

                    # Don't retry for certain errors
                    if error_code in [1006, 1001]:  # Invalid amount, duplicate request
                        break

            except requests.exceptions.Timeout:
                last_error = Exception(f"Momo API timeout (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError:
                last_error = Exception(f"Momo connection error (attempt {attempt + 1})")
            except Exception as e:
                last_error = e

            if attempt < max_attempts - 1:
                sleep_time = 2 ** attempt
                logger.warning(f"⚠️ Momo attempt {attempt + 1} failed, retrying in {sleep_time}s...")
                time.sleep(sleep_time)

        # All attempts failed
        error_msg = str(last_error) if last_error else "Momo payment failed after all retries"
        logger.error(f"❌ Momo payment failed for order {order_id}: {error_msg}")
        return self._error_response(order_id, "momo", amount, error_msg)

    def check_payment_status(self, order_id: int, gateway: Optional[str] = None) -> Dict:
        """
        Kiểm tra trạng thái thanh toán

        Args:
            order_id: ID đơn hàng
            gateway: Cổng thanh toán

        Returns:
            Dict chứa trạng thái thanh toán
        """
        try:
            logger.info(f"🔍 Checking payment status for order {order_id}")

            # TODO: Implement real API calls to check status
            # For now, return mock data
            return {
                "success": True,
                "status": "pending",
                "paid": False,
                "order_id": order_id,
                "gateway": gateway or "unknown",
                "checked_at": datetime.now().isoformat(),
                "message": "Payment status checked successfully",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Payment status check failed for order {order_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "order_id": order_id,
                "checked_at": datetime.now().isoformat(),
                "timestamp": datetime.now().isoformat()
            }

    def process_refund(self, order_id: int, amount: Decimal, reason: str = "") -> Dict:
        """
        Xử lý hoàn tiền

        Args:
            order_id: ID đơn hàng
            amount: Số tiền hoàn
            reason: Lý do hoàn tiền

        Returns:
            Dict chứa kết quả hoàn tiền
        """
        try:
            logger.info(f"💸 Processing refund for order {order_id}, amount: {amount}, reason: {reason}")

            if amount <= 0:
                return {
                    "success": False,
                    "error": "Refund amount must be greater than 0",
                    "order_id": order_id
                }

            refund_id = f"REFUND_{uuid.uuid4().hex[:8].upper()}"

            # TODO: Implement actual refund API calls
            # This is a mock implementation

            return {
                "success": True,
                "refund_id": refund_id,
                "order_id": order_id,
                "amount": float(amount),
                "reason": reason,
                "processed_at": datetime.now().isoformat(),
                "message": "Refund processed successfully",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Refund failed for order {order_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "order_id": order_id,
                "timestamp": datetime.now().isoformat()
            }

    def verify_payment_webhook(self, data: Dict, gateway: str) -> Dict:
        """
        Xác thực webhook từ payment gateway

        Args:
            data: Dữ liệu webhook
            gateway: Cổng thanh toán

        Returns:
            Dict chứa kết quả xác thực
        """
        try:
            logger.info(f"🔐 Verifying {gateway} webhook")

            if gateway == "momo":
                return self._verify_momo_webhook(data)
            elif gateway == "vnpay":
                return self._verify_vnpay_webhook(data)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported gateway: {gateway}",
                    "gateway": gateway,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"❌ Webhook verification failed for {gateway}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "gateway": gateway,
                "timestamp": datetime.now().isoformat()
            }

    def validate_payment_parameters(self, method: str, amount: Decimal,
                                    bank_code: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate payment parameters

        Args:
            method: Phương thức thanh toán
            amount: Số tiền
            bank_code: Mã ngân hàng

        Returns:
            Tuple (is_valid, error_message)
        """
        if amount <= 0:
            return False, "Amount must be greater than 0"

        if method.lower() not in ["vnpay", "momo"]:
            return False, f"Unsupported payment method: {method}"

        if method.lower() == "vnpay" and bank_code and not self._is_valid_bank_code(bank_code):
            return False, f"Invalid bank code for VNPay: {bank_code}"

        return True, "Parameters are valid"

    def _verify_momo_webhook(self, data: Dict) -> Dict:
        """
        Xác thực Momo webhook

        Args:
            data: Dữ liệu webhook từ Momo

        Returns:
            Dict chứa kết quả xác thực
        """
        try:
            momo_config = self.config["momo"]

            # Extract order_id từ extraData
            order_id = None
            extra_data = data.get("extraData", "")

            if "order_id:" in extra_data:
                try:
                    order_id_str = extra_data.split("order_id:")[1].split(";")[0]
                    order_id = int(order_id_str)
                except (ValueError, IndexError):
                    logger.warning(f"Could not extract order_id from extraData: {extra_data}")

            # Verify signature theo docs Momo
            signature_params = [
                f"accessKey={data.get('accessKey', momo_config['access_key'])}",
                f"amount={data.get('amount')}",
                f"extraData={data.get('extraData', '')}",
                f"message={data.get('message', '')}",
                f"orderId={data.get('orderId')}",
                f"orderInfo={data.get('orderInfo', '')}",
                f"orderType={data.get('orderType', '')}",
                f"partnerCode={data.get('partnerCode')}",
                f"payType={data.get('payType', '')}",
                f"requestId={data.get('requestId')}",
                f"responseTime={data.get('responseTime')}",
                f"resultCode={data.get('resultCode')}",
                f"transId={data.get('transId')}"
            ]

            raw_signature = "&".join(signature_params)
            signature = self._create_hmac_signature(raw_signature, momo_config["secret_key"], 'sha256')

            if signature != data.get("signature"):
                logger.warning(f"Momo webhook signature mismatch for order {order_id}")
                return {
                    "success": False,
                    "valid": False,
                    "error": "Invalid signature",
                    "order_id": order_id,
                    "gateway": "momo",
                    "timestamp": datetime.now().isoformat()
                }

            # Determine status based on resultCode
            result_code = data.get("resultCode")
            status = "failed"

            if result_code == 0:
                status = "completed"
            elif result_code in [1000, 1001, 1002, 1003, 1005, 1006]:
                status = "pending"
            elif result_code in [10, 11, 12, 13, 20, 22, 40, 41, 42]:
                status = "failed"
            else:
                status = "unknown"

            return {
                "success": True,
                "valid": True,
                "status": status,
                "order_id": order_id,
                "gateway": "momo",
                "transaction_id": data.get("transId"),
                "amount": float(int(data.get("amount", 0)) / 100),  # Convert from cents
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Momo webhook verification failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "gateway": "momo",
                "timestamp": datetime.now().isoformat()
            }

    def _verify_vnpay_webhook(self, data: Dict) -> Dict:
        try:
            vnpay_config = self.config["vnpay"]

            # Extract order_id từ orderInfo
            order_id = None
            order_info = data.get("vnp_OrderInfo", "")

            if "OrderID:" in order_info:
                try:
                    order_id_str = order_info.split("OrderID:")[1].split()[0]
                    order_id = int(order_id_str)
                except (ValueError, IndexError):
                    logger.warning(f"Could not extract order_id from orderInfo: {order_info}")

            # Verify signature
            vnp_SecureHash = data.get("vnp_SecureHash")
            if not vnp_SecureHash:
                return {
                    "success": False,
                    "valid": False,
                    "error": "Missing signature",
                    "order_id": order_id,
                    "gateway": "vnpay",
                    "timestamp": datetime.now().isoformat()
                }

            # FIX: Chuẩn bị data xác thực đúng cách
            # Loại bỏ signature và các field không cần thiết
            input_data = {k: v for k, v in data.items()
                          if k != "vnp_SecureHash" and k != "vnp_SecureHashType"}

            # Sắp xếp theo alphabet
            sorted_params = sorted(input_data.items())

            # Tạo chuỗi để hash
            hash_data = "&".join([f"{key}={value}" for key, value in sorted_params])

            # Tạo hash với cùng logic
            raw_signature = vnpay_config["secret_key"] + hash_data
            calculated_hash = hashlib.sha512(raw_signature.encode('utf-8')).hexdigest()

            if vnp_SecureHash.lower() != calculated_hash.lower():
                logger.warning(f"VNPay webhook signature mismatch for order {order_id}")
                logger.debug(f"Expected: {calculated_hash[:20]}..., Got: {vnp_SecureHash[:20]}...")
                return {
                    "success": False,
                    "valid": False,
                    "error": "Invalid signature",
                    "order_id": order_id,
                    "gateway": "vnpay",
                    "timestamp": datetime.now().isoformat()
                }

            # Determine status
            vnp_ResponseCode = data.get("vnp_ResponseCode")
            vnp_TransactionStatus = data.get("vnp_TransactionStatus")

            status = "failed"
            if vnp_ResponseCode == "00" and vnp_TransactionStatus == "00":
                status = "completed"
            elif vnp_TransactionStatus in ["01", "02"] or vnp_ResponseCode == "07":
                status = "pending"
            elif vnp_ResponseCode == "09":
                status = "refunded"
            elif vnp_ResponseCode == "10":
                status = "charged_back"

            return {
                "success": True,
                "valid": True,
                "status": status,
                "order_id": order_id,
                "gateway": "vnpay",
                "transaction_id": data.get("vnp_TransactionNo"),
                "bank_code": data.get("vnp_BankCode"),
                "amount": float(int(data.get("vnp_Amount", 0)) / 100),  # Convert from cents
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ VNPay webhook verification failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "gateway": "vnpay",
                "timestamp": datetime.now().isoformat()
            }

    def get_supported_bank_codes(self) -> list:
        """Get list of supported bank codes for VNPay"""
        return [
            "VCB", "BIDV", "VIB", "ACB", "MB", "TCB",
            "TECHCOMBANK", "VPB", "HDB", "MSB", "OCB",
            "SCB", "EXIMBANK", "AGRIBANK", "VIETINBANK",
            "NAB", "SHB", "PG", "SEA", "VP"
        ]

    def get_service_status(self) -> Dict:
        """Get service status and configuration info"""
        return {
            "service": "RealPaymentService",
            "production": self.is_production,
            "vnpay_configured": bool(self.config["vnpay"]["terminal_id"] and self.config["vnpay"]["secret_key"]),
            "momo_configured": bool(self.config["momo"]["partner_code"] and self.config["momo"]["secret_key"]),
            "base_url": self.base_url,
            "store_name": self.store_name,
            "timestamp": datetime.now().isoformat()
        }
