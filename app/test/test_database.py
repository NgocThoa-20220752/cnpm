import sys
import os

# Thêm đường dẫn
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)
sys.path.insert(0, root_dir)

from app.core.config import get_settings

def test_mysql_connection():
    print("🔌 ĐANG THỬ KẾT NỐI MYSQL...")

    settings = get_settings()

    print(f"🔧 Thông tin kết nối:")
    print(f"   Host: {settings.DB_HOST}")
    print(f"   Port: {settings.DB_PORT}")
    print(f"   User: {settings.DB_USER}")
    print(f"   Database: {settings.DB_NAME}")
    print(f"   Password: {'*' * len(settings.DB_PASSWORD)}")

    try:
        import mysql.connector

        # Thử kết nối
        connection = mysql.connector.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )

        if connection.is_connected():
            print("✅ KẾT NỐI MYSQL THÀNH CÔNG!")

            # Kiểm tra thông tin
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()
            print(f"📊 Đang kết nối đến: {db_name[0]}")

            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"🗄️ MySQL Version: {version[0]}")

            cursor.close()
            connection.close()
            print("🔌 Đã đóng kết nối")

    except ImportError:
        print("❌ Chưa cài đặt mysql-connector-python")
        print("💡 Chạy lệnh: pip install mysql-connector-python")
    except Exception as e:
        print(f"❌ LỖI KẾT NỐI: {e}")
        print("\n🔧 KHẮC PHỤC:")
        print("1. Kiểm tra MySQL đã chạy chưa?")
        print("2. Kiểm tra mật khẩu trong file .env")
        print("3. Kiểm tra database 'cosmetics' đã tồn tại chưa?")

def test_settings():
    print("\n🔧 KIỂM TRA SETTINGS...")
    settings = get_settings()
    print(f"✅ APP_NAME: {settings.APP_NAME}")
    print(f"✅ SECRET_KEY: {settings.SECRET_KEY[:10]}...")
    print(f"✅ CORS: {settings.cors_origins_list}")
    print(f"✅ DATABASE_URL: {settings.database_url}")

if __name__ == "__main__":
    test_settings()
    test_mysql_connection()