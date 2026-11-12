# Cleanup AWS — 10/11/2026

Kiểm kê sau cleanup: **2026-11-10 04:34:39 UTC**, tức 11:34:39 giờ Việt Nam. Account `860366539351`, lab Singapore.

- [inventory-after.json](inventory-after.json): các dịch vụ lab đã trống, gồm S3/CloudFront toàn account; secret được xác minh bằng Lambda trong account vì endpoint Secrets Manager từ máy bị timeout. Lambda/quyền tạm đã gỡ.
- [operations.json](operations.json): SHA-256 saved plan, mốc hoàn tất từng root; support nêu rõ 16 tài nguyên xóa qua Terraform và 4 secret lên lịch xóa qua Lambda, không ghi Terraform apply hoàn tất giả.
- [offline-archive-summary.json](offline-archive-summary.json): checksum/metadata bản offline đã kiểm, không chứa dump hoặc credential. Backup cuối chưa được restore-test.
- [other-regions-summary.json](other-regions-summary.json): truy vấn bổ sung 16 region; Tokyo EC2/EBS còn timeout. Tagging ở us-east-1 có metadata IAM/payment toàn cục, không được suy ra đó là compute đang chạy.

Phạm vi không chứng nhận account khác hoặc mọi dịch vụ ở mọi region. Chi tiết và trạng thái state: [biên bản cleanup](../../15-aws-cleanup.md).
