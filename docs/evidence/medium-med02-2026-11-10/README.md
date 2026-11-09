# MED-02 — Bằng chứng AWS ngày 10/11/2026

URL đã kiểm tra: **https://www.moodle-cloud-distribution.mywire.org**. Các timestamp trong JSON dùng UTC/Unix; ngày tiêu đề theo giờ Việt Nam.

| File | Bằng chứng |
|---|---|
| [inventory.json](inventory.json) | Listener 80/443, ACM ARN/policy, hai target healthy, refresh 100%, compute private và RDS giữ nguyên |
| [certificate.json](certificate.json), [dns.json](dns.json) | ACM `ISSUED`, đúng hostname/region, CNAME xác thực và CNAME trực tiếp tới ALB |
| [med02-https.json](med02-https.json) | **16/16 đạt**: TLS/CA/hostname, redirect, HSTS, cookie, asset/form URL |
| [med02-http.json](med02-http.json) | **47/47 đạt** trên domain mới: các vai trò, học liệu, bài nộp, điểm/phản hồi và logout |
| [med02-upload.json](med02-upload.json) | File được teacher upload qua GUI HTTPS và student tải đúng SHA-256; guest/student ngoài course bị từ chối |
| [operations.json](operations.json) | Command IDs và mốc backup/maintenance, audit URL, kiểm tra bootstrap app, cutover |
| [browser.json](browser.json) | Browser/version, viewport và giới hạn của walkthrough |
| [desktop-course.png](desktop-course.png) | Giao diện teacher ở 1440×1000 |
| [mobile-course.png](mobile-course.png), [mobile-grade.png](mobile-grade.png) | Student A ở viewport 390×844; course và điểm/phản hồi riêng |

Không chứa credential, cookie, token đăng nhập, state hoặc saved plan. Đây là kết quả triển khai N2, để N3 kiểm tra lại. Các ca chưa chạy và quy trình chuyển đổi ở [nhật ký MED-02](../../13-medium-med02.md).
