# MED-02 — Domain miễn phí và HTTPS tại ALB

**Vòng đời sau nghiệm thu:** người dùng đã yêu cầu cleanup AWS. URL và IDs trong bài là dữ liệu của lượt nghiệm thu, không bảo đảm còn hoạt động; xem [trạng thái cleanup](15-aws-cleanup.md) và [dựng lại cho N3](14-n3-acceptance-guide.md).

Ngày nghiệm thu triển khai N2: **10/11/2026, giờ Việt Nam**. Trạng thái: **Đạt trong lượt kiểm tra này**, có hồ sơ để N3 kiểm tra lại. Các sự kiện AWS ghi UTC vào tối 09/11/2026.

URL hiện tại: **https://www.moodle-cloud-distribution.mywire.org**.

## Domain và chứng chỉ

- Đã tạo hostname miễn phí `moodle-cloud-distribution.mywire.org` trong tài khoản Dynu của người dùng; đây là subdomain được cấp quyền quản lý DNS, không phải mua tên miền cấp hai.
- Host `www` dùng CNAME trỏ thẳng tới `moodle-n2-dev-med-850643930.ap-southeast-1.elb.amazonaws.com`; không cố định IP của ALB. TTL 120 giây.
- ACM region **ap-southeast-1**, trạng thái **ISSUED**, bao phủ đúng `www.moodle-cloud-distribution.mywire.org`.
- Certificate ARN: `arn:aws:acm:ap-southeast-1:860366539351:certificate/f50651fc-3d2c-4b9f-9674-3947a2182036`.
- CNAME xác thực `_28219c134d281f5a2c416ea86b53db9f.www.moodle-cloud-distribution.mywire.org` trỏ tới `_d7a1bfab35e3fe588a32d3229dbe7429.wzccmgtwzk.acm-validations.aws`.
- ALB listener **443/HTTPS** gắn chứng chỉ này, policy `ELBSecurityPolicy-TLS13-1-2-2021-06`. Listener **80/HTTP** redirect 301 sang HTTPS, giữ path/query. Header Location có thể ghi rõ `:443`, tương đương cổng HTTPS mặc định.
- Đã gỡ CloudFront tạm `E10U8JR1BO5DY7` khỏi hạ tầng. Cấu hình hiện dùng `frontend: acm`, DNS ngoài Route 53 (`hosted_zone_id: ""`).

Tên truy cập/DNS được tạo bằng gói Dynu miễn phí; không đăng ký domain trả phí qua AWS. Hạ tầng EC2/ALB/RDS/EFS/Redis/NAT và storage vẫn tính phí, đang được giữ chạy theo yêu cầu người dùng. ACM public certificate dùng trực tiếp trong ALB, không yêu cầu export private key.

## Chuyển đổi có kiểm soát

Giữ nguyên RDS `moodle-n2-dev-med`, EFS `fs-05678c2b60740bcde`, hai Redis và artifact release `87da9a6a37239090b1113349a850b50375126811`. Saved plan chỉ tạo listener/rule mới, cập nhật listener/launch template/ASG, thay runner và gỡ CloudFront; không thay hoặc xóa dịch vụ dữ liệu.

1. Xác thực hai CNAME trên DNS công khai và đợi ACM `ISSUED`; validate YAML và review saved plan.
2. Dừng lịch cron/backup, đợi job hiện tại kết thúc; giữ chung operation lock, chặn web writer qua SSM, runtime DB NOLOGIN và terminate runtime connections.
3. Tạo backup nhất quán cuối tại `s3://moodle-n2-dev-860366539351-ap-southeast-1-backups/moodle-n2-dev-med/20261109T180717`.
4. Giữ maintenance qua Terraform apply và rolling refresh. Đợi cả hai app dùng launch template version **3**, cloud-init hoàn tất, EFS mount thành công và `wwwroot` đúng URL mới.
5. Runner mới giữ operation lock; kiểm tra các cột DB chứa URL cũ và độ dài sau thay. Dùng **Moodle tool replace CLI** đổi URL, rồi tạo lại MUC mapping, purge cache, kiểm tra TLS RDS và publish URL mới trước khi bỏ maintenance.

Moodle CLI yêu cầu `--shorten` để chấp nhận URL đích dài hơn; trước khi chạy đã kiểm tra không có giá trị nào vượt chiều dài cột. Các bảng/cột mà Moodle cố ý bỏ qua (ví dụ log lịch sử) được đối chiếu riêng; không thay chuỗi mù trong dump hoặc cắt bớt dữ liệu.

Maintenance bắt đầu `18:07:08Z`, cutover hoàn tất `18:20:31Z`, khoảng **13 phút 23 giây**, gồm thời gian AWS gỡ CloudFront và rolling app. Đây là đợt đổi URL có downtime của lab, không phải cam kết HA.

Runner hiện tại: `i-03cc4bc46f65f8b67`. Hai app sau chuyển đổi: `i-0e109bdc77ae51d99`, `i-078a1b5fb14d960fb`; cả hai healthy. ASG refresh đã `Successful`, 100%, không còn instance chờ cập nhật.

## Kết quả nghiệm thu

| Tiêu chí | Kết quả thực chạy |
|---|---|
| DNS/ACM/listener | CNAME trỏ trực tiếp ALB; DNS validation thành công; đúng chứng chỉ và region tại listener 443 |
| TLS public | **TLS 1.3**, xác minh CA chain và hostname bằng SSL context mặc định; không bỏ qua lỗi chứng chỉ |
| HTTP → HTTPS | 301 tới đúng hostname/path/query HTTPS, không redirect loop trong các luồng kiểm tra |
| Proxy/session | URL login/course/assignment dùng HTTPS đúng hostname; session cookie **Secure + HttpOnly**, thuộc đúng host; HSTS có mặt |
| Mixed content | Không có asset/form HTTP trong HTML login/course/assignment đã kiểm tra; theme/file hiển thị trong Chromium |
| LMS sau đổi URL | **47/47 ca đạt**: admin/teacher/student, quyền course/file/bài nộp/điểm, logout và replay cookie |
| Kiểm tra HTTPS riêng | **16/16 ca đạt**: DNS, TLS, redirect, cookie và URL/asset/form |
| Upload qua trình duyệt | Teacher upload `Kiểm tra HTTPS.txt`, 64 byte, lưu resource cmid **6** tại C01; student A tải lại có SHA-256 trùng; guest và student C bị từ chối |
| Walkthrough | Chrome **156.0.8078.80** trên Windows: teacher 1440×1000, student A 390×844; course, bài nộp, điểm 93 và phản hồi riêng hiển thị |

Màn hình hẹp được kiểm tra bằng viewport Chromium, chưa phải thiết bị di động thật/Safari. Bảng trạng thái bài nộp của Moodle có vùng cuộn ngang trên viewport 390 px; không tuyên bố mọi trình duyệt/thiết bị đều đã được thử. Ca upload lớn/vượt giới hạn 64 MiB, đo tải và các ca lỗi còn lại vẫn cần N3 nghiệm thu riêng.

Hồ sơ: [thư mục bằng chứng MED-02](evidence/medium-med02-2026-11-10/README.md). Các ảnh chỉ chứa fixture giả lập, không chứa password/cookie. Tài khoản Moodle giữ nguyên; URL trong file `.work/medium-live/private/demo-accounts.json` đã được cập nhật. Credential Dynu nằm riêng tại `.work/medium-live/private/dynu-account.json`, không commit.

## Chạy lại kiểm tra

YAML hiện hành trên máy: `.work/medium-live/medium.yaml`; bản trước chuyển đổi là `.work/medium-live/medium-before-med02.yaml`. Không apply lại cấu hình CloudFront cũ khi site đã dùng URL mới nếu chưa có kế hoạch chuyển ngược và backup.

```powershell
python -m src.moodle_cloud --config .work/medium-live/medium.yaml status
python -m scripts.acceptance.http_check --url https://www.moodle-cloud-distribution.mywire.org --fixture .work/medium-live/fixture-source.json --admin-credentials .work/medium-live/private/initial-admin.json --output .work/medium-live/med02-http.json
python -m scripts.acceptance.https_check --url https://www.moodle-cloud-distribution.mywire.org --alb-dns moodle-n2-dev-med-850643930.ap-southeast-1.elb.amazonaws.com --fixture .work/medium-live/fixture-source.json --admin-credentials .work/medium-live/private/initial-admin.json --output .work/medium-live/med02-https.json
```

Giữ CNAME xác thực ACM để hỗ trợ gia hạn chứng chỉ; quản lý hostname tại Dynu. Nếu thay ALB sau này, cập nhật CNAME phục vụ tới DNS ALB mới. Chứng chỉ được tạo ngoài root Terraform medium và được tham chiếu bằng ARN; khi cleanup phải kiểm kê thêm ACM và DNS ngoài AWS. Không chia sẻ state/plan hoặc profile trình duyệt trong `.work/`.
