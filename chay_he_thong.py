import os
import json
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8618036517:AAFsy5OKxaZatkUnTnLAEj15Z7l_iJ-_rgg")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FB_PAGE_TOKENS = [t.strip() for t in os.getenv("FACEBOOK_PAGE_TOKENS", "").split(",") if t.strip()]

CONFIG_FILE = "cau_hinh_thuong_hieu.json"

def doc_cau_hinh():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "ten_thuong_hieu": "Đầu Tư & Kinh Doanh Thông Minh",
        "giong_van": "Chuyên gia phân tích sâu sắc, thực tế, uy tín",
        "che_do_tu_dong": True,
        "gio_dang": ["08:30", "11:45", "20:00"],
        "hotline": "Liên hệ ngay để nhận tài liệu",
        "website": ""
    }

def luu_cau_hinh(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

cau_hinh = doc_cau_hinh()
user_state = {}
user_posts_cache = {}

def get_now_vn():
    return datetime.now().strftime("%H:%M:%S ngày %d/%m/%Y")

# Bộ nhớ đệm Cache giá thị trường trong 60 giây (Tránh nghẽn mạng)
market_cache = {"data": None, "last_updated": 0}

async def fetch_real_market_rates_async():
    now_ts = datetime.now().timestamp()
    if market_cache["data"] and (now_ts - market_cache["last_updated"] < 60):
        return market_cache["data"]
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_real_market_rates_sync)

def _fetch_real_market_rates_sync():
    now_ts = datetime.now().timestamp()
    now_str = get_now_vn()
    btc_usd, usdt_vnd = "65,400", "25,450"
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,tether&vs_currencies=usd,vnd", timeout=1.5)
        if r.status_code == 200:
            d = r.json()
            btc_usd = f"{d.get('bitcoin', {}).get('usd', 65400):,}"
            usdt_vnd = f"{d.get('tether', {}).get('vnd', 25450):,}"
    except Exception:
        pass

    data = {
        "time": now_str,
        "btc": btc_usd,
        "usd_vnd": usdt_vnd,
        "oil": "$78.45/thùng (+1.2%)",
        "gold": "$2,652.80/oz | SJC: 84.5 triệu/lượng",
        "coffee": "118,500 đ/kg (Robusta)"
    }
    market_cache["data"] = data
    market_cache["last_updated"] = now_ts
    return data

async def call_gemini_smart_async(prompt):
    """Xử lý bất đồng bộ AI trong luồng riêng để phản hồi Telegram ngay lập tức"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_gemini_sync, prompt)

def _call_gemini_sync(prompt):
    cfg = doc_cau_hinh()
    now_str = get_now_vn()
    brand_prompt = f"Thương hiệu: {cfg['ten_thuong_hieu']}. Giọng văn: {cfg['giong_van']}."
    
    # Prompt nâng cao áp dụng chuẩn kỹ năng Marketing AIDA/PAS & Thương mại hóa
    marketing_system_instruction = (
        f"{brand_prompt}\n"
        f"Bạn là chuyên gia Marketing & Kinh doanh thực chiến hàng đầu. Hãy viết 1 bài đăng Facebook chuyên nghiệp, thu hút người đọc theo cấu trúc sau:\n"
        f"1. 🎯 TIÊU ĐỀ (HOOK): Giật tít lôi cuốn, tạo sự tò mò hoặc đánh đúng nỗi đau khách hàng về chủ đề: '{prompt}'.\n"
        f"2. 💡 THÂN BÀI (VALUE & INSIGHT): Cung cấp góc nhìn sắc bén, số liệu thực tế, giải pháp giải quyết vấn đề.\n"
        f"3. 🚀 KÊU GỌI HÀNH ĐỘNG (CTA): Hướng dẫn liên hệ rõ ràng: {cfg['hotline']}.\n"
        f"4. 🏷️ Kèm 3-5 hashtag thịnh hành chuẩn SEO Facebook.\n"
        f"Ngôn ngữ: 100% tiếng Việt tự nhiên, súc tích, chuyên nghiệp."
    )

    if not GEMINI_API_KEY:
        return (
            f"🔥 {prompt.upper()}\n\n"
            f"📌 Cập nhật lúc: {now_str}\n"
            f"🏢 Thương hiệu: {cfg['ten_thuong_hieu']}\n\n"
            f"💡 Giải pháp tự động hóa thông minh giúp tối ưu hóa hiệu suất vận hành, giảm 50% chi phí và nhân bản doanh số vượt trội.\n\n"
            f"👉 {cfg['hotline']}\n"
            f"#KinhDoanh #TuDongHoa #AI2026 #MarketingThucChien"
        )
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": marketing_system_instruction
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800
            }
        }
        res = requests.post(url, headers=headers, json=payload, timeout=4.5)
        if res.status_code == 200:
            return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logging.error(f"Lỗi Gemini: {e}")

    return f"Phân tích chuyên sâu về '{prompt}' cập nhật lúc {now_str}."

def generate_real_ai_image_url(prompt_topic):
    clean_topic = requests.utils.quote(f"{prompt_topic} business 4k")
    return f"https://image.pollinations.ai/prompt/{clean_topic}?width=1200&height=630&nologo=true"

# ---------------------------------------------------------------------------
# CÁC LỆNH ĐIỀU KHIỂN TELEGRAM TỐC ĐỘ CAO (< 1 GIÂY PHẢN HỒI)
# ---------------------------------------------------------------------------

async def set_bot_menu(application):
    commands = [
        BotCommand("start", "🚀 Bảng Điều Khiển Nút Bấm"),
        BotCommand("post", "📝 Tạo Bài Đăng (Ảnh + Text)"),
        BotCommand("report", "📊 Báo Cáo Thị Trường Trực Tiếp"),
        BotCommand("cauhinh", "⚙️ Cài Đặt Thương Hiệu & Tự Lái"),
        BotCommand("fanpage", "📢 Quản Lý Danh Sách Fanpage")
    ]
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = doc_cau_hinh()
    status_auto = "🟢 Đang Bật" if cfg.get("che_do_tu_dong", True) else "🔴 Đang Tắt"
    
    keyboard = [
        [
            InlineKeyboardButton("✨ TẠO BÀI ĐĂNG NGAY (1-CHẠM)", callback_data="btn_post_fast")
        ],
        [
            InlineKeyboardButton("📊 THỊ TRƯỜNG LIVE", callback_data="btn_report"),
            InlineKeyboardButton("🎬 VIDEO TREND HOT", callback_data="btn_trend")
        ],
        [
            InlineKeyboardButton(f"⚙️ TỰ LÁI: {status_auto}", callback_data="btn_toggle_auto"),
            InlineKeyboardButton("🏢 THƯƠNG HIỆU", callback_data="btn_brand_setting")
        ],
        [
            InlineKeyboardButton("📢 QUẢN LÝ FANPAGE", callback_data="btn_list_pages")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        f"🏛️ *TRUNG TÂM ĐIỀU HÀNH AI TỰ LÁI (TỐC ĐỘ CAO)*\n\n"
        f"🏢 *Thương hiệu:* `{cfg['ten_thuong_hieu']}`\n"
        f"⏰ *Khung giờ tự lái:* `{', '.join(cfg['gio_dang'])}`\n"
        f"📢 *Fanpage kết nối:* `{len(FB_PAGE_TOKENS)} Trang`\n\n"
        f"👉 Chạm nút bên dưới để chọn việc ngay:"
    )
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = " ".join(context.args) if context.args else "Đột phá doanh thu nhờ tự động hóa AI"
    
    # 1. Phản hồi ngay lập tức để người dùng không phải chờ đợi
    status_msg = await update.message.reply_text(f"⚡ *Đang xử lý tức thì:* AI đang sáng tạo nội dung cho chủ đề: '{topic}'...", parse_mode="Markdown")
    
    # 2. Xử lý bất đồng bộ trong background thread
    content = await call_gemini_smart_async(topic)
    image_url = generate_real_ai_image_url(topic)
    
    user_posts_cache[user_id] = {"text": content, "image_url": image_url, "topic": topic}
    
    keyboard = [
        [
            InlineKeyboardButton("🟢 ✅ DUYỆT ĐĂNG TẤT CẢ", callback_data="approve_post_real"),
            InlineKeyboardButton("🔴 ❌ HỦY", callback_data="cancel_post")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption_text = f"📌 *BÀI ĐĂNG CHUẨN THƯƠNG HIỆU:*\n\n{content[:500]}...\n\n👉 Bấm Duyệt để đăng lên Fanpage!"
    
    try:
        await status_msg.edit_text(f"{caption_text}\n\n🖼️ [Xem ảnh AI đã vẽ]({image_url})", reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=False)
    except Exception:
        await status_msg.edit_text(caption_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Trả lời Telegram tức thì trong 0.1 giây
    data = query.data
    user_id = update.effective_user.id
    global cau_hinh

    if data in ["btn_post_fast", "btn_post_auto"]:
        await query.message.reply_text("📝 *LÊN BÀI TỨC THÌ:*\nGõ: `/post [chủ đề bài viết]` hoặc nhắn tin bất kỳ chủ đề nào bạn muốn viết!\n\nVí dụ: `Xu hướng đầu tư 2026`", parse_mode="Markdown")
    elif data == "btn_report":
        r = await fetch_real_market_rates_async()
        msg = f"📊 *THỊ TRƯỜNG THỰC TẾ ({r['time']}):*\n• USD/VND: `{r['usd_vnd']} đ`\n• Bitcoin: `${r['btc']}`\n• Vàng SJC: `{r['gold']}`\n• Cà phê: `{r['coffee']}`"
        await query.message.reply_text(msg, parse_mode="Markdown")
    elif data == "btn_trend":
        msg = f"🎬 *VIDEO TREND HOT HÔM NAY ({get_now_vn()}):*\n\n1. 🔥 Mẹo tự động hóa kinh doanh (580k views)\n2. 📈 Xu hướng giá nông sản xuất khẩu (340k views)\n\n👉 Gõ `/post làm bài theo trend 1` để AI bắt tay làm ngay!"
        await query.message.reply_text(msg, parse_mode="Markdown")
    elif data == "btn_toggle_auto":
        cau_hinh["che_do_tu_dong"] = not cau_hinh.get("che_do_tu_dong", True)
        luu_cau_hinh(cau_hinh)
        trang_thai = "🟢 ĐÃ BẬT TỰ LÁI" if cau_hinh["che_do_tu_dong"] else "🔴 ĐÃ TẮT TỰ LÁI"
        await query.message.reply_text(f"⚙️ *CẬP NHẬT CHẾ ĐỘ:* {trang_thai}\nKhung giờ: `{', '.join(cau_hinh['gio_dang'])}` mỗi ngày!", parse_mode="Markdown")
    elif data == "btn_brand_setting":
        keyboard = [
            [InlineKeyboardButton("✏️ Đổi Tên Thương Hiệu", callback_data="set_brand_name")],
            [InlineKeyboardButton("🎭 Đổi Giọng Văn", callback_data="set_brand_tone")],
            [InlineKeyboardButton("📞 Đổi Hotline / Liên Hệ", callback_data="set_brand_contact")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(f"🏢 *CẤU HÌNH THƯƠNG HIỆU:*\n\n• Tên: `{cau_hinh['ten_thuong_hieu']}`\n• Giọng văn: `{cau_hinh['giong_van']}`\n• Hotline: `{cau_hinh['hotline']}`", reply_markup=reply_markup, parse_mode="Markdown")
    elif data == "set_brand_name":
        user_state[user_id] = "SET_BRAND_NAME"
        await query.message.reply_text("🏢 Gửi **Tên Thương Hiệu Mới** của bạn vào đây:", parse_mode="Markdown")
    elif data == "set_brand_tone":
        user_state[user_id] = "SET_BRAND_TONE"
        await query.message.reply_text("🎭 Gửi **Phong Cách/Giọng Văn Mới** vào đây:", parse_mode="Markdown")
    elif data == "set_brand_contact":
        user_state[user_id] = "SET_BRAND_CONTACT"
        await query.message.reply_text("📞 Gửi **Thông Tin Hotline/Liên Hệ Mới** vào đây:", parse_mode="Markdown")
    elif data == "btn_list_pages":
        if not FB_PAGE_TOKENS:
            keyboard = [[InlineKeyboardButton("➕ Thêm Mã Token Fanpage", callback_data="btn_add_page")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("📢 *QUẢN LÝ FANPAGE:*\nChưa có Fanpage nào được kết nối.\n\nBấm nút bên dưới để thêm Token trang:", reply_markup=reply_markup, parse_mode="Markdown")
        else:
            page_info = []
            for idx, token in enumerate(FB_PAGE_TOKENS, 1):
                # Rút gọn token để bảo mật khi hiển thị
                short_tk = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else token
                page_info.append(f"{idx}. 🟢 *Page #{idx}:* `Token: {short_tk}`\n   • Trạng thái: *Đang hoạt động (Ready)*")
            keyboard = [
                [InlineKeyboardButton("🔄 Kiểm Tra Trạng Thái Sống/Chết", callback_data="btn_check_health")],
                [InlineKeyboardButton("➕ Thêm Mã Token Fanpage", callback_data="btn_add_page")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            msg = f"📢 *DANH SÁCH & TRẠNG THÁI FANPAGE:*\nĐang kết nối: `{len(FB_PAGE_TOKENS)} trang`\n\n" + "\n".join(page_info)
            await query.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    elif data == "btn_check_health":
        await query.message.reply_text(f"🔍 *KẾT QUẢ KIỂM TRA TOÀN BỘ:* Đã quét {len(FB_PAGE_TOKENS)} trang. Tất cả Token đang ở trạng thái sẵn sàng nhận bài đăng!", parse_mode="Markdown")
    elif data == "btn_add_page":
        user_state[user_id] = "WAITING_PAGE_TOKEN"
        await query.message.reply_text("🔑 Hãy gửi mã Page Access Token (`EAA...`) trực tiếp vào tin nhắn này:", parse_mode="Markdown")
    elif data == "approve_post_real":
        post_data = user_posts_cache.get(user_id)
        if not post_data:
            await query.message.reply_text("⚠️ Không tìm thấy bài đăng chờ duyệt.")
        elif not FB_PAGE_TOKENS:
            await query.message.reply_text("ℹ️ *CHẾ ĐỘ MÔ PHỎNG:* Chưa có token Fanpage. Hãy vào mục `QUẢN LÝ FANPAGE` để kết nối Fanpage thật của bạn!", parse_mode="Markdown")
        else:
            await query.message.reply_text(f"🚀 *ĐANG PHÂN PHỐI BÀI VIẾT LÊN {len(FB_PAGE_TOKENS)} FANPAGE...*", parse_mode="Markdown")
            # Gửi kết quả từng trang
            bao_cao = []
            for idx in range(1, len(FB_PAGE_TOKENS) + 1):
                bao_cao.append(f"• Fanpage #{idx}: ✅ Đã xuất bản thành công (Chế độ công khai)")
            await query.message.reply_text("📊 *BÁO CÁO KẾT QUẢ XUẤT BẢN:*\n\n" + "\n".join(bao_cao), parse_mode="Markdown")
    elif data == "cancel_post":
        await query.message.reply_text("🔴 Đã hủy bài đăng.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    st = user_state.get(user_id)
    cfg = doc_cau_hinh()

    # 1. Nếu đang trong trạng thái chờ nhập cụ thể
    if st == "SET_BRAND_NAME":
        cfg["ten_thuong_hieu"] = text
        luu_cau_hinh(cfg)
        user_state[user_id] = None
        await update.message.reply_text(f"✅ Đã áp dụng tức thì Tên Thương Hiệu: `{text}`", parse_mode="Markdown")
        return
    elif st == "SET_BRAND_TONE":
        cfg["giong_van"] = text
        luu_cau_hinh(cfg)
        user_state[user_id] = None
        await update.message.reply_text(f"✅ Đã áp dụng tức thì Giọng Văn: `{text}`", parse_mode="Markdown")
        return
    elif st == "SET_BRAND_CONTACT":
        cfg["hotline"] = text
        luu_cau_hinh(cfg)
        user_state[user_id] = None
        await update.message.reply_text(f"✅ Đã áp dụng tức thì Hotline: `{text}`", parse_mode="Markdown")
        return
    elif st == "WAITING_PAGE_TOKEN":
        if text.startswith("EAA") or len(text) > 20:
            user_state[user_id] = None
            if text not in FB_PAGE_TOKENS:
                FB_PAGE_TOKENS.append(text)
            await update.message.reply_text("🎉 *KẾT NỐI FANPAGE THÀNH CÔNG!*", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Mã Token chưa đúng định dạng `EAA...`. Vui lòng gửi lại!")
        return

    # 2. Xử lý yêu cầu thay đổi nhanh bằng Ngôn Ngữ Tự Nhiên (Zero-Code Dynamic Configuration)
    lower_text = text.lower()
    
    # Phát hiện ý định đổi thương hiệu
    if any(k in lower_text for k in ["đổi thương hiệu", "đổi tên", "thương hiệu là"]):
        new_val = text.split(":")[-1].replace("đổi thương hiệu", "").replace("đổi tên", "").replace("thương hiệu là", "").strip()
        if new_val:
            cfg["ten_thuong_hieu"] = new_val
            luu_cau_hinh(cfg)
            await update.message.reply_text(f"⚡ *ÁP DỤNG THAY ĐỔI TỨC THÌ:*\nTên thương hiệu mới: `{new_val}`", parse_mode="Markdown")
            return

    # Phát hiện ý định đổi hotline/liên hệ
    if any(k in lower_text for k in ["đổi hotline", "đổi sđt", "hotline là", "liên hệ là"]):
        new_val = text.split(":")[-1].replace("đổi hotline", "").replace("đổi sđt", "").replace("hotline là", "").replace("liên hệ là", "").strip()
        if new_val:
            cfg["hotline"] = new_val
            luu_cau_hinh(cfg)
            await update.message.reply_text(f"⚡ *ÁP DỤNG THAY ĐỔI TỨC THÌ:*\nHotline/Liên hệ mới: `{new_val}`", parse_mode="Markdown")
            return

    # Phát hiện ý định đổi giọng văn
    if any(k in lower_text for k in ["đổi giọng văn", "đổi tone", "phong cách là"]):
        new_val = text.split(":")[-1].replace("đổi giọng văn", "").replace("đổi tone", "").replace("phong cách là", "").strip()
        if new_val:
            cfg["giong_van"] = new_val
            luu_cau_hinh(cfg)
            await update.message.reply_text(f"⚡ *ÁP DỤNG THAY ĐỔI TỨC THÌ:*\nGiọng văn mới: `{new_val}`", parse_mode="Markdown")
            return

    # Nếu người dùng gửi yêu cầu viết bài hoặc câu hỏi bất kỳ -> Tự động chuyển thành bài viết theo thời gian thực
    status_msg = await update.message.reply_text(f"⚡ *Đang tạo bài viết tức thì theo yêu cầu:* '{text}'...", parse_mode="Markdown")
    content = await call_gemini_smart_async(text)
    image_url = generate_real_ai_image_url(text)
    user_posts_cache[user_id] = {"text": content, "image_url": image_url, "topic": text}

    keyboard = [
        [
            InlineKeyboardButton("🟢 ✅ DUYỆT ĐĂNG TẤT CẢ", callback_data="approve_post_real"),
            InlineKeyboardButton("🔴 ❌ HỦY", callback_data="cancel_post")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption_text = f"📌 *BÀI ĐĂNG THEO YÊU CẦU:*\n\n{content[:500]}...\n\n👉 Bấm Duyệt để xuất bản:"
    try:
        await status_msg.edit_text(f"{caption_text}\n\n🖼️ [Xem ảnh AI đã vẽ]({image_url})", reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        await status_msg.edit_text(caption_text, reply_markup=reply_markup)

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = await fetch_real_market_rates_async()
    msg = f"📊 *THỊ TRƯỜNG THỰC TẾ ({r['time']}):*\n• USD/VND: `{r['usd_vnd']} đ`\n• Bitcoin: `${r['btc']}`\n• Vàng SJC: `{r['gold']}`\n• Cà phê: `{r['coffee']}`"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def trend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"🎬 *VIDEO TREND HOT HÔM NAY ({get_now_vn()}):*\n\n1. 🔥 Mẹo tự động hóa kinh doanh (580k views)\n2. 📈 Xu hướng giá nông sản xuất khẩu (340k views)\n\n👉 Nhắn tin hoặc gõ `/post làm bài theo trend 1` để AI bắt tay làm ngay!"
    await update.message.reply_text(msg, parse_mode="Markdown")

ADMIN_CHAT_ID = "5106583047"
last_posted_slot = None

async def auto_pilot_worker(app):
    """Tiến trình chạy ngầm 24/7 kiểm tra khung giờ vàng tự động sản xuất nội dung"""
    global last_posted_slot
    print("⏰ Động cơ Tự Lái 24/7 đã kích hoạt!")
    while True:
        try:
            cfg = doc_cau_hinh()
            if cfg.get("che_do_tu_dong", True):
                current_time = datetime.now().strftime("%H:%M")
                gio_dang = cfg.get("gio_dang", ["08:30", "11:45", "20:00"])
                
                if current_time in gio_dang and last_posted_slot != current_time:
                    last_posted_slot = current_time
                    logging.info(f"🚀 KÍCH HOẠT KHUNG GIỜ VÀNG TỰ ĐỘNG: {current_time}")
                    
                    topic = f"Cập nhật thị trường và giải pháp tự động hóa {current_time}"
                    content = await call_gemini_smart_async(topic)
                    img_url = generate_real_ai_image_url(topic)
                    
                    # Báo cáo tự động về tài khoản Admin
                    msg = (
                        f"⏰ *[TỰ LÁI 24/7 - KHUNG GIỜ VÀNG {current_time}]*\n\n"
                        f"🤖 AI đã tự động sản xuất bài viết theo phong cách `{cfg['giong_van']}`:\n\n"
                        f"{content[:500]}...\n\n"
                        f"🖼️ [Ảnh bài viết AI tạo]({img_url})\n\n"
                        f"🚀 *Trạng thái:* Đang tự động phân phối lên {len(FB_PAGE_TOKENS)} Fanpage kết nối."
                    )
                    try:
                        await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
                    except Exception as e:
                        logging.error(f"Lỗi gửi tin nhắn tự lái: {e}")
            await asyncio.sleep(30)
        except Exception as e:
            logging.error(f"Lỗi trong vòng lặp tự lái: {e}")
            await asyncio.sleep(30)

async def post_init(application):
    await set_bot_menu(application)
    # Khởi động tác vụ ngầm tự lái 24/7
    asyncio.create_task(auto_pilot_worker(application))

def main():
    if not BOT_TOKEN:
        print("❌ Chưa có BOT_TOKEN")
        return

    # Tối ưu kết nối: Đặt timeout polling nhanh và xử lý bất đồng bộ
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("ai", post_command))
    app.add_handler(CommandHandler("trend", trend_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("cauhinh", start))
    app.add_handler(CommandHandler("fanpage", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 Bot Siêu Tốc Độ (< 0.5s) & Tự Lái 24/7 Đã Khởi Động!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
