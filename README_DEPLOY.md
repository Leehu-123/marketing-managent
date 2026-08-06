# HƯỚNG DẪN CHẠY LOCAL VÀ DEPLOY LÊN VPS

Dự án: **DAFA Glass Marketing Management SaaS**  
Repository: `https://github.com/Leehu-123/marketing-managent.git`

---

## 📋 1. THÔNG TIN HỆ THỐNG VPS

- **Cloud ID:** `CLOUD019347`
- **Gói dịch vụ:** ĐK SSD CLOUD VPS C
- **Máy chủ:** CloudVPS-OPS
- **IP VPS:** `45.117.177.80`
- **Tài khoản SSH:** `root`
- **Mật khẩu SSH:** `Y3pKPk3C4rH4EWe1`
- **Email quản trị:** `dafagroupvn@gmail.com`

---

## 🚀 2. CHẠY ỨNG DỤNG TRÊN LOCAL (TESTING)

Các file khởi chạy local đã được tạo sẵn ở thư mục gốc của project:

### Cách 1: Sử dụng Command Prompt (CMD) hoặc double-click
Nhấp đôi vào file **`start.bat`** ở thư mục gốc dự án.  
File này sẽ tự động:
1. Tạo file `.env` từ `.env.example` (nếu chưa có).
2. Tạo virtualenv Python và cài đặt các thư viện từ `backend/requirements.txt`.
3. Tự động mở trình duyệt web tại `http://localhost:8000`.
4. Chạy backend FastAPI server với chế độ hot-reload.

### Cách 2: Sử dụng PowerShell
Mở PowerShell tại thư mục dự án và chạy:
```powershell
.\start.ps1
```

### Cách 3: Sử dụng Git Bash / Linux / macOS
```bash
bash start.sh
```

🔑 **Tài khoản đăng nhập mặc định:**
- **Username:** `admin`
- **Password:** `dafa123`

---

## 🌐 3. DEPLOY ỨNG DỤNG LÊN VPS (PROD)

Bạn có 2 lựa chọn để deploy code lên VPS `45.117.177.80`:

### Lựa chọn A: Deploy tự động 1-Click từ máy local (Khuyên dùng)
Bạn chỉ cần đứng ở thư mục dự án trên máy tính của mình và chạy:

- Trên Windows Command Prompt (hoặc double-click):
  ```cmd
  deploy_vps.bat
  ```
- Hoặc trên PowerShell:
  ```powershell
  .\deploy_vps.ps1
  ```
- Hoặc chạy bằng Python:
  ```bash
  python deploy_vps.py
  ```

*Script `deploy_vps.py` sẽ tự động kết nối SSH tới VPS `45.117.177.80`, tải mã nguồn từ GitHub mới nhất, dựng Docker container, cấu hình Nginx reverse proxy và mở cổng firewall cho bạn.*

---

### Lựa chọn B: Deploy trực tiếp từ bên trong VPS
Nếu bạn đã SSH vào VPS (`ssh root@45.117.177.80`), bạn chỉ cần chạy lệnh sau:

```bash
curl -sSL https://raw.githubusercontent.com/Leehu-123/marketing-managent/main/deploy.sh | bash
```
Hoặc nếu đã upload file `deploy.sh`:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 🔍 4. QUẢN LÝ ỨNG DỤNG SAU KHI DEPLOY

Sau khi deploy thành công:
- **Địa chỉ truy cập Web App:** `http://45.117.177.80`
- **Cổng Backend API direct:** `http://45.117.177.80:8000`
- **Kiểm tra trạng thái Container:** `docker ps`
- **Xem log ứng dụng live trên VPS:** `docker logs -f dafa_glass_backend`
- **Khởi động lại app:** `docker compose restart` (trong `/var/www/marketing-management/backend`)
