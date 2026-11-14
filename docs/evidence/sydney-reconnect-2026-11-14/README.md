# Kiểm tra kết nối Sydney — 14/11/2026

Phạm vi: đăng nhập lại AWS và kiểm tra hai máy small đang có; không apply Terraform, không restore hoặc tạo tài nguyên mới. Source CLI tại thời điểm kiểm tra: `2130963`.

## Kết quả

- `aws login --profile moodle-project --region ap-southeast-2` hoàn tất và cập nhật profile thành công.
- STS xác nhận đúng account Sydney đã ghi trong [hồ sơ small](../../13-small-acceptance.md), role `AccountFullAccessRole`.
- SSM trả `Online` cho cả dev và staging.
- `validate` với `config/sydney.yaml` và `config/medium.example.yaml` đều thành công.
- Bộ unit test đã chạy trong cùng lượt rà soát: **89 tests, OK**.

| Môi trường | SSM command ID của health | Kết quả |
|---|---|---|
| Sydney dev | `699ef6b4-af5c-4533-aa4c-5e3f178a21f6` | Success, exit 0 |
| Sydney staging | `3fb97174-a405-4105-a6e7-bf4444c300d8` | Success, exit 0 |

Lệnh kiểm tra, với profile dự án đã được chọn:

```powershell
python -m src.moodle_cloud --config config/sydney.yaml health --wait --timeout 180
python -m src.moodle_cloud --config config/sydney-staging.yaml health --wait --timeout 180
```

Cả hai trả cùng nội dung:

```text
status: done
Database, admin account and container file permissions: OK
Basic health: OK. Also verify login, upload, cron completion and restore as documented.
Remote command completed with exit code 0. Application acceptance is separate.
```

## Giới hạn

Kết quả xác nhận kết nối và basic health của bản đang chạy. Không xác nhận runtime trên EC2 đã được cập nhật theo commit source hiện tại. Chưa chạy lại login/upload bằng trình duyệt, restore, ma trận tải, Docker integration hoặc toàn bộ CI trong lượt này. Không kiểm kê medium, chi phí hay cleanup của account khác. Nghiệm thu giao diện, kiểm tra chéo và các mục còn thiếu trong README chính vẫn mở.
