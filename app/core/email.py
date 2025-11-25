import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from app.core.config import get_settings

settings = get_settings()


class EmailService:
    """Email service for sending emails"""

    @staticmethod
    def send_email(
            to_email: str,
            subject: str,
            html_content: str,
            cc: List[str] = None,
            bcc: List[str] = None
    ) -> bool:
        """Send email using SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)

            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

                recipients = [to_email]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)

                server.send_message(msg)

            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    @staticmethod
    def send_verification_email(to_email: str, username: str, token: str) -> bool:
        """Send email verification"""
        subject = "Xác thực tài khoản của bạn"
        verification_link = f"http://localhost:3000/verify-email?token={token}"

        html_content = f"""
        <html>
            <body>
                <h2>Xin chào {username},</h2>
                <p>Cảm ơn bạn đã đăng ký tài khoản tại Cosmetics Store.</p>
                <p>Vui lòng nhấp vào liên kết bên dưới để xác thực tài khoản của bạn:</p>
                <a href="{verification_link}">Xác thực tài khoản</a>
                <p>Liên kết này sẽ hết hạn sau 24 giờ.</p>
                <p>Trân trọng,<br>Cosmetics Store Team</p>
            </body>
        </html>
        """

        return EmailService.send_email(to_email, subject, html_content)

    @staticmethod
    def send_reset_password_email(to_email: str, username: str, token: str) -> bool:
        """Send password reset email"""
        subject = "Đặt lại mật khẩu"
        reset_link = f"http://localhost:3000/reset-password?token={token}"

        html_content = f"""
        <html>
            <body>
                <h2>Xin chào {username},</h2>
                <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.</p>
                <p>Vui lòng nhấp vào liên kết bên dưới để đặt lại mật khẩu:</p>
                <a href="{reset_link}">Đặt lại mật khẩu</a>
                <p>Liên kết này sẽ hết hạn sau 1 giờ.</p>
                <p>Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.</p>
                <p>Trân trọng,<br>Cosmetics Store Team</p>
            </body>
        </html>
        """

        return EmailService.send_email(to_email, subject, html_content)

    @staticmethod
    def send_order_confirmation_email(to_email: str, username: str, order_code: str, total_amount: float) -> bool:
        """Send order confirmation email"""
        subject = f"Xác nhận đơn hàng #{order_code}"

        html_content = f"""
        <html>
            <body>
                <h2>Xin chào {username},</h2>
                <p>Cảm ơn bạn đã đặt hàng tại Cosmetics Store.</p>
                <p>Thông tin đơn hàng:</p>
                <ul>
                    <li>Mã đơn hàng: #{order_code}</li>
                    <li>Tổng tiền: {total_amount:,.0f} VNĐ</li>
                </ul>
                <p>Chúng tôi sẽ xử lý đơn hàng và thông báo cho bạn sớm nhất.</p>
                <p>Trân trọng,<br>Cosmetics Store Team</p>
            </body>
        </html>
        """

        return EmailService.send_email(to_email, subject, html_content)