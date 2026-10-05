"""Ứng dụng Web Chấm Thi Trắc Nghiệm - Phiếu Chuẩn Bộ GD&ĐT 2025.
Giao diện Liquid Glass chuẩn (VisionOS / Frosted Glass) với tab bo tròn 14px, chuyển động nảy lò xo sinh động.
"""

import importlib
import io
import json
import os
import re

import cv2
import numpy as np
import pandas as pd
import streamlit as st

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

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* 1. NỀN SÁNG TRẮNG TINH TẾ & HIỆN ĐẠI */
    .stApp, [data-testid="stAppViewContainer"], .main {
        background: #f8fafc !important;
        background-color: #f8fafc !important;
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

# Initialize session state for answer keys
if "active_keys" not in st.session_state:
    if os.path.exists(SAMPLE_KEY_PATH):
        with open(SAMPLE_KEY_PATH, "r", encoding="utf-8") as f:
            st.session_state["active_keys"] = json.load(f)
    else:
        st.session_state["active_keys"] = {
            "101": {
                "phan1": {str(i): "A" for i in range(1, 13)},
                "phan2": {str(i): {"a": "D", "b": "S", "c": "D", "d": "S"} for i in range(1, 5)},
                "phan3": {"1": "12", "2": "-3.5", "3": "0.25", "4": "2025", "5": "-12", "6": "100"}
            }
        }

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
                    with open(SAMPLE_KEY_PATH, "w", encoding="utf-8") as f:
                        json.dump(keys, f, ensure_ascii=False, indent=2)
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
                        with open(SAMPLE_KEY_PATH, "w", encoding="utf-8") as f:
                            json.dump(keys, f, ensure_ascii=False, indent=2)
                        st.success(f"✅ Đã thêm mã đề **{s_ma}** thành công!")
                        st.rerun()

    # SECTION 2: SOẠN ĐÁP ÁN CHI TIẾT
    with st.container(border=True):
        st.markdown(f"""
        <div class="glass-header">
            <div class="glass-header-icon">✍️</div>
            <div>
                <div style="font-size: 19px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px;">
                    2. Soạn Đáp Án Chi Tiết Cho Mã Đề: 
                    <span class="code-badge">{chon_made}</span>
                </div>
                <div style="font-size: 13px; color: #64748b; font-weight: 500;">Tùy chỉnh số câu hỏi và đáp án chuẩn cho từng phần thi (Phần I, II, III hoặc quét từ phiếu giáo viên)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        data_de = keys.get(chon_made, {"phan1": {}, "phan2": {}, "phan3": {}})
        curr_p1 = data_de.get("phan1", {})
        curr_p2 = data_de.get("phan2", {})
        curr_p3 = data_de.get("phan3", {})

        p_tabs = st.tabs([
            "1️⃣ Phần I: Trắc Nghiệm 4 Lựa Chọn (A-B-C-D)",
            "2️⃣ Phần II: Trắc Nghiệm Đúng / Sai",
            "3️⃣ Phần III: Trả Lời Ngắn (Số / Thập phân)",
            "📸 Quét Phiếu Đáp Án Giáo Viên"
        ])

        # ---- SUBTAB PHẦN I ----
        with p_tabs[0]:
            with st.container(border=True):
                c_p1_num, c_p1_quick = st.columns([1, 2])
                with c_p1_num:
                    so_cau_p1 = st.number_input(
                        "Số câu hỏi Phần I:",
                        min_value=1,
                        max_value=40,
                        value=len(curr_p1) if len(curr_p1) > 0 else 12,
                        step=1,
                        key=f"num_p1_{chon_made}"
                    )
                with c_p1_quick:
                    def_str = "".join([curr_p1.get(str(i), "A") for i in range(1, so_cau_p1 + 1)])
                    quick_str = st.text_input(
                        "⚡ Nhập nhanh chuỗi đáp án (gõ liền, ví dụ: ABCDABCDABCD):",
                        value=def_str,
                        key=f"quick_str_{chon_made}"
                    )

            clean_chars = re.sub(r"[^ABCDabcd]", "", quick_str).upper()

            st.write("Bảng chọn đáp án từng câu:")
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

        # ---- SUBTAB PHẦN II (ĐÚNG NHƯ ẢNH BẠN THÍCH) ----
        with p_tabs[1]:
            so_cau_p2 = st.number_input(
                "Số câu hỏi Phần II (mỗi câu gồm 4 ý a, b, c, d):",
                min_value=1,
                max_value=8,
                value=len(curr_p2) if len(curr_p2) > 0 else 4,
                step=1,
                key=f"num_p2_{chon_made}"
            )

            p2_cards = st.columns(min(so_cau_p2, 4))
            for q_i in range(1, so_cau_p2 + 1):
                col_target = p2_cards[(q_i - 1) % len(p2_cards)]
                with col_target:
                    with st.container(border=True):
                        st.markdown(f"**Câu {q_i}:**")
                        sub_dict = curr_p2.get(str(q_i), {"a": "D", "b": "S", "c": "D", "d": "S"})
                        updated_sub = {}
                        for s in ["a", "b", "c", "d"]:
                            cur_s = sub_dict.get(s, "D")
                            c_choice = st.radio(
                                f"Ý {s}):",
                                options=["Đúng (D)", "Sai (S)"],
                                index=0 if cur_s == "D" else 1,
                                key=f"p2_r_{chon_made}_{q_i}_{s}",
                                horizontal=True
                            )
                            updated_sub[s] = "D" if "Đúng" in c_choice else "S"
                        curr_p2[str(q_i)] = updated_sub

            data_de["phan2"] = {str(i): curr_p2[str(i)] for i in range(1, so_cau_p2 + 1)}

        # ---- SUBTAB PHẦN III ----
        with p_tabs[2]:
            st.markdown("**Soạn đáp án Phần III (Điền số thực, số âm, số thập phân):**")
            st.caption("Ví dụ: `12`, `-3.5`, `0.25`, `2025`, `-12`, `100`")

            p3_cards = st.columns(3)
            for q_i in range(1, 7):
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

            data_de["phan3"] = curr_p3

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
                        keys[chon_made] = data_gv
                        st.session_state["active_keys"] = keys
                        with open(SAMPLE_KEY_PATH, "w", encoding="utf-8") as f:
                            json.dump(keys, f, ensure_ascii=False, indent=2)
                        st.success("Đã cập nhật đáp án từ phiếu ảnh thành công!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

        # NÚT LƯU CHÍNH
        st.markdown("---")
        save_c1, save_c2 = st.columns([1, 2])
        with save_c1:
            if st.button(f"💾 LƯU ĐÁP ÁN MÃ ĐỀ {chon_made}", type="primary"):
                keys[chon_made] = data_de
                st.session_state["active_keys"] = keys
                with open(SAMPLE_KEY_PATH, "w", encoding="utf-8") as f:
                    json.dump(keys, f, ensure_ascii=False, indent=2)
                st.success(f"🎉 Đã lưu đáp án Mã đề **{chon_made}** vào hệ thống!")
        with save_c2:
            st.info(f"📌 Đang cấu hình: **{len(data_de['phan1'])} câu Phần I** | **{len(data_de['phan2'])} câu Phần II** | **{len(data_de['phan3'])} câu Phần III** cho mã đề **{chon_made}**.")

# ==========================================
# TAB 3: CHẤM THI & BÁO CÁO CHI TIẾT
# ==========================================
with tabs[2]:
    with st.container(border=True):
        st.markdown("""
        <div class="glass-header">
            <div class="glass-header-icon">📤</div>
            <div>
                <div style="font-size: 19px; font-weight: 800; color: #0f172a;">Tải Ảnh Bài Thi Học Sinh & Chấm Tự Động</div>
                <div style="font-size: 13px; color: #64748b;">Hỗ trợ ảnh chụp camera điện thoại (nghiêng, ngược sáng, xoay 180°), JPG, PNG</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Kéo thả hoặc chọn các ảnh bài thi cần chấm:",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True
        )

        bo_da_dung = st.session_state.get("active_keys", {})

        if uploaded_files and bo_da_dung:
            if st.button("🚀 BẮT ĐẦU CHẤM TẤT CẢ BÀI THI", type="primary"):
                prog_bar = st.progress(0.0)
                rows = []
                graded_images = []

                for idx, file in enumerate(uploaded_files):
                    img = doc_anh(file.getvalue())
                    row, anh_cham = xu_ly_file_bggdt(file.name, img, bo_da_dung)
                    rows.append(row)
                    if anh_cham is not None:
                        graded_images.append((file.name, anh_cham, row))
                    prog_bar.progress((idx + 1) / len(uploaded_files))

                st.session_state["results_df"] = pd.DataFrame(rows)
                st.session_state["graded_images"] = graded_images
                st.success(f"🎉 Hoàn tất chấm {len(uploaded_files)} bài thi!")

    if "results_df" in st.session_state:
        df_res = st.session_state["results_df"]
        diem_col = df_res["Tổng điểm"].dropna()

        # THỐNG KÊ KPI CARDS
        with st.container(border=True):
            st.markdown("""
            <div class="glass-header">
                <div class="glass-header-icon">📊</div>
                <div>
                    <div style="font-size: 19px; font-weight: 800; color: #0f172a;">Tổng Quan Kết Quả Đợt Thi</div>
                    <div style="font-size: 13px; color: #64748b;">Chỉ số thống kê học lực và phân bố điểm số</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            kpi_1, kpi_2, kpi_3, kpi_4, kpi_5, kpi_6 = st.columns(6)
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
                    <div class="stat-value" style="color: #0284c7;">{diem_col.mean():.2f}</div>
                    <div class="stat-label">Điểm Trung Bình</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_3:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #16a34a;">{diem_col.max():.2f}</div>
                    <div class="stat-label">Điểm Cao Nhất</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_4:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #ea580c;">{diem_col.min():.2f}</div>
                    <div class="stat-label">Điểm Thấp Nhất</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_5:
                so_dat = int((diem_col >= 5.0).sum())
                pct_dat = (so_dat / len(diem_col) * 100) if len(diem_col) > 0 else 0
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #0d9488;">{pct_dat:.1f}%</div>
                    <div class="stat-label">Tỉ Lệ Đạt (≥ 5.0)</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi_6:
                so_gioi = int((diem_col >= 8.0).sum())
                pct_gioi = (so_gioi / len(diem_col) * 100) if len(diem_col) > 0 else 0
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #7c3aed;">{pct_gioi:.1f}%</div>
                    <div class="stat-label">Tỉ Lệ Giỏi (≥ 8.0)</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            buf = io.BytesIO()
            cols_export = [c for c in df_res.columns if c != "_details"]
            df_res[cols_export].to_excel(buf, index=False, sheet_name="Bảng Điểm")
            st.download_button(
                "⬇️ TẢI BẢNG ĐIỂM EXCEL ĐẦY ĐỦ (.XLSX)",
                buf.getvalue(),
                file_name="bang_diem_bggdt_2025.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

            st.dataframe(df_res[cols_export], hide_index=True)

            if len(diem_col) > 0:
                st.markdown("#### 📈 Phổ Điểm Bài Thi (Histogram)")
                hist_vals, bin_edges = np.histogram(diem_col, bins=10, range=(0, 10))
                labels = [f"[{bin_edges[i]:.0f} - {bin_edges[i+1]:.0f})" for i in range(len(hist_vals) - 1)] + [f"[{bin_edges[-2]:.0f} - {bin_edges[-1]:.0f}]"]
                chart_data = pd.DataFrame({"Số lượng thí sinh": hist_vals}, index=labels)
                st.bar_chart(chart_data)

        # XEM TỪNG BÀI THI TRỰC QUAN (VISUAL SCORECARD)
        graded_imgs = st.session_state.get("graded_images", [])
        if graded_imgs:
            with st.container(border=True):
                st.markdown("""
                <div class="glass-header">
                    <div class="glass-header-icon">🔍</div>
                    <div>
                        <div style="font-size: 19px; font-weight: 800; color: #0f172a;">Chi Tiết Từng Bài Thi & Khoanh Đáp Án</div>
                        <div style="font-size: 13px; color: #64748b;">Xem ma trận điểm từng phần thi và ảnh phiếu chấm thực tế</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                fil_c1, fil_c2 = st.columns([1, 2])
                with fil_c1:
                    filter_opt = st.selectbox(
                        "Bộ lọc kết quả:",
                        options=["Tất cả bài thi", "Chỉ xem bài Giỏi (≥ 8.0)", "Chỉ xem bài Đạt (≥ 5.0)", "Chỉ xem bài Dưới TB (< 5.0)"],
                        key="filter_score_opt"
                    )
                with fil_c2:
                    search_txt = st.text_input("🔍 Tìm theo SBD hoặc tên file:", placeholder="VD: 000001...", key="txt_search_sbd")

                for fname, anh, row_data in graded_imgs:
                    details = row_data.get("_details", {})
                    score = row_data.get("Tổng điểm", 0) or 0.0
                    sbd_str = str(row_data.get("SBD", ""))

                    if filter_opt == "Chỉ xem bài Giỏi (≥ 8.0)" and score < 8.0:
                        continue
                    if filter_opt == "Chỉ xem bài Đạt (≥ 5.0)" and score < 5.0:
                        continue
                    if filter_opt == "Chỉ xem bài Dưới TB (< 5.0)" and score >= 5.0:
                        continue
                    if search_txt.strip():
                        q = search_txt.strip().lower()
                        if q not in sbd_str.lower() and q not in fname.lower():
                            continue

                    xep_loai = "Xuất sắc" if score >= 9.0 else ("Giỏi" if score >= 8.0 else ("Khá" if score >= 6.5 else ("Trung bình" if score >= 5.0 else "Yếu")))

                    with st.expander(f"📄 Bài thi: {fname} — SBD: {sbd_str} | Mã đề: {row_data.get('Mã đề', '-')} | Điểm: {score:.2f} ({xep_loai})", expanded=True):
                        card_left, card_right = st.columns([1.1, 1.1])

                        with card_left:
                            st.markdown(f"""
                            <div style="background: rgba(248, 250, 252, 0.85); border: 1.5px solid rgba(226, 232, 240, 0.9); border-radius: 16px; padding: 18px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-size: 20px; font-weight: 800; color: #0f172a;">SBD: {sbd_str}</div>
                                        <div style="font-size: 13.5px; color: #64748b;">Mã đề: <b>{row_data.get('Mã đề', '-')}</b> | Tệp: {fname}</div>
                                    </div>
                                    <div style="text-align: right;">
                                        <div style="font-size: 32px; font-weight: 800; color: {'#16a34a' if score >= 8 else ('#ea580c' if score >= 5 else '#dc2626')};">
                                            {score:.2f}đ
                                        </div>
                                        <span class="badge-pill {'badge-success' if score >= 8 else ('badge-warning' if score >= 5 else 'badge-danger')}">{xep_loai}</span>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            st.markdown("**Điểm thành phần 3 phần thi:**")
                            p1_d = row_data.get("Điểm Phần I", 0) or 0.0
                            p2_d = row_data.get("Điểm Phần II", 0) or 0.0
                            p3_d = row_data.get("Điểm Phần III", 0) or 0.0

                            st.write(f"• **Phần I (Trắc nghiệm):** {p1_d:.2f} đ ({row_data.get('P1 Đúng', '')})")
                            st.progress(min(p1_d / 3.0, 1.0) if p1_d else 0.0)

                            st.write(f"• **Phần II (Đúng/Sai):** {p2_d:.2f} đ")
                            st.progress(min(p2_d / 4.0, 1.0) if p2_d else 0.0)

                            st.write(f"• **Phần III (Trả lời ngắn):** {p3_d:.2f} đ ({row_data.get('P3 Đúng', '')})")
                            st.progress(min(p3_d / 3.0, 1.0) if p3_d else 0.0)

                            if details and "p1_chi_tiet" in details:
                                st.write("")
                                st.markdown("🎯 **Chi tiết Phần I (Trắc nghiệm):**")
                                chips_p1 = ""
                                p1_answers = details.get("p1_chi_tiet", {})
                                active_key_de = bo_da_dung.get(row_data.get("Mã đề"), {}).get("phan1", {})
                                for q_n in sorted(p1_answers.keys(), key=lambda x: int(x)):
                                    hs_ans = p1_answers[q_n]
                                    corr_ans = active_key_de.get(str(q_n), "")
                                    if hs_ans == corr_ans:
                                        chips_p1 += f'<span class="chip chip-ok">Câu {q_n}: {hs_ans} ✓</span>'
                                    else:
                                        chips_p1 += f'<span class="chip chip-wrong">Câu {q_n}: {hs_ans} (ĐA: {corr_ans})</span>'
                                st.markdown(chips_p1, unsafe_allow_html=True)

                            if details and "p2_chi_tiet" in details:
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
                                            subs_html += f'<span class="sub-item {"sub-item-ok" if s_ok else "sub-item-fail"}">{sub}:{sub_st.get("hs")}{"✓" if s_ok else "✗"}</span>'
                                        chips_p2 += f'<span class="chip {c_class}">Câu {q_n}: {so_y}/4 ({diem_c:.2f}đ) {subs_html}</span>'
                                    else:
                                        chips_p2 += f'<span class="chip chip-ok">Câu {q_n}: {item}</span>'
                                st.markdown(chips_p2, unsafe_allow_html=True)

                            if details and "p3_chi_tiet" in details:
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
                                        else:
                                            chips_p3 += f'<span class="chip chip-wrong">Câu {q_n}: {hs_v} (ĐA: {da_v})</span>'
                                    else:
                                        chips_p3 += f'<span class="chip chip-ok">Câu {q_n}: {item}</span>'
                                st.markdown(chips_p3, unsafe_allow_html=True)

                        with card_right:
                            st.image(anh, caption=f"Phiếu chấm trực quan: {fname} (Khoanh xanh: Đúng | Khoanh đỏ: Sai | Dưới P.III có in ĐA chuẩn)")


