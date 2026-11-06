# Lab AWS medium N2 — nhật ký triển khai

Người dùng đã yêu cầu tiếp tục triển khai AWS, chọn cửa sổ chạy thử khoảng **2 giờ** và URL HTTPS tạm bằng CloudFront vì chưa có domain. `MED-02` (ACM/domain/HTTPS ngay tại ALB) vẫn để chờ nghiệm thu. Không thay đổi máy small hiện có.

## Inventory trước mutation

- Account `860366539351`, region `ap-southeast-1`, identity IAM `test_user` đã được STS xác minh.
- Máy có sẵn: `i-0fde36cb6cb884f28`, tag `moodle-lab-dev`, loại `t3.medium`; giữ nguyên.
- Không có hosted zone Route 53, ACM certificate, S3 bucket, ECR repository hoặc AMI tự quản tại thời điểm kiểm kê.
- Base AMI Canonical: `ami-0cefdb30905dbeb73`, Ubuntu 26.04 amd64, tên build `20261104.1`.
- Project mới: `moodle-n2`, environment `dev`; support state, builder state và medium remote state độc lập.

## Dự toán tham khảo trước apply

Đọc từ AWS Price List API ngày 06/11/2026 cho Singapore, On-Demand, chưa trừ free tier/credit:

| Thành phần nền | Đơn giá USD/giờ | Số lượng |
|---|---:|---:|
| EC2 Linux `t3.medium` | 0.0528 | 3 (hai app + runner) |
| RDS PostgreSQL `db.t4g.micro` Single-AZ | 0.0250 | 1 |
| Redis `cache.t4g.micro` | 0.0240 | 2 |
| NAT Gateway theo AZ | 0.0590 | 1 |
| ALB | 0.0252 | 1 |

Tổng nền khoảng **0.3156 USD/giờ**, tương đương **0.6312 USD cho 2 giờ chạy đủ topology**. Đây chưa phải tổng hóa đơn: còn máy builder tạm, LCU, IPv4, EBS/RDS/EFS/S3/ECR storage, NAT/data transfer, CloudFront requests/data, CloudWatch metrics/alarms/logs, Secrets Manager và thời gian bootstrap/restore. Snapshot, bucket và artifact có thể còn chi phí sau khi compute đã dừng. Không dùng con số nền làm mức trần cam kết. Dữ liệu truy vấn gốc lưu riêng trong `.work/medium-*-prices.json`.

Nguồn giá là [AWS Price List Query API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-price-list-query-api.html). Thực tế phải đối chiếu Cost Explorer/Billing sau lab.

## Theo dõi thực thi

Các bước hiện tại: chuẩn bị dependency có SHA-256, kiểm tra local, lập saved plan cho support/builder. Chỉ đánh dấu tài nguyên đã tạo sau khi apply và inventory thực tế xác nhận. Metadata, outputs, state và nhật ký lệnh ở `.work/medium-live/`; không chia sẻ file state/plan hoặc credential.

Sau AMI/artifact/backend, cấu hình medium thật sẽ dùng `frontend: cloudfront`. Chỉ bắt đầu ghi bằng chứng LMS sau cloud-init, release/schema và health. Thời gian lab 2 giờ là mục tiêu vận hành, **chưa có lịch tự hủy**; cleanup cần backup và kiểm tra dữ liệu trước khi hủy tài nguyên có dữ liệu.
