import os
import traceback
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from agent_core import build_history, run_agent


# 1. Cấu hình trang, nạp .env nằm cạnh app.py.
st.set_page_config(page_title="Agent Streamlit", page_icon="\U0001F916",
                   layout="centered")
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
st.title("Trợ lý AI với Streamlit")
st.caption("Agent dùng công cụ tính toán và đếm từ · Chạy local")


# 2. Khởi tạo state đúng một lần trong phiên kết nối.
if "turns" not in st.session_state:
    st.session_state.turns = []


# 3. Sidebar: cấu hình và xóa lịch sử.
with st.sidebar:
    st.header("Cài đặt & quản lý")
    user_key = st.text_input("Google API Key", type="password",
                             help="Để trống để dùng khóa trong .env.")
    model_name = st.text_input("Tên mô hình", value=DEFAULT_MODEL).strip()
    if st.button("Xóa lịch sử hội thoại", use_container_width=True):
        st.session_state.turns = []
        st.rerun()
    st.caption("Ngữ cảnh: tối đa 5 lượt thành công gần nhất.")
    if DEBUG:
        st.caption("DEBUG bật: hiển thị chi tiết lỗi local.")

api_key = user_key.strip() or os.getenv("GOOGLE_API_KEY", "").strip()


# 4. Hiển thị lại hội thoại, kết quả tool và lỗi của các lượt cũ.
def show_turn(turn: dict) -> None:
    with st.chat_message("user"):
        st.markdown(turn["prompt"])
    with st.chat_message("assistant"):
        if turn.get("error"):
            st.error(turn["error"], icon=":material/error:")
            if DEBUG and turn.get("details"):
                with st.expander("Chi tiết lỗi (dành cho Developer)"):
                    st.code(turn["details"], language="text", wrap_lines=True)
        else:
            st.markdown(turn["reply"])
            if turn.get("events"):
                with st.expander("Công cụ đã chạy"):
                    for event in turn["events"]:
                        st.code(event["tool"], language="text")
                        st.json(event["args"])
                        st.code(event["result"], language="text")


for saved_turn in st.session_state.turns:
    show_turn(saved_turn)
if not st.session_state.turns:
    st.info("Hãy thử: Tính 123 × 456 bằng công cụ calculator.")


# 5. Nhận câu hỏi, gọi Agent và lưu kết quả hoặc lỗi vào state.
if prompt := st.chat_input("Nhập câu hỏi của bạn...", max_chars=2000,
                           submit_mode="disable"):
    prompt = prompt.strip()
    if not prompt:
        st.warning("Hãy nhập câu hỏi trước khi gửi.")
        st.stop()
    turn = {"prompt": prompt, "reply": "", "events": [], "error": ""}
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            if not api_key:
                raise ValueError("Chưa có Google API Key.")
            if not model_name:
                raise ValueError("Tên mô hình không được để trống.")
            history = build_history(st.session_state.turns, prompt)
            with st.spinner("Agent đang xử lý..."):
                turn["reply"], turn["events"] = run_agent(
                    history, api_key, model_name)
        except Exception as exc:
            message = str(exc).lower()
            if not api_key:
                turn["error"] = "Chưa có Google API Key. Hãy nhập ở thanh bên hoặc cấu hình .env."
            elif not model_name:
                turn["error"] = "Tên mô hình không được để trống."
            elif "429" in message or "resource_exhausted" in message:
                turn["error"] = "API đã hết hạn mức hoặc bị giới hạn tốc độ. Kiểm tra quota rồi thử lại."
            elif "api_key_invalid" in message or "api key not valid" in message:
                turn["error"] = "API key không hợp lệ. Kiểm tra hoặc tạo lại khóa trong Google AI Studio."
            elif "404" in message or "not_found" in message:
                turn["error"] = "Không truy cập được mô hình. Kiểm tra tên mô hình và quyền của tài khoản."
            else:
                turn["error"] = "Không thể xử lý yêu cầu. Kiểm tra kết nối, API key và mô hình."
            if DEBUG:
                details = traceback.format_exc()
                for secret in (api_key, os.getenv("GOOGLE_API_KEY", "")):
                    if secret:
                        details = details.replace(secret, "[API_KEY_DA_CHE]")
                turn["details"] = details
    st.session_state.turns.append(turn)
    st.rerun()
