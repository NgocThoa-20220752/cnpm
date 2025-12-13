from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import json
import requests
import re
from app.models.product import Product, ProductDetail, ProductColor, ProductSize
from app.enum import ProductStatusEnum

logger = logging.getLogger(__name__)


class AIProductAdvisorService:
    """Service tư vấn sản phẩm dùng Ollama AI"""

    def __init__(self, db: Session, ollama_url: str = "http://localhost:11434"):
        self.db = db
        self.ollama_url = ollama_url
        self.model = "llama3.2:3b"  # Model bạn đang dùng

    def get_product_context(self) -> str:
        """Lấy thông tin sản phẩm cho context"""
        products = self.db.query(Product).filter_by(
            status=ProductStatusEnum.ACTIVE
        ).limit(12).all()

        if not products:
            return "Hiện chưa có sản phẩm nào."

        context_lines = ["📦 DANH SÁCH SẢN PHẨM:\n"]

        for product in products:
            # Category
            category = product.category.name if product.category else "Chưa phân loại"

            # Price range
            from sqlalchemy import func
            price_info = self.db.query(
                func.min(ProductDetail.price).label('min_price'),
                func.max(ProductDetail.price).label('max_price')
            ).filter_by(product_id=product.id).first()

            price_text = ""
            if price_info and price_info.min_price:
                if price_info.min_price == price_info.max_price:
                    price_text = f"{price_info.min_price:,.0f}đ"
                else:
                    price_text = f"{price_info.min_price:,.0f}đ - {price_info.max_price:,.0f}đ"
            else:
                price_text = "Đang cập nhật"

            # Basic info
            product_text = f"""
🔹 ID: {product.id}
📌 Tên: {product.name}
🏷️ Danh mục: {category}
💰 Giá: {price_text}
"""

            # Thêm mô tả nếu có
            detail = self.db.query(ProductDetail).filter_by(
                product_id=product.id
            ).first()

            if detail and detail.description:
                desc = detail.description[:80] + "..." if len(detail.description) > 80 else detail.description
                product_text += f"📝 Mô tả: {desc}\n"

            context_lines.append(product_text)

        return "\n".join(context_lines)

    def create_prompt(self, user_query: str, context: str, history: Optional[List[Dict]] = None) -> str:
        """Tạo prompt cho AI"""
        system_instruction = f"""Bạn là nhân viên tư vấn sản phẩm. Dưới đây là danh sách sản phẩm:

{context}

QUY ĐỊNH:
1. CHỈ đề xuất sản phẩm có trong danh sách trên
2. Khi đề xuất, PHẢI ghi rõ "ID: [số]" hoặc "Sản phẩm ID: [số]"
3. Trả lời ngắn gọn, tập trung vào sản phẩm phù hợp
4. Nếu không có sản phẩm phù hợp, nói "Hiện chưa có sản phẩm phù hợp với yêu cầu của bạn"
5. Tối đa 3 sản phẩm mỗi lần tư vấn

Hãy tư vấn thân thiện và chuyên nghiệp!"""

        # Thêm lịch sử chat nếu có
        conversation = ""
        if history:
            for msg in history[-4:]:  # Lấy 4 tin nhắn gần nhất
                if msg["role"] == "user":
                    conversation += f"Khách: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    conversation += f"Tư vấn: {msg['content']}\n"
            conversation += "\n"

        prompt = f"""{system_instruction}

{conversation}Khách: {user_query}

Tư vấn: """

        return prompt

    def call_ollama(self, prompt: str) -> str:
        """Gọi Ollama API - Phiên bản nhanh"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,  # Streaming để nhanh
                    "options": {
                        "num_predict": 400,  # Giới hạn độ dài
                        "temperature": 0.7,  # Độ sáng tạo
                        "top_p": 0.9,
                        "num_ctx": 2048  # Context size
                    }
                },
                stream=True,
                timeout=45  # Timeout 45 giây
            )

            if response.status_code != 200:
                logger.error(f"API error {response.status_code}: {response.text}")
                return "Hiện tại hệ thống đang bận. Vui lòng thử lại sau."

            # Đọc streaming response
            full_text = ""
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        chunk = data.get('response', '')
                        if chunk:
                            full_text += chunk
                    except json.JSONDecodeError:
                        continue

            return full_text.strip()

        except requests.exceptions.Timeout:
            logger.warning("Ollama timeout after 45s")
            return "Câu hỏi của bạn cần nhiều thời gian xử lý. Vui lòng hỏi ngắn gọn hơn."
        except Exception as e:
            logger.error(f"Lỗi gọi Ollama: {str(e)}")
            return "Đã có lỗi xảy ra. Vui lòng thử lại."

    def extract_product_ids(self, response: str) -> List[int]:
        """Trích xuất ID sản phẩm từ câu trả lời"""
        patterns = [
            r'ID:\s*(\d+)',
            r'Sản phẩm ID:\s*(\d+)',
            r'SP\s*(\d+)',
            r'#(\d+)',
            r'\[ID:\s*(\d+)\]',
            r'product\s*(\d+)',
            r'sản phẩm\s*(\d+)'
        ]

        found_ids = set()
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                try:
                    found_ids.add(int(match))
                except ValueError:
                    continue

        # Kiểm tra ID có tồn tại không
        valid_ids = []
        for pid in found_ids:
            exists = self.db.query(Product).filter_by(
                id=pid,
                status=ProductStatusEnum.ACTIVE
            ).first()
            if exists:
                valid_ids.append(pid)

        return valid_ids[:5]  # Tối đa 5 sản phẩm

    def get_product_details(self, product_ids: List[int]) -> List[Dict[str, Any]]:
        """Lấy chi tiết sản phẩm theo IDs"""
        if not product_ids:
            return []

        products = self.db.query(Product).filter(
            Product.id.in_(product_ids),
            Product.status == ProductStatusEnum.ACTIVE
        ).all()

        result = []
        for product in products:
            # Lấy giá
            from sqlalchemy import func
            price_info = self.db.query(
                func.min(ProductDetail.price).label('min_price'),
                func.max(ProductDetail.price).label('max_price')
            ).filter_by(product_id=product.id).first()

            # Lấy ảnh đại diện (nếu có field image_url)
            image_url = None
            if hasattr(product, 'image_url'):
                image_url = product.image_url
            elif hasattr(product, 'thumbnail'):
                image_url = product.thumbnail

            result.append({
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "category": product.category.name if product.category else None,
                "category_id": product.category.id if product.category else None,
                "min_price": float(price_info.min_price) if price_info and price_info.min_price else None,
                "max_price": float(price_info.max_price) if price_info and price_info.max_price else None,
                "image_url": image_url,
                "has_variants": self.db.query(ProductDetail).filter_by(product_id=product.id).count() > 1
            })

        return result

    def advise_products(self, user_query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[
        str, Any]:
        """
        Tư vấn sản phẩm chính

        Args:
            user_query: Câu hỏi của khách
            conversation_history: Lịch sử chat (tùy chọn)

        Returns:
            Dict chứa: advice, products, product_ids, product_count
        """
        # 1. Lấy context sản phẩm
        context = self.get_product_context()

        # 2. Tạo prompt
        prompt = self.create_prompt(user_query, context, conversation_history)
        logger.info(f"Prompt length: {len(prompt)} chars")

        # 3. Gọi AI
        ai_response = self.call_ollama(prompt)

        # 4. Trích xuất ID sản phẩm
        product_ids = self.extract_product_ids(ai_response)

        # 5. Lấy thông tin sản phẩm
        products = self.get_product_details(product_ids)

        return {
            "advice": ai_response,
            "products": products,
            "product_ids": product_ids,
            "product_count": len(products),
            "success": len(ai_response) > 0 and "lỗi" not in ai_response.lower()
        }

    def get_specific_product_info(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin chi tiết của 1 sản phẩm cụ thể"""
        product = self.db.query(Product).filter_by(
            id=product_id,
            status=ProductStatusEnum.ACTIVE
        ).first()

        if not product:
            return None

        # Lấy tất cả variants
        details = self.db.query(ProductDetail).filter_by(product_id=product_id).all()

        variants = []
        for detail in details:
            color = None
            size = None

            if detail.color_id:
                color = self.db.query(ProductColor).filter_by(id=detail.color_id).first()
            if detail.size_id:
                size = self.db.query(ProductSize).filter_by(id=detail.size_id).first()

            variant = {
                "id": detail.id,
                "price": float(detail.price) if detail.price else None,
                "stock": detail.stock,
                "color": color.name if color else None,
                "size": size.name if size else None,
                "packaging_type": detail.packaging_type.name if detail.packaging_type else None,
                "description": detail.description,
                "ingredients": detail.ingredients
            }
            variants.append(variant)

        return {
            "id": product.id,
            "name": product.name,
            "category": product.category.name if product.category else None,
            "description": product.description if hasattr(product, 'description') else None,
            "variants": variants,
            "total_variants": len(variants)
        }

    def answer_product_question(self, product_id: int, question: str) -> str:
        """Trả lời câu hỏi cụ thể về 1 sản phẩm"""
        product_info = self.get_specific_product_info(product_id)

        if not product_info:
            return "Không tìm thấy sản phẩm này."

        # Tạo prompt đặc biệt
        prompt = f"""Thông tin sản phẩm:
- Tên: {product_info['name']}
- Danh mục: {product_info['category']}
- Số phiên bản: {product_info['total_variants']}

Chi tiết các phiên bản:
"""
        for i, variant in enumerate(product_info['variants'][:3], 1):  # Lấy 3 variants đầu
            variant_text = f"{i}. "
            if variant['color']:
                variant_text += f"Màu: {variant['color']}, "
            if variant['size']:
                variant_text += f"Size: {variant['size']}, "
            variant_text += f"Giá: {variant['price']:,.0f}đ"

            if variant['description']:
                variant_text += f", Mô tả: {variant['description'][:50]}..."

            prompt += variant_text + "\n"

        prompt += f"\nKhách hỏi: {question}\n\nChuyên viên trả lời:"

        # Gọi AI
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 250}
                },
                timeout=20
            )

            if response.status_code == 200:
                return response.json().get('response', 'Đang xử lý...')
            else:
                return "Không thể trả lời câu hỏi này ngay lúc này."

        except Exception:
            return "Hệ thống đang bận. Vui lòng thử lại sau."