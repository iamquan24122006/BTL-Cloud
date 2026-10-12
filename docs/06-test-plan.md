# Kiểm thử và bằng chứng nghiệm thu

## 1. Kiểm tra cục bộ

```powershell
python -m unittest discover -s tests -v
python -m src.moodle_cloud validate
terraform fmt -check -recursive infra
terraform -chdir=infra/small init -backend=false -input=false
terraform -chdir=infra/small validate
terraform -chdir=infra/small test
```

Terraform test dùng `mock_provider "aws"`; không tạo AWS resource. Nó kiểm tra không có ingress, IMDSv2, EBS encryption, kích thước user-data và phạm vi S3 IAM. Không thay thế kiểm tra AMI boot, IAM thực tế hoặc cloud-init.

Unit test kiểm tra đầu vào và chốt apply/destroy. Test AWS call dùng mock, không chứng minh account hiện tại có quyền deploy. CI còn build image PHP 8.3, kiểm tra extension/Apache config và lint PHP bằng chính runtime đó; không chứa AWS credential hay bước deploy tự động. Build thành công chưa chứng minh host Ubuntu 26.04, systemd, kết nối DB và Moodle đã chạy được.

## 2. Kiểm tra chức năng trên AWS

| ID | Thao tác | Kết quả phải có | Bằng chứng |
|---|---|---|---|
| F01 | Deploy vào EC2 sạch | cloud-init hoàn tất, health pass | Mã lần chạy, log đã lọc |
| F02 | Admin đăng nhập, đổi password | Thành công, không lộ credential | Ảnh dashboard |
| F03 | Tạo course và student giả, enrol | Student truy cập đúng course | Ảnh/course ID |
| F04 | Upload, download file mẫu | Hash SHA-256 trùng nguồn | Hash trước/sau |
| F05 | Student nộp bài, teacher xem | Quyền và file đúng | Ảnh thao tác |
| F06 | Chạy cron và đọc journal | Scheduled task hoàn tất | Journal + trang tasks |
| F07 | Request `/.git/config`, `/config.php` qua tunnel | 403/404, không lộ nội dung | HTTP status |
| F08 | Kiểm tra quyền OS | Web user không ghi code/config, ghi dataroot được | Kết quả `test -w` |
| F09 | Plan lần hai | Đọc diff; giải thích nếu AMI lookup thay đổi | Saved plan (giữ riêng tư) |
| F10 | Backup, restore sang staging | Course/file/user đầy đủ, health và cron pass | Biên bản restore |
| F11 | Destroy lab đã backup | Resource thuộc state được xóa | Kiểm kê AWS sau cleanup |
| F12 | Kiểm tra host/runtime sau boot | Ubuntu 26.04, PHP 8.3, PG16, web và CLI cùng image ID | OS/version, image ID và health |
| F13 | Reboot EC2 trong staging | Web và cron tự khởi động, login/upload được | Systemd journal, thao tác sau reboot |

Các ảnh/log phải có thời điểm và cấu hình tương ứng. Bỏ password, cookie, authorization header, session token và nội dung cá nhân.

## 3. Dữ liệu và kịch bản tải

Chỉ tạo dữ liệu ở staging với tài khoản giả. Moodle có Test course generator và JMeter test plan generator. Generator cần developer debugging và không dành cho site live; bật để tạo dữ liệu, sau đó trả debugging về baseline trước đo. [Test course generator](https://docs.moodle.org/405/en/Test_course_generator)

1. Vào Site administration → Development → Make test course, bắt đầu size S và giới hạn dung lượng phù hợp.
2. Tạo JMeter test plan cho course đó; xem `admin/tool/generator/cli/maketestplan.php --help` nếu dùng CLI. [JMeter generator](https://docs.moodle.org/405/en/JMeter_test_plan_generator)
3. Chạy 1 user, kiểm tra cookie, CSRF/login token và assertion xác nhận đã vào course. HTTP 200 có thể vẫn là trang lỗi hoặc login, nên không chỉ đo status code.
4. Dùng nhiều user khác nhau; tránh cho toàn bộ virtual user chung session/account vì khóa session có thể làm sai kết luận.
5. Lưu JMX, CSV user và kết quả raw trong `.work/load/`, không commit. Trích metric tổng hợp đã kiểm tra vào báo cáo.

Workload học tập gợi ý: 60% xem course/nội dung, 20% tải file nhỏ, 10% xem/nộp bài, 10% login/logout; có think time 3–8 giây. Kiểm thử quiz đồng thời là một workload riêng vì pattern ghi DB khác. Các tỷ lệ này là thiết kế thực nghiệm của nhóm, không phải benchmark chuẩn của Moodle.

## 4. Ma trận thử nghiệm

| Lần | User đồng thời | Ramp-up | Đo ổn định | Mục đích |
|---|---:|---:|---:|---|
| Smoke | 1–2 | 30 giây | 2 phút | Xác minh script làm đúng nghiệp vụ |
| Baseline | 10 | 2 phút | 10 phút | Mốc so sánh |
| Load 1 | 25 | 3 phút | 10 phút | Quan sát bắt đầu tắc nghẽn |
| Load 2 | 50 | 5 phút | 15 phút | Thử mục tiêu small |
| Stress tùy chọn | Tăng từng bậc | Có kiểm soát | Dừng khi lỗi kéo dài | Xác định giới hạn, không dùng cho site live |

Đây là mục tiêu thử nghiệm, chưa có kết quả. Lặp tối thiểu 3 lần cho mỗi cấu hình, giữ dataset và workload giống nhau; ghi riêng cold/warm cache. T3 ở chế độ **standard** nên phải ghi CPUCreditBalance: kết quả trước và sau cạn credit có thể khác đáng kể.

Với small, test qua SSM có thêm độ trễ/giới hạn đường hầm và máy phát tải. Kết quả là end-to-end của lab, không tách riêng năng lực EC2. Khi P1 public HTTPS sẵn sàng, chạy load generator trên máy riêng và ghi vị trí mạng; không chạy JMeter trên chính EC2 Moodle.

Lệnh mẫu sau khi tự sinh JMX:

```bash
jmeter -n -t .work/load/moodle.jmx -l .work/load/run-01.jtl -e -o .work/load/report-01
```

Thư mục HTML output cần mới/rỗng. Không giả định JMX tự nhận biến `-Jusers` nếu chưa nối biến đó trong test plan. Kiểm tra raw result không lưu password/cookie hoặc payload nhạy cảm trước khi chia sẻ.

## 5. Metric và tiêu chí

| Metric | Nơi lấy | Cách diễn giải |
|---|---|---|
| p50/p95/p99, throughput, error rate | JMeter, theo từng nghiệp vụ | Không trộn download lớn với trang text |
| CPU/RAM/swap/disk | EC2 + OS hoặc CloudWatch agent | RAM/disk cần agent/OS, không có mặc định đầy đủ |
| CPU credits | CloudWatch EC2 | Ghi cấu hình standard và số credit đầu/cuối |
| DB connections/slow query | PostgreSQL/RDS | Phân biệt thiếu connection với query chậm |
| Cron backlog/fail delay | Moodle tasks + journal | App web nhanh nhưng tác vụ nền chậm vẫn là lỗi |
| Thời gian deploy/restore | Đồng hồ + mốc thao tác đã định nghĩa | Tách thời gian hạ tầng và cài ứng dụng |

Tiêu chí nghiên cứu đề xuất cho baseline: p95 trang tương tác <=3 giây, tỷ lệ lỗi nghiệp vụ <1%, không mất file/bài nộp, cron không có lỗi kéo dài. Đây là ngưỡng nhóm cần phê duyệt theo yêu cầu môn học; chưa phải kết quả đạt được hay SLA.

## 6. Thử lỗi có kiểm soát

Small: trên staging, dừng `moodle-web.service`, xác nhận health báo lỗi rồi khôi phục; làm đầy đĩa chỉ trong filesystem test có giới hạn nếu thật sự cần; không phá đĩa DB. Thử thiếu quyền S3 ở staging để kiểm tra backup báo lỗi và site được mở lại. Kiểm tra backup chờ cron container thực sự hoàn tất trước khi dump/archive.

P1: loại một app khỏi ASG, kiểm tra node thay thế; gửi request qua hai node và xác nhận session/file; thử cron runner dừng và chạy lại; kiểm tra failover DB/cache khi đã có backup và cửa sổ kiểm thử. Không tuyên bố HA nếu mới thử thay web node mà chưa thử các phụ thuộc còn lại.

## 7. Mẫu biên bản

```text
Run ID / ngày giờ / người thực hiện:
Git commit / Moodle tag / AMI ID / Ubuntu / PHP / DB / Docker image ID:
Region / loại EC2 / dung lượng / credit mode:
Dataset / số tài khoản / số user đồng thời / workload:
Vị trí máy phát tải / đường truyền / cold hay warm cache:
Deploy: bắt đầu ..., infra xong ..., Moodle ready ...
JMeter: p50 ..., p95 ..., p99 ..., throughput ..., lỗi ...
CPU/RAM/DB/cron tại thời điểm chậm:
Backup URI và thời điểm / checksum:
Restore: bắt đầu ..., nghiệp vụ đã xác nhận lúc ...
Course/user/file trước và sau / hash file:
Kết luận, giới hạn, lỗi còn tồn tại, link bằng chứng:
```
