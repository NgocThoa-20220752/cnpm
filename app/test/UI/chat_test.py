# fast_chat_working.py - File duy nhất, nút Gửi hoạt động
from flask import Flask, render_template_string, request, jsonify, Response, stream_with_context
import requests
import json
import time

app = Flask(__name__)

# Config
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Chat - Nhanh như CMD</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: #ffffff;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .chat-container {
            width: 100%;
            max-width: 900px;
            height: 90vh;
            background: #2d2d2d;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .header {
            background: #3a3a3a;
            padding: 15px 20px;
            color: white;
            font-size: 18px;
            font-weight: bold;
            border-bottom: 1px solid #444;
        }
        .chat-box {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #1e1e1e;
        }
        .message {
            margin: 15px 0;
            padding: 12px 16px;
            border-radius: 8px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .user-message {
            background: #0078d4;
            color: white;
            margin-left: auto;
            text-align: right;
        }
        .bot-message {
            background: #333333;
            color: #e0e0e0;
            margin-right: auto;
            border-left: 3px solid #0078d4;
        }
        .input-area {
            padding: 15px;
            background: #3a3a3a;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        input {
            flex: 1;
            padding: 12px 15px;
            border: 2px solid #555;
            border-radius: 6px;
            background: #222;
            color: white;
            font-size: 14px;
            outline: none;
        }
        input:focus {
            border-color: #0078d4;
        }
        button {
            padding: 12px 24px;
            background: #0078d4;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #005a9e;
        }
        button:disabled {
            background: #555;
            cursor: not-allowed;
        }
        .typing {
            display: inline-flex;
            align-items: center;
        }
        .dot {
            width: 8px;
            height: 8px;
            background: #999;
            border-radius: 50%;
            margin: 0 2px;
            animation: bounce 1.4s infinite;
        }
        .dot:nth-child(2) { animation-delay: 0.2s; }
        .dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-5px); }
        }
        .timestamp {
            font-size: 11px;
            color: #999;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">🤖 AI Chat - Nhấn nút Gửi hoặc Enter</div>

        <div class="chat-box" id="chatBox">
            <div style="text-align:center; padding:40px; color:#999;">
                <h3>Chào bạn! 👋</h3>
                <p>Nhập tin nhắn và nhấn nút <strong>Gửi</strong> hoặc phím <strong>Enter</strong></p>
            </div>
        </div>

        <div class="input-area">
            <input type="text" id="userInput" placeholder="Nhập tin nhắn của bạn..." autocomplete="off">
            <button onclick="sendMessageNow()" id="sendBtn">Gửi</button>
        </div>
    </div>

    <script>
        // Gắn sự kiện khi trang load xong
        document.addEventListener('DOMContentLoaded', function() {
            console.log('✅ Trang đã load xong');

            const btn = document.getElementById('sendBtn');
            const input = document.getElementById('userInput');

            // Gắn sự kiện click cho button
            btn.addEventListener('click', sendMessageNow);

            // Gắn sự kiện Enter cho input
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    sendMessageNow();
                }
            });

            // Focus vào input
            input.focus();
        });

        async function sendMessageNow() {
            console.log('🎯 Hàm sendMessageNow được gọi');

            const input = document.getElementById('userInput');
            const btn = document.getElementById('sendBtn');
            const chatBox = document.getElementById('chatBox');
            const text = input.value.trim();

            console.log('Tin nhắn:', text);

            if (!text) {
                alert('⚠️ Vui lòng nhập tin nhắn!');
                return;
            }

            // Vô hiệu hóa nút và input
            btn.disabled = true;
            input.disabled = true;
            btn.textContent = 'Đang xử lý...';

            // Hiển thị tin nhắn người dùng
            const userTime = new Date().toLocaleTimeString();
            const userMsg = document.createElement('div');
            userMsg.className = 'message user-message';
            userMsg.innerHTML = `${text}<div class="timestamp">${userTime}</div>`;
            chatBox.appendChild(userMsg);

            // Xóa nội dung mặc định nếu có
            const welcomeMsg = chatBox.querySelector('div[style*="text-align:center"]');
            if (welcomeMsg) welcomeMsg.remove();

            // Hiển thị trạng thái "AI đang trả lời"
            const botMsg = document.createElement('div');
            botMsg.className = 'message bot-message';
            botMsg.innerHTML = '<div class="typing"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
            chatBox.appendChild(botMsg);

            // Cuộn xuống dưới
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                console.log('🔄 Đang gọi API chat...');

                // Gọi API chat
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: text })
                });

                if (!response.ok) {
                    throw new Error(`Lỗi HTTP: ${response.status}`);
                }

                // Xóa "đang typing"
                botMsg.remove();

                // Tạo div cho tin nhắn AI
                const aiMsg = document.createElement('div');
                aiMsg.className = 'message bot-message';
                chatBox.appendChild(aiMsg);

                // Đọc stream response
                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let fullResponse = '';

                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n\\n');

                    for (const line of lines) {
                        if (line.trim().startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.substring(6));

                                if (data.chunk) {
                                    fullResponse += data.chunk;
                                    aiMsg.innerHTML = fullResponse + '<span class="timestamp">Đang trả lời...</span>';
                                    chatBox.scrollTop = chatBox.scrollHeight;
                                }

                                if (data.done) {
                                    const aiTime = new Date().toLocaleTimeString();
                                    aiMsg.innerHTML = fullResponse + `<div class="timestamp">${aiTime}</div>`;
                                    console.log('✅ Hoàn thành');
                                }
                            } catch (e) {
                                console.log('Lỗi parse:', e);
                            }
                        }
                    }
                }

            } catch (error) {
                console.error('❌ Lỗi:', error);
                const errorMsg = document.createElement('div');
                errorMsg.className = 'message bot-message';
                errorMsg.innerHTML = `Lỗi: ${error.message}<div class="timestamp">${new Date().toLocaleTimeString()}</div>`;
                chatBox.appendChild(errorMsg);
            }

            // Kích hoạt lại nút và input
            btn.disabled = false;
            input.disabled = false;
            btn.textContent = 'Gửi';
            input.value = '';
            input.focus();
        }
    </script>
</body>
</html>'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/chat', methods=['POST'])
def chat():
    """API chat với streaming - nhanh như CMD"""

    def generate():
        try:
            data = request.json
            user_message = data.get('message', '').strip()

            print(f"\n📩 Tin nhắn mới: {user_message}")
            print(f"⏰ Thời gian: {time.strftime('%H:%M:%S')}")

            # Gọi Ollama với streaming
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": user_message,
                    "stream": True,
                    "options": {
                        "num_predict": 500,
                        "temperature": 0.7
                    }
                },
                stream=True,
                timeout=60
            )

            # Stream từng chunk về client
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        chunk = data.get('response', '')
                        if chunk:
                            # Gửi ngay lập tức
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    except:
                        continue

            # Kết thúc stream
            yield f"data: {json.dumps({'done': True})}\n\n"
            print(f"✅ Đã gửi xong tin nhắn")

        except requests.exceptions.Timeout:
            yield f"data: {json.dumps({'chunk': '\\n⏱️ Hết thời gian chờ...'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            print("⏱️ Timeout")
        except Exception as e:
            yield f"data: {json.dumps({'chunk': f'\\n❌ Lỗi: {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            print(f"❌ Lỗi: {e}")

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/test')
def test():
    """Trang test đơn giản"""
    return '''
    <h1>Test Page</h1>
    <p>Nếu bạn thấy trang này, server đang chạy.</p>
    <p><a href="/">Về trang chat</a></p>
    '''


@app.route('/health')
def health():
    """Kiểm tra tình trạng Ollama"""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        return jsonify({
            'status': 'online',
            'ollama': True,
            'model': MODEL,
            'message': 'Ollama đang chạy'
        })
    except:
        return jsonify({
            'status': 'offline',
            'ollama': False,
            'message': 'Ollama không chạy. Chạy lệnh: ollama serve'
        })


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 FAST CHAT SERVER - NHANH NHƯ CMD")
    print("=" * 60)
    print(f"🔗 URL: http://localhost:5000")
    print(f"🤖 Model: {MODEL}")
    print(f"📡 Ollama: {OLLAMA_URL}")
    print("=" * 60)
    print("📝 Hướng dẫn:")
    print("  1. Đảm bảo Ollama đang chạy: ollama serve")
    print("  2. Mở trình duyệt: http://localhost:5000")
    print("  3. Nhập tin nhắn và nhấn nút GỬI hoặc ENTER")
    print("=" * 60)

    # Test kết nối Ollama
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            print("✅ Ollama đang chạy")
        else:
            print("❌ Ollama không chạy")
    except:
        print("❌ Không thể kết nối Ollama")

    print("=" * 60)

    # Khởi động server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )