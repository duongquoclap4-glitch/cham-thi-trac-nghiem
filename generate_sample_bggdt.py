"""Trình tạo ảnh bài thi mẫu dựa trên phiếu chuẩn Bộ GD&ĐT để kiểm thử."""

import json
import os
from typing import Any, Dict, Tuple

import cv2
import numpy as np

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template_bggdt.json")
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    TEMPLATE = json.load(f)

BASE_IMG_PATH = os.path.join(os.path.dirname(__file__), "phieu_chuan_bggdt_150dpi.png")


def to_o_tron(img: np.ndarray, x: float, y: float, r: float, rng=None, intensity: int = 35):
    """Mô phỏng tô chì 2B vào một ô tròn."""
    ix, iy, ir = int(round(x)), int(round(y)), max(int(round(r - 1)), 3)
    # Vẽ vòng tròn đặc màu đen/xám than chì
    cv2.circle(img, (ix, iy), ir, (intensity, intensity, intensity), -1)
    if rng is not None:
        # Thêm chút noise mô phỏng vết tô tay tự nhiên
        roi = img[iy - ir : iy + ir + 1, ix - ir : ix + ir + 1]
        noise = rng.integers(-15, 15, roi.shape, dtype=np.int16)
        roi[:] = np.clip(roi.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def tao_bai_thi_mau(
    sbd: str = "012345",
    made: str = "101",
    dap_an_p1: Dict[int, str] = None,
    dap_an_p2: Dict[int, Dict[str, str]] = None,
    dap_an_p3: Dict[int, str] = None,
    goc_nghieng: bool = True,
    seed: int = 42
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Tạo một ảnh bài thi đã tô và trả về (ảnh_chụp, đáp_án_thực_tế)."""
    rng = np.random.default_rng(seed)
    img = cv2.imread(BASE_IMG_PATH, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Không tìm thấy ảnh gốc {BASE_IMG_PATH}")

    # 1. Tô SBD (6 số)
    for col_idx, ch in enumerate(sbd[:6]):
        if ch.isdigit():
            coord = TEMPLATE["sbd"][str(col_idx)][ch]
            to_o_tron(img, *coord, rng)

    # 2. Tô Mã đề (3 số)
    for col_idx, ch in enumerate(made[:3]):
        if ch.isdigit():
            coord = TEMPLATE["made"][str(col_idx)][ch]
            to_o_tron(img, *coord, rng)

    # 3. Tô Phần I
    if dap_an_p1 is None:
        dap_an_p1 = {q: ["A", "B", "C", "D"][rng.integers(4)] for q in range(1, 13)}
    for q, opt in dap_an_p1.items():
        if opt in ("A", "B", "C", "D"):
            coord = TEMPLATE["phan1"][str(q)][opt]
            to_o_tron(img, *coord, rng)

    # 4. Tô Phần II
    if dap_an_p2 is None:
        dap_an_p2 = {
            q: {sub: ["D", "S"][rng.integers(2)] for sub in ["a", "b", "c", "d"]}
            for q in range(1, 5)
        }
    for q, subs in dap_an_p2.items():
        for sub, choice in subs.items():
            if choice in ("D", "S"):
                coord = TEMPLATE["phan2"][str(q)][sub][choice]
                to_o_tron(img, *coord, rng)

    # 5. Tô Phần III
    if dap_an_p3 is None:
        dap_an_p3 = {
            1: "12",
            2: "-3,5",
            3: "0,25",
            4: "2025",
            5: "-12",
            6: "100"
        }
    for q, val in dap_an_p3.items():
        # Phân tích chuỗi số val thành 4 cột
        val_clean = str(val).strip().replace(".", ",")
        q_cols = TEMPLATE["phan3"][str(q)]

        # Tìm vị trí các ký tự tương ứng
        chars = list(val_clean)
        # Điền từ trái sang hoặc từ phải sang tùy quy ước
        # Chuẩn thí sinh tô từ trái sang phải
        for col_idx, ch in enumerate(chars[:4]):
            c_data = q_cols[str(col_idx)]
            if ch in c_data:
                to_o_tron(img, *c_data[ch], rng)

    ground_truth = {
        "sbd": sbd,
        "made": made,
        "phan1": dap_an_p1,
        "phan2": dap_an_p2,
        "phan3": dap_an_p3
    }

    if not goc_nghieng:
        return img, ground_truth

    # Giả lập chụp nghiêng bằng điện thoại đặt trên mặt bàn tối
    H, W = img.shape[:2]
    # Nền bàn gỗ / bàn tối kích thước 2100 x 1600
    nen = np.full((2100, 1600, 3), 140, dtype=np.uint8)
    # Thêm vân gỗ / noise nền
    nen = np.clip(nen.astype(np.int16) + rng.integers(-20, 20, nen.shape), 0, 255).astype(np.uint8)

    # Tọa độ 4 góc của tờ giấy trên nền bàn (nghiêng nhẹ)
    src_pts = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    dst_pts = np.float32([
        [160 + rng.integers(-20, 20), 120 + rng.integers(-15, 15)],
        [1420 + rng.integers(-20, 20), 170 + rng.integers(-15, 15)],
        [1380 + rng.integers(-20, 20), 1960 + rng.integers(-15, 15)],
        [120 + rng.integers(-20, 20), 1910 + rng.integers(-15, 15)]
    ])

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(img, M, (1600, 2100), borderMode=cv2.BORDER_TRANSPARENT)

    # Dán tờ giấy lên nền
    mask = cv2.warpPerspective(np.full((H, W), 255, dtype=np.uint8), M, (1600, 2100))
    nen[mask > 128] = warped[mask > 128]

    # Giả lập nén ảnh JPEG và ánh sáng
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
    _, enc = cv2.imencode(".jpg", nen, encode_param)
    final_img = cv2.imdecode(enc, cv2.IMREAD_COLOR)

    return final_img, ground_truth
