"""Ứng dụng Web Chấm Thi Trắc Nghiệm - Phiếu Chuẩn Bộ GD&ĐT 2025.
Giao diện Liquid Glass chuẩn (VisionOS / Frosted Glass) với tab bo tròn 14px, chuyển động nảy lò xo sinh động.
"""

import hashlib
import importlib
import io
import json
import os
import re

import cv2
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import omr_bggdt
importlib.reload(omr_bggdt)
import auth
importlib.reload(auth)
from generate_sample_bggdt import tao_bai_thi_mau
from omr_bggdt import doc_anh, tao_dap_an_tu_anh_phieu, xu_ly_file_bggdt
from auth import require_auth, logout

st.set_page_config(
    page_title="Hệ Thống Chấm Thi Trắc Nghiệm Bộ GD&ĐT 2025",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# CUSTOM CSS: LIQUID GLASS DESIGN SYSTEM
# ==========================================
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* CỐ ĐỊNH CHỦ ĐỀ SÁNG (LIGHT MODE ONLY) - CHỐNG HOÀN TOÀN MỌI ẢNH HƯỞNG TỪ NỀN TỐI */
    :root, html, body, [class*="css"], .stApp {
        color-scheme: light !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Ẩn hoàn toàn thanh công cụ và nút đổi giao diện của Streamlit */
    #MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"] {
        visibility: hidden !important;
        display: none !important;
    }

    /* 1. NỀN SÁNG TRẮNG TINH TẾ & HIỆN ĐẠI */
    .stApp, [data-testid="stAppViewContainer"], .main {
        background: #f8fafc !important;
        background-color: #f8fafc !important;
        color: #0f172a !important;
        color-scheme: light !important;
    }

    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 4rem !important;
        max-width: 1320px !important;
    }

    /* 2. LIQUID GLASS HERO BANNER */
    .hero-banner {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.90) 0%, rgba(30, 58, 138, 0.85) 50%, rgba(2, 132, 199, 0.85) 100%) !important;
        backdrop-filter: blur(28px) saturate(210%) !important;
        -webkit-backdrop-filter: blur(28px) saturate(210%) !important;
        border: 1.5px solid rgba(255, 255, 255, 0.3) !important;
        color: white;
        padding: 26px 34px;
        border-radius: 22px;
        margin-bottom: 24px;
        box-shadow: 
            0 24px 50px -12px rgba(2, 132, 199, 0.38),
            0 0 0 1px rgba(255, 255, 255, 0.2) inset,
            0 2px 4px rgba(0, 0, 0, 0.1) !important;
        position: relative;
        overflow: hidden;
    }
    .hero-banner::after {
        content: '';
        position: absolute;
        top: -40%;
        right: -15%;
        width: 380px;
        height: 380px;
        background: radial-gradient(circle, rgba(56, 189, 248, 0.4) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-title {
        font-size: 26px;
        font-weight: 800;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .hero-subtitle {
        font-size: 14.5px;
        color: #e0f2fe;
        opacity: 0.95;
        line-height: 1.55;
        max-width: 950px;
    }
    .badge-pill {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 8px;
        margin-top: 8px;
    }
    .badge-primary { background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.4); }
    .badge-success { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
    .badge-danger { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
    .badge-warning { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }

    /* 3. KHỐI THẺ VÀ KHUNG CONTAINER RÕ RÀNG, SẮC NÉT & CÓ BÓNG 3D */
    div[data-testid="stVerticalBlock"] > div.stElementContainer:has(> div[data-testid="stVerticalBlock"]) > div[data-testid="stVerticalBlock"],
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div.stElementContainer > div[data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlockBorderWrapper"],
    div.stVerticalBlock[style*="border"],
    div:has(> [data-testid="stVerticalBlock"])[style*="border"] {
        background: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 18px !important;
        box-shadow: 
            0 4px 16px rgba(15, 23, 42, 0.05),
            0 1px 3px rgba(0, 0, 0, 0.02) !important;
        padding: 18px !important;
        margin-bottom: 16px !important;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    }
    div[data-testid="stVerticalBlock"] > div.stElementContainer:has(> div[data-testid="stVerticalBlock"]) > div[data-testid="stVerticalBlock"]:hover,
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div.stElementContainer > div[data-testid="stVerticalBlock"]:hover,
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #38bdf8 !important;
        box-shadow: 
            0 10px 26px rgba(14, 165, 233, 0.16),
            0 1px 3px rgba(0, 0, 0, 0.02) !important;
        transform: translateY(-2px) !important;
    }

    /* Header đề mục kính mờ */
    .glass-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 18px;
        padding-bottom: 14px;
        border-bottom: 1px solid rgba(226, 232, 240, 0.6);
    }
    .glass-header-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.18), rgba(99, 102, 241, 0.22));
        border: 1.5px solid rgba(255, 255, 255, 0.9);
        box-shadow: 0 6px 16px rgba(14, 165, 233, 0.2);
        font-size: 22px;
        flex-shrink: 0;
    }
    .code-badge {
        background: linear-gradient(135deg, #0ea5e9, #2563eb);
        color: white;
        padding: 3px 14px;
        border-radius: 10px;
        font-size: 19px;
        font-weight: 800;
        display: inline-block;
        box-shadow: 0 4px 14px rgba(2, 132, 199, 0.4);
        letter-spacing: 0.5px;
    }

    /* 4. THANH TABS: BO TRÒN 14PX Y HỆT NÚT DƯỚI, XÓA GẠCH ĐỎ & NẨY SPRING */
    /* Triệt tiêu hoàn toàn thanh gạch đỏ và đường kẻ ngang dưới */
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-highlight"],
    [data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] [data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-border"],
    [data-baseweb="tab-border"],
    .react-aria-SelectionIndicator,
    [data-testid="stTab"] .react-aria-SelectionIndicator,
    div[data-testid="stTabs"] .react-aria-SelectionIndicator,
    div[role="tab"] .react-aria-SelectionIndicator,
    div[data-testid="stTabs"] [role="tablist"]::after,
    div[data-testid="stTabs"] div:has(> [data-testid="stTab"])::after,
    div[data-testid="stTabs"] div:has(> [role="tab"])::after,
    button[data-baseweb="tab"]::after,
    button[role="tab"]::after,
    div[role="tab"]::after,
    [data-testid="stTab"]::after {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        width: 0px !important;
        opacity: 0 !important;
        background: transparent !important;
        border: none !important;
        content: none !important;
    }

    /* =======================================================
       BUTTON-STYLE TABS (TẤT CẢ TAB ĐỀU LÀ NÚT BẤM BO TRÒN, GIÃN NHAU RA)
       ======================================================= */

    /* Thanh chứa tab: các nút giãn cách nhau ra 12px rõ rệt */
    div[data-testid="stTabs"] {
        overflow: visible !important;
    }
    div[data-testid="stTabs"] [role="tablist"],
    .stTabs [role="tablist"],
    [data-baseweb="tab-list"],
    div[data-baseweb="tab-list"],
    div[data-testid="stTabs"] div:has(> [data-testid="stTab"]),
    div[data-testid="stTabs"] div:has(> [role="tab"]) {
        background: transparent !important;
        border: none !important;
        border-bottom: none !important;
        box-shadow: none !important;
        padding: 8px 4px 16px 4px !important;
        overflow-y: visible !important;
        overflow-x: auto !important;
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 12px !important; /* GIÃN CÁCH NHAU RA 12PX ĐẸP MẮT */
        margin-bottom: 22px !important;
    }

    /* Từng tab (Cả tab lớn và tab con): Là một nút bấm bo tròn 14px hoàn chỉnh */
    div[data-testid="stTab"],
    [data-testid="stTab"],
    div[role="tab"],
    [role="tab"],
    .react-aria-Tab,
    div[data-testid="stTabs"] button[role="tab"],
    div[data-testid="stTabs"] button[data-baseweb="tab"],
    .stTabs button[role="tab"],
    button[data-baseweb="tab"],
    button[role="tab"] {
        height: auto !important;
        min-height: 42px !important;
        background: rgba(255, 255, 255, 0.92) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1.5px solid rgba(226, 232, 240, 0.95) !important;
        border-radius: 14px !important; /* BO TRÒN 14PX ĐẸP NHƯ NÚT BẤM */
        padding: 10px 22px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        color: #334155 !important;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05) !important;
        cursor: pointer !important;
        outline: none !important;
        margin: 0 !important;
        overflow: hidden !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        white-space: nowrap !important;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important; /* NẨY NẨY LÒ XO */
    }

    div[data-testid="stTab"] > div,
    [role="tab"] > div,
    .react-aria-Tab > div,
    button[data-baseweb="tab"] > div {
        border-radius: 14px !important;
        display: flex !important;
        align-items: center !important;
    }

    div[data-testid="stTab"] p,
    [role="tab"] p,
    .react-aria-Tab p,
    div[data-testid="stTab"] span,
    [role="tab"] span,
    button[data-baseweb="tab"] p {
        color: #334155 !important;
        font-weight: 700 !important;
        margin: 0 !important;
        font-size: 14px !important;
        transition: color 0.2s ease !important;
    }

    /* Hiệu ứng Rê chuột (Hover): Nổi lên và phát sáng viền */
    div[data-testid="stTab"]:hover,
    [role="tab"]:hover,
    .react-aria-Tab:hover,
    button[data-baseweb="tab"]:hover {
        background: #f0f9ff !important;
        border-color: #38bdf8 !important;
        transform: translateY(-2.5px) scale(1.025) !important;
        box-shadow: 0 8px 20px rgba(56, 189, 248, 0.25) !important;
    }
    div[data-testid="stTab"]:hover p,
    [role="tab"]:hover p,
    .react-aria-Tab:hover p,
    div[data-testid="stTab"]:hover span,
    [role="tab"]:hover span,
    button[data-baseweb="tab"]:hover p {
        color: #0284c7 !important;
    }

    /* Hiệu ứng Bấm chuột (Active): Lún thụt xuống như bấm nút thật */
    div[data-testid="stTab"]:active,
    [role="tab"]:active,
    .react-aria-Tab:active,
    div[data-testid="stTab"][data-pressed="true"],
    [role="tab"][data-pressed="true"],
    button[data-baseweb="tab"]:active {
        transform: translateY(2px) scale(0.96) !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.08s ease !important;
    }

    /* Nút Tab Đang Chọn: Liquid Glass Viên Nang Phát Sáng Xanh, Bo Tròn 14px */
    div[data-testid="stTab"][aria-selected="true"],
    div[data-testid="stTab"][data-selected="true"],
    div[data-testid="stTab"][data-selected],
    [role="tab"][aria-selected="true"],
    [role="tab"][data-selected="true"],
    [role="tab"][data-selected],
    .react-aria-Tab[aria-selected="true"],
    .react-aria-Tab[data-selected="true"],
    .react-aria-Tab[data-selected],
    button[data-baseweb="tab"][aria-selected="true"],
    button[role="tab"][aria-selected="true"] {
        border-radius: 14px !important; /* LUÔN BO TRÒN 14PX */
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        border: 1.5px solid #0284c7 !important;
        color: #ffffff !important;
        box-shadow: 
            0 8px 22px -2px rgba(2, 132, 199, 0.45),
            0 0 0 1px rgba(255, 255, 255, 0.35) inset !important;
        transform: translateY(-1px) !important;
        overflow: hidden !important;
    }
    div[data-testid="stTab"][aria-selected="true"] p,
    div[data-testid="stTab"][data-selected="true"] p,
    div[data-testid="stTab"][aria-selected="true"] span,
    div[data-testid="stTab"][data-selected="true"] span,
    [role="tab"][aria-selected="true"] p,
    [role="tab"][data-selected="true"] p,
    [role="tab"][aria-selected="true"] span,
    [role="tab"][data-selected="true"] span,
    .react-aria-Tab[aria-selected="true"] p,
    .react-aria-Tab[data-selected="true"] p,
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 800 !important;
    }

    /* 5. NÚT CHỌN MÃ ĐỀ & ĐÚNG/SAI (RADIO BUTTONS) BO TRÒN & NẨY NẨY NHƯ ẢNH BẠN THÍCH */
    /* Lược bỏ hoàn toàn nền trắng ở các nhãn tiêu đề ý a), ý b), ý c), ý d) */
    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"],
    div[data-testid="stRadio"] > label,
    label[data-testid="stWidgetLabel"] {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 2px 0 6px 0 !important;
        margin: 0 !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
    }
    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] p,
    label[data-testid="stWidgetLabel"] p {
        font-weight: 700 !important;
        color: #0f172a !important;
        font-size: 14.5px !important;
        background: transparent !important;
    }

    div[data-testid="stRadio"] > div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 10px !important;
        padding: 4px 0 !important;
    }
    /* Chỉ áp dụng nền nút bo tròn cho các lựa chọn bấm (Đúng / Sai, Mã đề) */
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(14px) !important;
        border: 1.5px solid rgba(226, 232, 240, 0.9) !important;
        padding: 8px 18px !important;
        border-radius: 14px !important; /* BO TRÒN 14PX */
        font-weight: 700 !important;
        color: #1e293b !important;
        cursor: pointer !important;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04) !important;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important; /* NẨY NẨY */
        margin: 0 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background: #f0f9ff !important;
        border-color: #38bdf8 !important;
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 20px rgba(56, 189, 248, 0.25) !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:active {
        transform: translateY(2px) scale(0.96) !important;
        transition: all 0.08s ease !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        border-color: #0284c7 !important;
        box-shadow: 0 8px 22px -2px rgba(2, 132, 199, 0.5) !important;
        transform: translateY(-1px) !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
        color: #ffffff !important;
        font-weight: 800 !important;
    }

    /* 6. NÚT BẤM CHÍNH (PRIMARY BUTTONS): LIQUID GRADIENT & NẨY NẨY */
    button[kind="primary"], .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 50%, #4f46e5 100%) !important;
        color: white !important;
        border: 1.5px solid rgba(255, 255, 255, 0.35) !important;
        border-radius: 14px !important; /* BO TRÒN 14PX */
        padding: 11px 24px !important;
        font-weight: 800 !important;
        font-size: 14.5px !important;
        letter-spacing: 0.3px !important;
        box-shadow: 
            0 8px 22px -3px rgba(37, 99, 235, 0.45), 
            0 0 0 1px rgba(255, 255, 255, 0.3) inset !important;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important; /* Bouncy Spring */
        cursor: pointer !important;
    }
    button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {
        transform: translateY(-3px) scale(1.025) !important; /* Nẩy lên */
        box-shadow: 
            0 14px 30px -3px rgba(37, 99, 235, 0.65), 
            0 0 0 1px rgba(255, 255, 255, 0.5) inset !important;
    }
    button[kind="primary"]:active, .stButton > button[kind="primary"]:active {
        transform: translateY(2px) scale(0.96) !important; /* Nẩy lún xuống */
        box-shadow: 0 3px 8px -2px rgba(37, 99, 235, 0.4) !important;
        transition: all 0.08s ease !important;
    }

    /* Nút phụ (Secondary) */
    button[kind="secondary"], .stButton > button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.8) !important;
        backdrop-filter: blur(14px) !important;
        border: 1.5px solid rgba(203, 213, 225, 0.8) !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        color: #334155 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    }
    button[kind="secondary"]:hover, .stButton > button[kind="secondary"]:hover {
        background: rgba(254, 242, 242, 0.95) !important;
        color: #dc2626 !important;
        border-color: #fca5a5 !important;
        transform: translateY(-2.5px) scale(1.02) !important;
        box-shadow: 0 8px 20px rgba(220, 38, 38, 0.18) !important;
    }
    button[kind="secondary"]:active, .stButton > button[kind="secondary"]:active {
        transform: translateY(2px) scale(0.96) !important;
        transition: all 0.08s ease !important;
    }

    /* Nút Tải File */
    div[data-testid="stDownloadButton"] > button {
        border-radius: 14px !important;
        font-weight: 800 !important;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        transform: translateY(-2.5px) scale(1.02) !important;
    }
    div[data-testid="stDownloadButton"] > button:active {
        transform: translateY(2px) scale(0.96) !important;
        transition: all 0.08s ease !important;
    }

    /* 7. FORM INPUTS & SELECTBOXES */
    div[data-baseweb="input"] {
        background: #ffffff !important;
        border-radius: 12px !important;
        border: 1.5px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) inset !important;
        transition: all 0.2s ease !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #0284c7 !important;
        box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.2), 0 1px 3px rgba(0, 0, 0, 0.02) inset !important;
    }
    div[data-baseweb="select"] > div {
        background: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
    }

    /* 8. STAT CARDS (HỘP THỐNG KÊ KPI NỀN TRẮNG) */
    .stat-card {
        background: #ffffff !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 18px !important;
        padding: 18px 16px !important;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04) !important;
        text-align: center !important;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    }
    .stat-card:hover {
        transform: translateY(-3px) scale(1.02) !important;
        border-color: #38bdf8 !important;
        box-shadow: 0 10px 24px rgba(14, 165, 233, 0.15) !important;
    }
    .stat-value {
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
    }
    .stat-label {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        margin-top: 4px;
    }

    /* 9. FEATURE CARDS NỀN TRẮNG */
    .feature-card {
        background: #ffffff !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
        height: 100%;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    .feature-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 24px rgba(14, 165, 233, 0.15);
        border-color: #38bdf8;
    }
    .feature-icon {
        font-size: 30px;
        margin-bottom: 10px;
        display: inline-block;
    }
    .feature-title {
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 6px;
    }
    .feature-desc {
        font-size: 13px;
        color: #64748b;
        line-height: 1.5;
    }

    /* 10. EXPANDERS NỀN TRẮNG */
    div[data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 18px !important;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04) !important;
        margin-bottom: 16px !important;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        overflow: hidden !important;
    }
    div[data-testid="stExpander"]:hover {
        border-color: #cbd5e1 !important;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08) !important;
    }

    /* 11. QUESTION MATRIX CHIPS */
    .chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 5px 10px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 700;
        margin: 3px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
        cursor: default;
    }
    .chip:hover {
        transform: translateY(-2px) scale(1.05);
    }
    .chip-ok { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
    .chip-warn { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
    .chip-wrong { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }

    .sub-item {
        display: inline-block;
        padding: 1px 5px;
        border-radius: 4px;
        font-size: 11px;
        margin: 0 1px;
        font-weight: 700;
    }
    .sub-item-ok { background: #bbf7d0; color: #14532d; }
    .sub-item-fail { background: #fecaca; color: #7f1d1d; }

    /* Bubble mini preview */
    .bubble-mini {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        font-size: 12.5px;
        font-weight: 800;
        background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
        color: #0369a1;
        border: 1.5px solid #7dd3fc;
        margin-right: 5px;
        box-shadow: 0 2px 6px rgba(14, 165, 233, 0.2);
    }

    /* ========================================================
       CHỐNG BỊ ẢNH HƯỞNG BỞI NỀN TỐI (DARK MODE OVERRIDE)
       Bảo vệ 100% giao diện: Chữ luôn sắc nét, không bị ẩn chữ
       ======================================================== */
    /* 1. Mọi nhãn widget, tiêu đề và văn bản luôn có màu đậm rõ nét */
    label,
    .stWidgetLabel,
    .stWidgetLabel *,
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] *,
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] span,
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3,
    div[data-testid="stMarkdownContainer"] h4,
    div[data-testid="stMarkdownContainer"] h5,
    div[data-testid="stMarkdownContainer"] strong,
    div[data-testid="stMarkdownContainer"] em,
    .stSelectbox label,
    .stSelectbox label *,
    .stTextInput label,
    .stTextInput label *,
    .stNumberInput label,
    .stNumberInput label *,
    .stRadio label,
    .stRadio label *,
    .stCheckbox label,
    .stCheckbox label *,
    .stFileUploader label,
    .stFileUploader label * {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    /* 2. Toàn bộ các ô nhập dữ liệu (Text Input, Number Input) luôn nền trắng, viền xám sáng */
    div[data-baseweb="input"],
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"],
    div[data-baseweb="base-input"] input,
    .stTextInput input,
    .stNumberInput input,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        border-color: #cbd5e1 !important;
    }

    /* 3. Nút tăng giảm số của Number Input (+ / -) */
    div[data-testid="stNumberInput"] button {
        background-color: #f1f5f9 !important;
        border-color: #cbd5e1 !important;
    }
    div[data-testid="stNumberInput"] button svg {
        fill: #0f172a !important;
    }

    /* 4. Toàn bộ các hộp chọn Selectbox (Chọn A, B, C, D, ...) luôn nền trắng, chữ đen */
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] [role="combobox"],
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        border-color: #cbd5e1 !important;
    }
    div[data-baseweb="select"] svg {
        fill: #0f172a !important;
    }

    /* 5. Menu xổ xuống của Selectbox (Dropdown Popover) */
    ul[data-baseweb="menu"],
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] ul,
    li[data-baseweb="menu-item"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }
    li[data-baseweb="menu-item"]:hover {
        background-color: #f0f9ff !important;
        color: #0284c7 !important;
        -webkit-text-fill-color: #0284c7 !important;
    }

    /* 6. Hộp tải file (File Uploader) luôn sáng sủa */
    div[data-testid="stFileUploader"] section {
        background-color: #ffffff !important;
        border-color: #cbd5e1 !important;
    }
    div[data-testid="stFileUploader"] section * {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    /* 7. Khung Radio (chọn mã đề) */
    div[data-testid="stRadio"] [role="radiogroup"] label * {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    /* 8. Bảng điểm Dataframe / Table */
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    /* 9. Nút bấm phụ (Secondary buttons, Download buttons) luôn nền trắng, chữ đậm */
    button[kind="secondary"],
    div[data-testid="stButton"] button:not([kind="primary"]),
    div[data-testid="stDownloadButton"] button:not([kind="primary"]) {
        background-color: #ffffff !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        border: 1.5px solid #cbd5e1 !important;
    }
    button[kind="secondary"]:hover,
    div[data-testid="stButton"] button:not([kind="primary"]):hover,
    div[data-testid="stDownloadButton"] button:not([kind="primary"]):hover {
        background-color: #f1f5f9 !important;
        border-color: #0284c7 !important;
        color: #0284c7 !important;
        -webkit-text-fill-color: #0284c7 !important;
    }

    /* Ngoại lệ cho Hero Banner và nút Primary (có màu nền xanh/tối) */
    .hero-banner, .hero-banner *,
    button[kind="primary"], button[kind="primary"] *,
    .badge-primary, .code-badge {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    .hero-subtitle {
        color: #e0f2fe !important;
        -webkit-text-fill-color: #e0f2fe !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CỔNG BẢO MẬT & ĐĂNG NHẬP
# ==========================================
require_auth()

# ==========================================
# HERO BANNER & THÔNG TIN TÀI KHOẢN
# ==========================================
user_info = st.session_state.get("user_info", {})
fullname = user_info.get("fullname", st.session_state.get("username", "Giáo viên"))
role_label = "Quản trị viên" if user_info.get("role") == "admin" else "Giáo viên"

col_hero, col_user = st.columns([3.8, 1.2])
with col_hero:
    st.markdown("""
    <div class="hero-banner" style="margin-bottom: 0px; padding: 18px 28px;">
        <div class="hero-title" style="font-size: 24px;">🎓 Hệ Thống Chấm Phiếu Trắc Nghiệm</div>
        <div style="margin-top: 8px;">
            <span class="badge-pill badge-primary">✨ Quoc Lap</span>
            <span class="badge-pill badge-primary">📐 Barem Chuẩn Bộ GD&ĐT 2025</span>
            <span class="badge-pill badge-primary">⚡ Quét Mã Đề Tự Động</span>
            <span class="badge-pill badge-primary">📊 Xuất Bảng Điểm Excel</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_user:
    with st.container(border=True):
        st.markdown(f"""
        <div style="font-size: 13.5px; font-weight: 700; color: #0f172a;">👤 {fullname}</div>
        <div style="font-size: 12px; color: #64748b; margin-bottom: 6px;">Vai trò: <b>{role_label}</b></div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Đăng Xuất", type="secondary", use_container_width=True, key="btn_logout"):
            logout()

st.write("")

# File paths
PDF_PATH = os.path.join(os.path.dirname(__file__), "phieu_chuan_bggdt_2025.pdf")
IMG_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "phieu_chuan_bggdt_150dpi.png")
SAMPLE_KEY_PATH = os.path.join(os.path.dirname(__file__), "dap_an_chuan_bggdt.json")


def get_user_keys_path(username: str) -> str:
    """Đường dẫn file đáp án riêng cho từng tài khoản."""
    clean_u = re.sub(r'[^a-zA-Z0-9_-]', '_', str(username).strip().lower())
    if not clean_u:
        clean_u = "default_user"
    user_dir = os.path.join(os.path.dirname(__file__), "user_data", clean_u)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, "dap_an_chuan.json")


def save_user_keys(username: str, keys_dict: dict):
    """Lưu đáp án vào kho riêng của tài khoản."""
    path = get_user_keys_path(username)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(keys_dict, f, ensure_ascii=False, indent=2)


# Phân tách dữ liệu đáp án riêng biệt cho từng tài khoản người dùng
current_user = st.session_state.get("username", "default")
user_key_file = get_user_keys_path(current_user)

if "active_keys_user" not in st.session_state or st.session_state.get("active_keys_user") != current_user:
    if os.path.exists(user_key_file):
        try:
            with open(user_key_file, "r", encoding="utf-8") as f:
                st.session_state["active_keys"] = json.load(f)
        except Exception:
            st.session_state["active_keys"] = {}
    elif os.path.exists(SAMPLE_KEY_PATH):
        with open(SAMPLE_KEY_PATH, "r", encoding="utf-8") as f:
            st.session_state["active_keys"] = json.load(f)
        save_user_keys(current_user, st.session_state["active_keys"])
    else:
        st.session_state["active_keys"] = {
            "101": {
                "phan1": {str(i): "A" for i in range(1, 13)},
                "phan2": {str(i): {"a": "D", "b": "S", "c": "D", "d": "S"} for i in range(1, 5)},
                "phan3": {"1": "12", "2": "-3.5", "3": "0.25", "4": "2025", "5": "-12", "6": "100"}
            }
        }
        save_user_keys(current_user, st.session_state["active_keys"])
    st.session_state["active_keys_user"] = current_user

tabs = st.tabs([
    "🖨️ Tải Phiếu Thi",
    "🔑 Quản Lý Mã Đề & Đáp Án",
    "✅ Chấm Thi & Báo Cáo Chi Tiết"
])

# ==========================================
# TAB 1: TẢI PHIẾU THI
# ==========================================
with tabs[0]:
    c_left, c_right = st.columns([1.1, 0.9])

    with c_left:
        with st.container(border=True):
            st.markdown("#### 📥 Tải Phiếu In")
            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if os.path.exists(PDF_PATH):
                    with open(PDF_PATH, "rb") as f_pdf:
                        st.download_button(
                            "📄 TẢI FILE PDF CHÍNH THỨC (A4)",
                            f_pdf.read(),
                            file_name="phieu_tra_loi_trac_nghiem_bggdt_2025.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
            with btn_c2:
                if os.path.exists(IMG_TEMPLATE_PATH):
                    with open(IMG_TEMPLATE_PATH, "rb") as f_img:
                        st.download_button(
                            "🖼️ Tải Ảnh Phiếu Mẫu (PNG 150 DPI)",
                            f_img.read(),
                            file_name="phieu_chuan_bggdt_150dpi.png",
                            mime="image/png"
                        )

            st.info("💡 **Lưu ý khi in phiếu:** Trong hộp thoại in của máy tính, chọn **Scale 100%** (hoặc *Actual Size*) và chọn khổ giấy **A4** để giữ nguyên kích thước tọa độ chuẩn.")

    with c_right:
        with st.container(border=True):
            st.markdown("""
            <div class="glass-header">
                <div class="glass-header-icon">🖼️</div>
                <div>
                    <div style="font-size: 19px; font-weight: 800; color: #0f172a;">Xem Trước Phiếu Thi Gốc</div>
                    <div style="font-size: 13px; color: #64748b;">Mẫu chính thức Bộ Giáo dục và Đào tạo 2025</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if os.path.exists(IMG_TEMPLATE_PATH):
                st.image(IMG_TEMPLATE_PATH, caption="Phiếu thi chính thức Bộ GD&ĐT (Áp dụng từ kỳ thi tốt nghiệp 2025)")

# ==========================================
# TAB 2: QUẢN LÝ MÃ ĐỀ & ĐÁP ÁN (LIQUID GLASS FORM)
# ==========================================
with tabs[1]:
    keys = st.session_state["active_keys"]
    ds_made = sorted(list(keys.keys()))

    if not ds_made:
        keys["101"] = {
            "phan1": {str(i): "A" for i in range(1, 13)},
            "phan2": {str(i): {"a": "D", "b": "S", "c": "D", "d": "S"} for i in range(1, 5)},
            "phan3": {"1": "12", "2": "-3.5", "3": "0.25", "4": "2025", "5": "-12", "6": "100"}
        }
        ds_made = ["101"]

    # SECTION 1: QUẢN LÝ & CHUYỂN ĐỔI MÃ ĐỀ
    with st.container(border=True):
        st.markdown("""
        <div class="glass-header">
            <div class="glass-header-icon">🏷️</div>
            <div>
                <div style="font-size: 19px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px;">1. Quản Lý & Chuyển Đổi Mã Đề</div>
                <div style="font-size: 13px; color: #64748b; font-weight: 500;">Bấm vào nút mã đề để chuyển đổi hoặc nhập mã đề mới tự do (VD: 332, 445)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        card_col1, card_col2 = st.columns([1.3, 1.1])

        with card_col1:
            st.markdown("**Chọn mã đề:**")
            chon_made = st.radio(
                "Danh sách mã đề đang có:",
                options=ds_made,
                horizontal=True,
                key="radio_made_selector",
                label_visibility="collapsed"
            )

            if len(ds_made) > 1:
                st.write("")
                if st.button(f"🗑️ Xóa mã đề {chon_made}", type="secondary", key="btn_del_made"):
                    del keys[chon_made]
                    st.session_state["active_keys"] = keys
                    save_user_keys(current_user, keys)
                    st.success(f"Đã xóa mã đề {chon_made}!")
                    st.rerun()

        with card_col2:
            st.markdown("**➕ Thêm mã đề mới (nhập 3 chữ số tự do, VD: `332`, `445`):**")
            add_c1, add_c2 = st.columns([1.2, 1])
            with add_c1:
                new_code_val = st.text_input("Mã đề mới:", max_chars=3, placeholder="VD: 332", key="txt_new_made", label_visibility="collapsed")
            with add_c2:
                if st.button("➕ Thêm Mã Đề", type="primary"):
                    s_ma = str(new_code_val).strip()
                    if not s_ma or not s_ma.isdigit():
                        st.error("Mã đề phải gồm 3 chữ số (ví dụ: 332, 445).")
                    elif s_ma in keys:
                        st.warning(f"Mã đề {s_ma} đã có trong danh sách.")
                    else:
                        src_data = keys.get(chon_made, {})
                        keys[s_ma] = json.loads(json.dumps(src_data))
                        st.session_state["active_keys"] = keys
                        save_user_keys(current_user, keys)
                        st.success(f"✅ Đã thêm mã đề **{s_ma}** thành công vào kho của bạn!")
                        st.rerun()

    # SECTION 2: SOẠN ĐÁP ÁN CHI TIẾT
    # SECTION 2: CẤU HÌNH MÔN THI & SOẠN ĐÁP ÁN CHI TIẾT
    with st.container(border=True):
        st.markdown(f"""
        <div class="glass-header">
            <div class="glass-header-icon">✍️</div>
            <div>
                <div style="font-size: 19px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px;">
                    2. Cấu Hình Môn Thi & Soạn Đáp Án Cho Mã Đề: 
                    <span class="code-badge">{chon_made}</span>
                </div>
                <div style="font-size: 13px; color: #64748b; font-weight: 500;">Chọn nhanh định dạng môn thi chuẩn Bộ GD&ĐT 2025 hoặc tự do tùy biến số câu hỏi và thang điểm</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        data_de = keys.get(chon_made, {"phan1": {}, "phan2": {}, "phan3": {}})
        curr_p1 = data_de.get("phan1", {})
        curr_p2 = data_de.get("phan2", {})
        curr_p3 = data_de.get("phan3", {})
        curr_mon = data_de.get("mon", "Toán (12 P.I + 4 P.II + 6 P.III)")
        curr_diem_p1 = float(data_de.get("diem_moi_cau_p1", 0.25))
        curr_diem_p3 = float(data_de.get("diem_moi_cau_p3", 0.50))

        # CÁC NÚT CHỌN NHANH MÔN THI (1-CLICK PRESETS)
        st.markdown("**🎯 Chọn nhanh định dạng môn thi (Chuẩn Bộ GD&ĐT 2025):**")
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

        with col_m1:
            if st.button("📐 Môn Toán\n(12 P1 + 4 P2 + 6 P3)", use_container_width=True, key=f"btn_pre_toan_{chon_made}"):
                data_de["phan1"] = {str(i): curr_p1.get(str(i), "A") for i in range(1, 13)}
                data_de["phan2"] = {str(i): curr_p2.get(str(i), {"a": "Đ", "b": "S", "c": "Đ", "d": "S"}) for i in range(1, 5)}
                data_de["phan3"] = {str(i): curr_p3.get(str(i), "0") for i in range(1, 7)}
                data_de["mon"] = "Toán (12 P.I + 4 P.II + 6 P.III)"
                data_de["diem_moi_cau_p1"] = 0.25
                data_de["diem_moi_cau_p3"] = 0.50
                keys[chon_made] = data_de
                st.session_state["active_keys"] = keys
                save_user_keys(current_user, keys)
                st.rerun()

        with col_m2:
            if st.button("🌐 Ngoại Ngữ\n(40 câu P1 - 0.25đ)", use_container_width=True, key=f"btn_pre_nn_{chon_made}"):
                data_de["phan1"] = {str(i): curr_p1.get(str(i), "A") for i in range(1, 41)}
                data_de["phan2"] = {}
                data_de["phan3"] = {}
                data_de["mon"] = "Ngoại ngữ / Tiếng Anh (40 câu P.I)"
                data_de["diem_moi_cau_p1"] = 0.25
                data_de["diem_moi_cau_p3"] = 0.0
                keys[chon_made] = data_de
                st.session_state["active_keys"] = keys
                save_user_keys(current_user, keys)
                st.rerun()

        with col_m3:
            if st.button("📜 KH Xã Hội\n(24 P1 + 4 P2)", use_container_width=True, key=f"btn_pre_khxh_{chon_made}"):
                data_de["phan1"] = {str(i): curr_p1.get(str(i), "A") for i in range(1, 25)}
                data_de["phan2"] = {str(i): curr_p2.get(str(i), {"a": "Đ", "b": "S", "c": "Đ", "d": "S"}) for i in range(1, 5)}
                data_de["phan3"] = {}
                data_de["mon"] = "Lịch sử / Địa lí / GDKT&PL (24 P.I + 4 P.II)"
                data_de["diem_moi_cau_p1"] = 0.25
                data_de["diem_moi_cau_p3"] = 0.0
                keys[chon_made] = data_de
                st.session_state["active_keys"] = keys
                save_user_keys(current_user, keys)
                st.rerun()

        with col_m4:
            if st.button("🔬 KH Tự Nhiên\n(18 P1 + 4 P2 + 6 P3)", use_container_width=True, key=f"btn_pre_khtn_{chon_made}"):
                data_de["phan1"] = {str(i): curr_p1.get(str(i), "A") for i in range(1, 19)}
                data_de["phan2"] = {str(i): curr_p2.get(str(i), {"a": "Đ", "b": "S", "c": "Đ", "d": "S"}) for i in range(1, 5)}
                data_de["phan3"] = {str(i): curr_p3.get(str(i), "0") for i in range(1, 7)}
                data_de["mon"] = "Vật lí / Hóa / Sinh / Tin / CN (18 P.I + 4 P.II + 6 P.III)"
                data_de["diem_moi_cau_p1"] = 0.25
                data_de["diem_moi_cau_p3"] = 0.25
                keys[chon_made] = data_de
                st.session_state["active_keys"] = keys
                save_user_keys(current_user, keys)
                st.rerun()

        with col_m5:
            if st.button("⚙️ Tùy Biến\n(Tự cấu hình)", use_container_width=True, key=f"btn_pre_custom_{chon_made}"):
                data_de["mon"] = "Tùy biến cấu hình"
                keys[chon_made] = data_de
                st.session_state["active_keys"] = keys
                save_user_keys(current_user, keys)
                st.rerun()

        # Hiển thị tóm tắt cấu hình đang chọn
        p1_pts = len(curr_p1) * curr_diem_p1
        p2_pts = len(curr_p2) * 1.0
        p3_pts = len(curr_p3) * curr_diem_p3
        tong_pts = p1_pts + p2_pts + p3_pts

        st.markdown(f"""
        <div style="background: rgba(240, 249, 255, 0.9); border: 1.5px solid #bae6fd; border-radius: 12px; padding: 10px 16px; margin: 12px 0 16px 0; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
            <span style="font-weight: 700; color: #0369a1; font-size: 13.5px;">📌 Đang áp dụng: <b>{curr_mon}</b></span>
            <span class="badge-pill badge-primary">P.I: {len(curr_p1)} câu ({p1_pts:.2f}đ)</span>
            <span class="badge-pill badge-primary">P.II: {len(curr_p2)} câu ({p2_pts:.2f}đ)</span>
            <span class="badge-pill badge-primary">P.III: {len(curr_p3)} câu ({p3_pts:.2f}đ)</span>
            <span class="badge-pill badge-success" style="font-size: 13px; font-weight: 800;">Tổng điểm tối đa: {tong_pts:.2f}đ</span>
        </div>
        """, unsafe_allow_html=True)

        p_tabs = st.tabs([
            f"1️⃣ Phần I: 4 Lựa Chọn ({len(curr_p1)} câu)",
            f"2️⃣ Phần II: Đúng / Sai ({len(curr_p2)} câu)",
            f"3️⃣ Phần III: Trả Lời Ngắn ({len(curr_p3)} câu)",
            "📸 Quét Phiếu Đáp Án Giáo Viên"
        ])

        # ---- SUBTAB PHẦN I ----
        with p_tabs[0]:
            with st.container(border=True):
                c_p1_num, c_p1_diem, c_p1_quick = st.columns([1, 1, 2])
                with c_p1_num:
                    so_cau_p1 = st.number_input(
                        "Số câu hỏi Phần I:",
                        min_value=0,
                        max_value=40,
                        value=len(curr_p1) if len(curr_p1) > 0 else (40 if "Ngoại ngữ" in curr_mon else 12),
                        step=1,
                        key=f"num_p1_{chon_made}"
                    )
                with c_p1_diem:
                    diem_val_p1 = st.number_input(
                        "Điểm mỗi câu P.I:",
                        min_value=0.05,
                        max_value=2.0,
                        value=curr_diem_p1,
                        step=0.05,
                        format="%.2f",
                        key=f"diem_p1_{chon_made}"
                    )
                with c_p1_quick:
                    def_str = "".join([curr_p1.get(str(i), "A") for i in range(1, so_cau_p1 + 1)])
                    quick_str = st.text_input(
                        "⚡ Nhập nhanh chuỗi đáp án (gõ liền, ví dụ: ABCDABCDABCD):",
                        value=def_str,
                        key=f"quick_str_{chon_made}"
                    )

            if so_cau_p1 > 0:
                clean_chars = re.sub(r"[^ABCDabcd]", "", quick_str).upper()
                st.write("Bảng chọn đáp án từng câu Phần I:")
                grid_cols = st.columns(4)
                for i in range(1, so_cau_p1 + 1):
                    target_col = grid_cols[(i - 1) % 4]
                    default_val = clean_chars[i - 1] if i - 1 < len(clean_chars) else curr_p1.get(str(i), "A")
                    idx_opt = ["A", "B", "C", "D"].index(default_val) if default_val in ["A", "B", "C", "D"] else 0
                    with target_col:
                        with st.container(border=True):
                            st.markdown(f"**Câu {i}:**")
                            sel_opt = st.selectbox(
                                f"Đáp án Câu {i}:",
                                options=["A", "B", "C", "D"],
                                index=idx_opt,
                                key=f"p1_sel_{chon_made}_{i}",
                                label_visibility="collapsed"
                            )
                            curr_p1[str(i)] = sel_opt
                data_de["phan1"] = {str(i): curr_p1[str(i)] for i in range(1, so_cau_p1 + 1)}
            else:
                data_de["phan1"] = {}
                st.info("Phần I hiện có 0 câu hỏi.")

        # ---- SUBTAB PHẦN II (ĐÚNG / SAI) ----
        with p_tabs[1]:
            so_cau_p2 = st.number_input(
                "Số câu hỏi Phần II (mỗi câu gồm 4 ý a, b, c, d):",
                min_value=0,
                max_value=8,
                value=len(curr_p2),
                step=1,
                key=f"num_p2_{chon_made}"
            )

            if so_cau_p2 > 0:
                p2_cards = st.columns(min(so_cau_p2, 4))
                for q_i in range(1, so_cau_p2 + 1):
                    col_target = p2_cards[(q_i - 1) % len(p2_cards)]
                    with col_target:
                        with st.container(border=True):
                            st.markdown(f"**Câu {q_i}:**")
                            sub_dict = curr_p2.get(str(q_i), {"a": "Đ", "b": "S", "c": "Đ", "d": "S"})
                            updated_sub = {}
                            for s in ["a", "b", "c", "d"]:
                                cur_s = str(sub_dict.get(s, "Đ")).upper()
                                c_choice = st.radio(
                                    f"Ý {s}):",
                                    options=["Đúng (Đ)", "Sai (S)"],
                                    index=0 if cur_s in ("Đ", "D") else 1,
                                    key=f"p2_r_{chon_made}_{q_i}_{s}",
                                    horizontal=True
                                )
                                updated_sub[s] = "Đ" if "Đúng" in c_choice else "S"
                            curr_p2[str(q_i)] = updated_sub
                data_de["phan2"] = {str(i): curr_p2[str(i)] for i in range(1, so_cau_p2 + 1)}
            else:
                data_de["phan2"] = {}
                st.info("💡 Môn này hiện không có câu hỏi Đúng / Sai Phần II (0 câu). Tăng số câu ở trên nếu đề thi của bạn có Phần II.")

        # ---- SUBTAB PHẦN III ----
        with p_tabs[2]:
            c_p3_num, c_p3_diem = st.columns([1, 1])
            with c_p3_num:
                so_cau_p3 = st.number_input(
                    "Số câu hỏi Phần III (trả lời ngắn):",
                    min_value=0,
                    max_value=6,
                    value=len(curr_p3),
                    step=1,
                    key=f"num_p3_{chon_made}"
                )
            with c_p3_diem:
                diem_val_p3 = st.number_input(
                    "Điểm mỗi câu P.III:",
                    min_value=0.05,
                    max_value=2.0,
                    value=curr_diem_p3,
                    step=0.05,
                    format="%.2f",
                    key=f"diem_p3_{chon_made}"
                )

            if so_cau_p3 > 0:
                st.markdown("**Soạn đáp án Phần III (Điền số thực, số âm, số thập phân):**")
                st.caption("Ví dụ: `12`, `-3.5`, `0.25`, `2025`, `-12`, `100`")

                p3_cards = st.columns(3)
                for q_i in range(1, so_cau_p3 + 1):
                    with p3_cards[(q_i - 1) % 3]:
                        with st.container(border=True):
                            cur_v = curr_p3.get(str(q_i), "0")
                            in_v = st.text_input(
                                f"Câu {q_i}:",
                                value=str(cur_v),
                                key=f"p3_txt_{chon_made}_{q_i}",
                                placeholder="VD: 12 hoặc -3.5"
                            )
                            curr_p3[str(q_i)] = str(in_v).strip()

                            chars_preview = list(str(in_v).strip().replace(".", ","))[:4]
                            if chars_preview:
                                preview_html = '<div style="margin-top: 6px;"><span style="font-size: 11px; color: #64748b; font-weight: 600;">Mô phỏng ô tô: </span>'
                                for ch in chars_preview:
                                    preview_html += f'<span class="bubble-mini">{ch}</span>'
                                preview_html += '</div>'
                                st.markdown(preview_html, unsafe_allow_html=True)
                data_de["phan3"] = {str(i): curr_p3[str(i)] for i in range(1, so_cau_p3 + 1)}
            else:
                data_de["phan3"] = {}
                st.info("💡 Môn này hiện không có câu hỏi Trả lời ngắn Phần III (0 câu). Tăng số câu ở trên nếu đề thi của bạn có Phần III.")

        # ---- SUBTAB QUÉT PHIẾU GV ----
        with p_tabs[3]:
            st.markdown(f"**📸 Quét từ ảnh phiếu đáp án của Giáo viên cho Mã đề {chon_made}:**")
            st.write("Nếu bạn đã tô sẵn 1 tờ phiếu thi giấy làm đáp án mẫu, chỉ cần tải ảnh lên:")
            f_gv = st.file_uploader("Tải ảnh phiếu đáp án:", type=["jpg", "jpeg", "png"], key=f"f_gv_{chon_made}")
            if f_gv:
                try:
                    img_gv = doc_anh(f_gv.getvalue())
                    code_gv, data_gv = tao_dap_an_tu_anh_phieu(img_gv)
                    st.success(f"Quét thành công! Mã đề trên phiếu: **{code_gv}**.")
                    if st.button(f"Áp dụng vào mã đề {chon_made}"):
                        data_gv["mon"] = curr_mon
                        data_gv["diem_moi_cau_p1"] = diem_val_p1
                        data_gv["diem_moi_cau_p3"] = diem_val_p3
                        keys[chon_made] = data_gv
                        st.session_state["active_keys"] = keys
                        save_user_keys(current_user, keys)
                        st.success("Đã cập nhật đáp án từ phiếu ảnh vào kho riêng của bạn!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

        # NÚT LƯU CHÍNH
        st.markdown("---")
        save_c1, save_c2 = st.columns([1, 2])
        with save_c1:
            if st.button(f"💾 LƯU ĐÁP ÁN MÃ ĐỀ {chon_made}", type="primary"):
                data_de["mon"] = curr_mon
                data_de["diem_moi_cau_p1"] = diem_val_p1
                data_de["diem_moi_cau_p3"] = diem_val_p3
                keys[chon_made] = data_de
                st.session_state["active_keys"] = keys
                save_user_keys(current_user, keys)
                st.success(f"🎉 Đã lưu đáp án Mã đề **{chon_made}** vào kho riêng của bạn ({fullname})!")
        with save_c2:
            st.info(f"📌 Đang cấu hình: **{len(data_de['phan1'])} câu Phần I** | **{len(data_de['phan2'])} câu Phần II** | **{len(data_de['phan3'])} câu Phần III** cho mã đề **{chon_made}**.")

# ==========================================
# TAB 3: CHẤM THI & BÁO CÁO CHI TIẾT
# ==========================================
with tabs[2]:
    # 1. KHỚP DANH SÁCH HỌC SINH (STUDENT ROSTER MAPPING)
    with st.expander("📋 Khớp Danh Sách Học Sinh (Excel / CSV) — Tự động điền Họ tên & Lớp", expanded=("student_roster" in st.session_state)):
        r_c1, r_c2 = st.columns([1.5, 1])
        with r_c1:
            f_roster = st.file_uploader(
                "Tải lên tệp danh sách học sinh (.xlsx, .xls, .csv):",
                type=["xlsx", "xls", "csv"],
                key="uploader_roster_file"
            )
            if f_roster is not None:
                try:
                    if f_roster.name.endswith(".csv"):
                        df_roster = pd.read_csv(f_roster)
                    else:
                        df_roster = pd.read_excel(f_roster)

                    # Nhận diện cột thông minh (SBD, Họ và tên, Lớp)
                    col_sbd, col_name, col_class = None, None, None
                    for c in df_roster.columns:
                        c_clean = str(c).strip().lower()
                        if not col_sbd and any(k in c_clean for k in ["sbd", "số báo danh", "so bao danh", "mã học sinh", "ma hoc sinh", "id", "thí sinh"]):
                            col_sbd = c
                        elif not col_name and any(k in c_clean for k in ["họ và tên", "ho va ten", "họ tên", "ho ten", "tên", "ten", "học sinh", "name"]):
                            col_name = c
                        elif not col_class and any(k in c_clean for k in ["lớp", "lop", "class"]):
                            col_class = c

                    if col_sbd and col_name:
                        roster_map = {}
                        for _, r in df_roster.iterrows():
                            sbd_raw = str(r[col_sbd]).strip()
                            if sbd_raw.endswith(".0"):
                                sbd_raw = sbd_raw[:-2]
                            t_val = str(r[col_name]).strip()
                            l_val = str(r[col_class]).strip() if col_class else "—"

                            item = {"ten": t_val, "lop": l_val}
                            roster_map[sbd_raw] = item
                            roster_map[sbd_raw.zfill(6)] = item
                            roster_map[sbd_raw.lstrip("0")] = item

                        st.session_state["student_roster"] = roster_map
                        st.session_state["roster_filename"] = f_roster.name
                        cols_to_preview = [col_sbd, col_name] + ([col_class] if col_class else [])
                        st.session_state["roster_preview"] = df_roster[cols_to_preview].head(5)
                        st.success(f"✅ Đã liên kết danh sách: **{len(df_roster)} học sinh** từ file `{f_roster.name}`!")
                    else:
                        st.error("Không tìm thấy cột Số Báo Danh (SBD) hoặc cột Họ và tên trong file. Vui lòng kiểm tra lại dòng tiêu đề.")
                except Exception as ex:
                    st.error(f"Lỗi khi đọc file danh sách học sinh: {ex}")

        with r_c2:
            if "student_roster" in st.session_state:
                st.markdown(f"**Đang áp dụng danh sách:** `{st.session_state.get('roster_filename', 'danh_sach.xlsx')}`")
                if "roster_preview" in st.session_state:
                    st.dataframe(st.session_state["roster_preview"], hide_index=True, use_container_width=True)
                if st.button("🗑️ Hủy liên kết danh sách này", type="secondary", key="btn_clear_roster"):
                    del st.session_state["student_roster"]
                    if "roster_filename" in st.session_state:
                        del st.session_state["roster_filename"]
                    if "roster_preview" in st.session_state:
                        del st.session_state["roster_preview"]
                    st.rerun()
            else:
                st.info("💡 Mẹo: File danh sách chỉ cần gồm các cột: **SBD** (ví dụ 000101 hoặc 101), **Họ và tên**, và **Lớp** (tùy chọn).")

    # 2. CHỌN PHƯƠNG THỨC CHẤM: TẢI TỆP HÀNG LOẠT HOẶC QUÉT CAMERA TRỰC TIẾP
    with st.container(border=True):
        st.markdown("""
        <div class="glass-header">
            <div class="glass-header-icon">📤</div>
            <div>
                <div style="font-size: 19px; font-weight: 800; color: #0f172a;">Chấm Bài Thi Trắc Nghiệm</div>
                <div style="font-size: 13px; color: #64748b;">Hỗ trợ ảnh chụp camera điện thoại (nghiêng, ngược sáng, xoay 180°), JPG, PNG hoặc quét trực tiếp từ webcam/camera</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # CHỌN PHƯƠNG THỨC NỘP BÀI THI (KHÔNG BAO GIỜ TỰ ĐỘNG BẬT CAMERA)
        col_m1, col_m2 = st.columns(2)
        cur_mode = st.session_state.get("scan_mode", "file")
        with col_m1:
            if st.button(
                "📁 Tải Lên Tệp Bài Thi (Ảnh / Scan từ máy & điện thoại)",
                use_container_width=True,
                type="primary" if cur_mode == "file" else "secondary",
                key="btn_mode_file"
            ):
                st.session_state["scan_mode"] = "file"
                st.session_state["cam_active"] = False
                st.rerun()

        with col_m2:
            if st.button(
                "📸 Quét Trực Tiếp Bằng Máy Ảnh (Bật Camera trình duyệt)",
                use_container_width=True,
                type="primary" if cur_mode == "cam" else "secondary",
                key="btn_mode_cam"
            ):
                st.session_state["scan_mode"] = "cam"
                st.rerun()

        scan_mode = st.session_state.get("scan_mode", "file")
        bo_da_dung = st.session_state.get("active_keys", {})
        roster_data = st.session_state.get("student_roster")

        # ---- CHẾ ĐỘ 1: TẢI TỆP HÀNG LOẠT (MẶC ĐỊNH - KHÔNG HỀ BẬT CAMERA) ----
        if scan_mode == "file":
            st.markdown("""
            <div style="font-size: 13.5px; color: #475569; margin: 8px 0 12px 0;">
                📁 <b>Tải tệp ảnh bài thi:</b> Hỗ trợ ảnh JPG, PNG, WebP từ máy tính hoặc điện thoại.<br>
                📱 <b>Dành cho điện thoại:</b> Khi bấm nút chọn tệp bên dưới, bạn có thể <b>mở trực tiếp ứng dụng Máy ảnh</b> của điện thoại để chụp ảnh bài thi cực kỳ sắc nét mà không lo bị trình duyệt hỏi quyền webcam!
            </div>
            """, unsafe_allow_html=True)

            uploaded_files = st.file_uploader(
                "Kéo thả hoặc chọn các ảnh bài thi cần chấm (JPG, PNG, WebP):",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key="batch_file_uploader"
            )

            if uploaded_files and bo_da_dung:
                if st.button("🚀 BẮT ĐẦU CHẤM TẤT CẢ BÀI THI", type="primary", key="btn_run_batch"):
                    prog_bar = st.progress(0.0)
                    status_text = st.empty()
                    rows = []
                    graded_images = []

                    for idx, file in enumerate(uploaded_files):
                        status_text.text(f"Đang chấm bài {idx + 1}/{len(uploaded_files)}: {file.name}...")
                        img = doc_anh(file.getvalue())

                        row, anh_cham = xu_ly_file_bggdt(
                            ten_file=file.name,
                            img=img,
                            bo_dap_an=bo_da_dung,
                            cau_hinh_diem=None,
                            danh_sach_hoc_sinh=roster_data
                        )
                        rows.append(row)
                        if anh_cham is not None:
                            graded_images.append((file.name, anh_cham, row))
                        prog_bar.progress((idx + 1) / len(uploaded_files))

                    status_text.empty()
                    st.session_state["results_df"] = pd.DataFrame(rows)
                    st.session_state["graded_images"] = graded_images
                    st.success(f"🎉 Hoàn tất chấm {len(uploaded_files)} bài thi!")
                    st.rerun()

        # ---- CHẾ ĐỘ 2: QUÉT TRỰC TIẾP BẰNG CAMERA (CHỈ BẬT KHI NGƯỜI DÙNG BẤM CHO PHÉP) ----
        else:
            if not st.session_state.get("cam_active", False):
                st.markdown("""
                <div style="background: #f8fafc; border: 1.5px dashed #94a3b8; border-radius: 16px; padding: 28px 20px; text-align: center; margin: 14px 0;">
                    <div style="font-size: 38px; margin-bottom: 8px;">🔒 📷</div>
                    <div style="font-size: 17px; font-weight: 800; color: #0f172a;">Máy Ảnh Hiện Đang Được Tắt Hoàn Toàn</div>
                    <div style="font-size: 13.5px; color: #64748b; margin-top: 6px; max-width: 520px; margin-left: auto; margin-right: auto; line-height: 1.5;">
                        Để đảm bảo quyền riêng tư và bảo mật tuyệt đối cho thiết bị của bạn, camera chỉ được kích hoạt khi bạn chủ động bấm nút bật bên dưới.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("📷 BẬT CAMERA ĐỂ BẮT ĐẦU CHỤP", type="primary", use_container_width=True, key="btn_turn_on_cam"):
                    st.session_state["cam_active"] = True
                    st.rerun()
            else:
                col_c_head, col_c_btn = st.columns([2.6, 1])
                with col_c_head:
                    st.markdown("""
                    <div style="font-size: 13.5px; color: #475569; margin: 4px 0 10px 0;">
                        🟢 <b>Máy ảnh đang bật:</b> Đưa phiếu thi vào trước ống kính (thấy rõ 4 ô vuông đen ở 4 góc). Bấm <b>Chụp ảnh</b>, hệ thống sẽ <b>tự động tải bài lên và chấm điểm ngay lập tức</b>!
                    </div>
                    """, unsafe_allow_html=True)
                with col_c_btn:
                    if st.button("🔴 TẮT MÁY ẢNH", type="secondary", use_container_width=True, key="btn_turn_off_cam"):
                        st.session_state["cam_active"] = False
                        st.rerun()

                cam_shot = st.camera_input("📸 Khung chụp Camera:", key="camera_shot_input")

                if cam_shot is not None:
                    shot_bytes = cam_shot.getvalue()
                    shot_hash = hashlib.md5(shot_bytes).hexdigest()

                    # TỰ ĐỘNG TẢI LÊN & CHẤM NGAY LẬP TỨC
                    if st.session_state.get("last_cam_shot_hash") != shot_hash:
                        try:
                            img_cam = doc_anh(shot_bytes)
                            c_row, c_anh = xu_ly_file_bggdt(
                                ten_file=f"Cam_Scan_{len(st.session_state.get('results_df', [])) + 1}.jpg",
                                img=img_cam,
                                bo_dap_an=bo_da_dung,
                                cau_hinh_diem=None,
                                danh_sach_hoc_sinh=roster_data
                            )

                            if c_anh is not None:
                                # Tự động tích lũy vào danh sách kết quả chung
                                if "results_df" not in st.session_state:
                                    st.session_state["results_df"] = pd.DataFrame([c_row])
                                else:
                                    st.session_state["results_df"] = pd.concat([st.session_state["results_df"], pd.DataFrame([c_row])], ignore_index=True)

                                if "graded_images" not in st.session_state:
                                    st.session_state["graded_images"] = []
                                st.session_state["graded_images"].append((c_row["Tên file"], c_anh, c_row))

                                st.session_state["last_cam_shot_hash"] = shot_hash
                                st.session_state["last_cam_graded"] = (c_row, c_anh)
                                st.toast(f"✅ Đã tự động lưu bài thi của SBD {c_row['SBD']} ({c_row['Tổng điểm']}đ)!", icon="🎉")
                            else:
                                st.session_state["last_cam_graded"] = None
                                st.error(f"⚠️ {c_row.get('Cảnh báo', c_row.get('Ghi chú'))}. Vui lòng căn chỉnh lại góc máy ảnh và chụp lại.")
                        except Exception as ex_cam:
                            st.session_state["last_cam_graded"] = None
                            st.error(f"⚠️ Lỗi quét camera: {ex_cam}. Vui lòng chụp rõ 4 góc định vị.")

                # Hiển thị kết quả bài vừa chụp ngay tại chỗ
                if st.session_state.get("last_cam_graded"):
                    last_row, last_img = st.session_state["last_cam_graded"]
                    st.success(f"🎉 ĐÃ TỰ ĐỘNG CHẤM & LƯU BÀI: Thí sinh **{last_row['Họ và tên']}** (SBD: **{last_row['SBD']}**, Lớp: **{last_row['Lớp']}**) — Điểm: **{last_row['Tổng điểm']}đ**")

                    c_preview1, c_preview2 = st.columns([1, 1.2])
                    with c_preview1:
                        st.markdown(f"""
                        <div style="background: white; border: 1.5px solid #cbd5e1; border-radius: 14px; padding: 16px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.04);">
                            <div style="font-size: 18px; font-weight: 800; color: #0f172a;">{last_row['Họ và tên']}</div>
                            <div style="font-size: 13px; color: #64748b;">SBD: <b>{last_row['SBD']}</b> | Lớp: <b>{last_row['Lớp']}</b> | Mã đề: <b>{last_row['Mã đề']}</b></div>
                            <div style="font-size: 28px; font-weight: 800; color: #16a34a; margin-top: 6px;">{last_row['Tổng điểm']} điểm</div>
                            <div style="font-size: 13px; margin-top: 4px;">• Phần I: <b>{last_row['Điểm Phần I']}đ</b> ({last_row['P1 Đúng']})</div>
                            <div style="font-size: 13px;">• Phần II: <b>{last_row['Điểm Phần II']}đ</b></div>
                            <div style="font-size: 13px;">• Phần III: <b>{last_row['Điểm Phần III']}đ</b> ({last_row['P3 Đúng']})</div>
                            <div style="margin-top: 8px;"><span class="badge-pill {'badge-success' if '✅' in last_row['Cảnh báo'] else 'badge-warning'}">{last_row['Cảnh báo']}</span></div>
                            <div style="font-size: 12.5px; color: #16a34a; font-weight: 700; margin-top: 10px;">✓ Đã tự động cập nhật vào Bảng Điểm Tổng Hợp bên dưới!</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c_preview2:
                        st.image(last_img, caption=f"Phiếu chấm trực quan (SBD: {last_row['SBD']})", use_container_width=True)

    # 3. BẢNG TỔNG HỢP KẾT QUẢ, THỐNG KÊ KPI & CẢNH BÁO BẤT THƯỜNG
    if "results_df" in st.session_state and not st.session_state["results_df"].empty:
        df_res = st.session_state["results_df"]
        diem_col = pd.to_numeric(df_res["Tổng điểm"], errors="coerce").dropna()

        # Đếm số cảnh báo & hợp lệ
        so_canh_bao = sum(1 for c in df_res.get("Cảnh báo", []) if "⚠️" in str(c))
        so_hop_le = len(df_res) - so_canh_bao

        # THỐNG KÊ KPI CARDS
        with st.container(border=True):
            st.markdown("""
            <div class="glass-header">
                <div class="glass-header-icon">📊</div>
                <div>
                    <div style="font-size: 19px; font-weight: 800; color: #0f172a;">Tổng Quan Kết Quả Đợt Thi</div>
                    <div style="font-size: 13px; color: #64748b;">Chỉ số thống kê học lực, cảnh báo bất thường và phân bố điểm số</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            kpi_1, kpi_2, kpi_3, kpi_4, kpi_5, kpi_6, kpi_7 = st.columns(7)
            with kpi_1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{len(df_res)}</div>
                    <div class="stat-label">Tổng Số Bài Thi</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_2:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #16a34a;">{so_hop_le}</div>
                    <div class="stat-label">Bài Hợp Lệ</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_3:
                st.markdown(f"""
                <div class="stat-card" style="{'border-color: #f59e0b;' if so_canh_bao > 0 else ''}">
                    <div class="stat-value" style="color: {'#d97706' if so_canh_bao > 0 else '#64748b'};">{so_canh_bao}</div>
                    <div class="stat-label">Cần Lưu Ý / Lỗi</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_4:
                avg_val = diem_col.mean() if len(diem_col) > 0 else 0.0
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #0284c7;">{avg_val:.2f}</div>
                    <div class="stat-label">Điểm Trung Bình</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_5:
                max_val = diem_col.max() if len(diem_col) > 0 else 0.0
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #16a34a;">{max_val:.2f}</div>
                    <div class="stat-label">Điểm Cao Nhất</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_6:
                so_dat = int((diem_col >= 5.0).sum()) if len(diem_col) > 0 else 0
                pct_dat = (so_dat / len(diem_col) * 100) if len(diem_col) > 0 else 0
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #0d9488;">{pct_dat:.1f}%</div>
                    <div class="stat-label">Tỉ Lệ Đạt (≥ 5.0)</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_7:
                so_gioi = int((diem_col >= 8.0).sum()) if len(diem_col) > 0 else 0
                pct_gioi = (so_gioi / len(diem_col) * 100) if len(diem_col) > 0 else 0
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #7c3aed;">{pct_gioi:.1f}%</div>
                    <div class="stat-label">Tỉ Lệ Giỏi (≥ 8.0)</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")

            # Nút Tải Excel và nút Xóa làm mới
            down_c1, down_c2 = st.columns([1.5, 1])

            # Chuẩn bị cột xuất dữ liệu
            cols_export_order = [
                "SBD", "Họ và tên", "Lớp", "Mã đề", "Tổng điểm",
                "Điểm Phần I", "Điểm Phần II", "Điểm Phần III",
                "P1 Đúng", "P3 Đúng", "Cảnh báo", "Tên file"
            ]
            df_export = df_res.copy()
            if "STT" not in df_export.columns:
                df_export.insert(0, "STT", range(1, len(df_export) + 1))

            cols_avail = ["STT"] + [c for c in cols_export_order if c in df_export.columns]

            with down_c1:
                buf = io.BytesIO()
                df_export[cols_avail].to_excel(buf, index=False, sheet_name="Bảng Điểm")
                st.download_button(
                    "⬇️ TẢI BẢNG ĐIỂM EXCEL ĐẦY ĐỦ (.XLSX)",
                    buf.getvalue(),
                    file_name="bang_diem_bggdt_2025.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

            with down_c2:
                if st.button("🗑️ Xóa kết quả & Chấm đợt mới", type="secondary", key="btn_reset_results"):
                    del st.session_state["results_df"]
                    if "graded_images" in st.session_state:
                        del st.session_state["graded_images"]
                    st.rerun()

            st.dataframe(df_export[cols_avail], hide_index=True, use_container_width=True)

            if len(diem_col) > 0:
                st.markdown("#### 📈 Phổ Điểm Bài Thi (Histogram)")
                hist_vals, bin_edges = np.histogram(diem_col, bins=10, range=(0, 10))
                labels = [f"[{bin_edges[i]:.0f} - {bin_edges[i+1]:.0f})" for i in range(len(hist_vals) - 1)] + [f"[{bin_edges[-2]:.0f} - {bin_edges[-1]:.0f}]"]
                chart_data = pd.DataFrame({"Số lượng thí sinh": hist_vals}, index=labels)
                st.bar_chart(chart_data)

        # 4. XEM TỪNG BÀI THI TRỰC QUAN (VISUAL SCORECARD VỚI BỘ LỌC CẢNH BÁO)
        graded_imgs = st.session_state.get("graded_images", [])
        if graded_imgs:
            with st.container(border=True):
                st.markdown("""
                <div class="glass-header">
                    <div class="glass-header-icon">🔍</div>
                    <div>
                        <div style="font-size: 19px; font-weight: 800; color: #0f172a;">Chi Tiết Từng Bài Thi & Khoanh Đáp Án</div>
                        <div style="font-size: 13px; color: #64748b;">Xem ma trận điểm từng phần thi, đối chiếu cảnh báo nghi vấn và ảnh phiếu chấm thực tế</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                fil_c1, fil_c2 = st.columns([1.2, 1.8])
                with fil_c1:
                    filter_opt = st.selectbox(
                        "Bộ lọc danh sách bài thi:",
                        options=[
                            "Tất cả bài thi",
                            "⚠️ Chỉ xem bài CÓ CẢNH BÁO (Cần rà soát)",
                            "✅ Chỉ xem bài HỢP LỆ (Không có lỗi)",
                            "Chỉ xem bài Giỏi (≥ 8.0)",
                            "Chỉ xem bài Đạt (≥ 5.0)",
                            "Chỉ xem bài Dưới TB (< 5.0)"
                        ],
                        key="filter_score_opt"
                    )
                with fil_c2:
                    search_txt = st.text_input("🔍 Tìm theo SBD, Họ tên, hoặc tên file:", placeholder="VD: 000001, Nguyễn Văn A...", key="txt_search_sbd")

                for fname, anh, row_data in graded_imgs:
                    details = row_data.get("_details", {}) or {}
                    score = row_data.get("Tổng điểm", 0)
                    score = float(score) if score is not None else 0.0
                    sbd_str = str(row_data.get("SBD", ""))
                    ten_str = str(row_data.get("Họ và tên", "Chưa rõ"))
                    lop_str = str(row_data.get("Lớp", "—"))
                    canh_bao_str = str(row_data.get("Cảnh báo", "✅ Hợp lệ"))
                    co_cb = "⚠️" in canh_bao_str

                    if filter_opt == "⚠️ Chỉ xem bài CÓ CẢNH BÁO (Cần rà soát)" and not co_cb:
                        continue
                    if filter_opt == "✅ Chỉ xem bài HỢP LỆ (Không có lỗi)" and co_cb:
                        continue
                    if filter_opt == "Chỉ xem bài Giỏi (≥ 8.0)" and score < 8.0:
                        continue
                    if filter_opt == "Chỉ xem bài Đạt (≥ 5.0)" and score < 5.0:
                        continue
                    if filter_opt == "Chỉ xem bài Dưới TB (< 5.0)" and score >= 5.0:
                        continue

                    if search_txt.strip():
                        q = search_txt.strip().lower()
                        if q not in sbd_str.lower() and q not in fname.lower() and q not in ten_str.lower():
                            continue

                    xep_loai = "Xuất sắc" if score >= 9.0 else ("Giỏi" if score >= 8.0 else ("Khá" if score >= 6.5 else ("Trung bình" if score >= 5.0 else "Yếu")))

                    header_badge = f"⚠️ {canh_bao_str}" if co_cb else f"{score:.2f}đ ({xep_loai})"
                    with st.expander(f"📄 Bài thi: {fname} — SBD: {sbd_str} | {ten_str} ({lop_str}) | Mã đề: {row_data.get('Mã đề', '-')} | {header_badge}", expanded=co_cb):
                        card_left, card_right = st.columns([1.1, 1.1])

                        with card_left:
                            # Banner thông báo cảnh báo nếu bài có vấn đề
                            if co_cb:
                                st.markdown(f"""
                                <div style="background: #fef3c7; border: 1.5px solid #fde68a; border-radius: 12px; padding: 12px 16px; margin-bottom: 12px; color: #b45309; font-size: 13.5px; font-weight: 700;">
                                    ⚠️ <b>CẢNH BÁO NGHI VẤN:</b> {canh_bao_str.replace('⚠️', '').strip()}
                                    <div style="font-size: 12px; font-weight: 500; color: #92400e; margin-top: 4px;">Giáo viên vui lòng đối chiếu ảnh phiếu chấm bên cạnh để xác minh!</div>
                                </div>
                                """, unsafe_allow_html=True)

                            st.markdown(f"""
                            <div style="background: rgba(248, 250, 252, 0.85); border: 1.5px solid rgba(226, 232, 240, 0.9); border-radius: 16px; padding: 18px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-size: 18px; font-weight: 800; color: #0f172a;">{ten_str}</div>
                                        <div style="font-size: 13px; color: #64748b;">SBD: <b>{sbd_str}</b> | Lớp: <b>{lop_str}</b> | Mã đề: <b>{row_data.get('Mã đề', '-')}</b></div>
                                        <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">Tệp: {fname}</div>
                                    </div>
                                    <div style="text-align: right;">
                                        <div style="font-size: 30px; font-weight: 800; color: {'#16a34a' if score >= 8 else ('#ea580c' if score >= 5 else '#dc2626')};">
                                            {score:.2f}đ
                                        </div>
                                        <span class="badge-pill {'badge-success' if score >= 8 else ('badge-warning' if score >= 5 else 'badge-danger')}">{xep_loai}</span>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            st.markdown("**Điểm thành phần:**")
                            p1_d = float(row_data.get("Điểm Phần I", 0) or 0.0)
                            p2_d = float(row_data.get("Điểm Phần II", 0) or 0.0)
                            p3_d = float(row_data.get("Điểm Phần III", 0) or 0.0)

                            # Tính toán max điểm an toàn theo từng phần
                            de_cfg = bo_da_dung.get(row_data.get("Mã đề"), {})
                            p1_len = len(de_cfg.get("phan1", {})) or int(details.get("p1_tong", 12))
                            p2_len = len(de_cfg.get("phan2", {}))
                            p3_len = len(de_cfg.get("phan3", {})) or int(details.get("p3_tong", 6))

                            max_p1 = max(float(p1_len) * float(de_cfg.get("diem_moi_cau_p1", 0.25)), 0.1)
                            max_p2 = max(float(p2_len) * 1.0, 0.1)
                            max_p3 = max(float(p3_len) * float(de_cfg.get("diem_moi_cau_p3", 0.50)), 0.1)

                            if p1_len > 0:
                                st.write(f"• **Phần I (Trắc nghiệm):** {p1_d:.2f} đ ({row_data.get('P1 Đúng', '')}) / tối đa {max_p1:.2f}đ")
                                st.progress(min(max(p1_d / max_p1, 0.0), 1.0))

                            if p2_len > 0:
                                st.write(f"• **Phần II (Đúng/Sai):** {p2_d:.2f} đ / tối đa {max_p2:.2f}đ")
                                st.progress(min(max(p2_d / max_p2, 0.0), 1.0))

                            if p3_len > 0:
                                st.write(f"• **Phần III (Trả lời ngắn):** {p3_d:.2f} đ ({row_data.get('P3 Đúng', '')}) / tối đa {max_p3:.2f}đ")
                                st.progress(min(max(p3_d / max_p3, 0.0), 1.0))

                            # Chi tiết Phần I
                            if details and "p1_chi_tiet" in details and details["p1_chi_tiet"]:
                                st.write("")
                                st.markdown("🎯 **Chi tiết Phần I (Trắc nghiệm):**")
                                chips_p1 = ""
                                p1_answers = details.get("p1_chi_tiet", {})
                                active_key_de = de_cfg.get("phan1", {})
                                for q_n in sorted(p1_answers.keys(), key=lambda x: int(x)):
                                    hs_ans = p1_answers[q_n]
                                    corr_ans = active_key_de.get(str(q_n), "")
                                    if hs_ans == corr_ans:
                                        chips_p1 += f'<span class="chip chip-ok">Câu {q_n}: {hs_ans} ✓</span>'
                                    elif len(hs_ans) > 1 and hs_ans != "-":
                                        chips_p1 += f'<span class="chip chip-warn">Câu {q_n}: Tô đúp {hs_ans} (ĐA: {corr_ans})</span>'
                                    elif hs_ans in ("-", ""):
                                        chips_p1 += f'<span class="chip chip-wrong">Câu {q_n}: Bỏ trống (ĐA: {corr_ans})</span>'
                                    else:
                                        chips_p1 += f'<span class="chip chip-wrong">Câu {q_n}: {hs_ans} (ĐA: {corr_ans})</span>'
                                st.markdown(chips_p1, unsafe_allow_html=True)

                            # Chi tiết Phần II
                            if details and "p2_chi_tiet" in details and details["p2_chi_tiet"]:
                                st.write("")
                                st.markdown("⚖️ **Chi tiết Phần II (Đúng/Sai - Barem Bộ GD&ĐT):**")
                                chips_p2 = ""
                                p2_info = details.get("p2_chi_tiet", {})
                                for q_n in sorted(p2_info.keys(), key=lambda x: int(x)):
                                    item = p2_info[q_n]
                                    if isinstance(item, dict):
                                        so_y = item.get("so_y", 0)
                                        diem_c = item.get("diem", 0.0)
                                        c_class = "chip-ok" if so_y == 4 else ("chip-warn" if so_y > 0 else "chip-wrong")
                                        subs_html = ""
                                        for sub, sub_st in item.get("subs", {}).items():
                                            s_ok = sub_st.get("dung", False)
                                            hs_display = str(sub_st.get("hs", "-")).replace("D", "Đ")
                                            subs_html += f'<span class="sub-item {"sub-item-ok" if s_ok else "sub-item-fail"}">{sub}:{hs_display}{"✓" if s_ok else "✗"}</span>'
                                        chips_p2 += f'<span class="chip {c_class}">Câu {q_n}: {so_y}/4 ({diem_c:.2f}đ) {subs_html}</span>'
                                    else:
                                        chips_p2 += f'<span class="chip chip-ok">Câu {q_n}: {item}</span>'
                                st.markdown(chips_p2, unsafe_allow_html=True)

                            # Chi tiết Phần III
                            if details and "p3_chi_tiet" in details and details["p3_chi_tiet"]:
                                st.write("")
                                st.markdown("🔢 **Chi tiết Phần III (Trả lời ngắn):**")
                                chips_p3 = ""
                                p3_info = details.get("p3_chi_tiet", {})
                                for q_n in sorted(p3_info.keys(), key=lambda x: int(x)):
                                    item = p3_info[q_n]
                                    if isinstance(item, dict):
                                        is_dung = item.get("dung", False)
                                        hs_v = item.get("hs", "-")
                                        da_v = item.get("da", "")
                                        if is_dung:
                                            chips_p3 += f'<span class="chip chip-ok">Câu {q_n}: {hs_v} ✓</span>'
                                        elif hs_v in ("-", ""):
                                            chips_p3 += f'<span class="chip chip-wrong">Câu {q_n}: Bỏ trống (ĐA: {da_v})</span>'
                                        else:
                                            chips_p3 += f'<span class="chip chip-wrong">Câu {q_n}: {hs_v} (ĐA: {da_v})</span>'
                                    else:
                                        chips_p3 += f'<span class="chip chip-ok">Câu {q_n}: {item}</span>'
                                st.markdown(chips_p3, unsafe_allow_html=True)

                        with card_right:
                            st.image(anh, caption=f"Phiếu chấm trực quan: {fname} (Khoanh xanh: Đúng | Khoanh đỏ: Sai | Dưới P.III có in ĐA chuẩn)")


