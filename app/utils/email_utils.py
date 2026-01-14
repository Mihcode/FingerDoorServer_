import smtplib
import socket 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  
SENDER_EMAIL = settings.SMTP_EMAIL
SENDER_PASSWORD = settings.SMTP_PASSWORD

def send_account_email(to_email: str, full_name: str, username: str, temp_password: str):
    # ==============================================================================
    # 🩹 HACK: ÉP BUỘC DÙNG IPv4 (FIX LỖI ERRNO 101 TRÊN RAILWAY/DOCKER)
    # ==============================================================================
    old_getaddrinfo = socket.getaddrinfo

    def new_getaddrinfo(*args, **kwargs):
        # args[0]: host, args[1]: port
        # args[2]: family (cái chúng ta muốn thay đổi)
        # args[3:]: các tham số còn lại (type, proto, flags...)
        
        # Lấy các tham số phía sau (nếu có) để truyền lại cho đúng
        rest_args = args[3:]
        
        # Gọi hàm gốc: Giữ nguyên Host, Port, Các tham số đuôi. 
        # Chỉ thay tham số thứ 3 (family) thành AF_INET (IPv4)
        return old_getaddrinfo(args[0], args[1], socket.AF_INET, *rest_args)

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
        <p>Tài khoản nhân viên của bạn đã được tạo thành công ở chộ đó, chộ đó.</p>
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
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT) 
        # Bật debug để xem log bắt tay (nếu cần)
        server.set_debuglevel(1) 
        
        # 3. Gửi lệnh EHLO đầu tiên
        server.ehlo()
        
        # 4. Nâng cấp lên đường truyền bảo mật
        server.starttls()
        
        # 5. Chào lại sau khi mã hóa
        server.ehlo()
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
        # 🩹 TRẢ LẠI HÀM GỐC (QUAN TRỌNG: Để không làm hỏng các request khác)
        # ==========================================================================
        socket.getaddrinfo = old_getaddrinfo
