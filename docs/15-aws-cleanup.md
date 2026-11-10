# Cleanup AWS và lưu trữ offline — 10/11/2026

Người dùng yêu cầu xóa môi trường để ngừng phí, thay cho yêu cầu giữ lab demo trước đó. Phạm vi đã kiểm kê trong account `860366539351`, Singapore: medium `moodle-n2-dev-med`, small cũ `moodle-lab-dev`, builder `moodle-n2-dev-builder`, ba bucket support, ECR, secret, AMI và snapshot liên quan. Không áp dụng cho account/profile Sydney của N1 chưa được xác định ở phiên này.

## Trạng thái thực hiện

**Đang thực hiện; chưa xác nhận hết tài nguyên tính phí.** Kết nối từ máy tới AWS/GitHub bị timeout trong lúc tải backup. Không coi việc dừng web/cron là dừng phí EC2, ALB, NAT, RDS, Redis hoặc storage.

Các bước đã hoàn tất trước khi mất kết nối:

- Medium: giữ operation lock, dừng/drain cron, chặn web writer trên cả hai app và runtime DB; backup cuối `moodle-n2-dev-med/20261109T185426` trên bucket backup. SSM `024bd9e5-67aa-4940-ace5-7cc0da03f1ae` hoàn tất thành công. Giữ maintenance để dữ liệu không thay đổi sau backup.
- Small: chạy script backup chuẩn, kiểm đủ checksum DB/file/config/code/runtime rồi upload một archive riêng. SSM `abb9ddf1-812d-403e-894a-3fa68b6c8d72` hoàn tất thành công. SHA-256 archive: `ffa69f97ec51e71b139af9928f42ce5b9a366a04a85fdead1946c28be72c37cc`. Web/cron đã dừng sau backup.
- Đã tải xong backup, artifact và state vào khu vực private. SHA-256 của cả bốn bộ backup medium (gồm bộ cuối `20261109T185426`) và archive small đã khớp; có `archive-verified.json`. Image runtime đã export, kiểm tar đọc được và lưu SHA-256 trong `runtime-archive.json`. Bản offline cuối chưa được restore-test; không dùng việc có backup để ký ca restore mới đạt.

Mã/hướng dẫn N3 đã push trên nhánh `khoi`. Tại mốc ghi nhận này chưa có marker `destroy-complete.json`: medium đang lập plan và chờ đọc Secrets Manager; small đang init provider. Chưa có inventory sau destroy để chứng nhận ngừng phí. Cần kiểm tra các log và trạng thái process trước khi chạy lại, tránh hai phiên Terraform cùng mutation; nếu process đã dừng mà còn lock phải xác minh chủ lock trước khi phục hồi.

## Vị trí riêng trên máy triển khai

`.work/medium-live/private/offline-20261110/` chứa dữ liệu cần bảo vệ; không commit, không gửi vào báo cáo. Khi archive hoàn tất, `archive-verified.json` đối chiếu SHA-256 DB và moodledata theo từng manifest, cùng hash archive small; `runtime-archive.json` ghi hash image archive. Nếu chuyển máy, bàn giao qua kho riêng có kiểm soát quyền.

Saved plans, bản sao root cleanup và logs riêng ở `.work/medium-live/cleanup-all/` cùng các file `cleanup-all-*.log`. Root Terraform chuẩn trong Git tiếp tục có deletion protection/prevent_destroy; các thay đổi gỡ bảo vệ chỉ nằm trong bản cleanup riêng.

## Thứ tự dọn và xác minh

1. Tải và kiểm backup/artifact/state, lưu image offline; xác nhận đúng account.
2. Root medium riêng: review plan chỉ tắt RDS deletion protection/chọn không tạo snapshot cuối vì giữ dữ liệu offline; gỡ EFS prevent_destroy trong bản riêng. Apply plan thay bảo vệ, sau đó lập/review/apply saved destroy plan. Không xóa remote state trước bước này.
3. Destroy small và builder từ state riêng, đối chiếu instance ID trước apply; root EBS phải được xóa chứ không chỉ stop EC2.
4. Dọn AMI/EBS snapshot, manual RDS/Redis snapshot đã giữ từ drill. Xóa certificate ACM riêng sau khi listener ALB đã gỡ.
5. Tải state cuối, xóa mọi object version/delete marker và multipart ở đúng ba bucket, destroy support/ECR/secret metadata. Bucket state chỉ xóa khi các root dùng nó đã destroy xong.
6. Kiểm kê lại EC2/EBS/EIP/NAT/ALB/RDS/EFS/Redis/S3/ECR/logs/alarms/secret/snapshot; ghi tài nguyên còn lại và lý do. Kiểm region khác bằng API nếu có quyền; không khẳng định toàn account đã sạch chỉ từ một region.

Tên Dynu miễn phí có thể giữ để lần dựng lại cập nhật CNAME tới ALB mới. URL demo không sử dụng được khi đã dọn hạ tầng; không dùng nó như site hiện hành. Billing còn có thể ghi nhận chi phí đã phát sinh trước cleanup; số trên Billing không giảm về 0 ngay khi xóa tài nguyên.

Xem [hướng dẫn N3](14-n3-acceptance-guide.md) để dựng lại và chạy các ca còn thiếu.
