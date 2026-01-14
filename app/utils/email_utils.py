import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

# Cấu hình Email (Lấy từ biến môi trường, AN TOÀN TUYỆT ĐỐI)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = settings.SMTP_EMAIL       # <--- Dùng biến
SENDER_PASSWORD = settings.SMTP_PASSWORD # <--- Dùng biến

def send_account_email(to_email: str, full_name: str, username: str, temp_password: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = "Thông tin tài khoản hệ thống chấm công IoT"

        body = f"""
        <h3>Xin chào {full_name},</h3>
        <p>Tài khoản nhân viên của bạn đã được tạo thành công ở chộ đó chộ đó.</p>
        <p><b>Thông tin đăng nhập:</b></p>
        <ul>
            <li>Username: <b>{username}</b></li>
            <li>Mật khẩu tạm thời: <b>{temp_password}</b></li>
        </ul>
        <p>Vui lòng đăng nhập vào App và đổi mật khẩu ngay lập tức.</p>
        <p>Trân trọng,<br>Admin Team</p>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        print(f"📧 Đã gửi email tới {to_email}")
        return True
    except Exception as e:
        print(f"❌ Lỗi gửi email: {e}")
        return False
