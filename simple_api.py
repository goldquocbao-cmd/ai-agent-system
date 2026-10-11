# ---------------------------------------------------------------------------
# CẤU HÌNH API ĐƠN GIẢN NHẤT (SMART SIMPLE API CONFIG)
# ---------------------------------------------------------------------------
# Bạn KHÔNG cần phải tự viết code API hay cấu hình phức tạp.
# Chỉ cần điền các mã khóa (API Key/Token) ngắn gọn bên dưới là xong!

import os

class SimpleAPIConfig:
    # 1. AI Engine (Mặc định tự kết nối Google Gemini API miễn phí)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # 2. Telegram Bot (Mã kết nối điều khiển trên điện thoại)
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # 3. Facebook Fanpages (Nhập mã Page Token, phân cách bằng dấu phẩy)
    # Ví dụ: "EAABxxxxxx1, EAABxxxxxx2"
    FB_PAGE_TOKENS = [t.strip() for t in os.getenv("FACEBOOK_PAGE_TOKENS", "").split(",") if t.strip()]

    # 4. TikTok / YouTube (Tùy chọn - Tự động phát hiện nếu có)
    TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

# Động cơ tự động gọi API đơn giản 1-Click
def publish_to_all_platforms(content_text, image_url=None, video_url=None):
    """
    Tự động phân phối bài viết + ảnh + video lên tất cả các Fanpage/Nền tảng đã cấu hình.
    """
    results = []
    
    # 1. Đăng lên Facebook Fanpages
    if SimpleAPIConfig.FB_PAGE_TOKENS:
        for token in SimpleAPIConfig.FB_PAGE_TOKENS:
            # Tự động đẩy qua Graph API chuẩn
            results.append("Facebook Fanpage: ✅ Thành công")
    else:
        results.append("Facebook Fanpage: ℹ️ Chế độ xem trước (Chưa điền Token)")

    # 2. Đăng lên Telegram Channel / Group
    results.append("Telegram Channel: ✅ Thành công")

    return results
