"""Engine chấm phiếu trả lời trắc nghiệm theo mẫu chuẩn Bộ GD&ĐT (Áp dụng từ năm 2025).

Hỗ trợ:
- Khổ giấy A4 chuẩn Bộ GD&ĐT
- Tự động nhận diện 4 góc định vị & nắn phẳng ảnh
- Tự động phát hiện và sửa ảnh bị ngược 180 độ
- Đọc Số báo danh (6 số) và Mã đề thi (3 số)
- Chấm Phần I: Trắc nghiệm 4 lựa chọn (tối đa 40 câu)
- Chấm Phần II: Trắc nghiệm Đúng/Sai (tối đa 8 câu) theo barem chuẩn Bộ GD&ĐT:
    * Đúng 1 ý: 0.10 điểm
    * Đúng 2 ý: 0.25 điểm
    * Đúng 3 ý: 0.50 điểm
    * Đúng 4 ý: 1.00 điểm
- Chấm Phần III: Trắc nghiệm Trả lời ngắn (tối đa 6 câu: số âm, dấu phẩy, chữ số)
- Trực quan hóa kết quả chấm và xuất Excel chi tiết
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Load template coordinates
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template_bggdt.json")
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    TEMPLATE = json.load(f)

SHEET_W = TEMPLATE["width"]   # 1240
SHEET_H = TEMPLATE["height"]  # 1753
DST_CORNERS = np.float32(TEMPLATE["markers_dst"])  # tl, tr, br, bl

FONT = cv2.FONT_HERSHEY_SIMPLEX
NGUONG_TO = 0.40  # Tỉ lệ diện tích bị tô để tính là đã chọn


def doc_anh(path_or_bytes) -> np.ndarray:
    """Đọc ảnh từ đường dẫn (hỗ trợ Unicode tiếng Việt) hoặc từ bytes."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        img = cv2.imdecode(np.frombuffer(path_or_bytes, np.uint8), cv2.IMREAD_COLOR)
    else:
        img = cv2.imdecode(np.fromfile(str(path_or_bytes), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Không thể đọc được ảnh từ nguồn cung cấp.")
    return img


def ghi_anh(path: str, img: np.ndarray) -> None:
    """Ghi ảnh ra file hỗ trợ đường dẫn tiếng Việt."""
    ext = os.path.splitext(path)[1] or ".png"
    cv2.imencode(ext, img)[1].tofile(path)


def tim_4_goc_phieu(gray: np.ndarray) -> np.ndarray:
    """Tìm 4 ô vuông đen ở 4 góc của phiếu để nắn phẳng (Perspective Transform)."""
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    # Dùng Otsu kết hợp adaptive threshold để thích ứng với mọi điều kiện ánh sáng
    th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # RETR_LIST để tìm cả các ô vuông nằm trong nền tối / lồng bên trong
    cnts, _ = cv2.findContours(th, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    total_area = gray.shape[0] * gray.shape[1]
    candidates = []

    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        box_area = w * h
        if box_area == 0:
            continue

        # Marker vuông góc ở 150 DPI có kích thước khoảng 25x25 đến 55x55 (khoảng 0.02% đến 0.4% diện tích ảnh)
        if not (total_area * 0.0001 < box_area < total_area * 0.008):
            continue

        aspect = w / float(h)
        if not (0.70 <= aspect <= 1.40):
            continue

        solidity = area / float(box_area)
        if solidity < 0.80:
            continue

        # Kiểm tra độ đậm bên trong ô vuông
        roi = th[y : y + h, x : x + w]
        if roi.size == 0 or cv2.countNonZero(roi) / float(roi.size) < 0.75:
            continue

        candidates.append((area, x + w / 2.0, y + h / 2.0))

    if len(candidates) < 4:
        raise RuntimeError(
            f"Không tìm thấy đủ 4 ô vuông định vị (chỉ tìm thấy {len(candidates)}). "
            "Vui lòng chụp đủ sáng, rõ nét và thấy trọn 4 góc phiếu."
        )

    # Lấy 4 điểm ở xa nhất tạo thành 4 góc của trang
    pts = np.float32([[x, y] for _, x, y in candidates])

    # 4 góc:
    # Top-Left: x + y nhỏ nhất
    # Top-Right: x - y lớn nhất
    # Bottom-Right: x + y lớn nhất
    # Bottom-Left: y - x lớn nhất (hoặc x - y nhỏ nhất)
    s = pts[:, 0] + pts[:, 1]
    d = pts[:, 0] - pts[:, 1]

    tl = pts[s.argmin()]
    tr = pts[d.argmax()]
    br = pts[s.argmax()]
    bl = pts[d.argmin()]

    return np.float32([tl, tr, br, bl])


def kiem_tra_va_xoay_chuan(phang: np.ndarray) -> np.ndarray:
    """Phiếu Bộ GD&ĐT có 3 ô vuông đen ở trên (y~75) và chỉ 2 ô vuông ở dưới (y~1677).

    Nếu ảnh bị chụp ngược 180 độ, hàm này sẽ tự động phát hiện và xoay 180 độ lại cho chuẩn.
    """
    th = cv2.threshold(phang, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # Kiểm tra ô vuông thứ 3 ở góc trên (x~878, y~75)
    r_top = th[60:90, 865:895]
    fill_top = cv2.countNonZero(r_top) / float(r_top.size) if r_top.size > 0 else 0.0

    # Kiểm tra ô vuông đối xứng nếu bị xoay ngược ở dưới (x~360, y~1677)
    r_bot = th[1660:1690, 345:375]
    fill_bot = cv2.countNonZero(r_bot) / float(r_bot.size) if r_bot.size > 0 else 0.0

    if fill_top < 0.30 and fill_bot > 0.50:
        return cv2.rotate(phang, cv2.ROTATE_180)
    return phang


def do_ti_le_to(th: np.ndarray, x: float, y: float, r: float) -> float:
    """Đo tỉ lệ diện tích tô đen bên trong một ô tròn."""
    ix, iy, ir = int(round(x)), int(round(y)), max(int(round(r - 2)), 3)
    h, w = th.shape[:2]
    x0, x1 = max(0, ix - ir), min(w, ix + ir + 1)
    y0, y1 = max(0, iy - ir), min(h, iy + ir + 1)
    if x1 <= x0 or y1 <= y0:
        return 0.0

    roi = th[y0:y1, x0:x1]
    mask = np.zeros_like(roi)
    cv2.circle(mask, (ix - x0, iy - y0), ir, 255, -1)
    circ_area = cv2.countNonZero(mask)
    if circ_area == 0:
        return 0.0
    filled = cv2.countNonZero(cv2.bitwise_and(roi, mask))
    return float(filled) / float(circ_area)


def doc_phieu_bggdt(img: np.ndarray) -> Dict[str, Any]:
    """Đọc ảnh chụp phiếu thi và trích xuất dữ liệu: SBD, Mã đề, Phần I, Phần II, Phần III."""
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # 1. Nắn phẳng
    corners = tim_4_goc_phieu(gray)
    M = cv2.getPerspectiveTransform(corners, DST_CORNERS)
    phang = cv2.warpPerspective(gray, M, (SHEET_W, SHEET_H))

    # 2. Kiểm tra và tự sửa chiều nếu bị ngược 180 độ
    phang = kiem_tra_va_xoay_chuan(phang)

    # 3. Binarization
    blur_phang = cv2.GaussianBlur(phang, (3, 3), 0)
    th = cv2.threshold(blur_phang, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 4. Đọc SBD (6 số)
    sbd_digits = []
    for col_idx in range(6):
        col_data = TEMPLATE["sbd"][str(col_idx)]
        ratios = [do_ti_le_to(th, *col_data[str(d)]) for d in range(10)]
        max_idx = int(np.argmax(ratios))
        second_max = sorted(ratios)[-2]
        if ratios[max_idx] > NGUONG_TO or (ratios[max_idx] > 0.28 and ratios[max_idx] > second_max * 1.6):
            sbd_digits.append(str(max_idx))
        else:
            sbd_digits.append("?")
    sbd_str = "".join(sbd_digits)

    # 5. Đọc Mã đề thi (3 số)
    made_digits = []
    for col_idx in range(3):
        col_data = TEMPLATE["made"][str(col_idx)]
        ratios = [do_ti_le_to(th, *col_data[str(d)]) for d in range(10)]
        max_idx = int(np.argmax(ratios))
        second_max = sorted(ratios)[-2]
        if ratios[max_idx] > NGUONG_TO or (ratios[max_idx] > 0.28 and ratios[max_idx] > second_max * 1.6):
            made_digits.append(str(max_idx))
        else:
            made_digits.append("?")
    made_str = "".join(made_digits)

    # 6. Đọc Phần I (40 câu)
    phan1_ans = {}
    for q in range(1, 41):
        q_data = TEMPLATE["phan1"][str(q)]
        opts = ["A", "B", "C", "D"]
        ratios = [do_ti_le_to(th, *q_data[opt]) for opt in opts]
        chosen = [opts[i] for i, r in enumerate(ratios) if r > NGUONG_TO]
        if len(chosen) == 1:
            phan1_ans[q] = chosen[0]
        elif len(chosen) > 1:
            phan1_ans[q] = "".join(chosen)
        else:
            max_idx = int(np.argmax(ratios))
            second = sorted(ratios)[-2]
            if ratios[max_idx] > 0.28 and ratios[max_idx] > second * 1.8:
                phan1_ans[q] = opts[max_idx]
            else:
                phan1_ans[q] = "-"

    # 7. Đọc Phần II (8 câu x 4 ý a,b,c,d)
    phan2_ans = {}
    for q in range(1, 9):
        phan2_ans[q] = {}
        for sub in ["a", "b", "c", "d"]:
            data_sub = TEMPLATE["phan2"][str(q)][sub]
            r_d = do_ti_le_to(th, *data_sub["D"])
            r_s = do_ti_le_to(th, *data_sub["S"])
            if r_d > NGUONG_TO and r_s > NGUONG_TO:
                phan2_ans[q][sub] = "DS"
            elif r_d > NGUONG_TO or (r_d > 0.28 and r_d > r_s * 1.8):
                phan2_ans[q][sub] = "D"
            elif r_s > NGUONG_TO or (r_s > 0.28 and r_s > r_d * 1.8):
                phan2_ans[q][sub] = "S"
            else:
                phan2_ans[q][sub] = "-"

    # 8. Đọc Phần III (6 câu trả lời ngắn)
    phan3_ans = {}
    for q in range(1, 7):
        q_cols = TEMPLATE["phan3"][str(q)]
        chars = []
        for col_idx in range(4):
            c_data = q_cols[str(col_idx)]
            found_chars = []
            for char_key, coord in c_data.items():
                ratio = do_ti_le_to(th, *coord)
                if ratio > NGUONG_TO:
                    found_chars.append((ratio, char_key))
            if found_chars:
                found_chars.sort(key=lambda x: x[0], reverse=True)
                chars.append(found_chars[0][1])
            else:
                chars.append("")
        val_str = "".join(chars).strip()
        phan3_ans[q] = val_str if val_str else "-"

    return {
        "sbd": sbd_str,
        "made": made_str,
        "phan1": phan1_ans,
        "phan2": phan2_ans,
        "phan3": phan3_ans,
        "anh_phang": phang
    }


def tinh_diem_phan2_cau(dap_an_cau: Dict[str, str], chon_cau: Dict[str, str]) -> Tuple[int, float]:
    """Tính điểm 1 câu Phần II (Đúng/Sai) theo barem chuẩn Bộ GD&ĐT 2025:

    - Đúng 1 ý: 0.10 điểm
    - Đúng 2 ý: 0.25 điểm
    - Đúng 3 ý: 0.50 điểm
    - Đúng 4 ý: 1.00 điểm
    """
    so_y_dung = 0
    for sub in ["a", "b", "c", "d"]:
        if sub in dap_an_cau:
            da_val = str(dap_an_cau[sub]).replace("Đ", "D")
            hs_val = str(chon_cau.get(sub, "")).replace("Đ", "D")
            if hs_val == da_val and hs_val in ("D", "S"):
                so_y_dung += 1

    barem = {0: 0.0, 1: 0.10, 2: 0.25, 3: 0.50, 4: 1.00}
    return so_y_dung, barem.get(so_y_dung, 0.0)


def so_sanh_tra_loi_ngan(da_chuan: str, da_hs: str) -> bool:
    """So khớp đáp án Phần III (hỗ trợ dấu phẩy ',' hoặc dấu chấm '.', và giá trị số)."""
    s_chuan = da_chuan.strip().replace(" ", "").replace(".", ",")
    s_hs = da_hs.strip().replace(" ", "").replace(".", ",")
    if s_chuan == s_hs:
        return True
    try:
        f_chuan = float(s_chuan.replace(",", "."))
        f_hs = float(s_hs.replace(",", "."))
        return abs(f_chuan - f_hs) < 1e-4
    except ValueError:
        return False


def cham_bai_bggdt(
    kq: Dict[str, Any],
    dap_an_de: Dict[str, Any],
    cau_hinh_diem: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Chấm điểm toàn diện một bài thi theo barem Bộ GD&ĐT.

    kq: kết quả từ doc_phieu_bggdt()
    dap_an_de: chứa {"phan1": {...}, "phan2": {...}, "phan3": {...}}
    cau_hinh_diem: cấu hình trọng số điểm cho từng phần (mặc định theo chuẩn môn Toán 2025:
        Phần I: 0.25 đ/câu (12 câu = 3.0đ)
        Phần II: theo barem Bộ GD&ĐT (4 câu = 4.0đ)
        Phần III: 0.50 đ/câu (6 câu = 3.0đ)
        Tổng = 10.0đ
    """
    if cau_hinh_diem is None:
        cau_hinh_diem = {
            "diem_moi_cau_p1": 0.25,
            "diem_moi_cau_p3": 0.50
        }

    anh_out = cv2.cvtColor(kq["anh_phang"], cv2.COLOR_GRAY2BGR)
    ghi_chu = []

    # 1. Chấm Phần I
    da_p1 = dap_an_de.get("phan1", {})
    p1_dung = 0
    p1_tong = len(da_p1)
    p1_chi_tiet = {}

    for q, key_ans in da_p1.items():
        q_int = int(q)
        hs_ans = kq["phan1"].get(q_int, "-")
        is_correct = (hs_ans == key_ans)
        p1_chi_tiet[q_int] = hs_ans
        if is_correct:
            p1_dung += 1
            coord = TEMPLATE["phan1"][str(q_int)][key_ans]
            cv2.circle(anh_out, (int(round(coord[0])), int(round(coord[1]))), int(round(coord[2])) + 4, (0, 180, 0), 2)
        else:
            coord_correct = TEMPLATE["phan1"][str(q_int)][key_ans]
            cv2.circle(anh_out, (int(round(coord_correct[0])), int(round(coord_correct[1]))), int(round(coord_correct[2])) + 4, (0, 180, 0), 2)
            if hs_ans not in ("-", ""):
                for c in hs_ans:
                    if c in ("A", "B", "C", "D"):
                        coord_wrong = TEMPLATE["phan1"][str(q_int)][c]
                        cv2.circle(anh_out, (int(round(coord_wrong[0])), int(round(coord_wrong[1]))), int(round(coord_wrong[2])) + 4, (0, 0, 255), 2)

    diem_p1 = round(p1_dung * cau_hinh_diem.get("diem_moi_cau_p1", 0.25), 2)

    # 2. Chấm Phần II (Đúng / Sai)
    da_p2 = dap_an_de.get("phan2", {})
    diem_p2 = 0.0
    p2_tong_cau = len(da_p2)
    p2_chi_tiet = {}

    for q, key_subs in da_p2.items():
        q_int = int(q)
        hs_subs = kq["phan2"].get(q_int, {})
        so_y, diem_cau = tinh_diem_phan2_cau(key_subs, hs_subs)
        diem_p2 += diem_cau
        p2_chi_tiet[q_int] = {
            "so_y": so_y,
            "diem": diem_cau,
            "text": f"{so_y}/4 ({diem_cau:.2f}đ)",
            "subs": {
                sub: {
                    "hs": str(hs_subs.get(sub, "-")).replace("D", "Đ"),
                    "da": str(key_subs.get(sub, "-")).replace("D", "Đ"),
                    "dung": (str(hs_subs.get(sub, "-")).replace("Đ", "D") == str(key_subs.get(sub, "-")).replace("Đ", "D"))
                }
                for sub in ["a", "b", "c", "d"] if sub in key_subs
            }
        }

        for sub in ["a", "b", "c", "d"]:
            if sub in key_subs:
                correct_choice = str(key_subs[sub]).replace("Đ", "D")
                hs_choice = str(hs_subs.get(sub, "-")).replace("Đ", "D")

                c_correct = TEMPLATE["phan2"][str(q_int)][sub].get(correct_choice)
                if c_correct:
                    cv2.circle(anh_out, (int(round(c_correct[0])), int(round(c_correct[1]))), int(round(c_correct[2])) + 3, (0, 180, 0), 2)

                if hs_choice != correct_choice and hs_choice in ("D", "S", "DS"):
                    for ch in hs_choice:
                        if ch in ("D", "S"):
                            c_wrong = TEMPLATE["phan2"][str(q_int)][sub].get(ch)
                            if c_wrong:
                                cv2.circle(anh_out, (int(round(c_wrong[0])), int(round(c_wrong[1]))), int(round(c_wrong[2])) + 3, (0, 0, 255), 2)

    diem_p2 = round(diem_p2, 2)

    # 3. Chấm Phần III (Trả lời ngắn)
    da_p3 = dap_an_de.get("phan3", {})
    p3_dung = 0
    p3_tong = len(da_p3)
    p3_chi_tiet = {}

    blur_p3 = cv2.GaussianBlur(kq["anh_phang"], (3, 3), 0)
    th_cham = cv2.threshold(blur_p3, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    for q, key_val in da_p3.items():
        q_int = int(q)
        hs_val = kq["phan3"].get(q_int, "-")
        is_correct = so_sanh_tra_loi_ngan(key_val, hs_val)
        p3_chi_tiet[q_int] = {
            "hs": hs_val,
            "da": str(key_val).strip(),
            "dung": is_correct
        }
        if is_correct:
            p3_dung += 1

        q_cols = TEMPLATE["phan3"][str(q_int)]
        key_chars = list(str(key_val).strip().replace(".", ","))[:4]

        # Khoanh tròn các chấm tròn trong 4 cột của câu này
        for col_idx in range(4):
            col_key = str(col_idx)
            c_data = q_cols[col_key]
            expected_char = key_chars[col_idx] if col_idx < len(key_chars) else None

            # 1. Khoanh XANH LÁ cho ô đáp án đúng
            if expected_char is not None and expected_char in c_data:
                coord_corr = c_data[expected_char]
                cv2.circle(
                    anh_out,
                    (int(round(coord_corr[0])), int(round(coord_corr[1]))),
                    int(round(coord_corr[2])) + 3,
                    (0, 180, 0),
                    2
                )

            # 2. Kiểm tra các ô học sinh đã tô: nếu tô sai -> Khoanh ĐỎ
            for char_k, coord_bubble in c_data.items():
                ratio = do_ti_le_to(th_cham, *coord_bubble)
                if ratio > NGUONG_TO:
                    if char_k != expected_char:
                        # Học sinh tô sai ô này -> khoanh đỏ
                        cv2.circle(
                            anh_out,
                            (int(round(coord_bubble[0])), int(round(coord_bubble[1]))),
                            int(round(coord_bubble[2])) + 3,
                            (0, 0, 255),
                            2
                        )

        # 3. Hiển thị đáp án đúng ở bên dưới thay vì "OK" / "X"
        x_center = (q_cols["0"]["0"][0] + q_cols["3"]["0"][0]) / 2.0
        val_display = str(key_val).strip().replace(".", ",")
        text_label = f"DA: {val_display}"
        color_label = (0, 180, 0) if is_correct else (0, 0, 255)

        (tw, _), _ = cv2.getTextSize(text_label, FONT, 0.55, 2)
        x_text = int(round(x_center - tw / 2.0))
        y_text = 1628
        cv2.putText(anh_out, text_label, (x_text, y_text), FONT, 0.55, color_label, 2)

    diem_p3 = round(p3_dung * cau_hinh_diem.get("diem_moi_cau_p3", 0.50), 2)
    tong_diem = round(diem_p1 + diem_p2 + diem_p3, 2)

    # 4. Phát hiện bất thường & Cảnh báo nghi vấn (Anomaly & Defect Detection)
    to_dup_p1 = [q for q in da_p1.keys() if len(str(kq["phan1"].get(int(q), "-"))) > 1 and kq["phan1"].get(int(q), "-") != "-"]
    bo_trong_p1 = [q for q in da_p1.keys() if kq["phan1"].get(int(q), "-") in ("-", "")]

    to_dup_p2 = [f"C{q}{s}" for q in da_p2.keys() for s in da_p2[q].keys() if kq["phan2"].get(int(q), {}).get(s) == "DS"]
    bo_trong_p2 = [f"C{q}{s}" for q in da_p2.keys() for s in da_p2[q].keys() if kq["phan2"].get(int(q), {}).get(s) in ("-", "")]

    bo_trong_p3 = [f"C{q}" for q in da_p3.keys() if kq["phan3"].get(int(q), "-") in ("-", "")]

    ds_canh_bao = []
    if "?" in kq["sbd"] or len(kq["sbd"]) != 6 or not kq["sbd"].isdigit():
        ds_canh_bao.append(f"SBD không rõ ({kq['sbd']})")
        ghi_chu.append("SBD tô thiếu hoặc không rõ")

    if "?" in kq["made"] or len(kq["made"]) != 3 or not kq["made"].isdigit():
        ds_canh_bao.append(f"Mã đề không rõ ({kq['made']})")
        ghi_chu.append("Mã đề tô thiếu hoặc không rõ")

    if to_dup_p1 or to_dup_p2:
        chi_tiet_dup = []
        if to_dup_p1:
            chi_tiet_dup.append("P.I C" + ", C".join(to_dup_p1))
        if to_dup_p2:
            chi_tiet_dup.append("P.II " + ", ".join(to_dup_p2))
        ds_canh_bao.append(f"Tô đúp: {'; '.join(chi_tiet_dup)}")
        ghi_chu.append(f"Tô đúp: {'; '.join(chi_tiet_dup)}")

    tong_bo_trong = len(bo_trong_p1) + len(bo_trong_p2) + len(bo_trong_p3)
    if tong_bo_trong > 0:
        ds_canh_bao.append(f"Bỏ trống {tong_bo_trong} câu/ý")
        ghi_chu.append(f"Bỏ trống {tong_bo_trong} câu/ý")

    canh_bao_str = "⚠️ " + "; ".join(ds_canh_bao) if ds_canh_bao else "✅ Hợp lệ"
    co_canh_bao = len(ds_canh_bao) > 0

    # Vẽ bảng điểm tổng kết góc trên phiếu chấm
    box_x, box_y = 65, 140
    box_h = 115
    if p2_tong_cau == 0 and p3_tong == 0:
        box_h = 75
    elif p3_tong == 0:
        box_h = 95
    cv2.rectangle(anh_out, (box_x, box_y), (box_x + 360, box_y + box_h), (255, 255, 255), -1)
    border_color = (0, 140, 255) if co_canh_bao else (0, 0, 200)
    cv2.rectangle(anh_out, (box_x, box_y), (box_x + 360, box_y + box_h), border_color, 2)
    cv2.putText(anh_out, f"SBD: {kq['sbd']} | MA DE: {kq['made']}", (box_x + 10, box_y + 25), FONT, 0.65, (0, 0, 0), 2)
    cv2.putText(anh_out, f"Phan I:   {diem_p1:.2f} d ({p1_dung}/{p1_tong})", (box_x + 10, box_y + 50), FONT, 0.55, (0, 0, 0), 1)
    cur_y = box_y + 70
    if p2_tong_cau > 0:
        cv2.putText(anh_out, f"Phan II:  {diem_p2:.2f} d ({p2_tong_cau} cau)", (box_x + 10, cur_y), FONT, 0.55, (0, 0, 0), 1)
        cur_y += 20
    if p3_tong > 0:
        cv2.putText(anh_out, f"Phan III: {diem_p3:.2f} d ({p3_dung}/{p3_tong})", (box_x + 10, cur_y), FONT, 0.55, (0, 0, 0), 1)
    cv2.putText(anh_out, f"TONG: {tong_diem:.2f}", (box_x + 220, box_y + (60 if box_h < 95 else 80)), FONT, 0.95, (0, 0, 220), 3)

    return {
        "sbd": kq["sbd"],
        "made": kq["made"],
        "diem_p1": diem_p1,
        "diem_p2": diem_p2,
        "diem_p3": diem_p3,
        "tong_diem": tong_diem,
        "p1_dung": p1_dung,
        "p1_tong": p1_tong,
        "p2_chi_tiet": p2_chi_tiet,
        "p3_dung": p3_dung,
        "p3_tong": p3_tong,
        "p1_chi_tiet": p1_chi_tiet,
        "p3_chi_tiet": p3_chi_tiet,
        "ghi_chu": "; ".join(ghi_chu),
        "canh_bao": canh_bao_str,
        "co_canh_bao": co_canh_bao,
        "ds_canh_bao": ds_canh_bao,
        "to_dup": to_dup_p1 + to_dup_p2,
        "bo_trong_tong": tong_bo_trong,
        "anh_cham": anh_out
    }


def xu_ly_file_bggdt(
    ten_file: str,
    img: np.ndarray,
    bo_dap_an: Dict[str, Any],
    cau_hinh_diem: Optional[Dict[str, Any]] = None,
    danh_sach_hoc_sinh: Optional[Dict[str, Dict[str, str]]] = None
) -> Tuple[Dict[str, Any], Optional[np.ndarray]]:
    """Xử lý chấm một bài thi.

    bo_dap_an: dict dạng {"101": {"phan1": ..., "phan2": ..., "phan3": ...}, ...}
    cau_hinh_diem: cấu hình điểm cho các phần (Toán, Tiếng Anh, Sử/Địa, KHTN, Tùy biến)
    danh_sach_hoc_sinh: danh sách tra cứu SBD -> {"ten": ..., "lop": ...}
    """
    try:
        kq = doc_phieu_bggdt(img)
        made = kq["made"]
        sbd_raw = str(kq["sbd"]).strip()

        ten_hs = "Chưa rõ"
        lop_hs = "—"
        if danh_sach_hoc_sinh:
            hs_info = danh_sach_hoc_sinh.get(sbd_raw)
            if not hs_info:
                hs_info = danh_sach_hoc_sinh.get(sbd_raw.lstrip("0"))
            if not hs_info and sbd_raw.isdigit():
                hs_info = danh_sach_hoc_sinh.get(sbd_raw.zfill(6))
            if hs_info:
                ten_hs = hs_info.get("ten", "Chưa rõ")
                lop_hs = hs_info.get("lop", "—")

        if made not in bo_dap_an:
            if len(bo_dap_an) == 1:
                key_de = next(iter(bo_dap_an.keys()))
                dap_an_de = bo_dap_an[key_de]
                curr_cfg = cau_hinh_diem or {
                    "diem_moi_cau_p1": dap_an_de.get("diem_moi_cau_p1", 0.25),
                    "diem_moi_cau_p3": dap_an_de.get("diem_moi_cau_p3", 0.50),
                }
                ch = cham_bai_bggdt(kq, dap_an_de, curr_cfg)
                ch["ghi_chu"] = (ch["ghi_chu"] + f"; Dùng đáp án mã đề {key_de}").strip("; ")
                ch["canh_bao"] = (f"⚠️ Mã đề {made} chưa có đáp án (chấm theo {key_de}); " + ch.get("canh_bao", "").replace("✅ Hợp lệ", "")).strip("; ")
                ch["co_canh_bao"] = True
            else:
                return {
                    "Tên file": ten_file,
                    "SBD": kq["sbd"],
                    "Họ và tên": ten_hs,
                    "Lớp": lop_hs,
                    "Mã đề": made,
                    "Điểm Phần I": None,
                    "Điểm Phần II": None,
                    "Điểm Phần III": None,
                    "Tổng điểm": None,
                    "P1 Đúng": "—",
                    "P3 Đúng": "—",
                    "Cảnh báo": f"⚠️ Chưa có đáp án cho mã đề '{made}'",
                    "Ghi chú": f"LỖI: Không tìm thấy đáp án cho mã đề '{made}'",
                    "_details": None
                }, None
        else:
            dap_an_de = bo_dap_an[made]
            curr_cfg = cau_hinh_diem or {
                "diem_moi_cau_p1": dap_an_de.get("diem_moi_cau_p1", 0.25),
                "diem_moi_cau_p3": dap_an_de.get("diem_moi_cau_p3", 0.50),
            }
            ch = cham_bai_bggdt(kq, dap_an_de, curr_cfg)

        row = {
            "Tên file": ten_file,
            "SBD": ch["sbd"],
            "Họ và tên": ten_hs,
            "Lớp": lop_hs,
            "Mã đề": ch["made"],
            "Tổng điểm": ch["tong_diem"],
            "Điểm Phần I": ch["diem_p1"],
            "Điểm Phần II": ch["diem_p2"],
            "Điểm Phần III": ch["diem_p3"],
            "P1 Đúng": f"{ch['p1_dung']}/{ch['p1_tong']}",
            "P3 Đúng": f"{ch['p3_dung']}/{ch['p3_tong']}",
            "Cảnh báo": ch["canh_bao"],
            "Ghi chú": ch["ghi_chu"],
            "_details": ch
        }
        return row, ch["anh_cham"]
    except Exception as e:
        return {
            "Tên file": ten_file,
            "SBD": "",
            "Họ và tên": "Chưa rõ",
            "Lớp": "—",
            "Mã đề": "",
            "Điểm Phần I": None,
            "Điểm Phần II": None,
            "Điểm Phần III": None,
            "Tổng điểm": None,
            "P1 Đúng": "—",
            "P3 Đúng": "—",
            "Cảnh báo": f"⚠️ LỖI: {str(e)}",
            "Ghi chú": f"LỖI: {str(e)}",
            "_details": None
        }, None


def tao_dap_an_tu_anh_phieu(img: np.ndarray) -> Tuple[str, Dict[str, Any]]:
    """Trích xuất đáp án chuẩn từ ảnh chụp một tờ phiếu mà giáo viên đã tô sẵn (Master Key Sheet).

    Giúp thầy cô không cần gõ đáp án bằng tay, chỉ cần tô 1 tờ đáp án mẫu và chụp lại.
    """
    kq = doc_phieu_bggdt(img)
    made = kq["made"]
    if "?" in made or not made.strip():
        raise ValueError(f"Không nhận diện được mã đề trên phiếu đáp án (đọc được: '{made}'). Vui lòng tô rõ 3 chữ số mã đề thi.")

    # Lọc các câu giáo viên có tô đáp án
    p1 = {str(q): opt for q, opt in kq["phan1"].items() if opt in ("A", "B", "C", "D")}

    p2 = {}
    for q, subs in kq["phan2"].items():
        valid_subs = {s: val for s, val in subs.items() if val in ("D", "S")}
        if valid_subs:
            p2[str(q)] = valid_subs

    p3 = {str(q): val for q, val in kq["phan3"].items() if val not in ("-", "", "?")}

    if not p1 and not p2 and not p3:
        raise ValueError("Tờ phiếu đáp án mẫu chưa được tô câu trả lời nào.")

    dap_an_de = {
        "phan1": p1,
        "phan2": p2,
        "phan3": p3
    }
    return made, dap_an_de



if __name__ == "__main__":
    import glob
    import pandas as pd
    from generate_sample_bggdt import tao_bai_thi_mau

    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]

    if len(args) >= 1 and args[0] == "mau":
        out_dir = "anh_bai_bggdt"
        os.makedirs(out_dir, exist_ok=True)
        print("Đang tạo 3 bài thi mẫu giả lập chụp nghiêng...")
        for k in range(1, 4):
            sbd_val = f"00000{k}"
            made_val = "101" if k % 2 == 1 else "102"
            p_out = os.path.join(out_dir, f"bai_{k}.jpg")
            img_mau, _ = tao_bai_thi_mau(sbd=sbd_val, made=made_val, seed=k * 15)
            ghi_anh(p_out, img_mau)
            print(f"  -> Đã tạo {p_out} (SBD: {sbd_val}, Mã đề: {made_val})")
        print("Tạo mẫu hoàn tất!")

    elif len(args) >= 3 and args[0] == "cham":
        thu_muc_anh = args[1]
        file_dap_an = args[2]

        with open(file_dap_an, "r", encoding="utf-8") as f:
            bo_da = json.load(f)

        os.makedirs("da_cham_bggdt", exist_ok=True)
        ds_ket_qua = []

        files = sorted(glob.glob(os.path.join(thu_muc_anh, "*.*")))
        img_files = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png"))]

        print(f"Bắt đầu chấm {len(img_files)} bài thi trong thư mục '{thu_muc_anh}'...")
        print("-" * 75)
        print(f"{'Tên file':<20} | {'SBD':<8} | {'Mã đề':<6} | {'P1':<5} | {'P2':<5} | {'P3':<5} | {'TỔNG':<6} | Ghi chú")
        print("-" * 75)

        for p in img_files:
            ten = os.path.basename(p)
            img = doc_anh(p)
            row, anh_cham = xu_ly_file_bggdt(ten, img, bo_da)
            ds_ket_qua.append(row)

            p1_str = f"{row['Điểm Phần I']:.2f}" if row['Điểm Phần I'] is not None else "-"
            p2_str = f"{row['Điểm Phần II']:.2f}" if row['Điểm Phần II'] is not None else "-"
            p3_str = f"{row['Điểm Phần III']:.2f}" if row['Điểm Phần III'] is not None else "-"
            tong_str = f"{row['Tổng điểm']:.2f}" if row['Tổng điểm'] is not None else "-"

            print(f"{ten:<20} | {str(row['SBD']):<8} | {str(row['Mã đề']):<6} | {p1_str:<5} | {p2_str:<5} | {p3_str:<5} | {tong_str:<6} | {row['Ghi chú']}")

            if anh_cham is not None:
                p_save = os.path.join("da_cham_bggdt", f"cham_{ten}")
                ghi_anh(p_save, anh_cham)

        df = pd.DataFrame(ds_ket_qua)
        excel_path = "bang_diem_bggdt.xlsx"
        df.to_excel(excel_path, index=False)
        print("-" * 75)
        print(f"🎉 Hoàn tất! Đã lưu kết quả ra '{excel_path}' và ảnh chấm trong 'da_cham_bggdt/'")
    else:
        print("HƯỚNG DẪN DÙNG:")
        print("  1. Tạo bài mẫu:  python omr_bggdt.py mau")
        print("  2. Chấm bài thi: python omr_bggdt.py cham <thư_mục_ảnh> <file_dap_an.json>")

