# Bằng chứng rà soát cuối — 14/11/2026

Source được kiểm tra: `2130963f7fc3fd76007498ab766a0942b9db3f59`. Phạm vi live: small Sydney của nhóm, profile `moodle-project`. Các file trong thư mục này không chứa mật khẩu, cookie, token, Terraform state hoặc payload backup.

## Kiểm tra hiện tại

| Nội dung | Kết quả | Bằng chứng |
|---|---|---|
| CI đúng commit | Success; unit, runtime small/medium, backup/restore local, Terraform validate/mock tests và Bash syntax đều đạt | [Metadata CI](ci.json), [GitHub Actions](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/43480887498) |
| Small dev | Health và nghiệp vụ đạt: login các role, học liệu/hash, bài nộp/điểm, quyền riêng tư, logout | [dev-acceptance.json](dev-acceptance.json) |
| Small staging | Bộ kiểm tra tương tự đạt trên dữ liệu đã phục hồi trước đây | [staging-acceptance.json](staging-acceptance.json) |
| Cron | Scheduled task vừa chạy; scheduled/adhoc failure đều 0 ở thời điểm kiểm tra | [dev](dev-operations.json), [staging](staging-operations.json) |
| Backup tự động ngày 14/11 | Service success, exit 0; local checksum/format/archive verification đạt; có manifest S3 của cả hai site | [dev manifest](moodle-sydney-dev-backup-manifest.json), [staging manifest](moodle-sydney-staging-backup-manifest.json) |
| AWS inventory | Bốn EC2 running tại snapshot đầu; dev/staging cùng hai máy tạm. Sydney không có RDS/ALB/EFS/Redis/NAT trong các API đã kiểm | [inventory](sydney-inventory.json) |
| Chi phí | Usage trước credit/refund 27,3117946308 USD trong cửa sổ 01/10–14/11 exclusive, scope toàn account Sydney; số liệu Estimated | [cost-summary.json](cost-summary.json) |

Backup ngày 14/11 **chưa restore-test chính bộ đó**. Kiểm tra checksum không thay thế diễn tập restore. Dev/staging được kiểm tra bằng source verifier hiện tại, không apply lại EC2 hoặc xác nhận runtime đã được build từ commit tích hợp.

## Khép lại hồ sơ ma trận Sydney ngày 07/11

Ngày 14/11 đã lấy lại từ S3 lượt 50-user r3, timeline hoàn tất, tooling manifest và metric cũ. Đây là **thu hồi bằng chứng của lượt chạy ngày 07/11**, không phải một benchmark mới.

| User | Lượt | Sample JTL | Lỗi | Course p95 steady (ms) | Login p95 steady (ms) | Assignment p95 steady (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1 | 1701 | 0 | 141 | 385 | 188 |
| 10 | 2 | 1766 | 0 | 137 | 369 | 171 |
| 10 | 3 | 1784 | 0 | 136 | 327 | 164 |
| 25 | 1 | 4517 | 0 | 197 | 476 | 239 |
| 25 | 2 | 4557 | 0 | 216 | 552 | 254 |
| 25 | 3 | 4543 | 0 | 197 | 497 | 269 |
| 50 | 1 | 13394 | 0 | 431 | 991 | 475 |
| 50 | 2 | 13242 | 0 | 412 | 1085 | 529 |
| 50 | 3 | 13318 | 0 | 464 | 1174 | 566 |

Số user quan sát bằng số yêu cầu, từng lượt đủ thời lượng theo bộ kiểm tra. Các p95 trên lấy từ **steady**, khác bảng p95 toàn lượt trong biên bản cũ. Sample JTL có transaction cha/con; không cộng thành số hành động độc lập.

- Workload: 60% course, 20% download, 10% assignment view, 10% auth cycle theo logical actions; think time và đường private VPC như runbook; không ghi bài nộp và không đo render trình duyệt.
- [Timeline](sydney-load-progress.jsonl): matrix kết thúc `passed` lúc `2026-11-07T18:01:09.747459+00:00`.
- [CSV kết quả](sydney-load-matrix.csv), [metric tổng hợp](sydney-load-analysis.json), [tooling hashes](sydney-load-tooling.json), các file `users-*-summary.json` trong thư mục này.
- Metric OS được ghép theo khoảng runner start/end, bao gồm ramp; chu kỳ khoảng 15 giây. Có 664 dòng trong bộ thu, không có lỗi sampler/DB. RAM max trong các lượt là 41,093%, swap và task failures đều 0; CPU tăng theo tải, không đủ để kết luận nút thắt tối đa.
- [CloudWatch CPU credit](sydney-load-cpu-credits.json): 30 điểm 5 phút, minimum 537,5462783666667; credit chưa cạn trong cửa sổ Sydney. Không suy nguyên nhân CPU credit cho lượt N3 ở account khác từ số liệu này.

Kết luận giới hạn: Sydney đạt các assertion và p95 ba giao dịch hiển thị dưới 3 giây trong chín lượt đã đo. Điều này không bảo đảm tải dài hạn, nhiều upload/submission đồng thời, site có dữ liệu lớn hoặc mọi cấu hình `t3.small`. Hồ sơ [N3 riêng](../aws-n3-2026-11-11/README.md) vẫn có hai lượt 50-user không đạt độ trễ; giữ nguyên kết quả đó.

## Phạm vi và điểm chưa đóng

- Singapore trong **account Sydney** bị tổ chức từ chối qua SCP; không né chính sách và không chứng nhận inventory region đó. Hai account N2/N3 khác chưa được truy cập lại.
- Chi phí chỉ là account Sydney; chưa tổng hợp chi phí N2/N3, không coi credit là không phát sinh usage, không coi Estimated là hóa đơn cuối.
- CI không phải live deploy medium. Bằng chứng medium/GUI ngày 09–10/11 vẫn là hồ sơ lịch sử, lab đó đã cleanup.
- Chưa có walkthrough GUI small mới và chữ ký người kiểm tra độc lập. Không ký thay nhóm.
- [Thời gian cài từng pha](installation-report.json) là lượt do agent thực hiện và có khoảng nghỉ; không dùng tổng pha remote 343,509 giây để suy mức tăng tốc so với cài tự động.

Các checksum trong [checksums.json](checksums.json) ghi nhận các tệp dữ liệu JSON/JSONL/CSV của bộ evidence tại lần đóng gói cuối; không tự hash tệp checksum. [Kết quả kiểm tra hồ sơ](verification.json) xác nhận link tài liệu, cấu trúc dữ liệu, số liệu bảng tải và kiểm tra mẫu secret của các tệp mới.
