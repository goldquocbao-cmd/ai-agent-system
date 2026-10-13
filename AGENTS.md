# 🤖 AGENT INSTRUCTIONS & KNOWLEDGE GRAPH POINTER

> **Attention AI Agents (Antigravity, Claude Code, Cursor, Copilot, Codex):**
> Trước khi thực hiện bất kỳ lệnh duyệt hay sửa đổi nào trong repository này, hãy đọc file [`CODEBASE_MAP.md`](file:///Users/gbholding/.gemini/antigravity/scratch/ai-agent-system/CODEBASE_MAP.md).

### ⚡ QUY TẮC BẤT DI BẤT DỊCH:
1. **Xem Bản Đồ Trước Khi Đọc Code:**
   * Không đọc mù mờ toàn bộ file `main.py` hay `chay_he_thong.py`.
   * Tra cứu chuỗi gọi hàm và bảng phân tích tác động (Impact Analysis) trong [`CODEBASE_MAP.md`](file:///Users/gbholding/.gemini/antigravity/scratch/ai-agent-system/CODEBASE_MAP.md).
2. **Đồng Bộ Song Mã:**
   * File `main.py` và `chay_he_thong.py` luôn phải được đồng bộ 100% giống nhau trước khi commit (`cp main.py chay_he_thong.py`).
3. **Xác Minh Biên Dịch:**
   * Luôn chạy `python3 -m py_compile main.py chay_he_thong.py` để đảm bảo cú pháp không bị lỗi trước khi push.
4. **Bảo Vệ Luồng Bất Đồng Bộ:**
   * Mọi tác vụ I/O (Gemini API, Tỷ giá, Tạo ảnh) phải được chạy qua `loop.run_in_executor` để không làm nghẽn Telegram Polling.
