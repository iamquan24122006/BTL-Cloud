# Medium Sydney — vận hành và nghiệm thu 14/11/2026

URL chính: **https://www.moodle-cloud-distribution.mywire.org**. URL CloudFront cũ chuyển hướng sang tên miền. Hồ sơ dựng/restore ban đầu nằm trong [bằng chứng 14/11](evidence/medium-sydney-2026-11-14/README.md), kết quả cutover trong [bằng chứng 15/11](evidence/current-review-2026-11-15/README.md).

Cập nhật 15/11: URL chính là https://www.moodle-cloud-distribution.mywire.org, HTTPS/ACM trực tiếp tại ALB Sydney; CloudFront cũ chuyển hướng sang tên miền. 47/47 ca nghiệp vụ và ba tài khoản demo đạt; hai target healthy, runner mới `i-0bcafad1d2d89cad9`, ASG refresh Successful và plan không drift. Policy target 200 đã tự chạy chu kỳ 2→3→2. [Bằng chứng mới](evidence/current-review-2026-11-15/README.md), [runbook cutover](25-domain-cutover.md). Dashboard/ALARM/OK có [hồ sơ riêng](evidence/medium-operations-2026-11-14/README.md). Các kết quả restore ban đầu phía dưới giữ nguyên thời điểm và phạm vi.

## Cấu hình thực tế

| Thành phần | Cấu hình |
|---|---|
| Account / region | `828676179987` / `ap-southeast-2` |
| Project / environment | `moodle-medium` / `dev` |
| Compute | Hai app trong ASG, một runner; mỗi máy `t3.small`, 2 vCPU / 2 GiB RAM, EBS gp3 mã hóa 30 GiB |
| Network | VPC riêng, hai AZ; compute không có public IP, quản trị qua SSM |
| Frontend | Tên miền Dynu → ALB HTTPS/ACM; HTTP chuyển HTTPS; CloudFront cũ giữ làm đường chuyển hướng |
| Database | RDS PostgreSQL **16.13**, `db.t4g.micro`, gp3 20 GiB, private, mã hóa, `verify-full` TLS |
| Shared files | EFS mã hóa, mount TLS/IAM bằng access point trên cả ba máy |
| Session / MUC | Hai Redis 7.1 riêng, `cache.t4g.micro`, TLS/AUTH, mã hóa |
| Runner | Release, cron và backup; app không bật các timer này |
| State | S3 backend riêng theo account/project/environment, versioning và lockfile |
| Moodle | 4.5.15, image/bundle ghim theo release `2130963f7fc3fd76007498ab766a0942b9db3f59` |

Free Plan của account này đã từ chối `t3.medium` và RDS retention 7 ngày. Lab dùng loại `t3.small` được AWS trả về là eligible và `db_backup_retention_days: 1`. Preset **medium** mô tả topology nhiều app với state dùng chung; không có nghĩa máy phải thuộc instance size `.medium`. Dung lượng RAM này phục vụ lab, chưa được chứng nhận đáp ứng một mức tải cụ thể.

Tên miền Dynu đã chuyển CNAME sang ALB Sydney và ACM đã cấp chứng chỉ. **MED-02 HTTPS tại ALB đã có kiểm chứng live** với TLS 1.3, cookie Secure/HttpOnly, HSTS và 47/47 ca nghiệp vụ. CloudFront cũ dùng HTTP origin chỉ để nhận redirect về tên miền; không mô tả đường legacy này là mã hóa mọi chặng. Medium vẫn là lab, không phải HA/SLA production.

## Vận hành trên máy triển khai

YAML thật nằm tại **`.work/medium-sydney-live/medium.yaml`**, chỉ chứa resource references, không chứa password. Mẫu để tạo lab khác là [medium.example.yaml](../config/medium.example.yaml); cần thay toàn bộ identifiers.

```powershell
$env:AWS_PROFILE = 'moodle-project'
$Config = '.work/medium-sydney-live/medium.yaml'
$Py = '.work/validation-venv/Scripts/python.exe'

& $Py -m src.moodle_cloud --config $Config status
& $Py -m src.moodle_cloud --config $Config health --wait
& $Py -m src.moodle_cloud --config $Config backup --wait
```

`status` chỉ đọc outputs, còn `health` kiểm tra runner và public readiness. Với backup/release có kế hoạch, dừng timer cron, chờ job đang chạy hoàn tất rồi thực hiện dưới operation lock; nếu job khác đang giữ lock, kiểm tra command hiện tại trước khi gửi lại. Theo dõi SSM tới trạng thái terminal và kiểm chứng manifest/checksum/restore, không dùng thông báo “queued” làm kết quả.

Trong runner qua SSM:

```bash
sudo systemctl stop moodle-cron.timer
sudo systemctl status moodle-cron.service
# Đợi service đang chạy hoàn tất trước operation tiếp theo.
sudo /opt/moodle-medium/operation.sh backup
sudo systemctl start moodle-cron.timer
```

Không đổi artifact rồi chạy lại install thủ công trên app. Theo [runbook release/rollback](10-medium-n2.md), review saved plan, backup nhất quán, cập nhật và chạy release trên runner. State, raw backup, credential, saved plan và log riêng tư không đưa vào Git.

## Demo và dữ liệu

Fixture được seed độc lập bằng Moodle API; đây không phải migration dữ liệu từ small. Có hai course private `CLOUD-C01`/`CLOUD-C02`, teacher và ba student. Student A/B có bài nộp, điểm 93/85 và phản hồi riêng; student C không được truy cập C01. Bộ kiểm tra HTTPS nguồn đạt **47/47**, gồm đăng nhập, quyền, SHA-256 file, bài nộp/điểm và logout/replay cookie.

Các account demo nằm riêng trên máy triển khai tại `.work/medium-release-src/.work/medium-live/private/demo-medium-accounts.json`, có ACL bảo vệ; không công bố mật khẩu trong README/evidence. File credential/cookie tạm cho phép thử xuyên node đã được dọn khỏi EFS. GUI mới chưa được xác minh: công cụ Windows bị hệ thống dừng vì không xác định được URL trình duyệt đủ chắc chắn để thực thi chính sách. Kết quả HTTP không thay cho walkthrough bố cục desktop/mobile.

## Backup và restore drill

Bộ backup được kiểm thử trong lượt này:

```text
s3://moodle-medium-dev-828676179987-ap-southeast-2-backups/moodle-medium-dev-med/20261114T115610
```

Backup giữ database + moodledata cùng cửa sổ dừng writer, kiểm hash và publish manifest cuối. Timer backup hàng ngày chạy 02:00 UTC; RDS automated backup retention 1 ngày là cơ chế riêng.

Restore được thực hiện vào project `moodle-restore`, môi trường `staging`, với RDS và EFS mới, cùng image/source của backup. Không seed/install trước restore. URL đích dài hơn nguồn nên operator kiểm tra mọi cột ký tự có giới hạn; chỉ khi không có hàng bị tràn mới cho Moodle tool replace chạy với `--shorten`. Không sửa dump bằng thay chuỗi và không cho phép cắt dữ liệu.

Restore đã đối chiếu nguyên IDs của hai course, bốn user, hai học liệu và hai bài nộp/điểm, rồi đạt **47/47 HTTPS** và session/file/cache trên cả hai app mới. Target được dọn **71 tài nguyên**; state rỗng và final snapshot tạm được xóa. Backend/artifact và backup nguồn được giữ.

Nguồn đã hoạt động lại và được thử thay app bằng ASG: hai target healthy trở lại sau **139,67 giây**, cùng cookie và file được xác minh trên app thay thế. Thời gian nạp/kiểm thử trên target đã provision được phân biệt với thời gian dựng toàn bộ hạ tầng và gián đoạn xác thực AWS; không coi đây là cam kết RTO production. Chi tiết thời gian nằm trong bằng chứng.

## Chi phí và vòng đời

Giá AWS công khai tra ngày 14/11: chi phí cơ bản của **riêng medium nguồn** khoảng **0,26751 USD/giờ**, **6,42 USD/ngày** hoặc **195,28 USD/730 giờ**, trước credit/thuế. Giả định ba địa chỉ IPv4 và 1 GiB EFS; đã tính compute, RDS/Redis, ALB/NAT giờ và EBS/RDS storage. Chưa gồm LCU, NAT/transfer GB, CloudFront/S3/ECR, secret/log/metric, các lab khác và restore drill. Đây là dự toán, không phải hóa đơn hoặc tổng chi phí đồ án. [Chi tiết phép tính](evidence/medium-sydney-2026-11-14/cost-base.json).

Ngân sách toàn đồ án vẫn **150 USD**; không giữ cấu hình này chạy liên tục một tháng dựa trên việc account có credit. Nhóm cần xác nhận lịch demo và cleanup. Builder tạm đã được dọn 10 tài nguyên sau khi AMI được kiểm chứng; AMI/image/bundle phục vụ tái lập được giữ.

RDS nguồn có deletion protection và EFS nguồn có `prevent_destroy`. Cleanup nguồn cần backup đã restore-test, review đúng account/state và quy trình gỡ bảo vệ trong [runbook](10-medium-n2.md). Không xóa backend/artifact/backup chỉ để dừng compute.
