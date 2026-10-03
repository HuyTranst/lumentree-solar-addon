# ☀️ Lumentree Solar Guard & Valetudo Vacuum Home Assistant Add-on Repository

Bộ Repository Add-on mở rộng cho **Home Assistant**, cho phép bạn đóng gói và cài đặt hệ thống giám sát **Biến Tần Lumentree Solar 24/7**, tự động kiểm tra công suất phát điện, điều khiển máy lạnh Hồng Ngoại, và bản đồ Robot Valetudo xoay 90 độ chuẩn cảm ứng 1 ngón tay / 2 ngón tay lên bất kỳ máy Home Assistant nào chỉ với vài cú nhấp chuột!

---

## 📁 Cấu Trúc Thư Mục Repository (Repository Structure)

```text
lumentree-solar-addon-repo/
├── repository.yaml                   # File khai báo Add-on Repository chuẩn Home Assistant
├── README.md                         # Hướng dẫn chi tiết bằng Tiếng Việt
├── lumentree-solar-guard/            # MÃ NGUỒN ADD-ON CONTAINER CHÍNH
│   ├── config.yaml                   # File cấu hình Add-on (slug, arch, options)
│   ├── Dockerfile                     # Dockerfile tự động tải môi trường Python & MQTT
│   ├── run.sh                         # Script khởi động Daemon 24/7
│   ├── solar_ac_daemon.py             # Mã nguồn Python đọc telemetry Lumentree & đẩy sensor vào HA
│   └── DOCS.md                        # Tài liệu hướng dẫn sử dụng Add-on
└── homeassistant-config/             # CẤU HÌNH DASHBOARD, CARD & AUTOMATIONS
    ├── automations.yaml              # Kịch bản tự động báo lỗi 0W & Điều khiển máy lạnh
    ├── scripts.yaml                  # Script gửi lệnh Hồng Ngoại Tắt/Mở máy lạnh
    ├── configuration.yaml            # Cấu hình Template Sensors, Input Helpers & Shell Commands
    ├── valetudo-map-card.js          # Card bản đồ Robot Valetudo (Xoay 90°, Căn lề 20%, Pinch Zoom 2 ngón & Drag 1 ngón)
    ├── lovelace.lumentree_solar.json # Dashboard Lumentree Solar (Giao diện Real-Time & Cài đặt)
    └── lovelace.robot_mova.json      # Dashboard Robot Mova L40 Ultra
```

---

## 🚀 HƯỚNG DẪN 1: ĐƯA MÃ NGUỒN LÊN GITHUB (UPLOAD TO GITHUB)

1. Tạo một Repository mới trên **GitHub** (ví dụ đặt tên: `lumentree-solar-addon`).
2. Mở Terminal / PowerShell tại thư mục `lumentree-solar-addon-repo` và chạy các lệnh Git:

```bash
git init
git add .
git commit -m "Initial commit for Lumentree Solar Guard HA Add-on"
git branch -M main
git remote add origin https://github.com/TÊN_GITHUB_CỦA_BẠN/lumentree-solar-addon.git
git push -u origin main
```

---

## 📦 HƯỚNG DẪN 2: CÀI ĐẶT LÊN BẤT KỲ HOME ASSISTANT NÀO KHÁC (INSTALL ON OTHER HA)

Sau khi đưa lên GitHub, để cài đặt sang máy Home Assistant khác:

### Bước 1: Thêm Repository vào Add-on Store
1. Vào Home Assistant ➔ **Cài Đặt (Settings)** ➔ **Add-ons** ➔ **Cửa hàng Add-on (Add-on Store)**.
2. Bấm vào **dấu 3 chấm (⋮)** ở góc trên bên phải ➔ Chọn **Kho lưu trữ (Repositories)**.
3. Dán đường dẫn GitHub Repository của bạn (ví dụ: `https://github.com/TÊN_GITHUB_CỦA_BẠN/lumentree-solar-addon`) ➔ Bấm **Thêm (Add)**.

### Bước 2: Cài Đặt và Khởi Chạy Add-on
1. Tìm ứng dụng **Lumentree Solar Guard** vừa xuất hiện trong Add-on Store.
2. Bấm **Cài Đặt (Install)**.
3. Sang tab **Cấu hình (Configuration)**, nhập `device_id` biến tần Lumentree của bạn (mặc định: `H250521206`).
4. Bấm **Bắt đầu (Start)** và bật tùy chọn **Tự động khởi động (Start on boot)** và **Watchdog**.

---

## 🎨 HƯỚNG DẪN 3: SAO CHÉP GIAO DIỆN & CARD BẢN ĐỒ (DASHBOARD & CARDS)

### 1. Thêm Card Bản Đồ Robot Mova/Valetudo (`valetudo-map-card.js`)
- Copy file `homeassistant-config/valetudo-map-card.js` vào thư mục `/config/www/` của Home Assistant mới.
- Vào **Cài Đặt** ➔ **Dashboard** ➔ **Dấu 3 chấm (⋮)** ➔ **Tài nguyên (Resources)** ➔ Thêm URL: `/local/valetudo-map-card.js?v=1.0.0` (Loại: JavaScript Module).

### 2. Nhập Dashboard Lumentree Solar & Robot Mova
- Copy nội dung file `homeassistant-config/lovelace.lumentree_solar.json` và `homeassistant-config/lovelace.robot_mova.json` vào file cấu hình dashboard tương ứng trong `/config/.storage/`.

---

🎉 **Chúc mừng! Hệ thống Lumentree Solar Guard & Bản Đồ Robot Valetudo của bạn hiện đã được đóng gói thành chuẩn Add-on Repository Home Assistant chuyên nghiệp!**
