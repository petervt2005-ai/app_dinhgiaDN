import sys
import os
import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# Thêm đường dẫn tới vnstock_app
sys.path.insert(0, os.path.dirname(__file__))
from vnstock_app import extract_financial_data, ValuationEngine

# --- PAGE CONFIG FOR MOBILE ---
st.set_page_config(
    page_title="Vnstock Định Giá Doanh Nghiệp (Mobile & iPad)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR MODERN MOBILE UI ---
st.markdown("""
<style>
    .main { background-color: #F8FAFC; }
    .stMetric { background-color: #FFFFFF; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0; }
</style>
""", unsafe_allow_html=True)

st.title("📊 VNSTOCK — ĐỊNH GIÁ DOANH NGHIỆP (Web Mobile / iPad)")
st.caption("Ứng dụng Định giá 7 Phương pháp & Mô phỏng Giả lập dành cho iPhone, iPad và Máy tính")

# --- SIDEBAR INPUTS ---
st.sidebar.header("⚙️ Cấu hình Tra cứu")
symbol = st.sidebar.text_input("Nhập Mã cổ phiếu", value="IMP").upper()

st.sidebar.subheader("🏦 Chi phí Vốn (WACC & Ke)")
rf = st.sidebar.slider("Rf (Lãi suất phi rủi ro %)", 1.0, 8.0, 3.5, 0.1) / 100
beta = st.sidebar.slider("Beta (Hệ số rủi ro)", 0.3, 2.0, 0.8, 0.05)
erp = st.sidebar.slider("ERP (Phần bù rủi ro %)", 4.0, 12.0, 7.0, 0.5) / 100
kd = st.sidebar.slider("Kd (Chi phí nợ vay %)", 3.0, 15.0, 8.0, 0.5) / 100
tax_rate = st.sidebar.slider("Thuế suất TNDN %", 0.0, 30.0, 20.0, 1.0) / 100

st.sidebar.subheader("📈 Tăng trưởng & Dự báo")
g = st.sidebar.slider("g (Tăng trưởng dài hạn %)", 0.5, 6.0, 3.0, 0.25) / 100
revenue_growth = st.sidebar.slider("Tăng trưởng DT ngắn hạn %", 0.0, 25.0, 5.0, 0.5) / 100
forecast_years = st.sidebar.slider("Số năm dự báo FCFF", 3, 10, 5, 1)

st.sidebar.subheader("🏢 Bội số Ngành & Cổ tức")
pe_ratio = st.sidebar.slider("P/E ngành (lần)", 5.0, 40.0, 15.0, 0.5)
pb_ratio = st.sidebar.slider("P/B ngành (lần)", 0.5, 6.0, 2.5, 0.1)
ev_ebitda_ratio = st.sidebar.slider("EV/EBITDA ngành (lần)", 3.0, 25.0, 10.0, 0.5)
payout_ratio = st.sidebar.slider("Tỷ lệ chi trả cổ tức %", 0.0, 100.0, 50.0, 5.0) / 100

# Cache data fetch
@st.cache_data(ttl=3600)
def fetch_data(sym):
    return extract_financial_data(sym)

if symbol:
    with st.spinner(f"Đang tải BCTC cổ phiếu {symbol}..."):
        fin_data = fetch_data(symbol)

    if fin_data:
        asm = {
            "rf": rf, "beta": beta, "erp": erp, "kd": kd, "g": g,
            "revenue_growth": revenue_growth, "tax_rate": tax_rate,
            "pe_ratio": pe_ratio, "pb_ratio": pb_ratio,
            "ev_ebitda_ratio": ev_ebitda_ratio, "payout_ratio": payout_ratio,
            "forecast_years": forecast_years
        }
        engine = ValuationEngine(fin_data, asm)
        results = engine.calc_all()

        mkt_price = fin_data.get("market_price", 0)
        r_sum = results.get("summary", {})
        fair_value = r_sum.get("per_share")
        upside = (fair_value - mkt_price) / mkt_price * 100 if mkt_price > 0 and fair_value else 0

        # --- KPI METRICS ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("⭐ GIÁ TRỊ HỢP LÝ", f"{fair_value:,.0f} VNĐ" if fair_value else "—")
        col2.metric("📈 GIÁ THỊ TRƯỜNG", f"{mkt_price:,.0f} VNĐ" if mkt_price > 0 else "—")
        col3.metric("↕ UPSIDE / CHÊNH LỆCH", f"{upside:+.1f}%")
        
        if upside >= 20:
            col4.metric("🎯 KHUYẾN NGHỊ", "🟢 MUA MẠNH")
        elif upside >= 5:
            col4.metric("🎯 KHUYẾN NGHỊ", "🟢 MUA TÍCH LŨY")
        elif upside >= -10:
            col4.metric("🎯 KHUYẾN NGHỊ", "🟡 NẮM GIỮ")
        else:
            col4.metric("🎯 KHUYẾN NGHỊ", "🔴 CHỐT LỜI / BÁN")

        # --- RECOMMENDATION & ZONES ---
        st.subheader("🎯 Vùng giá Mua / Bán & Khuyến nghị Chiến lược")
        buy_safe = fair_value * 0.85 if fair_value else 0
        sell_target = fair_value * 1.10 if fair_value else 0

        st.info(
            f"🟢 **Vùng Mua An toàn (MOS 15%):** ≤ {buy_safe:,.0f} VNĐ  |  "
            f"🟡 **Vùng Nắm giữ:** {buy_safe:,.0f} – {sell_target:,.0f} VNĐ  |  "
            f"🔴 **Vùng Chốt lời / Bán:** ≥ {sell_target:,.0f} VNĐ"
        )

        if upside >= 20:
            st.success(
                "💡 **TRƯỜNG HỢP 1: GIÁ THỊ TRƯỜNG THẤP HƠN NHIỀU GIÁ ĐỊNH GIÁ**\n\n"
                "📋 **Check-list tra cứu giải trình trước khi mua:**\n"
                "1. Kiểm tra Phải thu (MS 130) & Tồn kho (MS 140) có nợ xấu/ảo không?\n"
                "2. LNST năm cơ sở có vọt lên do bán tài sản 1 lần không?\n"
                "3. Ban lãnh đạo / Cổ đông lớn có đang mua vào tích lũy không?"
            )
        elif upside < -10:
            st.warning(
                "⚠️ **TRƯỜNG HỢP 2: GIÁ THỊ TRƯỜNG CAO HƠN NHIỀU GIÁ ĐỊNH GIÁ**\n\n"
                "📋 **Check-list tra cứu giải trình trước khi bán:**\n"
                "1. Doanh nghiệp có dự án/nhà máy mới/M&A nào sắp vận hành không?\n"
                "2. Có lợi thế độc quyền EU-GMP/Japan-GMP hay thị phần lớn không?\n"
                "3. Thị trường đang trong sóng ngành / FOMO ngắn hạn?"
            )

        # --- RESULTS TABLE ---
        st.subheader("📊 Bảng Kết quả Định giá 7 Phương pháp")
        table_rows = []
        for k in ["nav", "pe", "pb", "ev_ebitda", "fcff", "fcfe", "ddm", "summary"]:
            r = results.get(k, {})
            m_name = r.get("method", "?")
            if k == "summary":
                m_name = "⭐ " + m_name
            ev_v = f"{r.get('ev')/1e9:,.1f}" if r.get('ev') is not None else "— (Trực tiếp Equity)"
            eq_v = f"{r.get('equity')/1e9:,.1f}" if r.get('equity') is not None else "—"
            ps_v = f"{r.get('per_share'):,.0f}" if r.get('per_share') is not None else "—"
            up_v = f"{(r.get('per_share')-mkt_price)/mkt_price*100:+.1f}%" if mkt_price>0 and r.get('per_share') else "—"
            table_rows.append({"Phương pháp": m_name, "EV (Tỷ VNĐ)": ev_v, "Equity Value (Tỷ VNĐ)": eq_v, "Giá trị/CP (VNĐ)": ps_v, "Upside": up_v})

        df_res = pd.DataFrame(table_rows)
        st.dataframe(df_res, use_container_width=True)

        # --- CHART ---
        st.subheader("📈 Biểu đồ So sánh các Phương pháp Định giá")
        fig, ax = plt.subplots(figsize=(10, 4.5))
        methods = [r["Phương pháp"].replace("⭐ ", "") for r in table_rows[:-1]]
        values = [results.get(k, {}).get("per_share", 0) or 0 for k in ["nav", "pe", "pb", "ev_ebitda", "fcff", "fcfe", "ddm"]]

        bars = ax.barh(methods, values, color="#2563EB", height=0.55)
        if mkt_price > 0:
            ax.axvline(mkt_price, color="#DC2626", linestyle="--", linewidth=2, label=f"Giá TT ({mkt_price:,.0f} VNĐ)")

        ax.set_xlabel("VNĐ / Cổ phiếu")
        ax.set_title(f"So sánh Định giá Cổ phiếu {symbol}", fontsize=12, fontweight="bold")
        ax.legend()
        ax.grid(axis="x", linestyle=":", alpha=0.6)
        st.pyplot(fig)
