"""Lõi xử lý: tạo phiếu, đọc phiếu, chấm điểm."""
import os
import re
import sys

import cv2
import numpy as np

# ===== CẤU HÌNH PHIẾU (A4 @150dpi) =====
W, H = 1240, 1754
MARK, MARGIN = 60, 40
C = MARGIN + MARK / 2
DST = np.float32([[C, C], [W - C, C], [W - C, H - C], [C, H - C]])

LUA_CHON = "ABCD"
SO_CAU_TOI_DA, DONG_MOI_COT = 60, 20
R = 16                                   # bán kính ô tròn
COT_X, Y0, DY, DX = [170, 540, 910], 780, 43, 55

SO_CHU_SBD, SO_CHU_MADE = 6, 3
SBD_X, MADE_X, ID_Y0, ID_D = 260, 720, 330, 40
NGUONG_TO = 0.5                          # >50% diện tích bị tô => đã chọn
FONT = cv2.FONT_HERSHEY_SIMPLEX

_MASK = np.zeros((2 * R + 1, 2 * R + 1), np.uint8)
cv2.circle(_MASK, (R, R), R - 4, 1, -1)


def o_cau(q, i):
    cot, dong = divmod(q, DONG_MOI_COT)
    return COT_X[cot] + i * DX, Y0 + dong * DY


def o_so(x0, cot, so):
    return x0 + cot * ID_D, ID_Y0 + so * ID_D


# ---------- Đọc/ghi ảnh hỗ trợ tên file tiếng Việt ----------
def doc_anh(path):
    return cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)


def ghi_anh(path, img):
    cv2.imencode(os.path.splitext(path)[1] or ".png", img)[1].tofile(path)


# ---------- 1. Tạo phiếu ----------
def tao_phieu_img():
    img = np.full((H, W), 255, np.uint8)
    for x, y in [(MARGIN, MARGIN), (W - MARGIN - MARK, MARGIN),
                 (W - MARGIN - MARK, H - MARGIN - MARK), (MARGIN, H - MARGIN - MARK)]:
        cv2.rectangle(img, (x, y), (x + MARK, y + MARK), 0, -1)
    cv2.putText(img, "PHIEU TRA LOI TRAC NGHIEM", (330, 110), FONT, 1.4, 0, 3)
    cv2.putText(img, "Ho ten: ..........................................   Lop: ..........",
                (150, 180), FONT, 0.8, 0, 2)

    for x0, n, ten in [(SBD_X, SO_CHU_SBD, "SO BAO DANH"), (MADE_X, SO_CHU_MADE, "MA DE")]:
        cv2.putText(img, ten, (x0 - 10, 245), FONT, 0.7, 0, 2)
        for cot in range(n):
            x, _ = o_so(x0, cot, 0)
            cv2.rectangle(img, (x - R, 262), (x + R, 298), 0, 1)   # ô viết số tay
            for so in range(10):
                x, y = o_so(x0, cot, so)
                cv2.circle(img, (x, y), R, 0, 2)
                cv2.putText(img, str(so), (x - 6, y + 6), FONT, 0.5, 0, 1)

    for q in range(SO_CAU_TOI_DA):
        x, y = o_cau(q, 0)
        cv2.putText(img, f"{q + 1:2d}", (x - 75, y + 8), FONT, 0.7, 0, 2)
        for i, c in enumerate(LUA_CHON):
            x, y = o_cau(q, i)
            cv2.circle(img, (x, y), R, 0, 2)
            cv2.putText(img, c, (x - 7, y + 6), FONT, 0.5, 0, 1)
    return img


# ---------- 2. Tìm 4 góc & đọc phiếu ----------
def tim_goc(gray):
    th = cv2.threshold(cv2.GaussianBlur(gray, (5, 5), 0), 0, 255,
                       cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    cnts, _ = cv2.findContours(th, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    ung_vien = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        a = w * h
        if not (gray.size * 0.0003 < a < gray.size * 0.02) or not 0.7 < w / h < 1.3:
            continue
        if cv2.countNonZero(th[y:y + h, x:x + w]) / a < 0.85:   # phải tô đặc
            continue
        ung_vien.append((a, x + w / 2, y + h / 2))
    if len(ung_vien) < 4:
        raise RuntimeError("Không tìm thấy đủ 4 ô vuông góc (chụp rõ, đủ sáng, thấy cả 4 góc)")
    pts = np.float32([[x, y] for _, x, y in sorted(ung_vien, reverse=True)[:4]])
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.float32([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]])


def ti_le_to(th, x, y):
    roi = th[y - R:y + R + 1, x - R:x + R + 1]
    return float((roi[_MASK == 1] > 0).mean())


def doc_so(th, x0, n):
    kq = ""
    for cot in range(n):
        to = [s for s in range(10) if ti_le_to(th, *o_so(x0, cot, s)) > NGUONG_TO]
        kq += str(to[0]) if len(to) == 1 else "?"
    return kq


def doc_phieu(img):
    if img is None:
        raise ValueError("Không đọc được ảnh")
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    M = cv2.getPerspectiveTransform(tim_goc(gray), DST)
    phang = cv2.warpPerspective(gray, M, (W, H))
    th = cv2.threshold(cv2.GaussianBlur(phang, (3, 3), 0), 0, 255,
                       cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    tra_loi = []
    for q in range(SO_CAU_TOI_DA):
        t = [ti_le_to(th, *o_cau(q, i)) for i in range(len(LUA_CHON))]
        tra_loi.append("".join(LUA_CHON[i] for i, v in enumerate(t) if v > NGUONG_TO))
    return {"sbd": doc_so(th, SBD_X, SO_CHU_SBD),
            "ma_de": doc_so(th, MADE_X, SO_CHU_MADE),
            "tra_loi": tra_loi, "anh_phang": phang}


# ---------- 3. Chấm điểm ----------
def parse_dap_an(txt):
    """Mỗi dòng: 'mã đề: đáp án'. VD: 101: ABCDA..."""
    bo = {}
    for dong in txt.splitlines():
        if ":" in dong:
            ma, da = dong.split(":", 1)
            da = re.sub(r"[^ABCD]", "", da.upper())
            if ma.strip() and da:
                bo[ma.strip()] = da[:SO_CAU_TOI_DA]
    return bo


def cham_diem(kq, bo):
    ma_de, ghi_chu = kq["ma_de"], []
    if ma_de not in bo:
        if len(bo) != 1:
            raise ValueError(f"Không có đáp án cho mã đề '{ma_de}'")
        ghi_chu.append(f"Mã đề đọc được '{ma_de}', dùng đáp án đề {next(iter(bo))}")
        ma_de = next(iter(bo))
    key = bo[ma_de]

    out = cv2.cvtColor(kq["anh_phang"], cv2.COLOR_GRAY2BGR)
    dung_sai, chi_tiet = [], []
    for q, d in enumerate(key):
        chon = kq["tra_loi"][q]
        dung_sai.append(chon == d)
        chi_tiet.append(chon or "-")
        if chon != d:
            for c in chon:
                cv2.circle(out, o_cau(q, LUA_CHON.index(c)), R + 4, (0, 0, 255), 3)  # đỏ
        cv2.circle(out, o_cau(q, LUA_CHON.index(d)), R + 4, (0, 180, 0), 3)          # xanh

    dung = sum(dung_sai)
    diem = round(dung / len(key) * 10, 2)
    if "?" in kq["sbd"]:
        ghi_chu.append("SBD tô thiếu/sai")
    if (n := sum(len(c) > 1 for c in chi_tiet)):
        ghi_chu.append(f"{n} câu tô nhiều ô")
    if (n := chi_tiet.count("-")):
        ghi_chu.append(f"{n} câu bỏ trống")

    for i, (t, sc) in enumerate([(f"SBD: {kq['sbd']}", 0.9), (f"Ma de: {ma_de}", 0.9),
                                 (f"Dung: {dung}/{len(key)}", 0.9), (f"DIEM: {diem}", 1.3)]):
        cv2.putText(out, t, (860, 380 + i * 60), FONT, sc, (0, 0, 255), 2 if sc < 1 else 3)

    return {"ma_de": ma_de, "dung": dung, "tong": len(key), "diem": diem,
            "ghi_chu": "; ".join(ghi_chu), "chi_tiet": chi_tiet,
            "dung_sai": dung_sai, "anh": out}


def xu_ly(ten, img, bo):
    """Trả về (dòng kết quả, ảnh đã chấm, danh sách đúng/sai)."""
    try:
        kq = doc_phieu(img)
        ch = cham_diem(kq, bo)
        row = {"Tên file": ten, "SBD": kq["sbd"], "Mã đề": ch["ma_de"],
               "Số câu đúng": ch["dung"], "Tổng số câu": ch["tong"],
               "Điểm": ch["diem"], "Ghi chú": ch["ghi_chu"]}
        row.update({f"Câu {i + 1}": c for i, c in enumerate(ch["chi_tiet"])})
        return row, ch["anh"], ch["dung_sai"]
    except Exception as e:
        return {"Tên file": ten, "Ghi chú": f"LỖI: {e}"}, None, None


COT_CHINH = ["Tên file", "SBD", "Mã đề", "Số câu đúng", "Tổng số câu", "Điểm", "Ghi chú"]


def sap_cot(df):
    return df.reindex(columns=COT_CHINH + [c for c in df.columns if c not in COT_CHINH])


# ---------- Ảnh mẫu để thử ----------
def tao_bai_mau(file="bai_mau.png", sbd="123456", ma_de="101", so_cau=40, seed=0):
    """Tạo ảnh bài đã tô (giả lập chụp nghiêng). Trả về chuỗi đáp án đã tô."""
    rng = np.random.default_rng(seed)
    img = tao_phieu_img()
    for x0, s in [(SBD_X, sbd), (MADE_X, ma_de)]:
        for cot, ch in enumerate(s):
            cv2.circle(img, o_so(x0, cot, int(ch)), R - 2, 0, -1)
    da_to = ""
    for q in range(so_cau):
        i = int(rng.integers(4))
        da_to += LUA_CHON[i]
        cv2.circle(img, o_cau(q, i), R - 2, 0, -1)
    nen = np.full((2000, 1600), 170, np.uint8)
    M = cv2.getPerspectiveTransform(
        np.float32([[0, 0], [W, 0], [W, H], [0, H]]),
        np.float32([[150, 120], [1420, 180], [1380, 1900], [110, 1850]]))
    cv2.warpPerspective(img, M, (1600, 2000), dst=nen, borderMode=cv2.BORDER_TRANSPARENT)
    ghi_anh(file, nen)
    return da_to


# ---------- Dòng lệnh ----------
def main(a):
    import glob
    import pandas as pd

    if a[:1] == ["tao-phieu"]:
        ghi_anh("phieu_tra_loi.png", tao_phieu_img())
        print("Đã tạo phieu_tra_loi.png - in khổ A4.")
    elif a[:1] == ["mau"]:
        os.makedirs("anh_bai", exist_ok=True)
        for k in range(3):
            p = f"anh_bai/bai_{k + 1}.png"
            tao_bai_mau(p, sbd=f"00000{k + 1}", ma_de="101" if k % 2 == 0 else "102", seed=k)
            print(f"Đã tạo ảnh mẫu {p}")
    elif len(a) == 3 and a[0] == "cham":
        with open(a[2], encoding="utf-8") as f:
            bo = parse_dap_an(f.read())
        os.makedirs("da_cham", exist_ok=True)
        rows = []
        for p in sorted(glob.glob(os.path.join(a[1], "*"))):
            if not p.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            row, anh, _ = xu_ly(os.path.basename(p), doc_anh(p), bo)
            rows.append(row)
            print(f"{row['Tên file']:<25} SBD {str(row.get('SBD', '-')):<8} "
                  f"Điểm {str(row.get('Điểm', '-')):<6} {row['Ghi chú']}")
            if anh is not None:
                ghi_anh(os.path.join("da_cham", os.path.basename(p)), anh)
        sap_cot(pd.DataFrame(rows)).to_excel("ket_qua.xlsx", index=False)
        print("\n==> Đã lưu ket_qua.xlsx và ảnh chấm trong thư mục da_cham/")
    else:
        print("Dùng:\n  python omr_core.py tao-phieu\n  python omr_core.py mau\n"
              "  python omr_core.py cham <thư_mục_ảnh> dap_an.txt")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
