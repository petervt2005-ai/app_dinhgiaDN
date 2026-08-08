# 📊 Vnstock App — Hệ Thống Định Giá Doanh Nghiệp 7 Phương Pháp
*(Định giá Doanh nghiệp Niêm yết Chứng khoán Việt Nam chuẩn CFA & TT200/2014/TT-BTC)*

![Developer](https://img.shields.io/badge/Developer-V%C3%B5%20Ti%E1%BA%BFn%20D%C6%B0%C6%A1ng-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Mobile%20%26%20Web-FF4B4B)
![Vnstock](https://img.shields.io/badge/Vnstock-v4.0%2B-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20iOS%20%7C%20iPad-purple)

---

## 📌 GIỚI THIỆU TỔNG QUAN

**Vnstock App** là hệ thống tự động hóa tra cứu Báo cáo tài chính và Định giá Doanh nghiệp niêm yết trên thị trường chứng khoán Việt Nam, được phát triển bởi **Võ Tiến Dũng**. Ứng dụng tích hợp bộ máy tính toán **7 Phương pháp Định giá chuẩn mực CFA**, hỗ trợ nhà đầu tư giả lập kịch bản định giá real-time và nhận khuyến nghị vùng giá Mua/Bán theo nguyên lý **Biên An Toàn (Margin of Safety - MOS)**.

Ứng dụng hỗ trợ đa nền tảng:
- 💻 **Desktop App (Windows/macOS):** Giao diện Executive Financial Terminal (`Tkinter`).
- 📱 **Mobile Web App (iPhone/iPad):** Giao diện Web HMTL5/CSS3 tương thích vuốt chạm mượt mà trên Safari (`Streamlit Cloud`).

---

## ⭐ TÍNH NĂNG NỔI BẬT

### 1. 📊 Định giá 7 Phương pháp Cốt lõi (CFA Standard):
1. **Tài sản thuần (NAV):** Định giá dựa trên Giá trị sổ sách Vốn chủ sở hữu đã điều chỉnh.
2. **Tỷ số P/E:** Định giá theo Bội số Giá trên Lợi nhuận ngành.
3. **Tỷ số P/B:** Định giá theo Bội số Giá trên Giá trị sổ sách ngành.
4. **EV/EBITDA:** Định giá theo Giá trị Doanh nghiệp trên Lợi nhuận trước thuế, lãi vay và khấu hao.
5. **Dòng tiền Doanh nghiệp (FCFF - DCF):** Mô hình chiết khấu dòng tiền 2 giai đoạn (2-Stage Model).
6. **Dòng tiền Vốn Chủ Sở Hữu (FCFE):** Chiết khấu dòng tiền trực tiếp thuộc về cổ đông.
7. **Chiết khấu Cổ tức (DDM):** Định giá dựa trên dòng cổ tức tiền mặt dự phóng.
8. ⭐ **Giá trị Tổng hợp (Weighted Summary):** Tổng hợp bình quân có trọng số khoa học của các phương pháp hợp lệ.

### 2. 🎯 Khuyến nghị Mua/Bán & Vùng giá Biên An Toàn (Margin of Safety - MOS 15%):
- 🟢 **Vùng Mua An toàn:** Giá thị trường $\le 85\% \times \text{Giá trị Hợp lý}$ (Upside $\ge +20\%$).
- 🟡 **Vùng Nắm giữ:** Giá thị trường từ $85\% \dots 110\% \times \text{Giá trị Hợp lý}$.
- 🔴 **Vùng Chốt lời / Bán:** Giá thị trường $\ge 110\% \times \text{Giá trị Hợp lý}$ (Downside $< -10\%$).

### 3. 📋 Check-list Phân tích Giải trình Tự động:
- **Trường hợp 1 (Giá TT thấp hơn nhiều giá định giá):** Hướng dẫn kiểm tra chất lượng tài sản (Phải thu, Tồn kho), rủi ro nợ xấu và tính bất thường của lợi nhuận.
- **Trường hợp 2 (Giá TT cao hơn nhiều giá định giá):** Hướng dẫn tra cứu động lực tăng trưởng mới, công suất nhà máy mới, lợi thế vô hình (EU-GMP/Japan-GMP) hoặc sóng dòng tiền.

### 4. 🎛️ Giả lập Kịch bản Tương tác Real-time (Scenario Simulation):
12 thanh trượt Slider tương tác phân nhóm trực quan giúp nhà đầu tư chủ động thay đổi các tham số:
- **Chi phí vốn:** Lãi suất phi rủi ro ($R_f$), Beta ($\beta$), Phần bù rủi ro ($ERP$), Chi phí nợ ($K_d$), Thuế TNDN.
- **Tăng trưởng:** Tốc độ tăng trưởng dài hạn ($g$), Tăng trưởng ngắn hạn, Số năm dự báo FCFF.
- **Bội số ngành & Cổ tức:** P/E ngành, P/B ngành, EV/EBITDA ngành, Tỷ lệ chi trả cổ tức.

---

## 📁 CẤU TRÚC REPOSITORY

```text
├── streamlit_app.py      # Giao diện Web App tương thích Mobile (iPhone / iPad / Safari)
├── vnstock_app.py        # Bộ máy tính toán cốt lõi ValuationEngine & Desktop UI Tkinter
├── requirements.txt      # Khai báo phụ thuộc danh sách thư viện Python
├── Mo_App.bat            # Script click-to-run khởi động Desktop App trên Windows
├── Mo_Web_App.bat        # Script click-to-run khởi động Web App Streamlit nội bộ
├── AGENTS.md             # Quy tắc ngữ cảnh AI Agent & Vnstock Vibe Coding
└── README.md             # Tài liệu giới thiệu & Hướng dẫn sử dụng
```

---

## 🛠️ HƯỚNG DẪN CÀI ĐẶT VÀ KHỞI CHẠY

### 1. Cài đặt Môi trường (Local Installation)
Yêu cầu Python version **>= 3.10**. Mở Terminal/CMD và chạy:

```bash
git clone https://github.com/petervt2005-ai/app_dinhgiaDN.git
cd app_dinhgiaDN
pip install -r requirements.txt
```

### 2. Khởi chạy Desktop App (Windows / macOS)
```bash
python vnstock_app.py
# Hoặc nhấp đúp chuột vào file Mo_App.bat trên Windows
```

### 3. Khởi chạy Web App (iPhone / iPad / Browser)
```bash
streamlit run streamlit_app.py
# Hoặc nhấp đúp chuột vào file Mo_Web_App.bat
```

---

## ⚖️ TÁC GIẢ & MIỄN TRỪ TRÁCH NHIỆM (DISCLAIMER)

- **Người phát triển (Developer):** **Võ Tiến Dũng** (`petervt2005-ai`).
- **Tuyên bố Miễn trừ Trách nhiệm:**
  > ⚠️ **LƯU Ý QUAN TRỌNG:** Ứng dụng và toàn bộ kết quả định giá, khuyến nghị trong ứng dụng **chỉ mang tính chất THAM KHẢO HỌC THUẬT / MÔ PHỎNG GIẢ LẬP**, hoàn toàn KHÔNG phải là lời khuyên đầu tư hay khuyến nghị mua/bán chứng khoán chính thức.
  >
  > Tác giả Võ Tiến Dũng và nhóm phát triển **không chịu bất kỳ trách nhiệm pháp lý hay tài chính nào** đối với các quyết định đầu tư, tổn thất hay rủi ro phát sinh từ việc sử dụng dữ liệu và kết quả của ứng dụng này. Nhà đầu tư tự chịu trách nhiệm hoàn toàn đối với quyết định giải ngân của chính mình.

---
*Phát triển bởi Võ Tiến Dũng & Antigravity AI Agent Team.*
