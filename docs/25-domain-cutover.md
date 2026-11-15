# Chuyển tên miền Dynu sang medium Sydney

Chủ dự án chọn giữ `www.moodle-cloud-distribution.mywire.org`, không mua tên miền mới. DNS đã được xác minh lại trên nameserver Dynu và resolver công khai: `www` trỏ ALB Sydney.

**Đã hoàn tất chuyển đổi:** 47/47 ca nghiệp vụ, ba tài khoản demo và 11 kiểm tra HTTPS/redirect đạt. Hai app cùng runner mới bootstrap đúng URL/release; ASG refresh Successful, hai target healthy, cron không failure/backlog và full plan không drift. [Bộ bằng chứng](evidence/current-review-2026-11-15/README.md). Các bước dưới đây mô tả quy trình đã thực hiện và cách vận hành về sau.

## DNS cần giữ

| Hostname đầy đủ | Type | Giá trị |
|---|---|---|
| `www.moodle-cloud-distribution.mywire.org` | CNAME | `moodle-medium-dev-med-22320273.ap-southeast-2.elb.amazonaws.com` |
| `_820839ba6c83fb16217fe1776a5c026a.www.moodle-cloud-distribution.mywire.org` | CNAME | `_2db810396b116fa11207985f13345dc4.wzccmgtwzk.acm-validations.aws` |

Trong Dynu, Node Name của website là `www`. Bản ghi `_...` xác minh chứng chỉ, không dùng để chuyển website. Bản ghi xác minh lịch sử `_28219c134d281f5a2c416ea86b53db9f.www...` có giá trị gốc `_d7a1bfab35e3fe588a32d3229dbe7429.wzccmgtwzk.acm-validations.aws`, theo [hồ sơ N2](evidence/medium-med02-2026-11-10/certificate.json).

ACM Sydney đã trả `ISSUED`, validation `SUCCESS`; listener 443 dùng chứng chỉ `8a051ea8-60ae-4589-ab39-7a44b6bea671`. Probe trước chuyển canonical URL xác minh TLS thành công, HTTP 303 sang URL CloudFront cũ; chưa coi đây là nghiệm thu nghiệp vụ trên tên miền.

## Cấu hình chuyển đổi

```yaml
frontend: acm
domain: your-owned-hostname.example
wwwroot: https://your-owned-hostname.example
retain_cloudfront: true
app_requests_per_target: 200
```

`retain_cloudfront` mặc định false. Khi chuyển từ CloudFront sang ACM, bật true để giữ distribution cùng URL đã bàn giao. Listener HTTP chuyển về hostname sở hữu trên HTTPS, giữ path/query. Không giữ Host CloudFront trong redirect vì sẽ tạo vòng lặp. CloudFront cũ trở thành đường chuyển hướng; tên miền mới đi trực tiếp tới ALB 443. Đường legacy CloudFront vẫn dùng origin HTTP để nhận redirect, không tuyên bố mọi chặng legacy đều mã hóa.

YAML live cho cutover: `.work/medium-sydney-live/medium-domain.yaml`. Không áp dụng lại cấu hình CloudFront thuần sau cutover. State/plan/secret giữ ngoài Git.

## Trình tự và rollback

1. Kiểm tra DNS/ACM/TLS; thêm listener/ingress 443 bằng targeted saved plan hai tài nguyên. Đây là giai đoạn chuyển tiếp, phải review full plan sau đó.
2. Dừng cron timer và đợi service hoàn tất. Cron có thể chờ task thêm 180 giây sau khi xử lý hết; không giết tiến trình chỉ để lấy lock.
3. Backup nhất quán hoàn tất tại `s3://moodle-medium-dev-828676179987-ap-southeast-2-backups/moodle-medium-dev-med/20261114T200711`. Bộ này phục vụ rollback; không tự coi nó đã restore-test.
4. Review full plan: giữ DB/EFS/Redis/CloudFront; chỉ wwwroot đổi trong user-data. Runner được thay, launch template/ASG rollout và dashboard/runner alarm theo ID mới. Bật maintenance/fence writer trước apply.
5. Đợi runner bootstrap/SSM, mọi app nhận đúng template/wwwroot, ASG refresh hoàn tất. Resume bằng runner mới sau khi kiểm tra không có migration/worker dở dang; kiểm tra cron/backup timers.
6. Chạy HTTPS acceptance, quyền/hash/file/bài nộp/điểm, cookie và redirect. Chỉ đóng MED-02 khi có đủ kết quả.

Nếu apply lỗi, giữ maintenance và điều tra trước resume. Không chạy lại install hoặc đổi artifact để sửa URL. Rollback cấu hình phải xét wwwroot mọi node và URL trong nội dung; backup nguyên vẹn còn ở S3. Không migration schema trong cutover. Không đổi CNAME về ALB Singapore đã cleanup để làm rollback.

Hướng dẫn: [Dynu CNAME](https://www.dynu.com/Resources/Tutorials/DynamicDNS/CreateCNAMERecord), [ACM DNS validation](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html).
