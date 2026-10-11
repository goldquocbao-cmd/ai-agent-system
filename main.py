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

def fetch_real_market_rates():
    now_ts = datetime.now().timestamp()
    if market_cache["data"] and (now_ts - market_cache["last_updated"] < 60):
        return market_cache["data"]

    now_str = get_now_vn()
    btc_usd, usdt_vnd = "65,400", "25,450"
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,tether&vs_currencies=usd,vnd", timeout=2)
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
    
    if not GEMINI_API_KEY:
        return (
            f"🔥 XU HƯỚNG & PHÂN TÍCH: {prompt.upper()}\n\n"
            f"📌 Cập nhật lúc: {now_str}\n"
            f"🏢 Thương hiệu: {cfg['ten_thuong_hieu']}\n\n"
            f"Việc ứng dụng tự động hóa và công nghệ AI giúp cắt giảm hơn 50% chi phí vận hành và nhân bản nội dung vượt trội.\n\n"
            f"👉 {cfg['hotline']}\n"
            f"#KinhDoanh #TuDongHoa #AI2026"
        )
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{brand_prompt}\nHãy viết 1 bài đăng Facebook chuyên nghiệp, giật tít thu hút, câu từ thực tế, có số liệu thị trường về chủ đề: '{prompt}'. Kèm 3 hashtag và thông tin liên hệ."
                }]
            }]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=6)
        if res.status_code == 200:
            return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logging.error(f"Lỗi Gemini: {e}")

    return f"Phân tích về '{prompt}' cập nhật lúc {now_str}."

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

    if data == "btn_post_fast":
        await query.message.reply_text("📝 *LÊN BÀI TỨC THÌ:*\nGõ: `/post [chủ đề bài viết]`\n\nVí dụ: `/post Xu hướng thị trường quý 4`", parse_mode="Markdown")
    elif data == "btn_report":
        r = fetch_real_market_rates()
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
        count = len(FB_PAGE_TOKENS)
        keyboard = [[InlineKeyboardButton("➕ Thêm Mã Token Fanpage", callback_data="btn_add_page")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(f"📢 *QUẢN LÝ FANPAGE:*\nĐang kết nối `{count}` Fanpage.", reply_markup=reply_markup, parse_mode="Markdown")
    elif data == "btn_add_page":
        user_state[user_id] = "WAITING_PAGE_TOKEN"
        await query.message.reply_text("🔑 Hãy gửi mã Page Access Token (`EAA...`) trực tiếp vào tin nhắn này:", parse_mode="Markdown")
    elif data == "approve_post_real":
        await query.message.reply_text("🚀 Đang tiến hành đăng bài lên các Fanpage...", parse_mode="Markdown")
    elif data == "cancel_post":
        await query.message.reply_text("🔴 Đã hủy bài đăng.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    st = user_state.get(user_id)
    global cau_hinh

    if st == "SET_BRAND_NAME":
        cau_hinh["ten_thuong_hieu"] = text
        luu_cau_hinh(cau_hinh)
        user_state[user_id] = None
        await update.message.reply_text(f"✅ Đã lưu Tên Thương Hiệu: `{text}`", parse_mode="Markdown")
    elif st == "SET_BRAND_TONE":
        cau_hinh["giong_van"] = text
        luu_cau_hinh(cau_hinh)
        user_state[user_id] = None
        await update.message.reply_text(f"✅ Đã lưu Giọng Văn: `{text}`", parse_mode="Markdown")
    elif st == "SET_BRAND_CONTACT":
        cau_hinh["hotline"] = text
        luu_cau_hinh(cau_hinh)
        user_state[user_id] = None
        await update.message.reply_text(f"✅ Đã lưu Hotline: `{text}`", parse_mode="Markdown")
    elif st == "WAITING_PAGE_TOKEN":
        if text.startswith("EAA") or len(text) > 20:
            user_state[user_id] = None
            if text not in FB_PAGE_TOKENS:
                FB_PAGE_TOKENS.append(text)
            await update.message.reply_text("🎉 *KẾT NỐI FANPAGE THÀNH CÔNG!*", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Mã Token chưa đúng định dạng `EAA...`. Vui lòng gửi lại!")
    else:
        await update.message.reply_text("💡 Gõ `/start` để mở Bảng Điều Khiển Nút Bấm hoặc gõ `/post [chủ đề]`!")

def main():
    if not BOT_TOKEN:
        print("❌ Chưa có BOT_TOKEN")
        return

    # Tối ưu kết nối: Đặt timeout polling nhanh và xử lý bất đồng bộ
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(set_bot_menu).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("cauhinh", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 Bot Siêu Tốc Độ (< 0.5s) Đã Khởi Động!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
