"""Xác thực người dùng & Phân quyền cho Ứng dụng Chấm thi Trắc Nghiệm.
Hỗ trợ tính năng Ghi nhớ thiết bị (Remember Device 30 ngày) bằng Cookie và Token an toàn.
"""

from datetime import datetime, timedelta
import hashlib
import json
import os
import re
import secrets
import time
import streamlit as st
from streamlit_cookies_controller import CookieController

USERS_PATH = os.path.join(os.path.dirname(__file__), "users.json")
TOKENS_PATH = os.path.join(os.path.dirname(__file__), "device_tokens.json")


def hash_pw(password: str) -> str:
    """Băm mật khẩu SHA256 an toàn."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_users() -> dict:
    """Tải danh sách người dùng từ file users.json (tự tạo mặc định nếu chưa có)."""
    default_users = {
        "admin": {
            "password_hash": hash_pw("123456"),
            "fullname": "Quản Trị Viên",
            "role": "admin"
        },
        "quoclap": {
            "password_hash": hash_pw("123456"),
            "fullname": "Thầy Quốc Lập",
            "role": "teacher"
        },
        "giaovien": {
            "password_hash": hash_pw("123456"),
            "fullname": "Giáo Viên Bộ Môn",
            "role": "teacher"
        }
    }

    if not os.path.exists(USERS_PATH):
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(default_users, f, ensure_ascii=False, indent=2)
        return default_users

    try:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_users


def save_users(users: dict):
    """Lưu danh sách người dùng."""
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def load_tokens() -> dict:
    """Tải danh sách token thiết bị đã ghi nhớ."""
    if not os.path.exists(TOKENS_PATH):
        return {}
    try:
        with open(TOKENS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_tokens(tokens: dict):
    """Lưu danh sách token thiết bị."""
    with open(TOKENS_PATH, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)


def create_device_token(username: str, days: int = 30) -> str:
    """Tạo token mới ghi nhớ thiết bị trong số ngày chỉ định."""
    token = secrets.token_hex(24)
    tokens = load_tokens()
    now = time.time()
    expires_at = now + days * 86400

    # Dọn dẹp các token đã quá hạn
    tokens = {k: v for k, v in tokens.items() if v.get("expires_at", 0) > now}

    tokens[token] = {
        "username": username.strip().lower(),
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at
    }
    save_tokens(tokens)
    return token


def verify_device_token(token: str):
    """Xác thực token thiết bị. Trả về (user_info, username) nếu hợp lệ."""
    if not token or not isinstance(token, str):
        return None
    tokens = load_tokens()
    if token in tokens:
        info = tokens[token]
        if info.get("expires_at", 0) > time.time():
            users = load_users()
            u = info.get("username", "")
            if u in users:
                return users[u], u
    return None


def check_login(username: str, password: str):
    """Kiểm tra tài khoản và mật khẩu."""
    users = load_users()
    u = username.strip().lower()
    if u in users:
        stored_hash = users[u].get("password_hash", "")
        if stored_hash == hash_pw(password):
            return True, users[u]
    return False, None


def logout():
    """Đăng xuất an toàn: Xóa token thiết bị trên Cookie, URL và File lưu trữ."""
    try:
        controller = CookieController(key="omr_auth_cookies")
        controller.remove("omr_device_token")
    except Exception:
        pass

    if "token" in st.query_params:
        curr_token = st.query_params.get("token")
        try:
            del st.query_params["token"]
        except Exception:
            pass
        if curr_token:
            tokens = load_tokens()
            if curr_token in tokens:
                tokens.pop(curr_token, None)
                save_tokens(tokens)

    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["user_info"] = {}
    st.rerun()


def require_auth():
    """Cổng chặn xác thực: Kiểm tra ghi nhớ thiết bị (Cookie/Token) trước khi hiện form đăng nhập."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["user_info"] = {}

    if st.session_state["logged_in"]:
        return True

    # 1. Khởi tạo cookie controller
    cookie_controller = CookieController(key="omr_auth_cookies")

    # 2. Kiểm tra token ghi nhớ từ URL (?token=...) hoặc từ Cookie trình duyệt
    token_candidate = st.query_params.get("token")
    if not token_candidate:
        token_candidate = cookie_controller.get("omr_device_token")

    if token_candidate:
        verified = verify_device_token(token_candidate)
        if verified:
            u_info, u_name = verified
            st.session_state["logged_in"] = True
            st.session_state["username"] = u_name
            st.session_state["user_info"] = u_info
            # Đồng bộ lại token trên query params và cookie
            if not st.query_params.get("token"):
                st.query_params["token"] = token_candidate
            try:
                cookie_controller.set(
                    "omr_device_token",
                    token_candidate,
                    max_age=30 * 86400,
                    expires=datetime.now() + timedelta(days=30)
                )
            except Exception:
                pass
            return True

    # 3. Giao diện Form Đăng Nhập / Đăng Ký Liquid Glass
    col_left, col_mid, col_right = st.columns([1, 1.45, 1])
    with col_mid:
        with st.container(border=True):
            st.markdown("""
            <div style="text-align: center; padding: 10px 0 16px 0;">
                <div style="display: inline-flex; align-items: center; justify-content: center; width: 62px; height: 62px; border-radius: 18px; background: linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(37, 99, 235, 0.25)); border: 1.5px solid #38bdf8; font-size: 30px; margin-bottom: 12px; box-shadow: 0 8px 20px rgba(14, 165, 233, 0.2);">
                    🔐
                </div>
                <div style="font-size: 23px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px;">Hệ Thống Chấm Thi Trắc Nghiệm</div>
                <div style="font-size: 13.5px; color: #64748b; margin-top: 4px;">Đăng nhập hoặc đăng ký tài khoản để sử dụng phần mềm</div>
            </div>
            """, unsafe_allow_html=True)

            auth_tabs = st.tabs(["🔐 Đăng Nhập", "📝 Đăng Ký Tài Khoản"])

            # ---- TAB 1: ĐĂNG NHẬP ----
            with auth_tabs[0]:
                with st.form("form_login", clear_on_submit=False):
                    username_input = st.text_input("👤 Tên đăng nhập:", placeholder="Nhập tên tài khoản của bạn...")
                    password_input = st.text_input("🔑 Mật khẩu:", type="password", placeholder="Nhập mật khẩu của bạn...")
                    remember_device = st.checkbox("☑️ Ghi nhớ đăng nhập trên thiết bị này (30 ngày)", value=True)
                    btn_submit = st.form_submit_button("🚀 ĐĂNG NHẬP NGAY", type="primary", use_container_width=True)

                    if btn_submit:
                        if not username_input or not password_input:
                            st.error("Vui lòng điền đầy đủ Tên đăng nhập và Mật khẩu!")
                        else:
                            ok, u_info = check_login(username_input, password_input)
                            if ok:
                                u = username_input.strip().lower()
                                st.session_state["logged_in"] = True
                                st.session_state["username"] = u
                                st.session_state["user_info"] = u_info

                                if remember_device:
                                    token = create_device_token(u, days=30)
                                    st.query_params["token"] = token
                                    try:
                                        cookie_controller.set(
                                            "omr_device_token",
                                            token,
                                            max_age=30 * 86400,
                                            expires=datetime.now() + timedelta(days=30)
                                        )
                                    except Exception:
                                        pass

                                st.success(f"Chào mừng {u_info.get('fullname', username_input)}!")
                                st.rerun()
                            else:
                                st.error("Tên đăng nhập hoặc mật khẩu không chính xác. Vui lòng thử lại!")

            # ---- TAB 2: ĐĂNG KÝ TÀI KHOẢN MỚI ----
            with auth_tabs[1]:
                with st.form("form_register", clear_on_submit=False):
                    reg_fullname = st.text_input("🏷️ Họ và tên:", placeholder="Ví dụ: Thầy Nguyễn Văn A")
                    reg_username = st.text_input("👤 Tên đăng nhập mới:", placeholder="Viết liền không dấu (VD: nguyenvana)")
                    reg_password = st.text_input("🔑 Mật khẩu mới:", type="password", placeholder="Nhập mật khẩu (từ 4 ký tự)...")
                    reg_confirm = st.text_input("🔒 Xác nhận lại mật khẩu:", type="password", placeholder="Nhập lại mật khẩu...")
                    reg_remember = st.checkbox("☑️ Ghi nhớ thiết bị này sau khi đăng ký (30 ngày)", value=True, key="cb_reg_rem")
                    btn_register = st.form_submit_button("✨ TẠO TÀI KHOẢN MỚI", type="primary", use_container_width=True)

                    if btn_register:
                        fn = reg_fullname.strip()
                        u = reg_username.strip().lower()
                        p = reg_password
                        cp = reg_confirm

                        if not fn or not u or not p or not cp:
                            st.error("Vui lòng điền đầy đủ tất cả các trường thông tin!")
                        elif len(u) < 3:
                            st.error("Tên đăng nhập phải có ít nhất 3 ký tự!")
                        elif not re.match(r"^[a-zA-Z0-9_.-]+$", u):
                            st.error("Tên đăng nhập chỉ gồm chữ cái, chữ số hoặc dấu gạch dưới, không dấu và không khoảng trắng!")
                        elif len(p) < 4:
                            st.error("Mật khẩu phải có độ dài từ 4 ký tự trở lên!")
                        elif p != cp:
                            st.error("Mật khẩu xác nhận không khớp. Vui lòng nhập lại!")
                        else:
                            users = load_users()
                            if u in users:
                                st.warning(f"Tên tài khoản '{u}' đã tồn tại! Vui lòng chọn tên khác.")
                            else:
                                users[u] = {
                                    "password_hash": hash_pw(p),
                                    "fullname": fn,
                                    "role": "teacher"
                                }
                                save_users(users)
                                st.session_state["logged_in"] = True
                                st.session_state["username"] = u
                                st.session_state["user_info"] = users[u]

                                if reg_remember:
                                    token = create_device_token(u, days=30)
                                    st.query_params["token"] = token
                                    try:
                                        cookie_controller.set(
                                            "omr_device_token",
                                            token,
                                            max_age=30 * 86400,
                                            expires=datetime.now() + timedelta(days=30)
                                        )
                                    except Exception:
                                        pass

                                st.success(f"🎉 Đăng ký thành công! Chào mừng {fn} đến với hệ thống.")
                                st.rerun()

    st.stop()
    return False
