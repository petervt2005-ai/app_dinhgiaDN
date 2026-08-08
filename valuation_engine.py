# -*- coding: utf-8 -*-
"""
ValuationEngine & Data Extractor Module for Vnstock App
Thuần Python xử lý dữ liệu định giá - Không phụ thuộc vào Tkinter hoặc GUI.
"""

import sys
import os
import re
import time
import json
import unicodedata
from datetime import date, timedelta
import pandas as pd

_NON_PERIOD_COLS = {
    "item", "chi tieu", "chitieu", "organname", "ticker", "symbol",
    "ma cp", "macp", "ten cong ty", "tencongty", "index", "id"
}

def normalize_text(s):
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

def fix_quarterly_column_headers(df):
    if df is None or len(df) == 0:
        return df
    fixed_df = df.copy()
    dup_cols = [c for c in fixed_df.columns if str(c).endswith('_1')]
    if dup_cols:
        fixed_df = fixed_df.drop(columns=dup_cols, errors='ignore')
    return fixed_df

_COMPANY_DATABASE_CACHE = None

def get_company_lookup_database():
    global _COMPANY_DATABASE_CACHE
    if _COMPANY_DATABASE_CACHE is not None:
        return _COMPANY_DATABASE_CACHE

    stock_dict = {}
    search_options = []
    try:
        from vnstock import Listing
        df = Listing().all_symbols()
        if not df.empty:
            for _, row in df.iterrows():
                sym = str(row.get("symbol", "")).strip().upper()
                name = str(row.get("organ_name", "")).strip()
                if sym:
                    stock_dict[sym] = name
                    search_options.append(f"{sym} — {name}")
    except Exception as e:
        print("Lỗi tải danh sách công ty:", e)

    if not stock_dict:
        default_stocks = [
            ("IMP", "CTCP Dược phẩm Imexpharm"),
            ("DHG", "CTCP Dược Hậu Giang"),
            ("DBT", "CTCP Dược phẩm Bến Tre"),
            ("TRA", "CTCP Traphaco"),
            ("DBD", "CTCP Dược - Thiết bị Y tế Bình Định"),
            ("HSG", "CTCP Tập đoàn Hoa Sen"),
            ("HPG", "CTCP Tập đoàn Hòa Phát"),
            ("VNM", "CTCP Sữa Việt Nam"),
            ("FPT", "CTCP FPT"),
        ]
        for sym, name in default_stocks:
            stock_dict[sym] = name
            search_options.append(f"{sym} — {name}")

    _COMPANY_DATABASE_CACHE = (stock_dict, search_options)
    return _COMPANY_DATABASE_CACHE

def resolve_ticker_symbol(input_text):
    if not input_text:
        return ""
    text = str(input_text).strip()
    if " — " in text:
        return text.split(" — ")[0].strip().upper()

    stock_dict, _ = get_company_lookup_database()
    query = text.upper()

    if query in stock_dict:
        return query
    for sym in stock_dict:
        if sym.startswith(query):
            return sym
    for sym, name in stock_dict.items():
        if query in name.upper():
            return sym
    return query

def extract_financial_data(symbol, period="year"):
    from vnstock import Fundamental, Reference, Market

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

    try:
        df_inc = eq.income_statement(period=period, lang='vi')
        if df_inc is None or len(df_inc) == 0:
            try:
                df_inc = eq.income_statement(period=period, source='VCI', lang='vi')
            except Exception:
                pass
        df_inc = fix_quarterly_column_headers(df_inc)
        non_meta = [c for c in df_inc.columns if normalize_text(c) not in _NON_PERIOD_COLS]
        latest_col = non_meta[0] if non_meta else None

        data["revenue"] = _find_value(df_inc, ["Doanh thu thuần về bán hàng và cung cấp dịch vụ", "3. Doanh thu thuần", "Doanh thu thuần"], latest_col)
        data["cogs"] = abs(_find_value(df_inc, ["Giá vốn hàng bán", "4. Giá vốn"], latest_col))
        data["gross_profit"] = _find_value(df_inc, ["Lợi nhuận gộp về bán hàng", "5. Lợi nhuận gộp", "Lợi nhuận gộp"], latest_col)
        data["interest_expense"] = abs(_find_value(df_inc, ["Trong đó: Chi phí lãi vay", "Chi phí lãi vay", "of_which_interest_expense"], latest_col))
        data["net_income"] = _find_value(df_inc, ["Lợi nhuận sau thuế thu nhập doanh nghiệp", "15. Lợi nhuận sau thuế", "Lợi nhuận sau thuế", "LNST"], latest_col)

        pbt = _find_value(df_inc, ["Tổng lợi nhuận kế toán trước thuế", "14. Tổng lợi nhuận", "Lợi nhuận trước thuế"], latest_col)
        data["ebit"] = pbt + data["interest_expense"] if pbt != 0 else (data["net_income"] * 1.25 + data["interest_expense"])
    except Exception as e:
        print(f"Lỗi tải KQKD {symbol}: {e}")

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

        data["total_assets"] = _find_value(df_bs, ["TỔNG CỘNG TÀI SẢN", "Tổng cộng tài sản", "Tài sản"], latest_col)
        data["total_liabilities"] = _find_value(df_bs, ["NỢ PHẢI TRẢ", "Nợ phải trả"], latest_col)
        data["equity_book"] = _find_value(df_bs, ["VỐN CHỦ SỞ HỮU", "Vốn chủ sở hữu"], latest_col)
        if data["equity_book"] == 0 and data["total_assets"] > 0:
            data["equity_book"] = max(0, data["total_assets"] - data["total_liabilities"])

        data["cash"] = _find_value(df_bs, ["Tiền và các khoản tương đương tiền", "I. Tiền và các khoản tương đương tiền", "Tiền"], latest_col)
        data["short_term_debt"] = _find_value(df_bs, ["Vay và nợ thuê tài chính ngắn hạn", "Vay ngắn hạn"], latest_col)
        data["long_term_debt"] = _find_value(df_bs, ["Vay và nợ thuê tài chính dài hạn", "Vay dài hạn"], latest_col)
        data["total_debt"] = data["short_term_debt"] + data["long_term_debt"]
    except Exception as e:
        print(f"Lỗi tải CĐKT {symbol}: {e}")

    try:
        df_cf = eq.cash_flow(period=period, lang='vi')
        df_cf = fix_quarterly_column_headers(df_cf)
        non_meta = [c for c in df_cf.columns if normalize_text(c) not in _NON_PERIOD_COLS]
        latest_col = non_meta[0] if non_meta else None

        data["depreciation"] = abs(_find_value(df_cf, ["Khấu hao TSCĐ", "Khấu hao tài sản cố định", "Chi phí khấu hao"], latest_col))
        data["capex"] = abs(_find_value(df_cf, ["Tiền chi để mua sắm, xây dựng TSCĐ", "Mua sắm TSCĐ"], latest_col))
        data["cfo"] = _find_value(df_cf, ["Lưu chuyển tiền thuần từ hoạt động kinh doanh"], latest_col)
    except Exception as e:
        print(f"Lỗi tải LCTT {symbol}: {e}")

    try:
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

    try:
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
                    p_val *= 1000.0
                data["market_price"] = p_val
    except Exception:
        pass

    return data

class ValuationEngine:
    def __init__(self, fin_data, assumptions):
        self.fin = fin_data
        self.asm = assumptions
        self.results = {}

    def calc_all(self):
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
        eq_book = self.fin["equity_book"]
        adj = self.asm.get("asset_adj", 0.0)
        nav = eq_book * (1.0 + adj)
        shares = self.fin["shares_outstanding"]
        per_share = nav / shares if shares > 0 else 0
        return {"method": "1. NAV (Tài sản thuần)", "ev": None, "equity": nav, "per_share": per_share}

    def calc_pe(self):
        ni = self.fin["net_income"]
        pe = self.asm.get("pe_ratio", 15.0)
        equity_val = ni * pe
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0
        return {"method": "2. Tỷ số P/E", "ev": None, "equity": equity_val, "per_share": per_share}

    def calc_pb(self):
        eq_book = self.fin["equity_book"]
        pb = self.asm.get("pb_ratio", 2.5)
        equity_val = eq_book * pb
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0
        return {"method": "3. Tỷ số P/B", "ev": None, "equity": equity_val, "per_share": per_share}

    def calc_ev_ebitda(self):
        ebitda = self.fin["ebitda"]
        m = self.asm.get("ev_ebitda_ratio", 10.0)
        ev = ebitda * m
        total_debt = self.fin["total_debt"]
        cash = self.fin["cash"]
        net_debt = total_debt - cash
        equity_val = ev - net_debt
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0
        return {"method": "4. EV/EBITDA", "ev": ev, "equity": equity_val, "per_share": per_share}

    def _calc_wacc(self):
        rf = self.asm.get("rf", 0.035)
        beta = self.asm.get("beta", 0.8)
        erp = self.asm.get("erp", 0.07)
        ke = rf + beta * erp
        kd = self.asm.get("kd", 0.08)
        tax = self.asm.get("tax_rate", 0.20)
        kd_after_tax = kd * (1 - tax)
        total_debt = self.fin["total_debt"]
        equity_book = self.fin["equity_book"]
        total_cap = total_debt + equity_book
        if total_cap > 0:
            w_d = total_debt / total_cap
            w_e = equity_book / total_cap
        else:
            w_d, w_e = 0.3, 0.7
        return w_e * ke + w_d * kd_after_tax

    def _calc_ke(self):
        rf = self.asm.get("rf", 0.035)
        beta = self.asm.get("beta", 0.8)
        erp = self.asm.get("erp", 0.07)
        return rf + beta * erp

    def calc_fcff(self, wacc_override=None, g_override=None):
        wacc = wacc_override if wacc_override is not None else self._calc_wacc()
        g = g_override if g_override is not None else self.asm.get("g", 0.03)
        growth = self.asm.get("revenue_growth", 0.05)
        years = int(self.asm.get("forecast_years", 5))

        ebit = self.fin["ebit"]
        tax = self.asm.get("tax_rate", 0.20)
        nopat = ebit * (1 - tax)
        depr = self.fin["depreciation"]
        capex = self.fin["capex"]
        delta_nwc = self.fin["delta_nwc"]

        fcff_base = nopat + depr - capex - delta_nwc
        if fcff_base <= 0:
            fcff_base = max(nopat * 0.7, self.fin["net_income"] * 0.6)

        if wacc <= g:
            return {"method": "5. DCF (FCFF)", "ev": None, "equity": None, "per_share": None,
                    "error": f"WACC ({wacc:.1%}) ≤ g ({g:.1%})", "wacc": wacc, "fcff_base": fcff_base}

        pv_fcff = 0
        for t in range(1, years + 1):
            fcff_t = fcff_base * (1 + growth) ** t
            pv_fcff += fcff_t / (1 + wacc) ** t

        fcff_terminal = fcff_base * (1 + growth) ** years * (1 + g)
        tv = fcff_terminal / (wacc - g)
        pv_tv = tv / (1 + wacc) ** years

        ev = pv_fcff + pv_tv
        net_debt = self.fin["total_debt"] - self.fin["cash"]
        equity_val = ev - net_debt
        shares = self.fin["shares_outstanding"]
        per_share = equity_val / shares if shares > 0 else 0

        return {"method": "5. DCF (FCFF)", "ev": ev, "equity": equity_val, "per_share": per_share,
                "wacc": wacc, "fcff_base": fcff_base}

    def calc_fcfe(self, ke_override=None, g_override=None):
        ke = ke_override if ke_override is not None else self._calc_ke()
        g = g_override if g_override is not None else self.asm.get("g", 0.03)
        growth = self.asm.get("revenue_growth", 0.05)
        years = int(self.asm.get("forecast_years", 5))

        ni = self.fin["net_income"]
        depr = self.fin["depreciation"]
        capex = self.fin["capex"]
        delta_nwc = self.fin["delta_nwc"]

        fcfe_base = ni + depr - capex - delta_nwc
        if fcfe_base <= 0:
            fcfe_base = max(ni * 0.6, 0)

        if ke <= g or fcfe_base <= 0:
            return {"method": "6. FCFE (Vốn CSH)", "ev": None, "equity": None, "per_share": None,
                    "error": f"Ke ({ke:.1%}) ≤ g ({g:.1%})" if ke <= g else "FCFE ≤ 0", "ke": ke, "fcfe_base": fcfe_base}

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

        return {"method": "6. FCFE (Vốn CSH)", "ev": None, "equity": equity_val, "per_share": per_share,
                "ke": ke, "fcfe_base": fcfe_base}

    def calc_ddm(self):
        ke = self._calc_ke()
        g = self.asm.get("g", 0.03)
        payout = self.asm.get("payout_ratio", 0.50)
        ni = self.fin["net_income"]
        shares = self.fin["shares_outstanding"]

        eps = ni / shares if shares > 0 else 0
        d0 = eps * payout
        if d0 <= 0:
            d0 = self.fin.get("dividend_per_share", 0)

        if ke <= g or d0 <= 0:
            return {"method": "7. DDM (Cổ tức)", "ev": None, "equity": None, "per_share": None,
                    "note": "Doanh nghiệp không trả cổ tức hoặc Ke ≤ g", "d0": d0}

        d1 = d0 * (1 + g)
        per_share = d1 / (ke - g)
        equity_val = per_share * shares

        return {"method": "7. DDM (Cổ tức)", "ev": None, "equity": equity_val, "per_share": per_share, "d0": d0}

    def calc_weighted_summary(self):
        weights = {"nav": 0.10, "pe": 0.20, "pb": 0.10, "ev_ebitda": 0.10, "fcff": 0.20, "fcfe": 0.15, "ddm": 0.15}
        total_weight = 0
        weighted_equity = 0
        weighted_ps = 0

        for key, w in weights.items():
            r = self.results.get(key, {})
            ps = r.get("per_share")
            eq = r.get("equity")
            if ps is not None and ps > 0:
                total_weight += w
                weighted_ps += ps * w
                if eq is not None and eq > 0:
                    weighted_equity += eq * w

        if total_weight > 0:
            weighted_equity /= total_weight
            weighted_ps /= total_weight

        return {"method": "GIÁ TRỊ TỔNG HỢP", "ev": None, "equity": weighted_equity,
                "per_share": weighted_ps, "total_weight": total_weight}
