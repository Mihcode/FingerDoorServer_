import smtplib
import socket # <--- Cần thư viện này để can thiệp mạng
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  
SENDER_EMAIL = settings.SMTP_EMAIL
SENDER_PASSWORD = settings.SMTP_PASSWORD

def send_account_email(to_email: str, full_name: str, username: str, temp_password: str):
    # ==============================================================================
    # 🩹 HACK: ÉP BUỘC DÙNG IPv4 (FIX LỖI ERRNO 101 TRÊN RAILWAY)
    # ==============================================================================
    # Lưu lại hàm xử lý địa chỉ gốc của hệ thống
    old_getaddrinfo = socket.getaddrinfo

    # Viết hàm mới chỉ lọc lấy địa chỉ IPv4 (AF_INET)
    def new_getaddrinfo(*args, **kwargs):
        # Ép tham số family thành AF_INET (IPv4)
        responses = old_getaddrinfo(args[0], args[1], socket.AF_INET, args[3], args[4], args[5])
        return responses

    # Thay thế hàm gốc bằng hàm mới (Monkey Patch)
    socket.getaddrinfo = new_getaddrinfo
    # ==============================================================================

    try:
        print(f"🔍 DEBUG EMAIL (IPv4 Forced): Server='{SMTP_SERVER}' | Port={SMTP_PORT}") 

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = "Thông tin tài khoản hệ thống chấm công IoT"

        body = f"""
        <h3>Xin chào {full_name},</h3>
        <p>Tài khoản nhân viên của bạn đã được tạo thành công.</p>
        <p><b>Thông tin đăng nhập:</b></p>
        <ul>
            <li>Username: <b>{username}</b></li>
            <li>Mật khẩu tạm thời: <b>{temp_password}</b></li>
        </ul>
        <p>Vui lòng đăng nhập vào App và đổi mật khẩu ngay lập tức.</p>
        <p>Trân trọng,<br>Admin Team</p>
        """
        msg.attach(MIMEText(body, 'html'))

        # Kết nối bằng SSL
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        
        print(f"📧 Đã gửi email tới {to_email}")
        return True

    except Exception as e:
        print(f"❌ Lỗi gửi email: {e}")
        return False
    
    finally:
        # ==========================================================================
        # 🩹 TRẢ LẠI HÀM GỐC (Để không ảnh hưởng các chức năng khác như MQTT)
        # ==========================================================================
        socket.getaddrinfo = old_getaddrinfo
