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

Ngày 09/11/2026 đã triển khai thật, release/schema thành công, chạy fixture teacher/student, thử thay app, tạo backup S3 và restore sang medium mới. Người dùng yêu cầu **giữ lab chính chạy để xem/demo** sau nghiệm thu; chưa có lịch tự hủy. Môi trường restore được dọn riêng sau khi kiểm tra đạt. Metadata, state/plan, log đầy đủ ở `.work/medium-live/`; chỉ chia sẻ các bằng chứng đã lọc trong [thư mục evidence](evidence/medium-2026-11-09/README.md).

## Môi trường demo chính

| Thành phần | Giá trị đã xác minh |
|---|---|
| URL | **https://d30wbiaf9ui8kr.cloudfront.net** |
| Project/region | `moodle-n2` / `ap-southeast-1` |
| ASG | `moodle-n2-dev-med-app`, min/desired 2, max 3; stickiness tắt |
| App sau thay node | `i-09fe1690ecdc65e47`, `i-0b88ff68eca9f7cdf` |
| Runner | `i-0ead190c8db53bdd6`; chỉ runner bật cron/backup timer |
| Database | RDS PostgreSQL **16.13**, private, encrypted, deletion protection bật |
| EFS | `fs-05678c2b60740bcde`, hai mount target, TLS/IAM, UID/GID 33 |
| Cache/session | Hai ElastiCache Redis riêng, TLS/AUTH, encrypted |
| CloudFront | `E10U8JR1BO5DY7`, HTTPS viewer, caching disabled; origin ALB HTTP giới hạn CloudFront prefix list |
| AMI | `ami-02954da0a202bfcf2`, Ubuntu 26.04 amd64 đã chuẩn bị runtime |
| Release | `87da9a6a37239090b1113349a850b50375126811` |
| Image | `860366539351.dkr.ecr.ap-southeast-1.amazonaws.com/moodle-n2-dev/moodle@sha256:547a6dcc97533d4a0bead1a6185db4640f1bc5f6e8ba25a19a4ea0e7d06ee130` |
| Bundle SHA-256 | `a5ec8210a307fc409fdb8caab503da59e04f8674754eae81c9072a9d30625604` |
| CloudWatch | `/moodle/moodle-n2-dev-med`, log bootstrap/web/operation, metric host/cron/backup và alarms |

Inventory có route, SG, listener, IP, target health, cache policy và log thực: [inventory.json](evidence/medium-2026-11-09/inventory.json). DB/cache/egress vẫn là điểm lỗi đơn của lab P1; chưa tuyên bố HA toàn hệ thống.

Tài khoản demo được giữ tại **`.work/medium-live/private/demo-accounts.json`** trên máy triển khai, thư mục có ACL riêng cho người dùng Windows và SYSTEM. File chứa admin và bốn tài khoản fixture; không commit/upload/chụp lại mật khẩu. Đổi mật khẩu admin khi tiếp nhận và giữ file này riêng. Cookie/token không lưu trong evidence.

Kịch bản demo: teacher `cloud_teacher` vào `CLOUD-C01`, mở hai học liệu và assignment; student A/B xem bài/điểm/phản hồi của mình; student C chỉ thuộc `CLOUD-C02`. Hai course đều private, guest bị tắt. Điểm mẫu A **93**, B **85**. File gồm văn bản và nhị phân, tên tiếng Việt/khoảng trắng.

## Bằng chứng thực chạy

| Phạm vi | Kết quả và giới hạn |
|---|---|
| LMS | **47/47 kiểm tra HTTPS đạt ở nguồn**, **47/47 sau restore**: admin/teacher/student login, sai mật khẩu, quyền course, học liệu/bài nộp đúng SHA-256, điểm/phản hồi riêng, student không chỉnh course/truy cập admin, logout và replay cookie cũ bị từ chối |
| MED-01,03 | Compute private; route/SG và hai AZ được lưu; kết nối từ chính driver Moodle là `pgsql`, `verify-full`, **TLS 1.3**; runtime/migration/master tách credential |
| MED-04,05,07 | ASG thay `i-02989bad4c677f72b` bằng `i-09fe1690ecdc65e47` trong khoảng **96 giây**; cookie sinh viên giữ nguyên, file đúng hash; hai app có cùng image digest. Log riêng từng node xác nhận file đã được phục vụ trên cả hai |
| MED-06 | MUC ghi A → đọc B đạt; purge dưới operation lock rồi **20 lượt** tải file bằng chính cookie trước purge đều đạt |
| MED-08 | App timer cron disabled; cron runner có task hoàn tất thực, audit `scheduled_failures=0`, `adhoc_failures=0`, `adhoc_overdue_10m=0`. Tranh cùng Moodle Lock API giữa app/runner: một `ACQUIRED`, một `BUSY` |
| MED-09,10 | Release/schema runner thành công lúc `15:20:54Z`; release cạnh tranh bị từ chối trước maintenance. Khi giữ maintenance và khởi động app, cả hai node trả **503** ở `/login/index.php` và `/_ready.php`; sau unblock phục hồi |
| MED-11 | Seed fixture tương đương độc lập bằng Moodle API; không gọi đây là di chuyển từ small. Bộ fixture/IDs được lưu và dùng nguyên để kiểm thử restore |
| MED-12 | Backup khi đã chặn web, dừng cron, runtime DB NOLOGIN và terminate runtime connections; restore dump+EFS+artifact/config tham chiếu vào DB/EFS mới, đổi URL qua Moodle CLI, tạo MUC đích, giữ maintenance đến kiểm tra ID/điểm xong |
| CLI state | Medium dùng S3 state/key riêng theo account/project/environment, lockfile bật. Plan thứ hai trong lúc apply thật nhận **S3 HTTP 412 PreconditionFailed**, không ghi đè state |

Các kết quả là bằng chứng triển khai N2, để N3 kiểm tra lại và chốt nghiệm thu. **MED-02 còn chờ domain/ACM/HTTPS tại ALB** theo lựa chọn lab tạm. Chưa có bằng chứng trình duyệt desktop/mobile, upload lớn/vượt 64 MiB, benchmark small/medium, báo cáo chi phí thực, toàn bộ ca phá dependency/CA sai trên AWS và khôi phục sau gián đoạn migration. Không đánh dấu toàn bộ LMS-03/LMS-06/OPS hoặc tất cả tiêu chí P1 đạt từ 47 kiểm tra HTTP này. Bộ kiểm tra local có thêm ca readiness/Redis lỗi; chúng không thay thế nghiệm thu AWS.

## Backup và diễn tập restore

Backup: `s3://moodle-n2-dev-860366539351-ap-southeast-1-backups/moodle-n2-dev-med/20261109T154309`.

- Maintenance nguồn: `15:42:59Z`; writer dừng: `15:43:08Z`; dump/archive bắt đầu `15:43:09Z`; manifest đã lên S3 `15:43:15Z`; nguồn mở lại `15:43:19Z` (khoảng **20 giây** maintenance).
- Có `database.dump` (1,914,242 byte), `moodledata.tar.gz` (162,497 byte), `manifest.json`; bucket versioning/encryption bật. Hash hai payload và artifact ở [backup.json](evidence/medium-2026-11-09/backup.json).
- Project đích `moodle-n2-restore`, VPC `10.45.0.0/16`, state key/DB/EFS/Redis/secret riêng; dùng chính image nguồn. URL khi kiểm thử: `https://d318ck82a5ict7.cloudfront.net` (sẽ không còn dùng sau cleanup).
- Restore bắt đầu `15:52:23Z`, nạp xong vẫn maintenance `15:53:25Z`; xác minh course IDs 2/3, user IDs 3/4/5/6, submission IDs 1/2, điểm 93/85; mở lại `15:53:31Z`. Pha restore/resume khoảng **68 giây**, chưa tính dựng hạ tầng.
- Từ apply đích bắt đầu `15:40:30Z` tới hoàn tất toàn bộ 47 kiểm tra HTTPS `15:55:04Z` khoảng **14 phút 34 giây**. Đây là thời gian quan sát của đợt drill, có cả chờ vận hành, không phải SLA/RTO cam kết.
- Tuổi điểm backup tại lúc bắt đầu restore khoảng **9 phút 14 giây**. Chưa có chuỗi giao dịch mới sau backup để đo mất dữ liệu; không suy ra RPO bằng 0 từ fixture tĩnh.
- Cùng phiên HTTPS sau restore đi qua cả hai app và file có hash đúng; [nodes.json](evidence/medium-2026-11-09/nodes.json) chứa sample log nội bộ. Redis mới cần đăng nhập lại; không phục hồi cookie từ Redis nguồn.

## Cleanup và trạng thái tính phí

Sau khi kiểm tra restore đạt, đã dùng bản Terraform riêng trỏ đúng backend/key của `moodle-n2-restore`, lập plan chỉ đổi bảo vệ RDS, rồi saved destroy plan **71 tài nguyên**. Terraform xác nhận `0 added, 0 changed, 71 destroyed`. Kiểm kê AWS sau cleanup ở [cleanup.json](evidence/medium-2026-11-09/cleanup.json): không còn app/runner, VPC, ASG, DB, Redis, EFS hoặc CloudFront của môi trường tạm; snapshot RDS cuối được giữ, bốn secret tạm đặt lịch xóa với 7 ngày phục hồi. Không gỡ bảo vệ hay xóa tài nguyên lab nguồn.

**Lab chính vẫn chạy và phát sinh phí theo yêu cầu người dùng**, chưa có lịch tự dừng/hủy. Bucket state/artifact/backup, image ECR, AMI/snapshot và log được giữ để tái lập/khôi phục; builder EC2 đang stopped, vẫn còn disk/snapshot. Snapshot cuối của restore cũng còn storage charge. Không coi cleanup môi trường tạm là ngừng toàn bộ chi phí AWS; khi demo xong dùng quy trình cleanup có backup/plan trong [runbook N2](10-medium-n2.md).

## Chạy lại fixture và kiểm tra HTTPS

YAML thật trên máy: `.work/medium-live/medium.yaml`. File này chỉ chứa ARN/reference; state/plan vẫn có thể chứa secret và không được chia sẻ.

```powershell
# Chỉ dùng trên lab đã release thành công; giữ nguyên fixture nếu đã tồn tại.
python -m scripts.acceptance.aws_seed --config .work/medium-live/medium.yaml --confirm moodle-n2-dev --output .work/medium-live/fixture-source.json
python -m scripts.acceptance.http_check --url https://d30wbiaf9ui8kr.cloudfront.net --fixture .work/medium-live/fixture-source.json --admin-credentials .work/medium-live/private/initial-admin.json --output .work/medium-live/acceptance-source.json
python -m src.moodle_cloud --config .work/medium-live/medium.yaml status
```

Không chạy seed ở đích trước restore. `aws_seed` xác minh account/runner tags, dừng timer và đợi cron hiện tại kết thúc, giữ chung operation lock, chạy API với đúng teacher/student capability; chỉ xuất ID/hash. Mật khẩu fixture suy ra từ secret khởi tạo trong runner, không in log. Đã chạy lại công cụ trên AWS: manifest giữ nguyên hoàn toàn. Nếu đã đổi mật khẩu demo, cần dùng credential kiểm thử phù hợp; bộ HTTP hiện dùng secret khởi tạo riêng để suy ra mật khẩu fixture.

## Các lỗi thực tế đã xử lý

- RDS managed master không có quyền sửa default privileges của migration role như PostgreSQL superuser: cấp quyền từ chính migration owner, chỉ với đối tượng `mdl_` thuộc owner đó.
- ASG lần đầu gặp độ trễ service-linked role: tạo role riêng trước ASG; giữ state, đối chiếu tài nguyên thật và lập plan khôi phục thay vì xóa state/data.
- Moodle CLI kiểm phiên bản cần `MATURITY_STABLE`; pipeline release sửa kiểm tra standalone, ghim Moodle commit và image digest.
- User fixture thiếu `mnethostid` không login được: đặt local MNet host khi tạo, sửa đúng user fixture cũ mà không reset password/IDs.

Mã runtime đang chạy là commit `87da9a6...`; các sửa fixture/công cụ nghiệm thu/tài liệu sau đó không thay image runtime. Có 40 unit test và 2 Terraform mock test đạt; xem [kiểm tra local](11-medium-validation.md). Chưa có bằng chứng GitHub Actions remote hoặc push: remote trước đó trả 404, công việc giữ trên nhánh local `n2-medium-lab`.
