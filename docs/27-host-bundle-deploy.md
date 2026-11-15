# Phát hành thay đổi mã chạy trên host (medium và small)

Trang này ghi quy trình đã dùng ngày 15/11/2026 để đưa bản sửa backup–cron lên lab Sydney mà **không build lại image Moodle**: medium nhận bundle host mới, small nhận hotfix file qua SSM. Kết quả và bằng chứng nằm trong [hồ sơ host bundle](evidence/hostfix-2026-11-15/README.md).

## Khi nào dùng

- Chỉ đổi `scripts/medium/*` (ví dụ `operations.py`, `observability.py`, `bootstrap.sh`) hoặc `scripts/backup.sh`, `verify_backup.py`, `health.sh` của small.
- Không đổi mã PHP của Moodle, `Dockerfile` hay dependency trong image. Nếu đổi những phần đó, phải build/push image mới và cập nhật `artifact.image`.
- Không dùng trang này để bỏ qua release flow. Medium vẫn phải chạy `operation.sh release` sau khi bundle lên node.

## Ràng buộc thiết kế

`bootstrap.sh` của medium kiểm tra label `org.opencontainers.image.revision` của image bằng `artifact.release`. Vì vậy:

| Đổi gì | `artifact.image` | `artifact.release` | `artifact.key` / `sha256` |
|---|---|---|---|
| Chỉ mã host | giữ nguyên digest | giữ nguyên | **key mới** + SHA mới |
| Mã Moodle/image | digest mới | commit source mới | key mới + SHA mới |

Key đã phát hành không được ghi đè. Bundle cũ vẫn nằm trong bucket để rollback.

## Các bước

### 1. Build bundle từ cây sạch

```powershell
git status --porcelain --untracked-files=normal
python -m scripts.medium_bundle --output .work/medium-artifact/medium.tar.gz
```

Bundle được dựng tất định (không mtime, LF). Ghi lại SHA-256 và commit HEAD của repo; hai giá trị này phải được ghi riêng với digest image.

### 2. Phát hành lên bucket artifact

```powershell
aws s3 cp .work/medium-artifact/medium.tar.gz `
  s3://<artifact-bucket>/releases/<release-tag>/host-<commit-prefix>.tar.gz --sse AES256
aws s3api head-object --bucket <artifact-bucket> --key releases/<release-tag>/host-<commit-prefix>.tar.gz
```

Điền `artifact.key` và `artifact.sha256` trong YAML thật (thư mục `.work`, không commit). Không sửa `release` khi chỉ đổi mã host.

### 3. Plan, review, apply

```powershell
python -m src.moodle_cloud --config .work/medium-sydney-live/medium.yaml plan
# Review: runner thường bị replace, ASG refresh app; cửa sổ release sẽ chặn ghi.
python -m src.moodle_cloud --config .work/medium-sydney-live/medium.yaml apply `
  --confirm <project>-<environment> --allow-data-loss
```

Plan có `data_loss_risk=true` khi thay EC2 runner; đây là thay máy, không phải xóa dữ liệu. Dữ liệu nằm ở RDS/EFS.

### 4. Kiểm tra node và bundle

Trên runner/app mới qua SSM, đối chiếu `/etc/moodle/deploy.json` với SHA mong đợi, `sha256sum /opt/moodle-medium/bundle.tar.gz` và `systemctl is-active` của các unit. Chờ `cloud-init status --long` = `done` và ASG instance refresh `Successful` trước khi release; `operations.py` từ chối chạy khi có app đang `pending`/`stopping`.

### 5. Xử lý marker trước khi release

Nếu có `worker-pending.json`, **không xóa ngay**. Kiểm tra container worker đã biến mất, không còn session DB của `moodle_migration`/`moodle_runtime`, ghi lại hash/step/thời điểm, rồi mới gỡ marker. Sau đó:

```bash
sudo systemctl stop moodle-cron.timer
sudo systemctl is-active moodle-cron.service    # phải inactive/failed trước khi tiếp tục
sudo /opt/moodle-medium/operation.sh release
sudo systemctl start moodle-cron.timer
```

`release` tự chạy backup baseline, upgrade (nếu cần), cấp quyền, MUC, purge cache và TLS proof. Release lỗi sẽ giữ maintenance; không dùng `resume` để bỏ qua migration lỗi.

### 6. Nghiệm thu sau deploy

- `operation.sh cron` phải kết thúc `cron-completed-and-task-audit-clear`; kiểm tra `mdl_task_scheduled.faildelay`, ad hoc backlog và quyền `TRUNCATE` (494 bảng ở lab hiện tại).
- Chạy lại bộ HTTPS (`scripts.acceptance.http_check`) và so sánh số ca đạt với baseline.
- Plan lại: phải `No changes`.
- Ghi inventory/alarm/policy mới nếu thay node.

### 7. Small

Small nhận script qua user-data, nên thay file trên host đang chạy phải làm bằng hotfix có kiểm hash:

```bash
# Base64 file đã review, ghi atomically, sha256sum -c trước khi mv
echo '<base64>' | base64 -d > /opt/moodle-distribution/verify_backup.py.new
echo '<sha256>  /opt/moodle-distribution/verify_backup.py.new' | sha256sum -c -
chmod 0644 /opt/moodle-distribution/verify_backup.py.new
mv /opt/moodle-distribution/verify_backup.py.new /opt/moodle-distribution/verify_backup.py
```

Sau hotfix, chạy một backup thật để chứng minh script mới hoạt động và ghi lại SHA trước/sau. **Không thay EC2 small chỉ để cập nhật script**: root volume chứa database và `moodledata`. User-data của instance hiện tại vẫn mang bản cũ cho tới lần thay máy tiếp theo; hồ sơ phải ghi rõ điểm này.

## Sự cố đã gặp: bản nâng cấp tự động restart containerd

Ngày 15/11/2026, ngay sau release, `unattended-upgrades` trên runner nâng `libc6` và kernel; containerd restart lúc `07:20:41Z`, kill container `cron.php` đang chạy. Wrapper giữ `worker-pending.json` (đúng thiết kế) nên cron dừng khoảng 15 phút cho tới khi có người review.

Cách xử lý (đã dùng):

1. Xác nhận container worker không còn, không còn process `cron.php`, 0 session DB.
2. Ghi lại hash/step/thời điểm marker, rồi gỡ `worker-pending.json`.
3. Dừng timer, chạy `operation.sh cron` bằng tay, bật lại timer và theo dõi ít nhất hai chu kỳ.

Phòng ngừa: đặt cửa sổ nâng cấp hoặc loại trừ các gói buộc restart container runtime trên runner trong giờ vận hành; không tắt cơ chế giữ marker. Đồng thời phải kiểm chứng alarm `CronSuccess-missing` — trong sự cố này alarm không chuyển ALARM dù cron dừng 15 phút. Chi tiết trong [bằng chứng sự cố](evidence/hostfix-2026-11-15/cron-incident.json) và [danh sách còn lại](24-remaining-work.md).

## Rollback

- Medium: đổi `artifact.key`/`sha256` về bundle cũ (key cũ vẫn tồn tại), plan/apply, rồi `operation.sh release`. Nếu schema đã đổi, rollback phải dùng DB + file + artifact của backup tương ứng, không chỉ quay bundle.
- Small: giữ bản `.new`/bản cũ trước khi `mv`; khôi phục file và chạy lại `health.sh`, một backup mới.

## Chi phí và tác động

Mỗi lần apply thay runner tạo EC2/EBS mới và bản ghi SSM/CloudWatch; thay app theo ASG refresh tạo thêm instance trong thời gian ngắn. Release tạo một backup đầy đủ trong bucket (S3 storage + request). Không có thay đổi RDS/EFS/Redis nếu chỉ đổi mã host.
