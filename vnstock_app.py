# -*- coding: utf-8 -*-
"""
Vnstock App v3.8 - Tra cứu & Phân Tích Báo Cáo Tài Chính
Nâng cấp mới nhất (v3.8):
1. Giữ nguyên nhãn kỳ báo cáo gốc từ API TCBS (2026-Q2, 2026-Q1...) - không đổi nhãn sai.
2. Tự động loại bỏ cột trùng lặp dạng _1 từ API.
3. Chèn Logo Cá Nhân "KTT.jpg" nổi bật trên thanh tiêu đề ứng dụng.
4. Tính năng SORT số liệu linh hoạt khi nhấp vào Tiêu đề cột (Tăng dần ▲ / Giảm dần ▼).
5. Mặc định tự động sắp xếp báo cáo thống kê ngành theo Cột Năm Mới Nhất Giảm Dần.
6. Đồng bộ Bộ Lọc "TỪ NĂM -> ĐẾN NĂM" cho cả 2 Tab (mở rộng đến 2027).
7. Multi-threading tải song song (Parallel Processing) + Timeout 7s + Rate-limit Throttling chống treo app.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import concurrent.futures
import traceback
import unicodedata
import re
import time
import socket
import os
import json
from datetime import date, timedelta
import pandas as pd
from PIL import Image, ImageTk

# Matplotlib cho biểu đồ định giá (tùy chọn)
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Thiết lập Socket Timeout toàn cục 5.0 giây chống treo mạng
socket.setdefaulttimeout(5.0)

APP_TITLE = "Vnstock App v3.8 - Tra cứu & Phân Tích Báo Cáo Tài Chính"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "KTT.jpg")

last_dataframe = None
last_label = ""

YEAR_LIST = [str(y) for y in range(2015, 2028)]

# ------------------------------------------------------------------
# TỪ ĐIỂN ĐỒNG NGHĨA NGÀNH (SECTOR ALIAS MAPPING)
# ------------------------------------------------------------------
SECTOR_ALIASES = {
    "duoc pham": ["Chăm sóc sức khỏe", "Dược phẩm", "Y tế", "Sản xuất Dược phẩm"],
    "duoc": ["Chăm sóc sức khỏe", "Dược phẩm", "Y tế"],
    "y te": ["Chăm sóc sức khỏe", "Y tế"],
    "pharma": ["Chăm sóc sức khỏe", "Dược phẩm"],
    "healthcare": ["Chăm sóc sức khỏe", "Y tế"],
    "ngan hang": ["Ngân hàng"],
    "bank": ["Ngân hàng"],
    "bat dong san": ["Bất động sản"],
    "bds": ["Bất động sản"],
    "chung khoan": ["Dịch vụ tài chính", "Chứng khoán"],
    "ctck": ["Dịch vụ tài chính", "Chứng khoán"],
    "thep": ["Tài nguyên", "Thép"],
    "kim loai": ["Tài nguyên", "Kim loại"],
    "ban le": ["Bán lẻ"],
    "retail": ["Bán lẻ"],
    "cong nghe": ["Công nghệ Thông tin"],
    "it": ["Công nghệ Thông tin"],
    "cntt": ["Công nghệ Thông tin"],
    "thuc pham": ["Thực phẩm và đồ uống"],
    "do uong": ["Thực phẩm và đồ uống"],
    "dau khi": ["Dầu khí"],
    "oil": ["Dầu khí"],
    "tien ich": ["Tiện ích"],
    "dien": ["Tiện ích"],
    "nuoc": ["Tiện ích"],
    "xay dung": ["Xây dựng và Vật liệu"],
    "vat lieu": ["Xây dựng và Vật liệu"],
    "van tai": ["Hàng & Dịch vụ Công nghiệp", "Vận tải"],
    "logistics": ["Hàng & Dịch vụ Công nghiệp", "Vận tải"],
    "hoa chat": ["Hóa chất"],
    "bao hiem": ["Bảo hiểm"],
}

PHARMA_TICKERS_FALLBACK = [
    "DHG", "IMP", "TRA", "DBD", "DCL", "PMC", "DP3", "DVN", "DHT", "OPC",
    "SPM", "MKP", "WDB", "CDP", "AMP", "DPC", "DDN", "LDP", "PME", "HEV",
    "PPP", "DTP", "PBC", "TW3", "VMD", "DBT", "VDP", "MED", "NDP", "UPH",
    "FMC", "CYC", "TBR", "VET", "DOP", "MKV", "HAP", "BIO", "DP2", "DP1",
    "FIT", "AMV", "JVC", "DNM", "TNH", "AGP", "DVY", "MEP", "PNT", "YTC",
    "DTH", "CPC", "HDM", "TTP", "BCP", "NBP", "SPE", "VNH", "DCH", "DPH"
]

METRIC_ALIASES = {
    "doanh thu thuan": ["Doanh thu thuần về bán hàng và cung cấp dịch vụ", "Doanh thu thuần"],
    "doanh thu": ["Doanh thu thuần về bán hàng và cung cấp dịch vụ", "Doanh thu bán hàng và cung cấp dịch vụ", "Doanh thu thuần"],
    "revenue": ["Doanh thu thuần về bán hàng và cung cấp dịch vụ"],
    "loi nhuan sau thue": ["Lợi nhuận sau thuế thu nhập doanh nghiệp", "Lợi nhuận sau thuế của công ty mẹ", "LNST"],
    "lnst": ["Lợi nhuận sau thuế thu nhập doanh nghiệp", "Lợi nhuận sau thuế của công ty mẹ"],
    "net profit": ["Lợi nhuận sau thuế thu nhập doanh nghiệp"],
    "loi nhuan gop": ["Lợi nhuận gộp về bán hàng và cung cấp dịch vụ"],
    "ln gop": ["Lợi nhuận gộp về bán hàng và cung cấp dịch vụ"],
    "ebit": ["Lợi nhuận từ hoạt động kinh doanh", "EBIT"],
    "gia von": ["Giá vốn hàng bán"],
    "chi phi tai chinh": ["Chi phí tài chính"],
    "chi phi ban hang": ["Chi phí bán hàng"],
    "chi phi quan ly": ["Chi phí quản lý doanh nghiệp"],
    "thu nhap khac": ["Thu nhập khác"],
    "chi phi khac": ["Chi phí khác"],
    "doanh thu tai chinh": ["Doanh thu hoạt động tài chính"],
}

PRESET_METRICS = [
    "Doanh thu thuần",
    "Lợi nhuận sau thuế",
    "Lợi nhuận gộp",
    "EBIT",
    "Giá vốn hàng bán",
    "Chi phí tài chính",
    "Chi phí bán hàng",
    "Chi phí quản lý doanh nghiệp",
    "Thu nhập khác",
    "Chi phí khác",
    "Doanh thu hoạt động tài chính"
]

DROPDOWN_SECTOR_LIST = [
    "Chăm sóc sức khỏe (Dược phẩm & Y tế)",
    "Ngân hàng",
    "Bất động sản",
    "Dịch vụ tài chính (Chứng khoán)",
    "Tài nguyên (Thép & Khai khoáng)",
    "Thực phẩm & Đồ uống",
    "Bán lẻ",
    "Công nghệ Thông tin",
    "Dầu khí",
    "Tiện ích (Điện, Nước)",
    "Xây dựng & Vật liệu",
    "Hàng & Dịch vụ Công nghiệp (Vận tải & Logistics)",
    "Hóa chất",
    "Bảo hiểm"
]


def check_vnstock_installed():
    try:
        import vnstock  # noqa: F401
        return True
    except ImportError:
        return False


def normalize_text(s):
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def format_cell_value(val, unit_mode="Nguyên tệ"):
    if val is None or pd.isna(val) or str(val).strip() in ["", "nan", "None", "-", "NaN"]:
        return "-"
    try:
        num = float(val)
        if unit_mode == "Tỷ VNĐ":
            if abs(num) >= 1e5:
                return f"{num / 1e9:,.2f}"
            return f"{num:,.2f}"
        elif unit_mode == "Triệu VNĐ":
            if abs(num) >= 1e5:
                return f"{num / 1e6:,.2f}"
            return f"{num:,.2f}"
        else: # Nguyên tệ
            if abs(num - round(num)) < 1e-4:
                return f"{int(round(num)):,}"
            else:
                return f"{num:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def fix_quarterly_column_headers(df):
    """
    Chuẩn hóa tiêu đề cột Quý từ API vnstock/TCBS.
    - Giữ nguyên nhãn gốc API (ví dụ: 2026-Q2, 2025-Q4) vì đó là cách TCBS đánh nhãn.
    - Chỉ loại bỏ các cột trùng lặp dạng _1 (ví dụ: 2025-Q4_1 trùng với 2025-Q4 hoặc 2026-Q2).
    - Sắp xếp lại các cột kỳ báo cáo theo thứ tự mới nhất -> cũ nhất.
    """
    if df is None or len(df) == 0:
        return df

    fixed_df = df.copy()
    
    # Loại bỏ các cột có hậu tố _1 (duplicate columns từ API)
    dup_cols = [c for c in fixed_df.columns if str(c).endswith('_1')]
    if dup_cols:
        fixed_df = fixed_df.drop(columns=dup_cols, errors='ignore')

    return fixed_df


def filter_period_columns_by_year(cols, start_year=None, end_year=None):
    if start_year is None and end_year is None:
        return cols

    try:
        s_y = int(start_year) if start_year else None
        e_y = int(end_year) if end_year else None
    except ValueError:
        return cols

    filtered = []
    for c in cols:
        s_c = str(c).strip()
        m = re.search(r'(?:20)?(\d{2,4})', s_c)
        if m:
            yr_val = int(m.group(1))
            if yr_val < 100:
                yr_val += 2000
            
            if s_y is not None and yr_val < s_y:
                continue
            if e_y is not None and yr_val > e_y:
                continue
            filtered.append(c)
        else:
            filtered.append(c)
    return filtered


def get_symbols_by_industry(keyword, max_n=20, progress_cb=None):
    from vnstock import Listing

    raw_kw = keyword.strip()
    norm_kw = normalize_text(raw_kw)

    target_terms = [norm_kw]
    for key, aliases in SECTOR_ALIASES.items():
        if key in norm_kw or norm_kw in key:
            for al in aliases:
                norm_al = normalize_text(al)
                if norm_al not in target_terms:
                    target_terms.append(norm_al)

    if progress_cb:
        progress_cb(f"Đang tìm mã cổ phiếu cho ngành '{raw_kw}'...", pct=5)

    listing = Listing()
    df_ind = None
    try:
        df_ind = listing.symbols_by_industries(lang="vi")
    except Exception as e:
        print(f"Cảnh báo: Không gọi được symbols_by_industries(): {e}")

    results = []
    seen_symbols = set()

    if df_ind is not None and len(df_ind) > 0:
        df = df_ind.copy()
        text_cols = [c for c in df.columns if df[c].dtype == object]
        
        norm_col_names = []
        for c in text_cols:
            norm_c = f"_norm_{c}"
            df[norm_c] = df[c].apply(normalize_text)
            norm_col_names.append(norm_c)

        symbol_col = None
        for c in df.columns:
            nc = normalize_text(c)
            if "symbol" in nc or "ticker" in nc:
                symbol_col = c
                break
        if symbol_col is None and len(text_cols) > 0:
            symbol_col = text_cols[0]

        name_col = None
        for c in df.columns:
            nc = normalize_text(c)
            if "organ" in nc or "company" in nc or "name" in nc:
                name_col = c
                break

        matched_mask = pd.Series(False, index=df.index)
        for term in target_terms:
            for nc in norm_col_names:
                matched_mask = matched_mask | df[nc].str.contains(term, na=False)

        matched = df[matched_mask].drop_duplicates(subset=[symbol_col])
        
        for _, row in matched.iterrows():
            sym = str(row[symbol_col]).strip().upper()
            if sym and sym not in seen_symbols:
                seen_symbols.add(sym)
                c_name = str(row.get(name_col, sym)).strip() if name_col else sym
                ind_name = str(row.get("industry_name", raw_kw)).strip()
                results.append({"symbol": sym, "company_name": c_name, "industry": ind_name})

    is_pharma_search = any(term in ["chua soc suc khoe", "cham soc suc khoe", "duoc pham", "duoc", "y te", "pharma"] for term in target_terms)
    if is_pharma_search and len(results) < 15:
        if progress_cb:
            progress_cb("Bổ sung danh sách 62+ doanh nghiệp Dược phẩm niêm yết chuẩn...", pct=10)
        try:
            df_all = listing.all_symbols()
            name_map = {}
            if df_all is not None and len(df_all) > 0:
                s_col = [c for c in df_all.columns if "symbol" in normalize_text(c) or "ticker" in normalize_text(c)]
                n_col = [c for c in df_all.columns if "organ" in normalize_text(c) or "name" in normalize_text(c)]
                if s_col and n_col:
                    name_map = dict(zip(df_all[s_col[0]].astype(str).str.upper().str.strip(), df_all[n_col[0]].astype(str).str.strip()))
        except Exception:
            name_map = {}

        for sym in PHARMA_TICKERS_FALLBACK:
            if sym not in seen_symbols:
                seen_symbols.add(sym)
                c_name = name_map.get(sym, sym)
                results.append({"symbol": sym, "company_name": c_name, "industry": "Chăm sóc sức khỏe"})

    if len(results) == 0:
        raise RuntimeError(
            f"Khong tim thay nganh nao khop voi tu khoa '{keyword}'.\n\n"
            f"Vui long chon nganh tu danh sach Dropdown (vi du: 'Chăm sóc sức khỏe', 'Ngân hàng', 'Bất động sản'...)"
        )

    return results[:max_n]


_NON_PERIOD_COLS = {"item", "item_en", "item_id", "item_code", "unit", "ticker", "symbol"}


def _fetch_single_company_income(comp, period):
    from vnstock import Fundamental
    symbol = comp["symbol"]
    try:
        fund = Fundamental()
        df_income = fund.equity(symbol).income_statement(period=period, lang="vi")
        if period == "quarter":
            df_income = fix_quarterly_column_headers(df_income)
        return symbol, comp["company_name"], df_income, None
    except Exception as e:
        err_msg = str(e)
        if "Rate limit" in err_msg or "GIỚI HẠN API" in err_msg or "20 requests" in err_msg:
            return symbol, comp["company_name"], None, "RATE_LIMIT_EXCEEDED"
        return symbol, comp["company_name"], None, err_msg


def build_industry_metric_table(industry_keyword, metric_keywords, period, max_companies, start_year=None, end_year=None, progress_cb=None):
    companies = get_symbols_by_industry(industry_keyword, max_n=max_companies, progress_cb=progress_cb)

    total_comps = len(companies)
    if progress_cb:
        progress_cb(f"Tìm thấy {total_comps} công ty. Đang tải BCTC an toàn...", pct=10)

    rows = []
    errors = []
    completed_count = 0
    rate_limit_hit = False

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_comp = {}
        for idx, comp in enumerate(companies):
            if idx > 0 and idx % 3 == 0:
                time.sleep(0.15)
            future_to_comp[executor.submit(_fetch_single_company_income, comp, period)] = comp
        
        for future in concurrent.futures.as_completed(future_to_comp):
            completed_count += 1
            comp = future_to_comp[future]
            
            try:
                symbol, company_name, df_income, err = future.result(timeout=7.0)
            except concurrent.futures.TimeoutError:
                symbol, company_name, df_income, err = comp["symbol"], comp["company_name"], None, "Timeout (>7s)"
            except Exception as ex:
                symbol, company_name, df_income, err = comp["symbol"], comp["company_name"], None, str(ex)

            pct = 10 + (completed_count / total_comps) * 85

            if err == "RATE_LIMIT_EXCEEDED":
                rate_limit_hit = True
                errors.append(f"{symbol}: ⚠️ Đạt giới hạn API Rate-limit (20 req/min)")
                if progress_cb:
                    progress_cb(f"⚠️ Dừng tại {symbol} do chạm giới hạn API 20 req/phút ({completed_count}/{total_comps})", pct=pct)
                continue

            if progress_cb:
                progress_cb(f"Đang xử lý {symbol} ({completed_count}/{total_comps} - {pct:.1f}%) ...", pct=pct)

            if err or df_income is None or len(df_income) == 0:
                errors.append(f"{symbol}: {err or 'không có dữ liệu'}")
                continue

            item_col = None
            for cand in df_income.columns:
                if normalize_text(cand) == "item":
                    item_col = cand
                    break
            if item_col is None:
                for cand in df_income.columns:
                    if df_income[cand].dtype == object:
                        item_col = cand
                        break
            if item_col is None:
                errors.append(f"{symbol}: không xác định được cột chỉ tiêu")
                continue

            raw_period_cols = [c for c in df_income.columns if normalize_text(c) not in _NON_PERIOD_COLS]
            period_cols = filter_period_columns_by_year(raw_period_cols, start_year=start_year, end_year=end_year)

            if not period_cols:
                errors.append(f"{symbol}: không có kỳ báo cáo nào thuộc khoảng {start_year} -> {end_year}")
                continue

            for metric_kw in metric_keywords:
                norm_kw = normalize_text(metric_kw)
                
                target_metric_terms = [norm_kw]
                if norm_kw in METRIC_ALIASES:
                    target_metric_terms = [normalize_text(t) for t in METRIC_ALIASES[norm_kw]]

                matched_rows = pd.DataFrame()
                for tm in target_metric_terms:
                    m_r = df_income[df_income[item_col].apply(lambda x: tm in normalize_text(x))]
                    matched_rows = pd.concat([matched_rows, m_r])
                
                matched_rows = matched_rows.drop_duplicates()

                if len(matched_rows) == 0:
                    errors.append(f"{symbol}: không tìm thấy chỉ tiêu '{metric_kw}'")
                    continue

                for _, r in matched_rows.iterrows():
                    row_data = {
                        "Mã cổ phiếu": symbol,
                        "Tên công ty": company_name,
                        "Chỉ tiêu": r[item_col],
                    }
                    for pc in period_cols:
                        row_data[str(pc)] = r[pc]
                    rows.append(row_data)

    if not rows:
        detail = "\n".join(errors[:25])
        if rate_limit_hit:
            detail = "⚠️ BẠN ĐÃ ĐẠT GIỚI HẠN API RATE-LIMIT CỦA VNSTOCK GUEST MODE (20 requests/phút).\n\n💡 GIẢI PHÁP KHẮC PHÚC:\n1. Hãy cài đặt số lượng 'Tối đa số công ty xử lý' = 15 hoặc 20.\n2. Hoặc mở mục 'Cấu hình API Key' trong App và nhập API Key miễn phí từ https://vnstocks.com/login để tăng tốc!"
        raise RuntimeError("Khong lay duoc du lieu nao phu hop.\n\nChi tiet:\n" + detail)

    result_df = pd.DataFrame(rows)

    fixed_cols = ["Mã cổ phiếu", "Tên công ty", "Chỉ tiêu"]
    period_columns = [c for c in result_df.columns if c not in fixed_cols]
    
    try:
        period_columns_sorted = sorted(period_columns, key=lambda x: (re.sub(r"[^0-9\-]", "", str(x))), reverse=True)
    except Exception:
        period_columns_sorted = sorted(period_columns, reverse=True)

    result_df = result_df[fixed_cols + period_columns_sorted]

    if period_columns_sorted:
        latest_col = period_columns_sorted[0]
        try:
            result_df["_sort_val"] = pd.to_numeric(result_df[latest_col], errors="coerce").fillna(-1e18)
            result_df = result_df.sort_values(by="_sort_val", ascending=False).drop(columns=["_sort_val"])
        except Exception:
            pass

    if progress_cb:
        msg_suffix = " (Đã chuẩn hóa nhãn Quý & Lọc từ " + str(start_year) + " -> " + str(end_year) + ")" if (start_year or end_year) else ""
        progress_cb(f"Hoàn tất 100%! Đã tổng hợp {len(result_df)} dòng dữ liệu.{msg_suffix}", pct=100)

    return result_df


# ══════════════════════════════════════════════════════════════════
# ENGINE ĐỊNH GIÁ DOANH NGHIỆP - 6 PHƯƠNG PHÁP
# ══════════════════════════════════════════════════════════════════

def extract_financial_data(symbol, period="year"):
    """
    Tải BCTC từ vnstock API và trích xuất các chỉ tiêu cốt lõi cho định giá.
    Trả về dict các giá trị tài chính năm gần nhất.
    """
    from vnstock import Fundamental

    fund = Fundamental()
    eq = fund.equity(symbol)

    data = {
        "symbol": symbol,
        "revenue": 0, "cogs": 0, "gross_profit": 0,
        "ebit": 0, "net_income": 0, "interest_expense": 0,
        "total_assets": 0, "total_liabilities": 0, "equity_book": 0,
        "cash": 0, "short_term_debt": 0, "long_term_debt": 0,
        "total_debt": 0, "depreciation": 0, "capex": 0,
        "cfo": 0, "dividend_per_share": 0,
        "shares_outstanding": 0, "market_price": 0,
    }

    def _find_value(df, keywords, period_col=None):
        """Tìm giá trị trong DataFrame BCTC theo từ khóa."""
        if df is None or len(df) == 0:
            return 0
        item_col = None
        for c in df.columns:
            if normalize_text(c) == "item":
                item_col = c
                break
        if item_col is None:
            for c in df.columns:
                if df[c].dtype == object:
                    item_col = c
                    break
        if item_col is None:
            return 0

        non_meta_cols = [c for c in df.columns if normalize_text(c) not in _NON_PERIOD_COLS]
        if period_col and period_col in df.columns:
            val_col = period_col
        elif non_meta_cols:
            val_col = non_meta_cols[0]
        else:
            return 0

        for kw in keywords:
            nkw = normalize_text(kw)
            for _, row in df.iterrows():
                if nkw in normalize_text(str(row[item_col])):
                    v = row[val_col]
                    if pd.notna(v):
                        try:
                            return float(v)
                        except (ValueError, TypeError):
                            pass
        return 0

    # 1. Tải KQKD
    try:
        df_inc = eq.income_statement(period=period, lang='vi')
        if df_inc is None or len(df_inc) == 0:
            # Fallback sang nguồn VCI
            try:
                df_inc = eq.income_statement(period=period, source='VCI', lang='vi')
            except Exception:
                pass
        df_inc = fix_quarterly_column_headers(df_inc)

        non_meta = [c for c in df_inc.columns if normalize_text(c) not in _NON_PERIOD_COLS]
        latest_col = non_meta[0] if non_meta else None

        data["revenue"] = _find_value(df_inc, [
            "Doanh thu thuần về bán hàng và cung cấp dịch vụ",
            "3. Doanh thu thuần",
            "Doanh thu thuần"
        ], latest_col)
        data["cogs"] = abs(_find_value(df_inc, [
            "Giá vốn hàng bán", "4. Giá vốn"
        ], latest_col))
        data["gross_profit"] = _find_value(df_inc, [
            "Lợi nhuận gộp về bán hàng", "5. Lợi nhuận gộp", "Lợi nhuận gộp"
        ], latest_col)
        data["interest_expense"] = abs(_find_value(df_inc, [
            "Trong đó: Chi phí lãi vay", "Chi phí lãi vay",
            "of_which_interest_expense"
        ], latest_col))
        data["net_income"] = _find_value(df_inc, [
            "Lợi nhuận sau thuế thu nhập doanh nghiệp",
            "15. Lợi nhuận sau thuế",
            "Lợi nhuận sau thuế",
            "LNST"
        ], latest_col)

        pbt = _find_value(df_inc, [
            "Tổng lợi nhuận kế toán trước thuế",
            "14. Tổng lợi nhuận",
            "Lợi nhuận trước thuế"
        ], latest_col)
        data["ebit"] = pbt + data["interest_expense"] if pbt != 0 else (data["net_income"] * 1.25 + data["interest_expense"])

    except Exception as e:
        print(f"Lỗi tải KQKD {symbol}: {e}")

    # 2. Tải CĐKT (với fallback nguồn VCI nếu TCBS trả về rỗng)
    try:
        df_bs = eq.balance_sheet(period=period, lang='vi')
        if df_bs is None or len(df_bs) == 0:
            try:
                df_bs = eq.balance_sheet(period=period, source='VCI', lang='vi')
            except Exception:
                pass
        df_bs = fix_quarterly_column_headers(df_bs)
        non_meta = [c for c in df_bs.columns if normalize_text(c) not in _NON_PERIOD_COLS]
        latest_col = non_meta[0] if non_meta else None

        data["total_assets"] = _find_value(df_bs, [
            "TỔNG CỘNG TÀI SẢN", "Tổng cộng tài sản", "Tài sản"
        ], latest_col)
        data["total_liabilities"] = _find_value(df_bs, [
            "NỢ PHẢI TRẢ", "Nợ phải trả"
        ], latest_col)
        data["equity_book"] = _find_value(df_bs, [
            "VỐN CHỦ SỞ HỮU", "Vốn chủ sở hữu"
        ], latest_col)
        
        # Nếu thiếu VCSH nhưng có Tài sản và Nợ phải trả
        if data["equity_book"] == 0 and data["total_assets"] > 0:
            data["equity_book"] = max(0, data["total_assets"] - data["total_liabilities"])

        data["cash"] = _find_value(df_bs, [
            "Tiền và các khoản tương đương tiền",
            "I. Tiền và các khoản tương đương tiền",
            "Tiền"
        ], latest_col)
        data["short_term_debt"] = _find_value(df_bs, [
            "Vay và nợ thuê tài chính ngắn hạn",
            "Vay ngắn hạn"
        ], latest_col)
        data["long_term_debt"] = _find_value(df_bs, [
            "Vay và nợ thuê tài chính dài hạn",
            "Vay dài hạn"
        ], latest_col)
        data["total_debt"] = data["short_term_debt"] + data["long_term_debt"]

    except Exception as e:
        print(f"Lỗi tải CĐKT {symbol}: {e}")

    try:
        df_cf = eq.cash_flow(period=period, lang='vi')
        df_cf = fix_quarterly_column_headers(df_cf)
        non_meta = [c for c in df_cf.columns if normalize_text(c) not in _NON_PERIOD_COLS]
        latest_col = non_meta[0] if non_meta else None

        data["depreciation"] = abs(_find_value(df_cf, [
            "Khấu hao TSCĐ", "Khấu hao tài sản cố định",
            "Chi phí khấu hao"
        ], latest_col))
        data["capex"] = abs(_find_value(df_cf, [
            "Tiền chi để mua sắm, xây dựng TSCĐ",
            "Mua sắm TSCĐ"
        ], latest_col))
        data["cfo"] = _find_value(df_cf, [
            "Lưu chuyển tiền thuần từ hoạt động kinh doanh"
        ], latest_col)

    except Exception as e:
        print(f"Lỗi tải LCTT {symbol}: {e}")

    try:
        from vnstock import Reference
        info = Reference().company(symbol).info()
        if info is not None and len(info) > 0:
            for c in info.columns:
                nc = normalize_text(c)
                if "outstanding" in nc or "luu hanh" in nc or "co phieu" in nc:
                    val = info.iloc[0][c]
                    if pd.notna(val):
                        try:
                            shares = float(val)
                            if shares > 0:
                                data["shares_outstanding"] = shares
                        except Exception:
                            pass
    except Exception:
        pass

    if data["shares_outstanding"] == 0 and data["equity_book"] > 0:
        data["shares_outstanding"] = data["equity_book"] / 10000

    data["ebitda"] = data["ebit"] + data["depreciation"]
    data["delta_nwc"] = 0

    # Lấy giá thị trường hiện tại
    try:
        from vnstock import Market
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=10)
        df_price = Market().equity(symbol).ohlcv(
            start=start_dt.strftime("%Y-%m-%d"),
            end=end_dt.strftime("%Y-%m-%d")
        )
        if df_price is not None and len(df_price) > 0:
            close_col = None
            for c in df_price.columns:
                if "close" in str(c).lower():
                    close_col = c
                    break
            if close_col:
                p_val = float(df_price[close_col].iloc[-1])
                if 0 < p_val < 1000:
                    p_val *= 1000.0  # Chuyển từ nghìn VNĐ sang VNĐ
                data["market_price"] = p_val
    except Exception:
        pass

    return data


class ValuationEngine:
    """Engine tính toán 6 phương pháp định giá doanh nghiệp."""

    def __init__(self, fin_data, assumptions):
        self.fin = fin_data
        self.asm = assumptions
        self.results = {}

    def calc_all(self):
        """Tính toán tất cả 7 phương pháp định giá."""
        self.results = {}
        self.results["nav"] = self.calc_nav()
        self.results["pe"] = self.calc_pe()
        self.results["pb"] = self.calc_pb()
        self.results["ev_ebitda"] = self.calc_ev_ebitda()
        self.results["fcff"] = self.calc_fcff()
        self.results["fcfe"] = self.calc_fcfe()
        self.results["ddm"] = self.calc_ddm()
        self.results["summary"] = self.calc_weighted_summary()
        return self.results

    def calc_nav(self):
        adj = self.asm.get("nav_adjustment", 0)
        equity_val = self.fin["total_assets"] + adj - self.fin["total_liabilities"]
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0
        return {"method": "1. Tài sản thuần (NAV)", "ev": None, "equity": equity_val, "per_share": per_share}

    def calc_pe(self):
        pe_ratio = self.asm.get("pe_ratio", 15.0)
        ni = self.fin["net_income"]
        equity_val = ni * pe_ratio
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0
        return {"method": "2. Tỷ số P/E", "ev": None, "equity": equity_val, "per_share": per_share, "pe_used": pe_ratio}

    def calc_pb(self):
        pb_ratio = self.asm.get("pb_ratio", 2.5)
        bv = self.fin["equity_book"]
        equity_val = bv * pb_ratio
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0
        return {"method": "3. Tỷ số P/B", "ev": None, "equity": equity_val, "per_share": per_share, "pb_used": pb_ratio}

    def calc_ev_ebitda(self):
        ev_ebitda_ratio = self.asm.get("ev_ebitda_ratio", 10.0)
        ebitda = self.fin["ebitda"]
        ev = ebitda * ev_ebitda_ratio
        equity_val = ev - self.fin["total_debt"] + self.fin["cash"]
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0
        return {"method": "4. EV/EBITDA", "ev": ev, "equity": equity_val, "per_share": per_share}

    def _calc_ke(self):
        rf = self.asm.get("rf", 0.035)
        beta = self.asm.get("beta", 0.8)
        erp = self.asm.get("erp", 0.07)
        return rf + beta * erp

    def _calc_wacc(self):
        ke = self._calc_ke()
        kd = self.asm.get("kd", 0.08)
        tax = self.asm.get("tax_rate", 0.20)
        e_val = max(self.fin["equity_book"], 1)
        d_val = self.fin["total_debt"]
        total = e_val + d_val
        if total == 0:
            return ke
        return (e_val / total) * ke + (d_val / total) * kd * (1 - tax)

    def calc_fcff(self, wacc_override=None, g_override=None):
        wacc = wacc_override if wacc_override else self._calc_wacc()
        g = g_override if g_override else self.asm.get("g", 0.03)
        years = self.asm.get("forecast_years", 5)
        tax = self.asm.get("tax_rate", 0.20)
        growth = self.asm.get("revenue_growth", 0.05)

        ebit = self.fin["ebit"]
        da = self.fin["depreciation"]
        capex = self.fin["capex"]
        delta_nwc = self.fin.get("delta_nwc", 0)

        fcff_base = ebit * (1 - tax) + da - capex - delta_nwc
        if fcff_base <= 0:
            fcff_base = self.fin["cfo"] if self.fin["cfo"] > 0 else abs(self.fin["net_income"] * 0.8)

        if wacc <= g:
            return {"method": "5. FCFF (DCF)", "ev": None, "equity": None, "per_share": None,
                    "error": f"WACC ({wacc:.1%}) ≤ g ({g:.1%})", "wacc": wacc, "fcff_base": fcff_base}

        pv_fcff = 0
        for t in range(1, years + 1):
            fcff_t = fcff_base * (1 + growth) ** t
            pv_fcff += fcff_t / (1 + wacc) ** t

        fcff_terminal = fcff_base * (1 + growth) ** years * (1 + g)
        tv = fcff_terminal / (wacc - g)
        pv_tv = tv / (1 + wacc) ** years

        ev = pv_fcff + pv_tv
        equity_val = ev - self.fin["total_debt"] + self.fin["cash"]
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0
        tv_pct = pv_tv / ev * 100 if ev > 0 else 0

        return {"method": "5. FCFF (DCF)", "ev": ev, "equity": equity_val, "per_share": per_share,
                "wacc": wacc, "ke": self._calc_ke(), "fcff_base": fcff_base, "tv_pct": tv_pct}

    def calc_ddm(self):
        ke = self._calc_ke()
        g = self.asm.get("g_dividend", self.asm.get("g", 0.03))
        dps = self.asm.get("dividend_per_share", 0)
        shares = self.fin["shares_outstanding"]

        if dps <= 0:
            ni = self.fin["net_income"]
            payout = self.asm.get("payout_ratio", 0.5)
            if ni > 0 and shares > 0:
                dps = (ni * payout) / shares
            else:
                return {"method": "7. DDM (Cổ tức)", "ev": None, "equity": None, "per_share": None,
                        "note": "Không áp dụng (LNST ≤ 0 hoặc thiếu dữ liệu cổ tức)"}

        if ke <= g:
            return {"method": "7. DDM (Cổ tức)", "ev": None, "equity": None, "per_share": None,
                    "error": f"Ke ({ke:.1%}) ≤ g ({g:.1%})"}

        p0 = dps * (1 + g) / (ke - g)
        equity_val = p0 * shares
        return {"method": "7. DDM (Cổ tức)", "ev": None, "equity": equity_val, "per_share": p0}

    def calc_fcfe(self, ke_override=None, g_override=None):
        """Phương pháp 6: FCFE — Dòng tiền thuần Vốn chủ sở hữu chiết khấu."""
        ke = ke_override if ke_override else self._calc_ke()
        g = g_override if g_override else self.asm.get("g", 0.03)
        years = self.asm.get("forecast_years", 5)
        growth = self.asm.get("revenue_growth", 0.05)

        ni = self.fin["net_income"]
        da = self.fin["depreciation"]
        capex = self.fin["capex"]
        delta_nwc = self.fin.get("delta_nwc", 0)
        # Net borrowing giả định = Nợ vay × tỷ lệ tăng trưởng (cấu trúc vốn ổn định)
        net_borrowing = self.fin["total_debt"] * growth

        fcfe_base = ni + da - capex - delta_nwc + net_borrowing
        if fcfe_base <= 0:
            fcfe_base = ni * 0.7 if ni > 0 else abs(self.fin.get("cfo", 1) * 0.5)

        if ke <= g:
            return {"method": "6. FCFE (Vốn CSH)", "ev": None, "equity": None, "per_share": None,
                    "error": f"Ke ({ke:.1%}) ≤ g ({g:.1%})", "ke": ke, "fcfe_base": fcfe_base}

        pv_fcfe = 0
        for t in range(1, years + 1):
            fcfe_t = fcfe_base * (1 + growth) ** t
            pv_fcfe += fcfe_t / (1 + ke) ** t

        fcfe_terminal = fcfe_base * (1 + growth) ** years * (1 + g)
        tv = fcfe_terminal / (ke - g)
        pv_tv = tv / (1 + ke) ** years

        equity_val = pv_fcfe + pv_tv
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0
        tv_pct = pv_tv / equity_val * 100 if equity_val > 0 else 0

        return {"method": "6. FCFE (Vốn CSH)", "ev": None, "equity": equity_val, "per_share": per_share,
                "ke": ke, "fcfe_base": fcfe_base, "tv_pct": tv_pct}

    def calc_weighted_summary(self):
        weights = {"nav": 0.10, "pe": 0.20, "pb": 0.10, "ev_ebitda": 0.10, "fcff": 0.20, "fcfe": 0.15, "ddm": 0.15}
        total_weight = 0
        weighted_equity = 0
        weighted_ps = 0

        for key, w in weights.items():
            r = self.results.get(key, {})
            eq_val = r.get("equity")
            ps_val = r.get("per_share")
            if eq_val is not None and ps_val is not None and eq_val > 0:
                weighted_equity += eq_val * w
                weighted_ps += ps_val * w
                total_weight += w

        if total_weight > 0:
            weighted_equity /= total_weight
            weighted_ps /= total_weight

        return {"method": "GIÁ TRỊ TỔNG HỢP", "ev": None, "equity": weighted_equity,
                "per_share": weighted_ps, "total_weight": total_weight}

    def sensitivity_matrix(self, wacc_steps=None, g_steps=None):
        if wacc_steps is None:
            base_wacc = self._calc_wacc()
            wacc_steps = [base_wacc - 0.02, base_wacc - 0.01, base_wacc, base_wacc + 0.01, base_wacc + 0.02]
        if g_steps is None:
            base_g = self.asm.get("g", 0.03)
            g_steps = [base_g - 0.01, base_g - 0.005, base_g, base_g + 0.005, base_g + 0.01]

        matrix = []
        for w in wacc_steps:
            row = {"wacc": w}
            for g in g_steps:
                r = self.calc_fcff(wacc_override=w, g_override=g)
                ps = r.get("per_share")
                row[f"g_{g:.1%}"] = ps if ps is not None else "N/A"
            matrix.append(row)
        return matrix, wacc_steps, g_steps

    def sensitivity_matrix_fcfe(self, ke_steps=None, g_steps=None):
        """Ma trận độ nhạy Ke vs g cho phương pháp FCFE."""
        if ke_steps is None:
            base_ke = self._calc_ke()
            ke_steps = [base_ke - 0.02, base_ke - 0.01, base_ke, base_ke + 0.01, base_ke + 0.02]
        if g_steps is None:
            base_g = self.asm.get("g", 0.03)
            g_steps = [base_g - 0.01, base_g - 0.005, base_g, base_g + 0.005, base_g + 0.01]

        matrix = []
        for ke_val in ke_steps:
            row = {"ke": ke_val}
            for g_val in g_steps:
                r = self.calc_fcfe(ke_override=ke_val, g_override=g_val)
                ps = r.get("per_share")
                row[f"g_{g_val:.1%}"] = ps if ps is not None else "N/A"
            matrix.append(row)
        return matrix, ke_steps, g_steps


class VnstockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x920")
        self.minsize(1000, 720)

        self.current_df = None
        self.sort_column = None
        self.sort_descending = True

        self._build_header()
        self._build_ui()

        if not check_vnstock_installed():
            messagebox.showwarning(
                "Chưa có thư viện vnstock",
                "Chưa tìm thấy thư viện 'vnstock' trong máy.\n\n"
                "Hãy mở CMD và gõ: pip install -U vnstock"
            )

    def _build_header(self):
        header_frame = tk.Frame(self, background="#0F172A", padx=8, pady=8)
        header_frame.pack(side=tk.TOP, fill=tk.X)

        self.logo_img = None
        if os.path.exists(LOGO_PATH):
            try:
                raw_img = Image.open(LOGO_PATH)
                resized_img = raw_img.resize((52, 48), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(resized_img)
                lbl_logo = tk.Label(header_frame, image=self.logo_img, background="#0F172A")
                lbl_logo.pack(side=tk.LEFT, padx=(8, 12))
            except Exception as e:
                print("Lỗi tải logo KTT.jpg:", e)

        lbl_title = tk.Label(
            header_frame,
            text="VNSTOCK APP v3.8 — HỆ THỐNG TRUY XUẤT & PHÂN TÍCH BÁO CÁO TÀI CHÍNH",
            font=("Segoe UI", 12, "bold"),
            foreground="#F8FAFC",
            background="#0F172A"
        )
        lbl_title.pack(side=tk.LEFT, pady=4)

        lbl_sub = tk.Label(
            header_frame,
            text="Phân tích Doanh nghiệp & Ngành Chứng khoán Việt Nam | KTT Logo",
            font=("Segoe UI", 9, "italic"),
            foreground="#94A3B8",
            background="#0F172A"
        )
        lbl_sub.pack(side=tk.RIGHT, padx=12)

    def _setup_custom_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        font_main = ("Segoe UI", 9)
        font_bold = ("Segoe UI", 9, "bold")
        font_header = ("Segoe UI", 9, "bold")

        # Treeview styling
        style.configure("Treeview.Heading", font=font_header, background="#1E293B", foreground="#F8FAFC", padding=6)
        style.map("Treeview.Heading", background=[("active", "#334155")])
        style.configure("Treeview", font=font_main, rowheight=26, gridcolor="#CBD5E1")
        style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", "#1E3A8A")])

        # Notebook Tab Styling
        style.configure("TNotebook", background="#0F172A", padding=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[14, 8], background="#1E293B", foreground="#94A3B8")
        style.map("TNotebook.Tab", background=[("selected", "#2563EB"), ("active", "#334155")], foreground=[("selected", "#FFFFFF"), ("active", "#F8FAFC")])

        # Accent Button
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), background="#2563EB", foreground="#FFFFFF", padding=[12, 6])
        style.map("Accent.TButton", background=[("active", "#1D4ED8")])

        # Secondary Button
        style.configure("Secondary.TButton", font=("Segoe UI", 9), background="#64748B", foreground="#FFFFFF", padding=[10, 5])
        style.map("Secondary.TButton", background=[("active", "#475569")])

        # Labelframe Style
        style.configure("TLabelframe", background="#F8FAFC", relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"), foreground="#1E40AF", background="#F8FAFC")

    def _build_ui(self):
        self._setup_custom_styles()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        tab1 = ttk.Frame(self.notebook)
        tab2 = ttk.Frame(self.notebook)
        tab3 = ttk.Frame(self.notebook)
        tab4 = ttk.Frame(self.notebook)
        tab5 = ttk.Frame(self.notebook)
        self.notebook.add(tab1, text=" Tra cứu 1 mã cổ phiếu ")
        self.notebook.add(tab2, text=" Thống kê theo ngành ")
        self.notebook.add(tab3, text=" ⚙️ Cấu hình API Key (Miễn phí) ")
        self.notebook.add(tab4, text=" 📊 Định giá Doanh nghiệp (7 PP) ")
        self.notebook.add(tab5, text=" 📘 Công thức & Thuyết minh ")

        self._build_tab_single(tab1)
        self._build_tab_industry(tab2)
        self._build_tab_config(tab3)
        self._build_tab_valuation(tab4)
        self._build_tab_explanation(tab5)

        # Container cho bảng tra cứu chung (dùng cho Tab 1 & Tab 2)
        self.main_table_container = ttk.Frame(self)
        self.main_table_container.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        status_frame = ttk.Frame(self.main_table_container, padding=(10, 4))
        status_frame.pack(side=tk.TOP, fill=tk.X)

        self.status_var = tk.StringVar(value="Sẵn sàng.")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="#1D4ED8", font=("Segoe UI", 9, "bold"))
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate", length=280)
        self.progress_bar.pack(side=tk.RIGHT, padx=4)

        tool_bar = ttk.Frame(self.main_table_container, padding=(10, 6))
        tool_bar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(tool_bar, text="🔍 Lọc số liệu bảng:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(tool_bar, textvariable=self.filter_var, width=28)
        self.filter_entry.pack(side=tk.LEFT, padx=4)
        self.filter_entry.bind("<KeyRelease>", self._on_filter_changed)

        ttk.Label(tool_bar, text="💰 Đơn vị số liệu:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(20, 4))
        self.unit_var = tk.StringVar(value="Nguyên tệ")
        self.unit_combo = ttk.Combobox(
            tool_bar, textvariable=self.unit_var,
            values=["Nguyên tệ", "Tỷ VNĐ", "Triệu VNĐ"],
            width=14, state="readonly"
        )
        self.unit_combo.pack(side=tk.LEFT, padx=4)
        self.unit_combo.bind("<<ComboboxSelected>>", self._on_unit_changed)

        ttk.Label(tool_bar, text="💡 Bấm vào Tiêu đề cột để Sắp xếp (Sort: Tăng/Giảm)", foreground="#16A34A", font=("Segoe UI", 8, "italic")).pack(side=tk.LEFT, padx=12)

        table_frame = ttk.Frame(self.main_table_container, padding=10)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, show="headings")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        export_frame = ttk.Frame(self.main_table_container, padding=10)
        export_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(export_frame, text="📥 Xuất ra Excel (.xlsx)", command=self.export_excel).pack(side=tk.LEFT, padx=4)
        ttk.Button(export_frame, text="📥 Xuất ra CSV", command=self.export_csv).pack(side=tk.LEFT, padx=4)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event):
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab in (0, 1):
            self.main_table_container.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        else:
            self.main_table_container.pack_forget()

    def _build_tab_single(self, parent):
        top = ttk.Frame(parent, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)

        f_row1 = ttk.Frame(top)
        f_row1.pack(side=tk.TOP, fill=tk.X, pady=4)

        ttk.Label(f_row1, text="Mã cổ phiếu:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.symbol_var = tk.StringVar(value="DHG")
        ttk.Entry(f_row1, textvariable=self.symbol_var, width=10).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(f_row1, text="Kỳ báo cáo:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.period_var = tk.StringVar(value="year")
        ttk.Combobox(
            f_row1, textvariable=self.period_var, values=["year", "quarter"],
            width=8, state="readonly"
        ).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(f_row1, text="📅 TỪ NĂM:", font=("Segoe UI", 9, "bold"), foreground="#1D4ED8").pack(side=tk.LEFT, padx=(0, 4))
        self.t1_start_year_var = tk.StringVar(value="2020")
        combo_sy = ttk.Combobox(f_row1, textvariable=self.t1_start_year_var, values=YEAR_LIST, width=8)
        combo_sy.pack(side=tk.LEFT, padx=(0, 12))
        combo_sy.bind("<<ComboboxSelected>>", self._sync_tab1_years_to_dates)

        ttk.Label(f_row1, text="📅 ĐẾN NĂM:", font=("Segoe UI", 9, "bold"), foreground="#1D4ED8").pack(side=tk.LEFT, padx=(0, 4))
        self.t1_end_year_var = tk.StringVar(value="2026")
        combo_ey = ttk.Combobox(f_row1, textvariable=self.t1_end_year_var, values=YEAR_LIST, width=8)
        combo_ey.pack(side=tk.LEFT, padx=(0, 16))
        combo_ey.bind("<<ComboboxSelected>>", self._sync_tab1_years_to_dates)

        f_row2 = ttk.Frame(top)
        f_row2.pack(side=tk.TOP, fill=tk.X, pady=4)

        ttk.Label(f_row2, text="Từ ngày (Cho Giá lịch sử):").pack(side=tk.LEFT, padx=(0, 4))
        self.start_var = tk.StringVar(value="2020-01-01")
        ttk.Entry(f_row2, textvariable=self.start_var, width=13).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(f_row2, text="Đến ngày (Cho Giá lịch sử):").pack(side=tk.LEFT, padx=(0, 4))
        self.end_var = tk.StringVar(value="2026-12-31")
        ttk.Entry(f_row2, textvariable=self.end_var, width=13).pack(side=tk.LEFT, padx=(0, 16))

        btn_frame = ttk.Frame(parent, padding=(10, 4, 10, 10))
        btn_frame.pack(side=tk.TOP, fill=tk.X)

        buttons = [
            ("📈 Giá lịch sử (OHLCV)", self.action_price_history),
            ("🏢 Thông tin công ty", self.action_company_info),
            ("📑 Bảng cân đối kế toán", self.action_balance_sheet),
            ("📊 Kết quả kinh doanh", self.action_income_statement),
            ("💰 Lưu chuyển tiền tệ", self.action_cash_flow),
            ("🎯 Chỉ số tài chính", self.action_ratio),
        ]
        for i, (text, cmd) in enumerate(buttons):
            b = ttk.Button(btn_frame, text=text, command=cmd)
            b.grid(row=i // 3, column=i % 3, sticky="ew", padx=4, pady=4)
        for c in range(3):
            btn_frame.columnconfigure(c, weight=1)

    def _sync_tab1_years_to_dates(self, event=None):
        sy = self.t1_start_year_var.get().strip()
        ey = self.t1_end_year_var.get().strip()
        if len(sy) == 4:
            self.start_var.set(f"{sy}-01-01")
        if len(ey) == 4:
            self.end_var.set(f"{ey}-12-31")

    def _build_tab_industry(self, parent):
        top = ttk.Frame(parent, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Ngành nghề (Chọn từ danh sách hoặc gõ tự do):", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", padx=4, pady=6
        )
        self.industry_var = tk.StringVar(value="Chăm sóc sức khỏe (Dược phẩm & Y tế)")
        combo_ind = ttk.Combobox(top, textvariable=self.industry_var, values=DROPDOWN_SECTOR_LIST, width=42)
        combo_ind.grid(row=0, column=1, columnspan=2, sticky="w", padx=4, pady=6)

        ttk.Label(top, text="Chỉ tiêu cần lấy (Check chọn nhiều từ Dropdown hoặc gõ tự do):", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky="w", padx=4, pady=6
        )
        
        metric_frame = ttk.Frame(top)
        metric_frame.grid(row=1, column=1, columnspan=3, sticky="w", padx=4, pady=6)

        self.metrics_var = tk.StringVar(value="Doanh thu thuần, Lợi nhuận sau thuế")
        self.metrics_entry = ttk.Entry(metric_frame, textvariable=self.metrics_var, width=45)
        self.metrics_entry.pack(side=tk.LEFT, padx=(0, 6))

        self.mb_metrics = tk.Menubutton(metric_frame, text="☑ Stick Chọn Chỉ Tiêu ▾", relief="raised", background="#E2E8F0", font=("Segoe UI", 9, "bold"))
        self.mb_metrics.pack(side=tk.LEFT)
        
        self.metric_menu = tk.Menu(self.mb_metrics, tearoff=False)
        self.mb_metrics["menu"] = self.metric_menu

        self.metric_checkbox_vars = {}
        for m_name in PRESET_METRICS:
            is_default = m_name in ["Doanh thu thuần", "Lợi nhuận sau thuế"]
            var = tk.BooleanVar(value=is_default)
            self.metric_checkbox_vars[m_name] = var
            self.metric_menu.add_checkbutton(
                label=m_name, variable=var,
                command=self._on_metric_checkbox_toggled
            )

        ttk.Label(top, text="Kỳ báo cáo & Khoảng năm:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", padx=4, pady=6)
        
        period_frame = ttk.Frame(top)
        period_frame.grid(row=2, column=1, columnspan=3, sticky="w", padx=4, pady=6)

        self.industry_period_var = tk.StringVar(value="year")
        ttk.Combobox(
            period_frame, textvariable=self.industry_period_var, values=["year", "quarter"],
            width=8, state="readonly"
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(period_frame, text="📅 Từ năm:", font=("Segoe UI", 9, "bold"), foreground="#1D4ED8").pack(side=tk.LEFT, padx=(0, 4))
        self.start_year_var = tk.StringVar(value="2020")
        ttk.Combobox(period_frame, textvariable=self.start_year_var, values=YEAR_LIST, width=8).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(period_frame, text="📅 Đến năm:", font=("Segoe UI", 9, "bold"), foreground="#1D4ED8").pack(side=tk.LEFT, padx=(0, 4))
        self.end_year_var = tk.StringVar(value="2026")
        ttk.Combobox(period_frame, textvariable=self.end_year_var, values=YEAR_LIST, width=8).pack(side=tk.LEFT, padx=(0, 14))

        ttk.Label(period_frame, text="Tối đa số công ty:").pack(side=tk.LEFT, padx=(0, 4))
        self.max_companies_var = tk.StringVar(value="15")
        ttk.Entry(period_frame, textvariable=self.max_companies_var, width=6).pack(side=tk.LEFT)

        note = (
            "✨ v3.8: Nhãn kỳ báo cáo giữ nguyên từ API TCBS. Tự động loại bỏ cột trùng lặp.\n"
            "⚠️ Lưu ý: Bản Community giới hạn tối đa 8 kỳ/quý. Nhập API Key (Tab 3) để mở rộng.\n"
            "Tích hợp Logo KTT & Tính năng SORT SỐ LIỆU (Bấm tiêu đề cột để Sắp xếp Tăng/Giảm)."
        )
        ttk.Label(top, text=note, foreground="#15803D", justify="left").grid(
            row=3, column=0, columnspan=4, sticky="w", padx=4, pady=(6, 4)
        )

        btn_frame = ttk.Frame(parent, padding=(10, 0, 10, 10))
        btn_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(
            btn_frame, text="⚡ XUẤT BÁO CÁO THỐNG KÊ THEO NGÀNH (CHUẨN HÓA KỲ BÁO CÁO)", command=self.action_industry_stats
        ).pack(side=tk.LEFT, padx=4, pady=4)

    def _build_tab_config(self, parent):
        top = ttk.Frame(parent, padding=16)
        top.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        ttk.Label(top, text="🔑 CẤU HÌNH API KEY MIỄN PHÍ VNSOCK", font=("Segoe UI", 11, "bold"), foreground="#1D4ED8").pack(anchor="w", pady=(0, 8))
        
        desc = (
            "Mặc định vnstock chạy ở chế độ Guest (giới hạn 20 request/phút).\n"
            "Để tăng tốc độ tải báo cáo tài chính lên 60 - 600 request/phút và không bao giờ bị nghẽn rate-limit:\n"
            "1. Đăng ký tài khoản miễn phí tại: https://vnstocks.com/login\n"
            "2. Đăng nhập và lấy API Key cá nhân của bạn tại https://vnstocks.com/settings\n"
            "3. Dán API Key vào ô dưới đây và bấm 'Lưu cấu hình API Key'."
        )
        ttk.Label(top, text=desc, justify="left", font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 12))

        f_key = ttk.Frame(top)
        f_key.pack(anchor="w", fill=tk.X, pady=4)

        ttk.Label(f_key, text="API Key của bạn:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.api_key_var = tk.StringVar()
        ttk.Entry(f_key, textvariable=self.api_key_var, width=45).pack(side=tk.LEFT, padx=4)

        ttk.Button(f_key, text="💾 Lưu cấu hình API Key", command=self.save_api_key).pack(side=tk.LEFT, padx=8)

        self.lbl_key_status = ttk.Label(top, text="", font=("Segoe UI", 9, "italic"))
        self.lbl_key_status.pack(anchor="w", pady=6)

        self.load_api_key()

    def load_api_key(self):
        key_file = os.path.expanduser("~/.vnstock/api_key.json")
        if os.path.exists(key_file):
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    key = data.get("api_key", "")
                    if key:
                        self.api_key_var.set(key)
                        self.lbl_key_status.config(text="✓ Đã nhận diện API Key trong máy! Giới hạn API đã được nâng cấp.", foreground="#16A34A")
            except Exception:
                pass

    def save_api_key(self):
        key = self.api_key_var.get().strip()
        if not key:
            messagebox.showwarning("Cảnh báo", "Bạn chưa nhập API Key.")
            return
        try:
            folder = os.path.expanduser("~/.vnstock")
            os.makedirs(folder, exist_ok=True)
            key_file = os.path.join(folder, "api_key.json")
            with open(key_file, "w", encoding="utf-8") as f:
                json.dump({"api_key": key}, f)
            
            try:
                from vnstock.core import setup_api_key
                setup_api_key(key)
            except Exception:
                pass

            messagebox.showinfo("Thành công", f"Đã lưu API Key thành công vào:\n{key_file}\n\nHệ thống đã sẵn sàng cho tốc độ cao!")
            self.lbl_key_status.config(text="✓ Đã lưu và kích hoạt API Key thành công!", foreground="#16A34A")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không lưu được API Key: {e}")

    # ══════════════════════════════════════════════════════════════
    # TAB 4: ĐỊNH GIÁ DOANH NGHIỆP (6 PHƯƠNG PHÁP) + SLIDER GIẢ LẬP
    # ══════════════════════════════════════════════════════════════

    def _build_tab_valuation(self, parent):
        self.val_fin_data = None
        self.val_engine = None

        # Scrollable canvas
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _on_canvas_configure)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        main = scroll_frame

        # --- HEADER ---
        ttk.Label(main, text="📊 ĐỊNH GIÁ DOANH NGHIỆP — 7 PHƯƠNG PHÁP + MÔ HÌNH GIẢ LẬP TƯƠNG TÁC",
                  font=("Segoe UI", 12, "bold"), foreground="#1D4ED8").grid(
            row=0, column=0, columnspan=6, sticky="w", padx=10, pady=(10, 4))

        ttk.Label(main, text="Kéo thanh trượt (Slider) để thay đổi giả định → KPI tự động cập nhật real-time",
                  font=("Segoe UI", 9, "italic"), foreground="#16A34A").grid(
            row=1, column=0, columnspan=6, sticky="w", padx=10, pady=(0, 8))

        # --- ROW 1: MÃ CK + NÚT TẢI ---
        f_input = ttk.Frame(main)
        f_input.grid(row=2, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        ttk.Label(f_input, text="Mã cổ phiếu:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.val_symbol_var = tk.StringVar(value="DHG")
        ttk.Entry(f_input, textvariable=self.val_symbol_var, width=10).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(f_input, text="⚡ TẢI BCTC & TÍNH TOÁN", command=self.action_load_valuation).pack(side=tk.LEFT, padx=4)
        ttk.Button(f_input, text="🔄 Reset giả định", command=self._reset_valuation_sliders).pack(side=tk.LEFT, padx=4)

        self.val_status_var = tk.StringVar(value="Chưa tải dữ liệu.")
        ttk.Label(f_input, textvariable=self.val_status_var, foreground="#DC2626", font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT, padx=12)

        # --- ROW 1.5: KPI METRIC CARDS (EXECUTIVE DASHBOARD) ---
        kpi_frame = ttk.Frame(main)
        kpi_frame.grid(row=3, column=0, columnspan=6, sticky="ew", padx=10, pady=6)

        # Card 1: Fair Value
        card1 = tk.Frame(kpi_frame, background="#EFF6FF", highlightbackground="#93C5FD", highlightthickness=1, padx=12, pady=8)
        card1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(card1, text="⭐ GIÁ TRỊ HỢP LÝ / CP", font=("Segoe UI", 8, "bold"), foreground="#1E40AF", background="#EFF6FF").pack(anchor="w")
        self.lbl_kpi_fair_value = tk.Label(card1, text="— VNĐ", font=("Segoe UI", 13, "bold"), foreground="#1E3A8A", background="#EFF6FF")
        self.lbl_kpi_fair_value.pack(anchor="w", pady=(2, 0))

        # Card 2: Market Price
        card2 = tk.Frame(kpi_frame, background="#F8FAFC", highlightbackground="#CBD5E1", highlightthickness=1, padx=12, pady=8)
        card2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(card2, text="📈 GIÁ THỊ TRƯỜNG HIỆN TẠI", font=("Segoe UI", 8, "bold"), foreground="#475569", background="#F8FAFC").pack(anchor="w")
        self.lbl_kpi_market_price = tk.Label(card2, text="— VNĐ", font=("Segoe UI", 13, "bold"), foreground="#0F172A", background="#F8FAFC")
        self.lbl_kpi_market_price.pack(anchor="w", pady=(2, 0))

        # Card 3: Upside %
        card3 = tk.Frame(kpi_frame, background="#ECFDF5", highlightbackground="#6EE7B7", highlightthickness=1, padx=12, pady=8)
        card3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(card3, text="↕ UPSIDE / CHÊNH LỆCH", font=("Segoe UI", 8, "bold"), foreground="#065F46", background="#ECFDF5").pack(anchor="w")
        self.lbl_kpi_upside = tk.Label(card3, text="— %", font=("Segoe UI", 13, "bold"), foreground="#047857", background="#ECFDF5")
        self.lbl_kpi_upside.pack(anchor="w", pady=(2, 0))

        # Card 4: Recommendation
        card4 = tk.Frame(kpi_frame, background="#F0FDF4", highlightbackground="#86EFAC", highlightthickness=1, padx=12, pady=8)
        card4.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(card4, text="🎯 TRẠNG THÁI KHUYẾN NGHỊ", font=("Segoe UI", 8, "bold"), foreground="#166534", background="#F0FDF4").pack(anchor="w")
        self.lbl_kpi_rec = tk.Label(card4, text="CHƯA ĐỊNH GIÁ", font=("Segoe UI", 11, "bold"), foreground="#15803D", background="#F0FDF4")
        self.lbl_kpi_rec.pack(anchor="w", pady=(2, 0))

        # --- ROW 2: SỐ LIỆU TÀI CHÍNH TỰ ĐỘNG ---
        ttk.Label(main, text="═══ SỐ LIỆU TÀI CHÍNH CƠ SỞ (Tự động từ API) ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=4, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        self.val_info_labels = {}
        info_items = [
            ("Doanh thu thuần:", "revenue"), ("LNST:", "net_income"),
            ("EBIT:", "ebit"), ("EBITDA:", "ebitda"),
            ("Tổng Tài sản:", "total_assets"), ("Nợ phải trả:", "total_liabilities"),
            ("VCSH:", "equity_book"), ("Tiền mặt:", "cash"),
            ("Nợ vay:", "total_debt"), ("Khấu hao:", "depreciation"),
            ("CAPEX:", "capex"), ("CP lưu hành:", "shares_outstanding"),
            ("💰 Giá thị trường:", "market_price"),
        ]
        for i, (label_text, key) in enumerate(info_items):
            r = 5 + i // 4
            c = (i % 4) * 2
            ttk.Label(main, text=label_text, font=("Segoe UI", 8)).grid(row=r, column=c, sticky="e", padx=(10, 2), pady=1)
            lbl = ttk.Label(main, text="—", font=("Segoe UI", 8, "bold"), foreground="#1E40AF", width=18)
            lbl.grid(row=r, column=c + 1, sticky="w", padx=(0, 8), pady=1)
            self.val_info_labels[key] = lbl

        # --- SEPARATOR ---
        ttk.Separator(main, orient="horizontal").grid(row=9, column=0, columnspan=6, sticky="ew", padx=10, pady=6)

        # --- ROW 3: GIẢ ĐỊNH TƯƠNG TÁC (SLIDERS PHÂN NHÓM CARDS) ---
        ttk.Label(main, text="═══ MÔ HÌNH GIẢ LẬP — PHÂN NHÓM GIẢ ĐỊNH KÉO SLIDER ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=10, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        slider_card_frame = ttk.Frame(main)
        slider_card_frame.grid(row=11, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        # Sub-Card 1: Chi phí vốn WACC
        card_wacc = ttk.LabelFrame(slider_card_frame, text=" 🏦 CHI PHÍ VỐN (WACC & Ke) ", padding=8)
        card_wacc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        # Sub-Card 2: Tăng trưởng
        card_growth = ttk.LabelFrame(slider_card_frame, text=" 📈 TĂNG TRƯỞNG & DỰ BÁO ", padding=8)
        card_growth.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        # Sub-Card 3: Bội số
        card_multiples = ttk.LabelFrame(slider_card_frame, text=" 🏢 BỘI SỐ NGÀNH & CỔ TỨC ", padding=8)
        card_multiples.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self.val_sliders = {}

        def _add_slider(parent_card, label_text, key, from_, to_, default, resolution):
            f_sl = ttk.Frame(parent_card)
            f_sl.pack(side=tk.TOP, fill=tk.X, pady=3)

            ttk.Label(f_sl, text=label_text, font=("Segoe UI", 8), width=22, anchor="w").pack(side=tk.LEFT)

            var = tk.DoubleVar(value=default)
            slider = tk.Scale(
                f_sl, variable=var, from_=from_, to=to_, resolution=resolution,
                orient="horizontal", length=110, font=("Segoe UI", 7),
                command=lambda val, k=key: self._on_slider_changed(k, val)
            )
            slider.pack(side=tk.LEFT, padx=2)

            val_lbl = ttk.Label(f_sl, text=f"{default}", font=("Segoe UI", 8, "bold"), foreground="#DC2626", width=5)
            val_lbl.pack(side=tk.RIGHT, padx=2)

            self.val_sliders[key] = {"var": var, "slider": slider, "label": val_lbl}

        # Populate Group 1 (WACC)
        _add_slider(card_wacc, "Rf (Lãi suất phi rủi ro %)", "rf", 1.0, 8.0, 3.5, 0.1)
        _add_slider(card_wacc, "Beta (Hệ số rủi ro)", "beta", 0.3, 2.0, 0.8, 0.05)
        _add_slider(card_wacc, "ERP (Phần bù rủi ro %)", "erp", 4.0, 12.0, 7.0, 0.5)
        _add_slider(card_wacc, "Kd (Chi phí nợ vay %)", "kd", 3.0, 15.0, 8.0, 0.5)
        _add_slider(card_wacc, "Thuế suất TNDN %", "tax_rate", 0.0, 30.0, 20.0, 1.0)

        # Populate Group 2 (Growth)
        _add_slider(card_growth, "g (Tăng trưởng dài hạn %)", "g", 0.5, 6.0, 3.0, 0.25)
        _add_slider(card_growth, "Tăng trưởng DT ngắn hạn %", "revenue_growth", 0.0, 25.0, 5.0, 0.5)
        _add_slider(card_growth, "Số năm dự báo FCFF", "forecast_years", 3.0, 10.0, 5.0, 1.0)

        # Populate Group 3 (Multiples)
        _add_slider(card_multiples, "P/E ngành (lần)", "pe_ratio", 5.0, 40.0, 15.0, 0.5)
        _add_slider(card_multiples, "P/B ngành (lần)", "pb_ratio", 0.5, 6.0, 2.5, 0.1)
        _add_slider(card_multiples, "EV/EBITDA ngành (lần)", "ev_ebitda_ratio", 3.0, 25.0, 10.0, 0.5)
        _add_slider(card_multiples, "Tỷ lệ chi trả cổ tức %", "payout_ratio", 0.0, 100.0, 50.0, 5.0)

        # --- SEPARATOR ---
        ttk.Separator(main, orient="horizontal").grid(row=16, column=0, columnspan=6, sticky="ew", padx=10, pady=6)

        # --- ROW 4: BẢNG KẾT QUẢ 7 PHƯƠNG PHÁP ---
        ttk.Label(main, text="═══ KẾT QUẢ ĐỊNH GIÁ TỔNG HỢP — 7 PHƯƠNG PHÁP (Tỷ VNĐ) ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=17, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        tree_frame = ttk.Frame(main)
        tree_frame.grid(row=18, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        cols = ("method", "ev", "equity", "per_share", "upside", "note")
        self.val_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        self.val_tree.heading("method", text="Phương pháp Định giá")
        self.val_tree.heading("ev", text="EV (Tỷ VNĐ)")
        self.val_tree.heading("equity", text="Equity Value (Tỷ VNĐ)")
        self.val_tree.heading("per_share", text="Giá trị/CP (VNĐ)")
        self.val_tree.heading("upside", text="↕ vs Giá TT")
        self.val_tree.heading("note", text="Ghi chú")

        self.val_tree.column("method", width=180, anchor="w")
        self.val_tree.column("ev", width=120, anchor="e")
        self.val_tree.column("equity", width=150, anchor="e")
        self.val_tree.column("per_share", width=120, anchor="e")
        self.val_tree.column("upside", width=100, anchor="center")
        self.val_tree.column("note", width=200, anchor="w")

        self.val_tree.pack(fill=tk.X, expand=True)

        # --- ROW 5: KHUYẾN NGHỊ ĐẦU TƯ THAM KHẢO & VÙNG GIÁ MUA / BÁN ---
        ttk.Separator(main, orient="horizontal").grid(row=19, column=0, columnspan=6, sticky="ew", padx=10, pady=6)
        ttk.Label(main, text="═══ KHUYẾN NGHỊ ĐẦU TƯ THAM KHẢO & VÙNG GIÁ MUA / BÁN (MARGIN OF SAFETY) ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=20, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        rec_card = ttk.Frame(main, padding=10, relief="solid", borderwidth=1)
        rec_card.grid(row=21, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        self.lbl_rec_action = ttk.Label(rec_card, text="🎯 CHƯA CÓ KẾT QUẢ: Vui lòng tải BCTC mã cổ phiếu.", font=("Segoe UI", 10, "bold"), foreground="#1D4ED8")
        self.lbl_rec_action.pack(side=tk.TOP, anchor="w", pady=(0, 4))

        self.lbl_rec_zones = ttk.Label(rec_card, text="🟢 Vùng Mua An toàn (MOS 15%): —  |  🟡 Vùng Nắm giữ: —  |  🔴 Vùng Chốt lời / Bán: —", font=("Segoe UI", 9), foreground="#334155")
        self.lbl_rec_zones.pack(side=tk.TOP, anchor="w", pady=2)

        self.lbl_rec_note = ttk.Label(rec_card, text="💡 Ghi chú chiến lược: Hãy nạp dữ liệu BCTC và xem khuyến nghị chi tiết.", font=("Segoe UI", 8, "italic"), foreground="#475569")
        self.lbl_rec_note.pack(side=tk.TOP, anchor="w", pady=(2, 0))

        self.lbl_rec_checklist = ttk.Label(rec_card, text="", font=("Segoe UI", 8), foreground="#1E293B", justify="left")
        self.lbl_rec_checklist.pack(side=tk.TOP, anchor="w", pady=(4, 0))

        # --- ROW 6: MA TRẬN ĐỘ NHẠY FCFF (WACC vs g) ---
        ttk.Separator(main, orient="horizontal").grid(row=22, column=0, columnspan=6, sticky="ew", padx=10, pady=6)
        ttk.Label(main, text="═══ MA TRẬN ĐỘ NHẠY FCFF (WACC vs g) — Giá trị/CP (VNĐ) ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=23, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        sens_frame = ttk.Frame(main)
        sens_frame.grid(row=24, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        self.val_sens_tree = ttk.Treeview(sens_frame, show="headings", height=6)
        self.val_sens_tree.pack(fill=tk.X, expand=True)

        # --- ROW 7: MA TRẬN ĐỘ NHẠY FCFE (Ke vs g) ---
        ttk.Separator(main, orient="horizontal").grid(row=25, column=0, columnspan=6, sticky="ew", padx=10, pady=4)
        ttk.Label(main, text="═══ MA TRẬN ĐỘ NHẠY FCFE (Ke vs g) — Giá trị/CP (VNĐ) ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=26, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        sens_fcfe_frame = ttk.Frame(main)
        sens_fcfe_frame.grid(row=27, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        self.val_sens_fcfe_tree = ttk.Treeview(sens_fcfe_frame, show="headings", height=6)
        self.val_sens_fcfe_tree.pack(fill=tk.X, expand=True)

        # --- ROW 8: BIỂU ĐỒ SO SÁNH ---
        ttk.Separator(main, orient="horizontal").grid(row=28, column=0, columnspan=6, sticky="ew", padx=10, pady=4)
        ttk.Label(main, text="═══ BIỂU ĐỒ SO SÁNH GIÁ TRỊ THEO 7 PHƯƠNG PHÁP ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=29, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        chart_frame = ttk.Frame(main)
        chart_frame.grid(row=30, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        if HAS_MATPLOTLIB:
            self.val_fig = Figure(figsize=(8, 3.5), dpi=96, facecolor='#F8FAFC')
            self.val_chart_canvas = FigureCanvasTkAgg(self.val_fig, master=chart_frame)
            self.val_chart_canvas.get_tk_widget().pack(fill=tk.X, expand=True)
        else:
            self.val_fig = None
            self.val_chart_canvas = None
            ttk.Label(chart_frame, text="⚠️ Cài matplotlib để xem biểu đồ: pip install matplotlib",
                      foreground="#DC2626", font=("Segoe UI", 9, "italic")).pack(anchor="w")

        # --- EXPORT ---
        f_export = ttk.Frame(main)
        f_export.grid(row=31, column=0, columnspan=6, sticky="ew", padx=10, pady=8)
        ttk.Button(f_export, text="📥 Xuất Báo cáo Định giá Excel", command=self.export_valuation_excel).pack(side=tk.LEFT, padx=4)

    def _get_valuation_assumptions(self):
        """Thu thập giả định từ các slider."""
        asm = {}
        pct_keys = {"rf", "erp", "kd", "g", "revenue_growth", "tax_rate", "payout_ratio"}
        for key, info in self.val_sliders.items():
            val = info["var"].get()
            if key in pct_keys:
                asm[key] = val / 100.0
            elif key == "forecast_years":
                asm[key] = int(val)
            else:
                asm[key] = val
        return asm

    def _on_slider_changed(self, key, val):
        """Khi người dùng kéo slider → cập nhật label + recalculate."""
        if key in self.val_sliders:
            self.val_sliders[key]["label"].config(text=f"{float(val):.2f}")

        if self.val_fin_data is not None:
            self._recalculate_valuation()

    def _reset_valuation_sliders(self):
        """Reset tất cả slider về giá trị mặc định."""
        defaults = {
            "rf": 3.5, "beta": 0.8, "erp": 7.0, "kd": 8.0,
            "g": 3.0, "revenue_growth": 5.0, "tax_rate": 20.0,
            "pe_ratio": 15.0, "pb_ratio": 2.5, "ev_ebitda_ratio": 10.0,
            "payout_ratio": 50.0, "forecast_years": 5.0,
        }
        for key, default_val in defaults.items():
            if key in self.val_sliders:
                self.val_sliders[key]["var"].set(default_val)
                self.val_sliders[key]["label"].config(text=f"{default_val:.2f}")

        if self.val_fin_data is not None:
            self._recalculate_valuation()

    def _update_valuation_chart(self):
        """Cập nhật biểu đồ bar chart so sánh 7 phương pháp định giá."""
        if not HAS_MATPLOTLIB or self.val_fig is None or self.val_engine is None:
            return

        self.val_fig.clear()
        ax = self.val_fig.add_subplot(111)

        methods = []
        values = []
        colors = []
        market_price = self.val_fin_data.get("market_price", 0) if self.val_fin_data else 0

        order = ["nav", "pe", "pb", "ev_ebitda", "fcff", "fcfe", "ddm"]
        labels = {
            "nav": "NAV", "pe": "P/E", "pb": "P/B",
            "ev_ebitda": "EV/EBITDA", "fcff": "FCFF", "fcfe": "FCFE", "ddm": "DDM"
        }

        for key in order:
            r = self.val_engine.results.get(key, {})
            ps = r.get("per_share")
            if ps is not None and ps > 0:
                methods.append(labels.get(key, key))
                values.append(ps)
                if market_price > 0:
                    upside = (ps - market_price) / market_price
                    if upside > 0.15:
                        colors.append("#10B981")  # Xanh lá - Upside
                    elif upside < -0.15:
                        colors.append("#EF4444")  # Đỏ - Downside
                    else:
                        colors.append("#F59E0B")  # Vàng - Trung tính
                else:
                    colors.append("#3B82F6")  # Xanh dương mặc định

        if not methods:
            self.val_chart_canvas.draw()
            return

        bars = ax.barh(methods, values, color=colors, height=0.55, edgecolor='white', linewidth=0.5)

        # Đường tham chiếu giá thị trường
        if market_price > 0:
            ax.axvline(x=market_price, color="#DC2626", linewidth=2, linestyle="--",
                       label=f"Giá TT: {market_price:,.0f} VNĐ")
            ax.legend(fontsize=7, loc="lower right")

        ax.set_xlabel("VNĐ / Cổ phiếu", fontsize=8)
        ax.tick_params(axis='both', labelsize=7)
        ax.set_title("So sánh Giá trị Cổ phiếu — 7 Phương pháp Định giá", fontsize=9, fontweight='bold')
        ax.set_facecolor('#F8FAFC')

        # Value labels trên mỗi thanh
        max_val = max(values) if values else 1
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max_val * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{val:,.0f}", va='center', fontsize=7, color='#1E293B')

        self.val_fig.tight_layout()
        self.val_chart_canvas.draw()

    def _recalculate_valuation(self):
        """Tính lại toàn bộ 7 phương pháp và cập nhật bảng + biểu đồ."""
        if self.val_fin_data is None:
            return

        asm = self._get_valuation_assumptions()
        self.val_engine = ValuationEngine(self.val_fin_data, asm)
        results = self.val_engine.calc_all()

        market_price = self.val_fin_data.get("market_price", 0)

        # Cập nhật bảng kết quả
        self.val_tree.delete(*self.val_tree.get_children())

        order = ["nav", "pe", "pb", "ev_ebitda", "fcff", "fcfe", "ddm", "summary"]
        for key in order:
            r = results.get(key, {})
            method = r.get("method", "?")
            ev = r.get("ev")
            equity = r.get("equity")
            per_share = r.get("per_share")
            note = r.get("error", r.get("note", ""))

            ev_str = f"{ev / 1e9:,.1f}" if ev is not None else "— (Trực tiếp Equity)"
            eq_str = f"{equity / 1e9:,.1f}" if equity is not None else "N/A"
            ps_str = f"{per_share:,.0f}" if per_share is not None else "N/A"

            # Upside/Downside vs giá thị trường
            upside_str = "—"
            if market_price > 0 and per_share is not None and per_share > 0:
                upside_pct = (per_share - market_price) / market_price * 100
                if upside_pct > 0:
                    upside_str = f"▲ +{upside_pct:.1f}%"
                else:
                    upside_str = f"▼ {upside_pct:.1f}%"

            if key == "fcff" and "tv_pct" in r:
                tv_pct = r.get('tv_pct', 0)
                note = f"WACC={r.get('wacc', 0):.1%} | TV={tv_pct:.0f}%"
                if tv_pct > 75:
                    note += " ⚠️ TV cao!"
            if key == "fcfe" and "tv_pct" in r:
                tv_pct = r.get('tv_pct', 0)
                note = f"Ke={r.get('ke', 0):.1%} | TV={tv_pct:.0f}%"
                if tv_pct > 75:
                    note += " ⚠️ TV cao!"
            if key == "summary":
                method = "⭐ " + method

            tag = "summary" if key == "summary" else ""
            self.val_tree.insert("", tk.END, values=(method, ev_str, eq_str, ps_str, upside_str, note), tags=(tag,))

        # Thêm dòng giá thị trường tham chiếu
        if market_price > 0:
            shares = self.val_fin_data.get("shares_outstanding", 0) if self.val_fin_data else 0
            mkt_cap_str = f"{market_price * shares / 1e9:,.1f}" if shares > 0 else "—"
            self.val_tree.insert("", tk.END, values=(
                "📈 Giá thị trường", "—", mkt_cap_str, f"{market_price:,.0f}", "Tham chiếu", "Giá đóng cửa gần nhất"
            ), tags=("market",))

        self.val_tree.tag_configure("summary", background="#DBEAFE", font=("Segoe UI", 9, "bold"))
        self.val_tree.tag_configure("market", background="#FEF3C7", font=("Segoe UI", 8, "italic"))

        # Cập nhật Ke, WACC hiển thị
        ke = self.val_engine._calc_ke()
        wacc = self.val_engine._calc_wacc()
        mkt_str = f" | Giá TT={market_price:,.0f}" if market_price > 0 else ""
        self.val_status_var.set(
            f"✅ Ke={ke:.2%} | WACC={wacc:.2%} | "
            f"FCFF={results.get('fcff', {}).get('fcff_base', 0) / 1e9:,.1f}T | "
            f"FCFE={results.get('fcfe', {}).get('fcfe_base', 0) / 1e9:,.1f}T{mkt_str}"
        )

        # Cập nhật ma trận độ nhạy
        self._update_sensitivity_matrix()

        # Cập nhật biểu đồ
        self._update_valuation_chart()

        # Cập nhật Khuyến nghị Đầu tư & Vùng giá Mua/Bán
        self._update_investment_recommendation(results)

        # Cập nhật Thuyết minh Tab 5
        self._update_tab_explanation()

    def _update_investment_recommendation(self, results):
        """Tính toán khuyến nghị đầu tư Mua/Bán & Vùng giá theo Biên an toàn (Margin of Safety - MOS)."""
        if not hasattr(self, 'lbl_rec_action'):
            return

        market_price = self.val_fin_data.get("market_price", 0) if self.val_fin_data else 0
        r_sum = results.get("summary", {})
        fair_value = r_sum.get("per_share")

        if market_price <= 0 or fair_value is None or fair_value <= 0:
            self.lbl_rec_action.config(text="🎯 KHUYẾN NGHỊ ĐẦU TƯ: Chưa đủ dữ liệu Giá thị trường hoặc Giá trị Hợp lý.", foreground="#64748B")
            self.lbl_rec_zones.config(text="🟢 Vùng Mua An toàn: —  |  🟡 Vùng Nắm giữ: —  |  🔴 Vùng Chốt lời / Bán: —")
            self.lbl_rec_note.config(text="💡 Vui lòng nạp BCTC và kiểm tra các giả định slider tại Tab 4.")
            if hasattr(self, 'lbl_kpi_fair_value'):
                self.lbl_kpi_fair_value.config(text="— VNĐ")
                self.lbl_kpi_market_price.config(text="— VNĐ")
                self.lbl_kpi_upside.config(text="— %")
                self.lbl_kpi_rec.config(text="CHƯA ĐỊNH GIÁ", foreground="#64748B")
            return

        upside_pct = (fair_value - market_price) / market_price * 100

        # Cập nhật KPI Cards
        if hasattr(self, 'lbl_kpi_fair_value'):
            self.lbl_kpi_fair_value.config(text=f"{fair_value:,.0f} VNĐ")
            self.lbl_kpi_market_price.config(text=f"{market_price:,.0f} VNĐ")
            self.lbl_kpi_upside.config(
                text=f"{upside_pct:+.1f}%",
                foreground="#047857" if upside_pct > 0 else "#B91C1C"
            )

        # Mức Biên an toàn (Margin of Safety - MOS) = 15% đến 20%
        buy_safe_price = fair_value * 0.85      # Vùng mua an toàn (dưới 85% fair value)
        sell_target_price = fair_value * 1.10    # Vùng chốt lời (trên 110% fair value)

        # Xác định Khuyến nghị & Checklist giải trình
        if upside_pct >= 20.0:
            action_str = f"🟢 KHUYẾN NGHỊ: MUA MẠNH (STRONG BUY) — Upside: +{upside_pct:.1f}%"
            bg_color = "#15803D"
            kpi_badge = "🟢 MUA MẠNH"
            note_str = (
                f"💡 [TRƯỜNG HỢP 1: GIÁ THỊ TRƯỜNG THẤP HƠN NHIỀU GIÁ ĐỊNH GIÁ]\n"
                f"   Giá thị trường ({market_price:,.0f} VNĐ) đang nằm TRONG VÙNG MUA AN TOÀN (Chiết khấu > 15% so với Giá trị Hợp lý {fair_value:,.0f} VNĐ)."
            )
            checklist_str = (
                "📋 CHECK-LIST TRA CỨU GIẢI TRÌNH TRƯỚC KHI GIẢI NGÂN MUA:\n"
                "   1. [Chất lượng tài sản]: Kiểm tra Phải thu (MS 130) & Tồn kho (MS 140) trên BCTC có bị nợ xấu/ảo không?\n"
                "   2. [Tính bất thường]: LNST năm cơ sở có vọt lên do bán tài sản 1 lần khiến định giá cao ảo không?\n"
                "   3. [Giao dịch nội bộ]: Ban lãnh đạo / Cổ đông lớn có đang đăng ký mua vào tích lũy cổ phiếu không?\n"
                "   ⇒ Nếu Tài sản sạch & LNST cốt lõi vững chắc: Đây là CƠ HỘI MUA TÍCH LŨY DƯỚI GIÁ TRỊ THỰC RẤT HẤP DẪN."
            )
        elif upside_pct >= 5.0:
            action_str = f"🟢 KHUYẾN NGHỊ: MUA TÍCH LŨY (ACCUMULATE) — Upside: +{upside_pct:.1f}%"
            bg_color = "#166534"
            kpi_badge = "🟢 MUA TÍCH LŨY"
            note_str = f"💡 Giá thị trường ({market_price:,.0f} VNĐ) đang thấp hơn Giá trị hợp lý ({fair_value:,.0f} VNĐ). Phù hợp giải ngân tích lũy từng phần."
            checklist_str = (
                "📋 HƯỚNG DẪN GIẢI NGÂN TÍCH LŨY:\n"
                "   • Giá thị trường đang chiết khấu hợp lý. Khuyến nghị chia nhỏ vốn giải ngân tích lũy theo các nhịp chỉnh của thị trường."
            )
        elif upside_pct >= -10.0:
            action_str = f"🟡 KHUYẾN NGHỊ: NẮM GIỮ (HOLD) — Upside: {upside_pct:+.1f}%"
            bg_color = "#B45309"
            kpi_badge = "🟡 NẮM GIỮ"
            note_str = f"💡 Giá thị trường ({market_price:,.0f} VNĐ) đang phản ánh khá sát Giá trị hợp lý ({fair_value:,.0f} VNĐ)."
            checklist_str = (
                "📋 HƯỚNG DẪN NẮM GIỮ:\n"
                "   • Tiếp tục nắm giữ và cập nhật BCTC các quý tiếp theo để kiểm tra tốc độ tăng trưởng thực tế."
            )
        else:
            action_str = f"🔴 KHUYẾN NGHỊ: CHỐT LỜI / BÁN (SELL) — Downside: {upside_pct:.1f}%"
            bg_color = "#B91C1C"
            kpi_badge = "🔴 CHỐT LỜI / BÁN"
            note_str = (
                f"⚠️ [TRƯỜNG HỢP 2: GIÁ THỊ TRƯỜNG CAO HƠN NHIỀU GIÁ ĐỊNH GIÁ]\n"
                f"   Giá thị trường ({market_price:,.0f} VNĐ) cao hơn đáng kể so với Giá trị hợp lý ({fair_value:,.0f} VNĐ)."
            )
            checklist_str = (
                "📋 CHECK-LIST TRA CỨU GIẢI TRÌNH TRƯỚC KHI CHỐT LỜI / BÁN:\n"
                "   1. [Dự án/Kỳ vọng mới]: Doanh nghiệp có dự án mới/nhà máy mới/M&A nào sắp đi vào hoạt động mà BCTC chưa phản ánh không?\n"
                "   2. [Lợi thế vô hình]: Doanh nghiệp có lợi thế độc quyền, tiêu chuẩn EU-GMP/Japan-GMP hay thị phần lớn chưa lên sổ sách không?\n"
                "   3. [Sóng dòng tiền]: Thị trường đang trong giai đoạn Hype / FOMO ngắn hạn?\n"
                "   ⇒ Nếu KHÔNG có động lực tăng trưởng đột biến sắp tới: Cân nhắc CHỐT LỜI HOẶC HẠ TỶ TRỌNG ĐỂ BẢO VỆ THÀNH QUẢ."
            )

        if hasattr(self, 'lbl_kpi_rec'):
            self.lbl_kpi_rec.config(text=kpi_badge, foreground=bg_color)

        self.lbl_rec_action.config(text=action_str, foreground=bg_color)
        self.lbl_rec_zones.config(
            text=f"🟢 Vùng Mua An toàn (MOS 15%): ≤ {buy_safe_price:,.0f} VNĐ  |  "
                 f"🟡 Vùng Nắm giữ Hợp lý: {buy_safe_price:,.0f} – {sell_target_price:,.0f} VNĐ  |  "
                 f"🔴 Vùng Chốt lời / Bán: ≥ {sell_target_price:,.0f} VNĐ"
        )
        self.lbl_rec_note.config(text=note_str)
        if hasattr(self, 'lbl_rec_checklist'):
            self.lbl_rec_checklist.config(text=checklist_str)

    def _update_sensitivity_matrix(self):
        """Cập nhật ma trận độ nhạy WACC vs g (FCFF) + Ke vs g (FCFE)."""
        if self.val_engine is None:
            return

        # --- Ma trận FCFF: WACC vs g ---
        matrix, wacc_steps, g_steps = self.val_engine.sensitivity_matrix()

        sens_cols = ["wacc_label"] + [f"g_{g:.1%}" for g in g_steps]
        self.val_sens_tree["columns"] = sens_cols
        self.val_sens_tree.delete(*self.val_sens_tree.get_children())

        self.val_sens_tree.heading("wacc_label", text="WACC \\ g")
        self.val_sens_tree.column("wacc_label", width=80, anchor="center")
        for g in g_steps:
            col_id = f"g_{g:.1%}"
            self.val_sens_tree.heading(col_id, text=f"g={g:.1%}")
            self.val_sens_tree.column(col_id, width=100, anchor="e")

        base_wacc = self.val_engine._calc_wacc()

        for row_data in matrix:
            w = row_data["wacc"]
            vals = [f"WACC={w:.1%}"]
            for g in g_steps:
                ps = row_data.get(f"g_{g:.1%}", "N/A")
                if isinstance(ps, (int, float)):
                    vals.append(f"{ps:,.0f}")
                else:
                    vals.append(str(ps))

            is_base = abs(w - base_wacc) < 0.001
            tag = "base" if is_base else ""
            self.val_sens_tree.insert("", tk.END, values=vals, tags=(tag,))

        self.val_sens_tree.tag_configure("base", background="#FEF3C7", font=("Segoe UI", 8, "bold"))

        # --- Ma trận FCFE: Ke vs g ---
        try:
            matrix_fcfe, ke_steps, g_steps_fcfe = self.val_engine.sensitivity_matrix_fcfe()

            fcfe_cols = ["ke_label"] + [f"g_{g:.1%}" for g in g_steps_fcfe]
            self.val_sens_fcfe_tree["columns"] = fcfe_cols
            self.val_sens_fcfe_tree.delete(*self.val_sens_fcfe_tree.get_children())

            self.val_sens_fcfe_tree.heading("ke_label", text="Ke \\ g")
            self.val_sens_fcfe_tree.column("ke_label", width=80, anchor="center")
            for g in g_steps_fcfe:
                col_id = f"g_{g:.1%}"
                self.val_sens_fcfe_tree.heading(col_id, text=f"g={g:.1%}")
                self.val_sens_fcfe_tree.column(col_id, width=100, anchor="e")

            base_ke = self.val_engine._calc_ke()

            for row_data in matrix_fcfe:
                ke_val = row_data["ke"]
                vals = [f"Ke={ke_val:.1%}"]
                for g in g_steps_fcfe:
                    ps = row_data.get(f"g_{g:.1%}", "N/A")
                    if isinstance(ps, (int, float)):
                        vals.append(f"{ps:,.0f}")
                    else:
                        vals.append(str(ps))

                is_base = abs(ke_val - base_ke) < 0.001
                tag = "base" if is_base else ""
                self.val_sens_fcfe_tree.insert("", tk.END, values=vals, tags=(tag,))

            self.val_sens_fcfe_tree.tag_configure("base", background="#E0F2FE", font=("Segoe UI", 8, "bold"))
        except Exception:
            pass

    def action_load_valuation(self):
        """Tải BCTC từ API và tính toán định giá."""
        symbol = self.val_symbol_var.get().strip().upper()
        if not symbol:
            messagebox.showerror("Lỗi", "Bạn chưa nhập mã cổ phiếu.")
            return

        self.val_status_var.set(f"⏳ Đang tải BCTC {symbol} từ API...")

        def task():
            return extract_financial_data(symbol, period="year")

        def on_done(fin_data):
            self.val_fin_data = fin_data

            # Cập nhật labels số liệu
            fmt_items = {
                "revenue": 1e9, "net_income": 1e9, "ebit": 1e9, "ebitda": 1e9,
                "total_assets": 1e9, "total_liabilities": 1e9, "equity_book": 1e9,
                "cash": 1e9, "total_debt": 1e9, "depreciation": 1e9, "capex": 1e9,
            }
            for key, lbl in self.val_info_labels.items():
                val = fin_data.get(key, 0)
                if key in fmt_items:
                    lbl.config(text=f"{val / fmt_items[key]:,.1f} Tỷ")
                elif key == "shares_outstanding":
                    lbl.config(text=f"{val / 1e6:,.1f} Tr CP" if val > 0 else "—")
                elif key == "market_price":
                    if val > 0:
                        lbl.config(text=f"{val:,.0f} VNĐ", foreground="#DC2626")
                    else:
                        lbl.config(text="Không lấy được")
                else:
                    lbl.config(text=f"{val:,.0f}")

            # Tính toán
            self._recalculate_valuation()

        def run():
            try:
                result = task()
                self.after(0, lambda: on_done(result))
            except Exception as e:
                self.after(0, lambda: self.val_status_var.set(f"❌ Lỗi: {e}"))

        t = threading.Thread(target=run, daemon=True)
        t.start()

    def export_valuation_excel(self):
        """Xuất báo cáo định giá ra Excel."""
        if self.val_engine is None or not self.val_engine.results:
            messagebox.showinfo("Chưa có dữ liệu", "Hãy tải BCTC và tính toán trước khi xuất.")
            return

        symbol = self.val_symbol_var.get().strip().upper()
        path = filedialog.asksaveasfilename(
            title="Lưu Báo cáo Định giá", defaultextension=".xlsx",
            initialfile=f"DinhGia_{symbol}.xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if not path:
            return

        try:
            results = self.val_engine.results
            rows = []
            market_price = self.val_fin_data.get("market_price", 0) if self.val_fin_data else 0
            for key in ["nav", "pe", "pb", "ev_ebitda", "fcff", "fcfe", "ddm", "summary"]:
                r = results.get(key, {})
                ps = r.get("per_share", 0)
                upside = ""
                if market_price > 0 and ps and ps > 0:
                    upside_pct = (ps - market_price) / market_price * 100
                    upside = f"{upside_pct:+.1f}%"
                rows.append({
                    "Phương pháp": r.get("method", ""),
                    "EV (VNĐ)": r.get("ev", ""),
                    "Equity Value (VNĐ)": r.get("equity", ""),
                    "Giá trị/CP (VNĐ)": ps,
                    "Upside vs Giá TT": upside,
                    "Ghi chú": r.get("error", r.get("note", "")),
                })

            df_results = pd.DataFrame(rows)

            # Assumptions
            asm = self._get_valuation_assumptions()
            df_asm = pd.DataFrame([
                {"Tham số": k, "Giá trị": v} for k, v in asm.items()
            ])
            # Thêm dòng giá thị trường
            if market_price > 0:
                df_asm = pd.concat([df_asm, pd.DataFrame([{"Tham số": "market_price", "Giá trị": market_price}])], ignore_index=True)

            # Sensitivity FCFF (WACC vs g)
            matrix, wacc_steps, g_steps = self.val_engine.sensitivity_matrix()
            sens_rows = []
            for row_data in matrix:
                w = row_data["wacc"]
                sr = {"WACC": f"{w:.1%}"}
                for g in g_steps:
                    ps = row_data.get(f"g_{g:.1%}", "N/A")
                    sr[f"g={g:.1%}"] = ps
                sens_rows.append(sr)
            df_sens = pd.DataFrame(sens_rows)

            # Sensitivity FCFE (Ke vs g)
            try:
                matrix_fcfe, ke_steps, g_steps_fcfe = self.val_engine.sensitivity_matrix_fcfe()
                sens_fcfe_rows = []
                for row_data in matrix_fcfe:
                    ke_val = row_data["ke"]
                    sr = {"Ke": f"{ke_val:.1%}"}
                    for g in g_steps_fcfe:
                        ps = row_data.get(f"g_{g:.1%}", "N/A")
                        sr[f"g={g:.1%}"] = ps
                    sens_fcfe_rows.append(sr)
                df_sens_fcfe = pd.DataFrame(sens_fcfe_rows)
            except Exception:
                df_sens_fcfe = pd.DataFrame()

            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df_results.to_excel(writer, sheet_name="Kết quả Định giá", index=False)
                df_asm.to_excel(writer, sheet_name="Giả định", index=False)
                df_sens.to_excel(writer, sheet_name="Độ nhạy FCFF", index=False)
                if not df_sens_fcfe.empty:
                    df_sens_fcfe.to_excel(writer, sheet_name="Độ nhạy FCFE", index=False)

            messagebox.showinfo("Thành công", f"Đã lưu báo cáo định giá:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không xuất được: {e}")

    def _on_metric_checkbox_toggled(self):
        selected = [m_name for m_name, var in self.metric_checkbox_vars.items() if var.get()]
        if selected:
            self.metrics_var.set(", ".join(selected))
        else:
            self.metrics_var.set("")

    def set_status(self, msg, pct=None):
        self.status_var.set(msg)
        if pct is not None:
            self.progress_bar["value"] = pct
        else:
            self.progress_bar["value"] = 0

    def get_symbol(self):
        s = self.symbol_var.get().strip().upper()
        if not s:
            messagebox.showerror("Lỗi", "Bạn chưa nhập mã cổ phiếu.")
            return None
        return s

    def run_in_thread(self, target, label):
        self.set_status(f"Đang lấy dữ liệu: {label} ...", pct=5)
        t = threading.Thread(target=self._safe_run, args=(target, label), daemon=True)
        t.start()

    def _safe_run(self, target, label):
        try:
            df = target()
            self.after(0, lambda: self._on_success(df, label))
        except Exception as e:
            err_text = str(e)
            tb = traceback.format_exc()
            print(tb)
            self.after(0, lambda: self._on_error(err_text, label))

    def _on_success(self, df, label):
        global last_dataframe, last_label
        if df is None or len(df) == 0:
            self.set_status(f"Không có dữ liệu cho: {label}", pct=0)
            messagebox.showinfo("Không có dữ liệu", f"Không tìm thấy dữ liệu cho: {label}")
            return
        last_dataframe = df
        last_label = label
        self.current_df = df
        self.sort_column = None
        self.sort_descending = True
        self._populate_table(df)
        self.set_status(f"Hoàn tất 100%! {label} — {len(df)} dòng dữ liệu.", pct=100)

    def _on_error(self, err_text, label):
        self.set_status(f"Lỗi khi lấy: {label}", pct=0)
        messagebox.showerror(
            "Có lỗi xảy ra",
            f"Khong lay duoc du lieu cho: {label}\n\n"
            f"Chi tiet loi:\n{err_text}"
        )

    def _on_filter_changed(self, event=None):
        if self.current_df is not None:
            self._populate_table(self.current_df)

    def _on_unit_changed(self, event=None):
        if self.current_df is not None:
            self._populate_table(self.current_df)

    def _on_header_clicked(self, col):
        if self.current_df is None or len(self.current_df) == 0:
            return

        if self.sort_column == col:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = col
            self.sort_descending = True

        df_to_sort = self.current_df.copy()

        try:
            temp_num = pd.to_numeric(df_to_sort[col], errors="coerce")
            if temp_num.notna().sum() > 0:
                df_to_sort["_sort_key"] = temp_num.fillna(-1e18 if self.sort_descending else 1e18)
                df_to_sort = df_to_sort.sort_values(by="_sort_key", ascending=not self.sort_descending).drop(columns=["_sort_key"])
            else:
                df_to_sort = df_to_sort.sort_values(by=col, ascending=not self.sort_descending)
        except Exception:
            df_to_sort = df_to_sort.sort_values(by=col, ascending=not self.sort_descending)

        self.current_df = df_to_sort
        self._populate_table(df_to_sort)

    def _populate_table(self, df):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)
        
        for col in df.columns:
            header_text = str(col)
            if self.sort_column == col:
                header_text += " ▼" if self.sort_descending else " ▲"

            self.tree.heading(
                col, text=header_text,
                command=lambda _c=col: self._on_header_clicked(_c)
            )

            col_lower = str(col).lower()
            if "tên" in col_lower or "name" in col_lower or "chỉ tiêu" in col_lower or "item" in col_lower:
                self.tree.column(col, width=240, anchor="w")
            elif "mã" in col_lower or "symbol" in col_lower or "ticker" in col_lower:
                self.tree.column(col, width=100, anchor="center")
            else:
                self.tree.column(col, width=130, anchor="e")

        query = normalize_text(self.filter_var.get().strip())
        unit_mode = self.unit_var.get()

        filtered_df = df.copy()
        if query:
            mask = pd.Series(False, index=filtered_df.index)
            for col in filtered_df.columns:
                mask = mask | filtered_df[col].apply(normalize_text).str.contains(query, na=False)
            filtered_df = filtered_df[mask]

        preview = filtered_df.head(1000)
        
        for _, row in preview.iterrows():
            formatted_values = []
            for col, v in zip(df.columns, row.tolist()):
                col_lower = str(col).lower()
                if any(x in col_lower for x in ["mã", "tên", "chỉ tiêu", "item", "symbol", "ticker", "sàn"]):
                    formatted_values.append(str(v) if not pd.isna(v) else "-")
                else:
                    formatted_values.append(format_cell_value(v, unit_mode=unit_mode))
                    
            self.tree.insert("", tk.END, values=formatted_values)

    # Tab 1 Actions
    def action_price_history(self):
        symbol = self.get_symbol()
        if not symbol: return
        start, end = self.start_var.get().strip(), self.end_var.get().strip()

        def task():
            from vnstock import Market
            return Market().equity(symbol).ohlcv(start=start, end=end)

        self.run_in_thread(task, f"Giá lịch sử {symbol} ({start}->{end})")

    def action_company_info(self):
        symbol = self.get_symbol()
        if not symbol: return

        def task():
            from vnstock import Reference
            return Reference().company(symbol).info()

        self.run_in_thread(task, f"Thông tin công ty {symbol}")

    def action_balance_sheet(self):
        symbol = self.get_symbol()
        if not symbol: return
        period = self.period_var.get()
        s_y = self.t1_start_year_var.get().strip()
        e_y = self.t1_end_year_var.get().strip()

        def task():
            from vnstock import Fundamental
            df = Fundamental().equity(symbol).balance_sheet(period=period, lang='vi')
            if df is not None and len(df) > 0:
                if period == "quarter":
                    df = fix_quarterly_column_headers(df)
                p_cols = [c for c in df.columns if normalize_text(c) not in _NON_PERIOD_COLS]
                filtered_p_cols = filter_period_columns_by_year(p_cols, start_year=s_y, end_year=e_y)
                non_p_cols = [c for c in df.columns if normalize_text(c) in _NON_PERIOD_COLS]
                return df[non_p_cols + filtered_p_cols]
            return df

        self.run_in_thread(task, f"Bảng cân đối kế toán {symbol} ({s_y}->{e_y}) ({period})")

    def action_income_statement(self):
        symbol = self.get_symbol()
        if not symbol: return
        period = self.period_var.get()
        s_y = self.t1_start_year_var.get().strip()
        e_y = self.t1_end_year_var.get().strip()

        def task():
            from vnstock import Fundamental
            df = Fundamental().equity(symbol).income_statement(period=period, lang='vi')
            if df is not None and len(df) > 0:
                if period == "quarter":
                    df = fix_quarterly_column_headers(df)
                p_cols = [c for c in df.columns if normalize_text(c) not in _NON_PERIOD_COLS]
                filtered_p_cols = filter_period_columns_by_year(p_cols, start_year=s_y, end_year=e_y)
                non_p_cols = [c for c in df.columns if normalize_text(c) in _NON_PERIOD_COLS]
                return df[non_p_cols + filtered_p_cols]
            return df

        self.run_in_thread(task, f"Kết quả kinh doanh {symbol} ({s_y}->{e_y}) ({period})")

    def action_cash_flow(self):
        symbol = self.get_symbol()
        if not symbol: return
        period = self.period_var.get()
        s_y = self.t1_start_year_var.get().strip()
        e_y = self.t1_end_year_var.get().strip()

        def task():
            from vnstock import Fundamental
            df = Fundamental().equity(symbol).cash_flow(period=period, lang='vi')
            if df is not None and len(df) > 0:
                if period == "quarter":
                    df = fix_quarterly_column_headers(df)
                p_cols = [c for c in df.columns if normalize_text(c) not in _NON_PERIOD_COLS]
                filtered_p_cols = filter_period_columns_by_year(p_cols, start_year=s_y, end_year=e_y)
                non_p_cols = [c for c in df.columns if normalize_text(c) in _NON_PERIOD_COLS]
                return df[non_p_cols + filtered_p_cols]
            return df

        self.run_in_thread(task, f"Lưu chuyển tiền tệ {symbol} ({s_y}->{e_y}) ({period})")

    def action_ratio(self):
        symbol = self.get_symbol()
        if not symbol: return
        period = self.period_var.get()

        def task():
            from vnstock import Fundamental
            return Fundamental().equity(symbol).ratios(period=period)

        self.run_in_thread(task, f"Chỉ số tài chính {symbol} ({period})")

    # Tab 2 Action
    def action_industry_stats(self):
        industry_kw = self.industry_var.get().strip()
        metrics_raw = self.metrics_var.get().strip()
        period = self.industry_period_var.get()
        start_year = self.start_year_var.get().strip()
        end_year = self.end_year_var.get().strip()

        if not industry_kw:
            messagebox.showerror("Lỗi", "Bạn chưa chọn hoặc nhập ngành nghề.")
            return
        if not metrics_raw:
            messagebox.showerror("Lỗi", "Bạn chưa nhập hoặc tick chọn chỉ tiêu cần lấy.")
            return

        try:
            max_companies = int(self.max_companies_var.get().strip())
        except Exception:
            max_companies = 15

        metric_keywords = [m.strip() for m in metrics_raw.split(",") if m.strip()]

        def progress_cb(msg, pct=None):
            self.after(0, lambda: self.set_status(msg, pct=pct))

        def task():
            return build_industry_metric_table(
                industry_kw, metric_keywords, period, max_companies,
                start_year=start_year, end_year=end_year, progress_cb=progress_cb
            )

        label = f"Thống kê ngành '{industry_kw}' ({start_year}->{end_year}) - {', '.join(metric_keywords)} ({period})"
        self.run_in_thread(task, label)

    # Export Functions
    def export_excel(self):
        global last_dataframe, last_label
        if last_dataframe is None:
            messagebox.showinfo("Chưa có dữ liệu", "Bạn chưa lấy dữ liệu nào để xuất.")
            return
        default_name = (last_label or "du_lieu").replace(" ", "_")[:80] + ".xlsx"
        path = filedialog.asksaveasfilename(
            title="Lưu file Excel", defaultextension=".xlsx", initialfile=default_name,
            filetypes=[("Excel files", "*.xlsx")]
        )
        if not path: return
        try:
            last_dataframe.to_excel(path, index=False)
            messagebox.showinfo("Thành công", f"Đã lưu file:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi khi xuất Excel", str(e))

    def export_csv(self):
        global last_dataframe, last_label
        if last_dataframe is None:
            messagebox.showinfo("Chưa có dữ liệu", "Bạn chưa lấy dữ liệu nào để xuất.")
            return
        default_name = (last_label or "du_lieu").replace(" ", "_")[:80] + ".csv"
        path = filedialog.asksaveasfilename(
            title="Lưu file CSV", defaultextension=".csv", initialfile=default_name,
            filetypes=[("CSV files", "*.csv")]
        )
        if not path: return
        try:
            last_dataframe.to_csv(path, index=False, encoding="utf-8-sig")
            messagebox.showinfo("Thành công", f"Đã lưu file:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi khi xuất CSV", str(e))


    # ══════════════════════════════════════════════════════════════
    # TAB 5: CÔNG THỨC TÍNH TOÁN & THUYẾT MINH ĐỊNH GIÁ DOANH NGHIỆP
    # ══════════════════════════════════════════════════════════════

    def _build_tab_explanation(self, parent):
        # Scrollable canvas
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _on_canvas_configure)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        main = scroll_frame

        # --- HEADER ---
        ttk.Label(main, text="📘 CÔNG THỨC TÍNH TOÁN & THUYẾT MINH ĐỊNH GIÁ DOANH NGHIỆP",
                  font=("Segoe UI", 12, "bold"), foreground="#1D4ED8").grid(
            row=0, column=0, columnspan=6, sticky="w", padx=10, pady=(10, 4))

        ttk.Label(main, text="Thuyết minh bản chất số liệu & Quy trình ánh xạ BCTC theo chuẩn mực CFA và TT200/2014/TT-BTC",
                  font=("Segoe UI", 9, "italic"), foreground="#16A34A").grid(
            row=1, column=0, columnspan=6, sticky="w", padx=10, pady=(0, 8))

        f_top = ttk.Frame(main)
        f_top.grid(row=2, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        ttk.Button(f_top, text="⚡ Cập nhật Thuyết minh theo Mã cổ phiếu hiện tại",
                   command=self._update_tab_explanation).pack(side=tk.LEFT, padx=4)

        self.exp_status_var = tk.StringVar(value="Chưa chọn mã cổ phiếu nào.")
        ttk.Label(f_top, textvariable=self.exp_status_var, font=("Segoe UI", 9, "bold"), foreground="#1E40AF").pack(side=tk.LEFT, padx=12)

        ttk.Separator(main, orient="horizontal").grid(row=3, column=0, columnspan=6, sticky="ew", padx=10, pady=6)

        # --- SECTION 1: LIVE MATHEMATICAL BREAKDOWN ---
        ttk.Label(main, text="═══ 1. THUYẾT MINH CHI TIẾT SỐ LIỆU TÍNH TOÁN (LIVE MATH BREAKDOWN) ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=4, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        txt_frame = ttk.Frame(main)
        txt_frame.grid(row=5, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        self.txt_live_exp = tk.Text(txt_frame, height=18, font=("Consolas", 9), background="#F8FAFC", foreground="#0F172A", relief="solid", bd=1)
        txt_sb = ttk.Scrollbar(txt_frame, orient="vertical", command=self.txt_live_exp.yview)
        self.txt_live_exp.configure(yscrollcommand=txt_sb.set)

        self.txt_live_exp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        txt_sb.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Separator(main, orient="horizontal").grid(row=6, column=0, columnspan=6, sticky="ew", padx=10, pady=6)

        # --- SECTION 2: ÁNH XẠ BCTC TT200 ⇄ BIẾN SỐ ĐỊNH GIÁ ---
        ttk.Label(main, text="═══ 2. ÁNH XẠ CHỈ TIÊU BCTC VIỆT NAM (TT200) ⇄ BIẾN SỐ ĐỊNH GIÁ ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=7, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        map_frame = ttk.Frame(main)
        map_frame.grid(row=8, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        map_cols = ("var_name", "bctc_item", "bctc_code", "note")
        map_tree = ttk.Treeview(map_frame, columns=map_cols, show="headings", height=8)
        map_tree.heading("var_name", text="Biến số Định giá")
        map_tree.heading("bctc_item", text="Chỉ tiêu BCTC (TT200)")
        map_tree.heading("bctc_code", text="Mã số BCTC")
        map_tree.heading("note", text="Ý nghĩa & Lưu ý trong Định giá")

        map_tree.column("var_name", width=180, anchor="w")
        map_tree.column("bctc_item", width=260, anchor="w")
        map_tree.column("bctc_code", width=90, anchor="center")
        map_tree.column("note", width=360, anchor="w")

        mapping_data = [
            ("Tiền & Tương đương tiền", "Tiền và các khoản tương đương tiền", "110 (CĐKT)", "Cộng vào EV để quy đổi sang Equity Value"),
            ("Đầu tư tài chính ngắn hạn", "Đầu tư tài chính ngắn hạn", "120 (CĐKT)", "Tiền gửi tiết kiệm, chứng khoán ngắn hạn (cộng EV)"),
            ("Nợ vay ngắn hạn (Debt ST)", "Vay và nợ thuê tài chính ngắn hạn", "320 (CĐKT)", "Nợ vay chịu lãi ngắn hạn (trừ EV)"),
            ("Nợ vay dài hạn (Debt LT)", "Vay và nợ thuê tài chính dài hạn", "338/330 (CĐKT)", "Nợ vay chịu lãi dài hạn (trừ EV)"),
            ("Tổng nợ vay (Total Debt)", "Vay ngắn hạn + Vay dài hạn", "320 + 338", "Tổng nợ tài chính dùng tính EV & WACC"),
            ("Nợ thuần (Net Debt)", "Total Debt - Cash - ĐTTC ngắn hạn", "—", "Nợ thuần dùng chuyển đổi EV ↔ Equity Value"),
            ("Vốn chủ sở hữu (Equity)", "Vốn chủ sở hữu", "400 (CĐKT)", "Giá trị sổ sách của vốn chủ sở hữu"),
            ("Doanh thu thuần", "Doanh thu thuần về bán hàng & CCDV", "10 (KQKD)", "Quy mô hoạt động và căn cứ dự báo tăng trưởng"),
            ("Giá vốn hàng bán (COGS)", "Giá vốn hàng bán", "11 (KQKD)", "Chi phí sản xuất kinh doanh trực tiếp"),
            ("Lợi nhuận gộp", "Lợi nhuận gộp về bán hàng & CCDV", "20 (KQKD)", "Doanh thu thuần - Giá vốn hàng bán"),
            ("EBIT", "Tổng lợi nhuận trước thuế + Chi phí lãi vay", "50 + 23", "Lợi nhuận trước lãi vay và thuế"),
            ("D&A (Khấu hao)", "Khấu hao TSCĐ & BĐSĐT", "02 (LCTT)", "Khấu hao tài sản cố định hữu hình & vô hình"),
            ("EBITDA", "EBIT + D&A", "—", "Lợi nhuận trước lãi, thuế và khấu hao"),
            ("Lợi nhuận sau thuế (LNST)", "Lợi nhuận sau thuế TNDN", "60 (KQKD)", "Lợi nhuận thuần thuộc về cổ đông"),
            ("CAPEX", "Tiền chi mua sắm, xây dựng TSCĐ", "21 (LCTT)", "Chi phí đầu tư tài sản cố định hàng năm"),
        ]

        for item in mapping_data:
            map_tree.insert("", tk.END, values=item)

        map_tree.pack(fill=tk.X, expand=True)

        ttk.Separator(main, orient="horizontal").grid(row=9, column=0, columnspan=6, sticky="ew", padx=10, pady=6)

        # --- SECTION 3: CƠ SỞ XÁC ĐỊNH TRỌNG SỐ & QUY TẮC AN TOÀN ---
        ttk.Label(main, text="═══ 3. CƠ SỞ XÁC ĐỊNH TRỌNG SỐ & QUY TẮC KIỂM SOÁT AN TOÀN ═══",
                  font=("Segoe UI", 10, "bold"), foreground="#0F172A").grid(
            row=10, column=0, columnspan=6, sticky="w", padx=10, pady=(4, 2))

        rule_frame = ttk.Frame(main)
        rule_frame.grid(row=11, column=0, columnspan=6, sticky="ew", padx=10, pady=4)

        txt_rules = tk.Text(rule_frame, height=12, font=("Segoe UI", 9), background="#FEF3C7", foreground="#78350F", relief="solid", bd=1)
        rule_sb = ttk.Scrollbar(rule_frame, orient="vertical", command=txt_rules.yview)
        txt_rules.configure(yscrollcommand=rule_sb.set)

        txt_rules.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rule_sb.pack(side=tk.RIGHT, fill=tk.Y)

        rules_content = (
            "📌 CƠ SỞ XÁC ĐỊNH TRỌNG SỐ ĐỊNH GIÁ (WEIGHTING RATIONALE):\n"
            "----------------------------------------------------------------------------------------------------\n"
            "1. FCFF (20%) & FCFE (15%): Là 2 phương pháp cốt lõi theo chuẩn CFA, phản ảnh đúng giá trị dòng tiền thực tế.\n"
            "2. P/E (20%): Tỷ số P/E có mức độ phổ biến cao nhất với nhà đầu tư trên thị trường chứng khoán Việt Nam.\n"
            "3. DDM (15%): Áp dụng hiệu quả với doanh nghiệp trả cổ tức tiền mặt đều đặn (như ngành Dược, Tiện ích).\n"
            "4. NAV (10%), P/B (10%), EV/EBITDA (10%): Dùng để cân bằng, tránh thiên lệch bởi lợi nhuận 1 năm bất thường.\n\n"
            "📈 CĂN CỨ LỊCH SỬ VÀ DỰ PHÓNG TƯƠNG LAI (HISTORICAL BASELINE & FORWARD PROJECTION):\n"
            "----------------------------------------------------------------------------------------------------\n"
            "• Mô hình kết hợp 2 giai đoạn (2-Stage DCF Model): Số liệu BCTC kỳ mới nhất đóng vai trò là Năm Cơ sở (Base Year).\n"
            "  Từ năm cơ sở, dòng tiền được dự phóng tăng trưởng ngắn hạn trong N năm (g_short = 5%) và vĩnh viễn (g_long = 3%).\n"
            "• Đảm bảo tính khả thi: Tốc độ tăng trưởng ngắn hạn nên được tham chiếu với Tốc độ tăng trưởng kép (CAGR 3 năm quá khứ)\n"
            "  của chính doanh nghiệp để tránh đưa ra các giả định lạc quan quá mức.\n\n"
            "🎯 CƠ CHẾ KHUYẾN NGHỊ ĐẦU TƯ & VÙNG GIÁ MUA / BÁN (MARGIN OF SAFETY - MOS):\n"
            "----------------------------------------------------------------------------------------------------\n"
            "• Vùng Mua An toàn (Strong Buy Zone): Giá thị trường <= 85% Giá trị hợp lý (Biên an toàn MOS >= 15%).\n"
            "• Vùng Mua Tích lũy (Accumulate Zone): Giá thị trường nằm từ 85% đến 95% Giá trị hợp lý.\n"
            "• Vùng Nắm giữ (Hold Zone): Giá thị trường nằm trong khoảng +/- 10% quanh Giá trị hợp lý.\n"
            "• Vùng Chốt lời / Bán (Sell / Take Profit Zone): Giá thị trường >= 110% Giá trị hợp lý.\n\n"
            "⚠️ QUY TẮC TỰ ĐỘNG QUY ĐỔI TRỌNG SỐ (RE-WEIGHTING RULES):\n"
            "• Khi một phương pháp bị lỗi hoặc không áp dụng được (ví dụ LNST <= 0 khiến DDM hoặc P/E bị âm/lỗi),\n"
            "  hệ thống sẽ tự động gán trọng số phương pháp đó = 0% và quy đổi tổng trọng số các phương pháp còn lại = 100%.\n\n"
            "🛡️ CÁC ĐIỀU KIỆN AN TOÀN TOÁN HỌC (SANITY CHECKS):\n"
            "1. Bắt buộc WACC > g (cho FCFF) và Ke > g (cho FCFE, DDM). Nếu WACC <= g hoặc Ke <= g, mẫu số <= 0 làm giá trị\n"
            "   tiến đến vô cực, hệ thống sẽ báo lỗi và không xuất giá trị âm.\n"
            "2. Cảnh báo TV% > 75%: Nếu Giá trị Cuối kỳ (Terminal Value) chiếm > 75% tổng giá trị EV, hệ thống sẽ thêm\n"
            "   cảnh báo '⚠️ TV cao!' để nhắc nhở người dùng cẩn trọng với các giả định dài hạn."
        )
        txt_rules.insert(tk.END, rules_content)
        txt_rules.config(state="disabled")

        # Initial live breakdown update
        self._update_tab_explanation()

    def _update_tab_explanation(self):
        """Cập nhật chi tiết thuyết minh tính toán theo số liệu cổ phiếu hiện tại."""
        if not hasattr(self, 'txt_live_exp'):
            return

        self.txt_live_exp.config(state="normal")
        self.txt_live_exp.delete("1.0", tk.END)

        if self.val_fin_data is None or self.val_engine is None:
            self.exp_status_var.set("ℹ️ Chưa tải dữ liệu cổ phiếu nào. (Hãy tải BCTC tại Tab 4)")
            self.txt_live_exp.insert(
                tk.END,
                "Chưa có dữ liệu cổ phiếu nào được tải.\n\n"
                "Hãy quay lại Tab 4 (📊 Định giá Doanh nghiệp), nhập mã cổ phiếu (ví dụ: IMP, DHG) và bấm '⚡ TẢI BCTC & TÍNH TOÁN'.\n"
                "Sau đó bấm nút '⚡ Cập nhật Thuyết minh theo Mã cổ phiếu hiện tại' tại Tab này để xem toàn bộ thuyết minh chi tiết!"
            )
            self.txt_live_exp.config(state="disabled")
            return

        fin = self.val_fin_data
        eng = self.val_engine
        asm = eng.asm
        results = eng.results
        symbol = fin.get("symbol", "—")

        self.exp_status_var.set(f"✓ Thuyết minh tính toán chi tiết cho mã cổ phiếu: {symbol}")

        rf = asm.get("rf", 0.035)
        beta = asm.get("beta", 0.8)
        erp = asm.get("erp", 0.07)
        kd = asm.get("kd", 0.08)
        tax = asm.get("tax_rate", 0.20)
        g = asm.get("g", 0.03)
        growth = asm.get("revenue_growth", 0.05)
        years = asm.get("forecast_years", 5)

        ke = eng._calc_ke()
        wacc = eng._calc_wacc()

        shares = fin.get("shares_outstanding", 1)
        market_price = fin.get("market_price", 0)

        # Pull method results
        r_nav = results.get("nav", {})
        r_pe = results.get("pe", {})
        r_pb = results.get("pb", {})
        r_ev = results.get("ev_ebitda", {})
        r_fcff = results.get("fcff", {})
        r_fcfe = results.get("fcfe", {})
        r_ddm = results.get("ddm", {})
        r_sum = results.get("summary", {})

        today_str = date.today().strftime("%d/%m/%Y")

        exp_text = f"""================================================================================
BÁO CÁO THUYẾT MINH & CHI TIẾT TÍNH TOÁN ĐỊNH GIÁ — CỔ PHIẾU [{symbol}]
================================================================================
Tên Doanh nghiệp: {symbol} | Ngày tính toán: {today_str}
Số lượng Cổ phiếu lưu hành: {shares/1e6:,.1f} Tr Cổ phiếu ({shares:,.0f} CP)
Giá đóng cửa gần nhất (Giá thị trường): {market_price:,.0f} VNĐ / Cổ phiếu
Vốn hóa thị trường (Market Cap): {market_price * shares / 1e9:,.1f} Tỷ VNĐ

--------------------------------------------------------------------------------
1. GIẢ ĐỊNH ĐẦU VÀO & THÔNG SỐ CHI PHÍ VỐN (CAPITAL COSTS)
--------------------------------------------------------------------------------
- Lãi suất phi rủi ro (Rf): {rf:.2%} (Trái phiếu Chính phủ Việt Nam kỳ hạn 10 năm)
- Hệ số Beta (β): {beta:.2f} (Hệ số rủi ro hệ thống ngành)
- Phần bù rủi ro thị trường (ERP): {erp:.2%} (Equity Risk Premium Việt Nam)
- Chi phí nợ vay (Kd): {kd:.2%} | Thuế suất Thuế TNDN (T): {tax:.2%}
- Chi phí vốn chủ sở hữu (Ke):
  Ke = Rf + β × ERP = {rf:.2%} + {beta:.2f} × {erp:.2%} = {ke:.2%}

- Chi phí vốn bình quân gia quyền (WACC):
  WACC = [VCSH / (VCSH + Nợ)] × Ke + [Nợ / (VCSH + Nợ)] × Kd × (1 - T)
  WACC = {wacc:.2%}

- Tốc độ tăng trưởng dài hạn (g): {g:.2%} | Tăng trưởng doanh thu ngắn hạn: {growth:.2%}

--------------------------------------------------------------------------------
2. CHI TIẾT BƯỚC TÍNH THEO 7 PHƯƠNG PHÁP ĐỊNH GIÁ
--------------------------------------------------------------------------------

[1] PHƯƠNG PHÁP TÀI SẢN THUẦN (NAV)
    • Công thức: Equity Value = Tổng tài sản - Nợ phải trả
    • Phép tính: {fin.get('total_assets',0)/1e9:,.1f} Tỷ - {fin.get('total_liabilities',0)/1e9:,.1f} Tỷ = {r_nav.get('equity',0)/1e9:,.1f} Tỷ VNĐ
    • Giá trị / 1 CP: {r_nav.get('equity',0)/1e9:,.1f} Tỷ / {shares/1e6:,.1f} Tr CP = {r_nav.get('per_share',0):,.0f} VNĐ

[2] PHƯƠNG PHÁP TỶ SỐ P/E
    • Công thức: Equity Value = LNST Chuẩn hóa × P/E Ngành ({asm.get('pe_ratio', 15):.1f} lần)
    • Phép tính: {fin.get('net_income',0)/1e9:,.1f} Tỷ × {asm.get('pe_ratio', 15):.1f} = {r_pe.get('equity',0)/1e9:,.1f} Tỷ VNĐ
    • Giá trị / 1 CP: {r_pe.get('equity',0)/1e9:,.1f} Tỷ / {shares/1e6:,.1f} Tr CP = {r_pe.get('per_share',0):,.0f} VNĐ

[3] PHƯƠNG PHÁP TỶ SỐ P/B
    • Công thức: Equity Value = VCSH Chuẩn hóa × P/B Ngành ({asm.get('pb_ratio', 2.5):.1f} lần)
    • Phép tính: {fin.get('equity_book',0)/1e9:,.1f} Tỷ × {asm.get('pb_ratio', 2.5):.1f} = {r_pb.get('equity',0)/1e9:,.1f} Tỷ VNĐ
    • Giá trị / 1 CP: {r_pb.get('equity',0)/1e9:,.1f} Tỷ / {shares/1e6:,.1f} Tr CP = {r_pb.get('per_share',0):,.0f} VNĐ

[4] PHƯƠNG PHÁP TỶ SỐ EV/EBITDA
    • Công thức EV: Enterprise Value = EBITDA Chuẩn hóa ({fin.get('ebitda',0)/1e9:,.1f} Tỷ) × EV/EBITDA ({asm.get('ev_ebitda_ratio', 10):.1f} lần) = {r_ev.get('ev',0)/1e9:,.1f} Tỷ VNĐ
    • Chuyển đổi Equity Value: EV - Tổng Nợ vay + Tiền mặt
      = {r_ev.get('ev',0)/1e9:,.1f} Tỷ - {fin.get('total_debt',0)/1e9:,.1f} Tỷ + {fin.get('cash',0)/1e9:,.1f} Tỷ = {r_ev.get('equity',0)/1e9:,.1f} Tỷ VNĐ
    • Giá trị / 1 CP: {r_ev.get('equity',0)/1e9:,.1f} Tỷ / {shares/1e6:,.1f} Tr CP = {r_ev.get('per_share',0):,.0f} VNĐ

[5] PHƯƠNG PHÁP DÒNG TIỀN THUẦN DN CHIẾT KHẨU (FCFF - DCF)
    • Công thức FCFF Base: EBIT×(1-T) + D&A - CAPEX - ΔNWC
      = {fin.get('ebit',0)/1e9:,.1f}×(1-{tax:.2f}) + {fin.get('depreciation',0)/1e9:,.1f} - {fin.get('capex',0)/1e9:,.1f} = {r_fcff.get('fcff_base',0)/1e9:,.1f} Tỷ VNĐ
    • Chiết khấu bằng WACC = {wacc:.2%} trong {years} năm dự báo với tăng trưởng ngắn hạn {growth:.1%}
    • Terminal Value (TV): {r_fcff.get('tv_pct', 0):.0f}% tổng EV
    • Enterprise Value (EV): {r_fcff.get('ev',0)/1e9:,.1f} Tỷ VNĐ
    • Equity Value: EV - Nợ vay + Tiền = {r_fcff.get('equity',0)/1e9:,.1f} Tỷ VNĐ
    • Giá trị / 1 CP: {r_fcff.get('per_share',0):,.0f} VNĐ

[6] PHƯƠNG PHÁP DÒNG TIỀN THUẦN VỐN CSH CHIẾT KHẨU (FCFE)
    • Công thức FCFE Base: LNST + D&A - CAPEX - ΔNWC + Net Borrowing
      = {fin.get('net_income',0)/1e9:,.1f} + {fin.get('depreciation',0)/1e9:,.1f} - {fin.get('capex',0)/1e9:,.1f} + {fin.get('total_debt',0)*growth/1e9:,.1f} = {r_fcfe.get('fcfe_base',0)/1e9:,.1f} Tỷ VNĐ
    • Chiết khấu bằng Chi phí vốn chủ Ke = {ke:.2%}
    • Terminal Value (TV): Chiếm {r_fcfe.get('tv_pct', 0):.0f}% tổng Equity Value
    • Equity Value: {r_fcfe.get('equity',0)/1e9:,.1f} Tỷ VNĐ
    • Giá trị / 1 CP: {r_fcfe.get('per_share',0):,.0f} VNĐ

[7] PHƯƠNG PHÁP CHIẾT KHẤU CỔ TỨC (DDM)
    • Công thức Gordon: P0 = DPS1 / (Ke - g) = DPS0 × (1+g) / (Ke - g)
    • Giá trị / 1 CP: {r_ddm.get('per_share',0):,.0f} VNĐ
    • Equity Value: {r_ddm.get('equity',0)/1e9:,.1f} Tỷ VNĐ

--------------------------------------------------------------------------------
3. TỔNG HỢP GIÁ TRỊ VÀ BẢNG TRỌNG SỐ (WEIGHTED VALUATION SUMMARY)
--------------------------------------------------------------------------------
Công thức: Equity Value_Tổng hợp = ∑ (w_i × Equity Value_i) / ∑ w_i

- NAV       (10%): {r_nav.get('equity',0)/1e9:,.1f} Tỷ × 10% = {r_nav.get('equity',0)*0.1/1e9:,.1f} Tỷ
- P/E       (20%): {r_pe.get('equity',0)/1e9:,.1f} Tỷ × 20% = {r_pe.get('equity',0)*0.2/1e9:,.1f} Tỷ
- P/B       (10%): {r_pb.get('equity',0)/1e9:,.1f} Tỷ × 10% = {r_pb.get('equity',0)*0.1/1e9:,.1f} Tỷ
- EV/EBITDA (10%): {r_ev.get('equity',0)/1e9:,.1f} Tỷ × 10% = {r_ev.get('equity',0)*0.1/1e9:,.1f} Tỷ
- FCFF      (20%): {r_fcff.get('equity',0)/1e9:,.1f} Tỷ × 20% = {r_fcff.get('equity',0)*0.2/1e9:,.1f} Tỷ
- FCFE      (15%): {r_fcfe.get('equity',0)/1e9:,.1f} Tỷ × 15% = {r_fcfe.get('equity',0)*0.15/1e9:,.1f} Tỷ
- DDM       (15%): {r_ddm.get('equity',0)/1e9:,.1f} Tỷ × 15% = {r_ddm.get('equity',0)*0.15/1e9:,.1f} Tỷ
--------------------------------------------------------------------------------
=> GIÁ TRỊ VỐN CHỦ SỞ HỮU TỔNG HỢP (EQUITY VALUE): {r_sum.get('equity',0)/1e9:,.1f} Tỷ VNĐ
=> GIÁ TRỊ TỔNG HỢP / 1 CỔ PHIẾU (FAIR VALUE):     {r_sum.get('per_share',0):,.0f} VNĐ / CP
=> GIÁ THỊ TRƯỜNG HIỆN TẠI (MARKET PRICE):          {market_price:,.0f} VNĐ / CP
=> TỶ LỆ CHÊNH LỆCH (UPSIDE / DOWNSIDE):            {((r_sum.get('per_share',0)-market_price)/market_price*100) if market_price>0 else 0:+.1f}%
================================================================================
"""
        self.txt_live_exp.insert(tk.END, exp_text)
        self.txt_live_exp.config(state="disabled")


if __name__ == "__main__":
    app = VnstockApp()
    app.mainloop()
