"""
Ollama Client SIMPLE FIX for llama3.2:3b
"""

import requests
import logging
from typing import Optional

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class OllamaClient:
    """Client SIMPLE - chỉ gọi Ollama cơ bản"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self.base_url = base_url
        self.model = model

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        timeout: int = 20  # Giảm timeout
    ) -> str:
        """
        Gọi Ollama SIÊU ĐƠN GIẢN
        """
        # RÚT GỌN prompt cực mạnh
        short_prompt = prompt[:100]  # Chỉ 100 ký tự

        payload = {
            "model": self.model,
            "prompt": short_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 80,  # Rất ngắn
                "top_k": 20,
                "top_p": 0.8,
                "num_ctx": 1024  # GIẢM context window
            }
        }

        # Thêm system nếu có (ngắn)
        if system:
            payload["system"] = system[:50]

        try:
            # Gọi API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout
            )

            if response.status_code == 200:
                data = response.json()
                reply = data.get("response", "").strip()

                if reply:
                    return reply[:200]  # Giới hạn response
                else:
                    return self._fallback(short_prompt)

            else:
                logger.error(f"Ollama error: {response.status_code}")
                return self._fallback(short_prompt)

        except requests.exceptions.Timeout:
            logger.warning("Ollama timeout")
            return "Xin lỗi, tôi đang xử lý. Vui lòng thử lại."
        except Exception as e:
            logger.error(f"Error: {e}")
            return "Tôi có thể giúp bạn chọn sản phẩm phù hợp."

    def _fallback(self, prompt: str) -> str:
        """Fallback cực đơn giản"""
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["chào", "hello", "hi"]):
            return "Xin chào! Tôi có thể giúp gì về skincare?"

        elif any(word in prompt_lower for word in ["da dầu", "dầu"]):
            return "Da dầu nên dùng sản phẩm kiềm dầu, làm sạch nhẹ."

        elif any(word in prompt_lower for word in ["da khô", "khô"]):
            return "Da khô cần dưỡng ẩm sâu với ceramide, hyaluronic acid."

        elif any(word in prompt_lower for word in ["mụn"]):
            return "Da mụn cần làm sạch sâu và thành phần kháng khuẩn."

        elif any(word in prompt_lower for word in ["chu trình", "routine"]):
            return "Chu trình cơ bản: Làm sạch → Toner → Serum → Dưỡng ẩm → Chống nắng."

        else:
            return "Tôi có thể tư vấn về skincare. Bạn quan tâm vấn đề gì?"

    def health_check(self) -> bool:
        """Check đơn giản"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except:
            return False


