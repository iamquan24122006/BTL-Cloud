# Cleanup AWS và lưu trữ offline — 10/11/2026

**Đã dọn xong lab Singapore trong account `860366539351`.** Inventory cuối lúc **04:34:39 UTC / 11:34:39 giờ Việt Nam** không còn các tài nguyên lab tính phí đã kiểm kê. S3 và CloudFront toàn account cũng trống. URL demo cũ đã ngừng hoạt động.

Đây là thực hiện yêu cầu xóa để ngừng phí, thay cho yêu cầu giữ demo trước đó. Không chứng nhận account/profile Sydney của N1 hoặc mọi dịch vụ tại mọi region. Chi phí đã phát sinh trước cleanup vẫn có thể xuất hiện trên Billing.

## Kết quả và bằng chứng

| Nhóm | Kết quả |
|---|---|
| EC2/ASG | Đã thu hồi hai app, runner, small cũ và builder; không còn EC2 chạy/stop trong inventory Singapore |
| Ổ đĩa/IP/mạng | EBS, EIP, NAT Gateway, ALB và VPC endpoint đều trống |
| Dữ liệu | Không còn RDS instance, EFS hoặc Redis replication group |
| Snapshot/artifact | Không còn manual RDS/Redis snapshot, AMI/EBS snapshot hoặc ECR repository |
| S3 | Đã tải về máy, xóa current objects, versions/delete markers/multipart và cả ba bucket backup/artifact/state |
| Quan sát | Không còn CloudWatch log group/metric alarm/dashboard hoặc AWS Backup vault đã kiểm |
| HTTPS/CDN | ACM của lab đã xóa; CloudFront không còn distribution |
| Secret | Không còn secret active; 8 secret nguồn/restore đang chờ xóa theo recovery window |
| Công cụ tạm | Lambda cleanup và IAM role/policy tạm đã gỡ; không còn Lambda function trong region |

Hồ sơ đã lọc: [inventory, thao tác và checksum offline](evidence/cleanup-2026-11-10/README.md). Truy vấn thêm 16 region không thấy EC2/RDS ở các nơi trả lời thành công; **Tokyo EC2/EBS timeout**, ghi rõ trong JSON. Tagging us-east-1 trả metadata IAM/payment toàn cục; không xóa thông tin thanh toán của account.

## Cách xử lý timeout và state

Small và builder hoàn tất saved destroy plan, mỗi root 10 tài nguyên. Medium hoàn tất 72 tài nguyên; chỉ gỡ bảo vệ trong root cleanup riêng sau khi backup nhất quán đã được tải/kiểm. Root chuẩn trong Git vẫn có RDS deletion protection và EFS prevent_destroy.

Plan medium trước đó kẹt hơn 30 phút ở GetSecretValue. Đã xác minh/dừng đúng process và giải phóng đúng lock `OperationTypePlan` của chính phiên này. Root cleanup riêng bỏ việc đọc token Redis, giữ nguyên auth token bằng ignore_changes; plan bảo vệ chỉ có một cập nhật RDS. Không đổi token hoặc runtime đang chạy. Sau đó saved destroy plan được kiểm account/project/hash rồi áp dụng.

Support đã xóa 16 tài nguyên qua Terraform. Endpoint Secrets Manager từ máy vẫn timeout nên bốn secret được lên lịch xóa bằng Lambda tạm trong cùng account. Role chỉ có DeleteSecret/DescribeSecret cho đúng bốn ARN và ListSecrets để kiểm kê, không có GetSecretValue. Audit xác nhận không còn secret active; sau đó xóa Lambda/role/policy. Các secret đã đánh dấu xóa **không tính phí trong recovery window**, theo [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_delete-secret.html).

Không ghi support Terraform apply là hoàn tất 20 tài nguyên: local cleanup state còn giữ bốn ID secret đã scheduled để đối chiếu. Không xóa/chỉnh state nhằm bỏ quên tài nguyên. Khi endpoint hoạt động lại hoặc sau recovery window, có thể refresh đúng cleanup state để đối chiếu việc xóa hẳn. Support plan cuối dùng `-refresh=false` sau khi xác minh account, backup và inventory; chỉ gồm delete đúng project, không bỏ khóa hoặc dùng `-target`.

Saved plans, state và logs ở `.work/medium-live/cleanup-all/`, `cleanup-medium-retry.log`, `cleanup-support-retry.log`, `cleanup-secrets-lambda.log` và `cleanup-verification.log`. Giữ riêng các file này; state/plan có thể chứa dữ liệu nhạy cảm.

## Backup và image đã giữ riêng

Thư mục trên máy triển khai: `.work/medium-live/private/offline-20261110/`, không nằm trong Git.

- Medium: dừng/drain cron, giữ operation lock, chặn web writer và runtime DB; backup cuối `moodle-n2-dev-med/20261109T185426`, SSM `024bd9e5-67aa-4940-ace5-7cc0da03f1ae` thành công. Bốn bộ backup medium đã tải xuống và kiểm SHA-256 DB/file theo manifest.
- Small: backup cuối `20261109T185518Z`, SSM `abb9ddf1-812d-403e-894a-3fa68b6c8d72` thành công. Hash archive: `ffa69f97ec51e71b139af9928f42ce5b9a366a04a85fdead1946c28be72c37cc`.
- Có artifact bundle, state đã lưu trước cleanup, bản state cuối small/builder/support, image runtime export và metadata kiểm tar/SHA-256. Xem `archive-verified.json` và `runtime-archive.json` trong thư mục riêng.

Backup cuối này **chưa được restore-test**. Lượt restore medium trước đã có bằng chứng riêng, không tự chứng nhận bộ cuối. Cloud backup/artifact đã xóa để ngừng phí; muốn phục hồi cần nhận bản offline qua kênh riêng, tạo lại prerequisite và kiểm tương thích source/digest theo [hướng dẫn N3](14-n3-acceptance-guide.md).

Tên Dynu miễn phí được giữ để dùng lại. Lần deploy sau phải tạo ACM/AMI/bucket/ECR/secret và cập nhật DNS tới ALB mới; không dùng nguyên ARN/ID/URL cũ như một môi trường còn hoạt động.
