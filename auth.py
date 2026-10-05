"""Xác thực người dùng & Phân quyền cho Ứng dụng Chấm thi OMR."""

import hashlib
import json
import os
import re
import streamlit as st

USERS_PATH = os.path.join(os.path.dirname(__file__), "users.json")


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


def check_login(username: str, password: str):
    """Kiểm tra tài khoản và mật khẩu."""
    users = load_users()
    u = username.strip().lower()
    if u in users:
        stored_hash = users[u].get("password_hash", "")
        if stored_hash == hash_pw(password):
            return True, users[u]
    return False, None


def require_auth():
    """Cổng chặn xác thực: Nếu chưa đăng nhập thì hiện Form Đăng Nhập / Đăng Ký và dừng trang."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["user_info"] = {}

    if st.session_state["logged_in"]:
        return True

    # Giao diện Form Đăng Nhập / Đăng Ký Liquid Glass
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
                    btn_submit = st.form_submit_button("🚀 ĐĂNG NHẬP NGAY", type="primary", use_container_width=True)

                    if btn_submit:
                        if not username_input or not password_input:
                            st.error("Vui lòng điền đầy đủ Tên đăng nhập và Mật khẩu!")
                        else:
                            ok, u_info = check_login(username_input, password_input)
                            if ok:
                                st.session_state["logged_in"] = True
                                st.session_state["username"] = username_input.strip().lower()
                                st.session_state["user_info"] = u_info
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
                                st.success(f"🎉 Đăng ký thành công! Chào mừng {fn} đến với hệ thống.")
                                st.rerun()

    st.stop()
    return False
