#!/usr/bin/env python3
import os
from PIL import Image, ImageFilter 
import qrcode

# =====================================================================
# CẤU HÌNH ĐƯỜNG DẪN TẠI ĐÂY (Thay đổi các giá trị này theo ý bạn)
# =====================================================================
# 1. Đường link trang webserver của bạn
WEBSITE_URL = "http://192.168.0.185:8090/login?next=%2F"  

# 2. Đường dẫn đến file ảnh logo (Dùng os.path.expanduser để Python hiểu dấu ~)
LOGO_PATH = os.path.expanduser("~/mobile_robot/ros2_ws/src/amr_ai/amr_ai/web/static/picqr.png")

# 3. Đường dẫn và tên file bạn muốn lưu mã QR
SAVE_PATH = os.path.expanduser("~/mobile_robot/ros2_ws/src/amr_ai/amr_ai/web/static/qr_control.png")
# =====================================================================

def create_qr_fixed_paths():
    # Kiểm tra xem file logo có tồn tại hay không trước khi xử lý
    if not os.path.exists(LOGO_PATH):
        print(f"❌ LỖI: Không tìm thấy file logo tại đường dẫn: {LOGO_PATH}")
        print("Vui lòng kiểm tra lại chính xác đường dẫn đến file logo của bạn.")
        return

    try:
        # 1. Khởi tạo cấu hình QR Code với mức độ sửa lỗi cao nhất (ERROR_CORRECT_H)
        # Việc giữ mức H (High) giúp QR code chịu lỗi tới 30%, đảm bảo chèn logo xong vẫn quét được
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H, 
            box_size=40,
            border=4,
        )
        qr.add_data(WEBSITE_URL)
        qr.make(fit=True)

        # Tạo ảnh QR gốc dưới định dạng màu RGBA để xử lý ảnh màu tốt hơn
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGBA')

        # 2. Xử lý ảnh Logo
        logo = Image.open(LOGO_PATH).convert('RGBA')
        
        # Tính toán kích thước logo (tối đa 23% kích thước tổng thể của QR để quét mượt mà)
        qr_width, qr_height = qr_img.size
        logo_max_size = int(qr_width * 0.23)
        
        # Thay đổi kích thước logo nhưng vẫn giữ nguyên tỷ lệ gốc của logo (không bị méo ảnh)
        logo.thumbnail((logo_max_size, logo_max_size), Image.LANCZOS)
        logo = logo.filter(ImageFilter.SHARPEN)
        logo_width, logo_height = logo.size

        # Tính toán tọa độ (x, y) để đặt logo chính xác vào trung tâm của mã QR
        pos_x = (qr_width - logo_width) // 2
        pos_y = (qr_height - logo_height) // 2

        # 3. Chèn logo vào mã QR 
        # Sử dụng tham số mask=logo để giữ độ trong suốt (nếu file logo của bạn là dạng PNG trong suốt)
        qr_img.paste(logo, (pos_x, pos_y), mask=logo)

        # 4. Kiểm tra thư mục lưu file và tiến hành lưu kết quả
        save_dir = os.path.dirname(SAVE_PATH)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir) # Tự động tạo thư mục nếu thư mục đó chưa tồn tại
            
        qr_img.save(SAVE_PATH)
        print("🎉 QUY TRÌNH HOÀN TẤT THÀNH CÔNG!")
        print(f"🔗 Website: {WEBSITE_URL}")
        print(f"🖼️ Ảnh QR đã được lưu tại: {os.path.abspath(SAVE_PATH)}")

    except Exception as e:
        print(f"❌ Có lỗi xảy ra trong quá trình xử lý: {e}")

if __name__ == "__main__":
    create_qr_fixed_paths()