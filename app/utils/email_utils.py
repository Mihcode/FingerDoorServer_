import requests
import json
from app.core.config import settings

# 👇👇👇 DÁN CÁI URL BẠN VỪA COPY VÀO GIỮA CẶP NGOẶC KÉP NÀY 👇👇👇
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby61-LVI9AMVzUn1v4SqRorG4rppb2ZGNz3f6b2_9xXJafWwlCcLROSODvxl3QhMhkpeA/exec" 

def send_account_email(to_email: str, full_name: str, username: str, temp_password: str):
    print(f"🚀 Đang gửi request tới Google Script để gửi mail cho {to_email}...")
    
    # Nội dung HTML
    html_content = f"""
    <h3>Xin chào {full_name},</h3>
    <p>Tài khoản nhân viên của bạn đã được tạo thành công ở chộ đó, chộ đó.</p>
    <ul>
        <li>Username: <b>{username}</b></li>
        <li>Mật khẩu tạm thời: <b>{temp_password}</b></li>
    </ul>
    <p>Vui lòng đăng nhập vào App và đổi mật khẩu ngay lập tức.</p>
    <p>Trân trọng,<br>Admin Team</p>
    """

    payload = {
        "to": to_email,
        "subject": "Thông tin tài khoản hệ thống chấm công IoT",
        "body": html_content
    }

    try:
        # Gửi request HTTP (Cổng 443 - Không bao giờ bị chặn)
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=10)
        
        # Google Script trả về 200 OK nếu chạy ổn
        if response.status_code == 200:
            print(f"✅ Email đã gửi thành công!")
            return True
        else:
            print(f"❌ Lỗi từ Google Script: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi kết nối tới Google: {e}")
        return False
