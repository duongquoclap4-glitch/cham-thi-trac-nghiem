"""Xác thực người dùng & Phân quyền cho Ứng dụng Chấm thi Trắc Nghiệm.
Sử dụng công nghệ Cryptographic Signed Token (HMAC-SHA256) kết hợp LocalStorage & URL Parameter
để ghi nhớ thiết bị vĩnh viễn (30 ngày), hoạt động độc lập và bền vững trên Cloud (kể cả khi máy chủ khởi động lại).
"""

from datetime import datetime, timedelta
import base64
import hashlib
import hmac
import json
import os
import re
import time
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components

USERS_PATH = os.path.join(os.path.dirname(__file__), "users.json")
SECRET_SALT = "omr_grader_secret_salt_2025_bo_gddt_quoclap_persistent_key"


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
        try:
            with open(USERS_PATH, "w", encoding="utf-8") as f:
                json.dump(default_users, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return default_users

    try:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Luôn đảm bảo có các tài khoản mặc định
            for k, v in default_users.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default_users


def save_users(users: dict):
    """Lưu danh sách người dùng."""
    try:
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def create_signed_token(username: str, fullname: str, role: str, days: int = 30) -> str:
    """Tạo token ký số an toàn (HMAC-SHA256) chứa đầy đủ thông tin người dùng.
    Không phụ thuộc vào ổ đĩa của server hay container Cloud.
    """
    expires_at = int(time.time() + days * 86400)
    # Mã hóa họ tên bằng base64 an toàn URL
    b64_fullname = base64.urlsafe_b64encode(fullname.strip().encode("utf-8")).decode("ascii")
    payload = f"{username.strip().lower()}~{expires_at}~{role.strip()}~{b64_fullname}"
    sig = hmac.new(SECRET_SALT.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
    return f"{payload}~{sig}"


def verify_signed_token(token: str):
    """Xác thực token ký số HMAC. Trả về (user_info, username) nếu hợp lệ."""
    if not token or not isinstance(token, str):
        return None
    try:
        parts = token.strip().split("~")
        if len(parts) != 5:
            return None
        u, exp_str, role, b64_fn, sig = parts
        exp = int(exp_str)
        if time.time() > exp:
            return None  # Token hết hạn

        payload = f"{u}~{exp_str}~{role}~{b64_fn}"
        expected_sig = hmac.new(SECRET_SALT.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
        if not hmac.compare_digest(sig, expected_sig):
            return None  # Chữ ký không hợp lệ

        fn = base64.urlsafe_b64decode(b64_fn.encode("ascii")).decode("utf-8")
        user_info = {
            "fullname": fn,
            "role": role
        }
        return user_info, u
    except Exception:
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
    """Đăng xuất an toàn: Xóa token trên LocalStorage của trình duyệt và URL."""
    # Xóa token trong query_params
    if "token" in st.query_params:
        try:
            del st.query_params["token"]
        except Exception:
            pass

    # Xóa trong LocalStorage của client
    components.html("""
    <script>
    try {
        if (window.parent && window.parent.localStorage) {
            window.parent.localStorage.removeItem('omr_device_token');
        }
    } catch(e) {}
    try {
        localStorage.removeItem('omr_device_token');
    } catch(e) {}
    </script>
    """, height=0, width=0)

    for k in ["logged_in", "username", "user_info", "active_keys", "active_keys_user", "results_df", "graded_images"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()


def require_auth():
    """Cổng chặn xác thực thông minh:
    1. Kiểm tra session hiện tại.
    2. Kiểm tra token ký số trong URL (?token=...).
    3. Nếu không có token trong URL, chạy JavaScript tự động đọc LocalStorage của thiết bị và tự reload vào thẳng.
    4. Nếu thiết bị chưa từng đăng nhập, hiển thị form Đăng Nhập / Đăng Ký.
    """
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["user_info"] = {}

    # Đã đăng nhập trong phiên làm việc
    if st.session_state["logged_in"]:
        return True

    # 1. Kiểm tra Token từ URL (?token=...)
    token_candidate = st.query_params.get("token")
    if token_candidate:
        verified = verify_signed_token(token_candidate)
        if verified:
            u_info, u_name = verified
            st.session_state["logged_in"] = True
            st.session_state["username"] = u_name
            st.session_state["user_info"] = u_info
            # Đảm bảo lưu token vào LocalStorage cho các lần truy cập bằng link trần
            components.html(f"""
            <script>
            try {{
                if (window.parent && window.parent.localStorage) {{
                    window.parent.localStorage.setItem('omr_device_token', '{token_candidate}');
                }}
            }} catch(e) {{}}
            try {{
                localStorage.setItem('omr_device_token', '{token_candidate}');
            }} catch(e) {{}}
            </script>
            """, height=0, width=0)
            return True

    # 2. Giao diện Form Đăng Nhập / Đăng Ký Liquid Glass (Khóa nền sáng chống Dark Mode)
    st.markdown("""
    <style>
    .stApp, [data-testid="stAppViewContainer"], .main {
        background: #f8fafc !important;
        background-color: #f8fafc !important;
    }
    label, [data-testid="stWidgetLabel"] *, p, span, div {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }
    div[data-baseweb="input"],
    div[data-baseweb="input"] input,
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        border-color: #cbd5e1 !important;
    }
    button[kind="primary"], button[kind="primary"] * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

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

            # Nút Đăng nhập nhanh 1-Chạm nếu thiết bị đã từng ghi nhớ
            components.html("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body { margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; background: transparent; }
                    .card {
                        text-align: center;
                        padding: 10px;
                        background: #f0f9ff;
                        border: 1.5px solid #0284c7;
                        border-radius: 12px;
                        box-sizing: border-box;
                    }
                    .btn {
                        display: block;
                        background: #0284c7;
                        color: #ffffff !important;
                        text-decoration: none;
                        font-weight: 700;
                        font-size: 13.5px;
                        padding: 9px 12px;
                        border-radius: 8px;
                        margin-top: 5px;
                    }
                </style>
            </head>
            <body>
                <div id="quick-card" style="display: none;" class="card">
                    <div style="font-size: 12px; font-weight: 700; color: #0284c7;">⚡ Thiết bị này đã được ghi nhớ:</div>
                    <a id="quick-btn" href="#" target="_top" class="btn">🚀 BẤM ĐỂ VÀO THẲNG (1 CHẠM)</a>
                </div>
                <script>
                try {
                    var token = null;
                    try {
                        if (window.parent && window.parent.localStorage) {
                            token = window.parent.localStorage.getItem('omr_device_token');
                        }
                    } catch(e) {}
                    if (!token) {
                        try {
                            token = localStorage.getItem('omr_device_token');
                        } catch(e) {}
                    }
                    if (token) {
                        var card = document.getElementById('quick-card');
                        var btn = document.getElementById('quick-btn');
                        var base = "";
                        try {
                            if (window.parent && window.parent.location) {
                                base = window.parent.location.href.split('?')[0];
                            }
                        } catch(e) {}
                        if (!base) {
                            base = window.location.href.split('?')[0];
                        }
                        btn.href = base + '?token=' + encodeURIComponent(token);
                        card.style.display = 'block';
                    }
                } catch(err) {}
                </script>
            </body>
            </html>
            """, height=76)

            auth_tabs = st.tabs(["🔐 Đăng Nhập", "📝 Đăng Ký Tài Khoản"])

            # ---- TAB 1: ĐĂNG NHẬP ----
            with auth_tabs[0]:
                with st.form("form_login", clear_on_submit=False):
                    username_input = st.text_input("👤 Tên đăng nhập:", placeholder="Nhập tên tài khoản của bạn...")
                    password_input = st.text_input("🔑 Mật khẩu:", type="password", placeholder="Nhập mật khẩu của bạn...")
                    remember_device = st.checkbox("☑️ Ghi nhớ thiết bị này (30 ngày không cần đăng nhập lại)", value=True)
                    btn_submit = st.form_submit_button("🚀 ĐĂNG NHẬP NGAY", type="primary", use_container_width=True)

                    if btn_submit:
                        if not username_input or not password_input:
                            st.error("Vui lòng điền đầy đủ Tên đăng nhập và Mật khẩu!")
                        else:
                            ok, u_info = check_login(username_input, password_input)
                            if ok:
                                u = username_input.strip().lower()
                                fn = u_info.get("fullname", username_input)
                                role = u_info.get("role", "teacher")
                                st.session_state["logged_in"] = True
                                st.session_state["username"] = u
                                st.session_state["user_info"] = u_info

                                if remember_device:
                                    token = create_signed_token(u, fn, role, days=30)
                                    st.query_params["token"] = token
                                    components.html(f"""
                                    <script>
                                    try {{
                                        if (window.parent && window.parent.localStorage) {{
                                            window.parent.localStorage.setItem('omr_device_token', '{token}');
                                        }}
                                    }} catch(e) {{}}
                                    try {{
                                        localStorage.setItem('omr_device_token', '{token}');
                                    }} catch(e) {{}}
                                    </script>
                                    """, height=0, width=0)

                                st.success(f"Chào mừng {fn}!")
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
                                    token = create_signed_token(u, fn, "teacher", days=30)
                                    st.query_params["token"] = token
                                    components.html(f"""
                                    <script>
                                    try {{
                                        if (window.parent && window.parent.localStorage) {{
                                            window.parent.localStorage.setItem('omr_device_token', '{token}');
                                        }}
                                    }} catch(e) {{}}
                                    try {{
                                        localStorage.setItem('omr_device_token', '{token}');
                                    }} catch(e) {{}}
                                    </script>
                                    """, height=0, width=0)

                                st.success(f"🎉 Đăng ký thành công! Chào mừng {fn} đến với hệ thống.")
                                st.rerun()

    st.stop()
    return False
