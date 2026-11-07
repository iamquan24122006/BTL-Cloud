# Vận hành, backup và khôi phục

## 1. Nhật ký và xử lý lỗi

| Vấn đề | Kiểm tra |
|---|---|
| Không mở SSM | IAM profile, agent, DNS/egress, region/instance đúng |
| Cài thất bại | `cloud-init status --long`, `/var/log/cloud-init-output.log`, `/var/log/moodle-install.log` |
| Trang 500 | `docker logs moodle-web`, PHP ini trong image, quyền config và DB |
| File không tải được | dataroot ngoài webroot, ownership, slash arguments |
| Task chưa chạy | journal `moodle-cron.service`, timer, trang Scheduled tasks |
| Hết đĩa | `df -h`, `docker system df`, backup, Moodle trash/cache và PostgreSQL |
| Backup thất bại | journal backup, timer/moodle-web còn chạy, IAM S3, dung lượng |

CloudWatch agent và alarm RAM/disk/cron/backup chưa được triển khai trong small. P0 dùng các log trên; P1 phải bổ sung agent, log retention và alarm hoạt động được. Không coi chỉ số EC2 CPU mặc định là đã giám sát database và ứng dụng.

PHP nằm trong container. Chạy lệnh Moodle bằng `sudo /opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/<script>.php ...`. Web quản lý bằng `moodle-web.service`, không phải Apache cài trên host. Xem `sudo journalctl -u moodle-web.service -n 80 --no-pager` để có log sau khi container đã dừng; Docker container dùng `--rm` nên log riêng của container mất khi xóa nó. Không dọn image ID đang được ghi trong `/var/lib/moodle-distribution/php-image-id`.

### Nghiệm thu xoay admin khởi tạo trong lab

`tests/integration/rotate_admin.php` dùng API của Moodle đã cài để kiểm tra credential cũ đã biết, đổi sang secret mới sinh trên EC2, kiểm tra secret cũ bị từ chối và thu hồi các phiên admin hiện có. Công cụ chỉ dành cho lab có fixture; nếu credential cũ không khớp thì dừng, không ép ghi đè. Password chỉ đi qua file tạm `/etc/moodle/admin-rotation.json` mode 0640 root:www-data và bộ nhớ PHP; không truyền bằng argv hoặc ghi vào log.

Sau bước PHP, người vận hành cập nhật nguyên tử `acceptance.json`, cập nhật file quản trị riêng tư `/root/moodle-initial-admin.txt` mode 0600, chạy lại acceptance HTTP, xuất fixture private và tạo backup mới. File mang tên initial được cập nhật để chứa credential hiện hành sau rotation; sau restore vẫn phải đối chiếu với DB nguồn như bước restore bên dưới. Chỉ xóa JSON tạm khi mọi kiểm tra và export đã thành công; status không chứa secret nằm ở `/var/lib/moodle-distribution/admin-rotation-status.json`.

Fixture thử nghiệm được version trên S3. Ghi VersionId trước/sau rotation và liên kết với backup tương ứng; fixture hiện tại không tự khớp credential của một dump cũ. Giữ các version/backup cần cho diễn tập trong nơi riêng tư. Kết quả CLI/HTTP không thay thế kiểm tra bố cục giao diện hoặc chữ ký kiểm tra chéo của thành viên nhóm.

## 2. Chuẩn bị S3 backup độc lập

Trước deploy, tạo một bucket tên duy nhất trong region đã chọn bằng console hoặc quy trình riêng của nhóm. Bật Block Public Access, default encryption, versioning và lifecycle phù hợp. Với script hiện tại dùng SSE-S3 (`AES256`); nếu dùng KMS phải thay script/quyền KMS tương ứng.

Đề xuất cho lab: giữ current versions 14 ngày, noncurrent versions 7 ngày, hủy multipart upload dở sau 1 ngày; điều chỉnh theo yêu cầu bảo tồn dữ liệu. Bucket policy từ chối transport không TLS. Kiểm tra default encryption và policy có hiệu lực. [Bảo vệ dữ liệu S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)

Điền tên bucket vào YAML trước plan đầu. EC2 role chỉ ghi prefix `<project>-<environment>/`. Bucket ở ngoài state small, phải tự kiểm kê và tính phí sau destroy. Muốn restore, cấp quyền đọc hẹp cho người vận hành/staging; runtime role mặc định không có quyền đó.

## 3. Chạy backup và xác nhận

```powershell
python -m src.moodle_cloud --config config/dev.yaml backup
aws --region ap-southeast-1 ssm get-command-invocation --command-id <COMMAND_ID> --instance-id <INSTANCE_ID>
```

Lệnh CLI chỉ xếp hàng; kiểm tra `Status=Success`, stdout và backup set thực sự tồn tại. Chưa có manifest hoặc thiếu file thì không dùng set đó. Khi kiểm tra ngay sau gửi command, SSM có thể chưa tạo invocation; chờ ngắn rồi đọc lại.

Có thể chạy trực tiếp trong SSM:

```bash
sudo /opt/moodle-distribution/backup.sh
sudo systemctl status moodle-web.service moodle-cron.timer --no-pager
```

Script dành riêng cho single-node: kiểm tra dịch vụ, lấy khóa local, bật maintenance, dừng timer, chờ cron (kể cả trạng thái systemd `activating`), dừng web, dump DB và archive dữ liệu. Sau đó mở dịch vụ trở lại và tải backup lên S3. Trap cố khôi phục dịch vụ khi lỗi, nhưng vẫn phải kiểm tra health sau lỗi/reboot.

| File trong set | Nội dung |
|---|---|
| database.dump | PostgreSQL custom-format dump |
| moodledata.tar.gz | File dữ liệu; bỏ cache/temp/session có thể tạo lại |
| config.php | Tham chiếu config cũ, **có secret** |
| code.txt | Commit code tương ứng |
| runtime-image.txt | Image ID PHP đã dùng, để đối chiếu |
| runtime-Dockerfile | Dockerfile và base image digest; không chứa image layers |
| SHA256SUMS | Hash DB/file/config/code và metadata runtime |
| manifest.json | Thời điểm, phiên bản, loại backup; upload cuối |

Checksum phát hiện lỗi truyền tải, không thay thế kiểm soát quyền hay kiểm chứng restore. S3 key chứa ngày giờ UTC và prefix môi trường. Backup DB được chụp khi maintenance đang bật; sau restore phải tắt maintenance chủ động.

Manifest phiên bản 2 có thêm thông tin Ubuntu/container. Image ID là bằng chứng nhận dạng, không phải artifact có thể tải bằng ID trên máy mới. Hai lần build có thể khác ID vì APT thay đổi; phải đối chiếu runtime và thực hiện kiểm thử chức năng. Để phục hồi đúng byte runtime, lưu image hoặc AMI riêng trước khi xóa máy nguồn; script backup hiện chưa thực hiện việc đó.

Nếu có bucket, bootstrap bật daily timer lúc **02:00 UTC** (09:00 tại Asia/Hovd). Mỗi lần backup có downtime ở small; đổi giờ theo lịch lớp học. Không có bucket thì timer chưa bật, backup thủ công chỉ nằm trên EBS và sẽ mất khi destroy. Không tự xóa backup local trong script: phải theo dõi dung lượng, xác nhận S3/restore rồi dọn những set đã hết thời hạn bằng thao tác có kiểm soát.

## 4. Restore drill lên staging mới

**Điều kiện:** một staging mới không có dữ liệu cần giữ, cùng Moodle tag và PostgreSQL major; một backup set hoàn chỉnh; quyền đọc đúng S3 prefix. Ghi thời gian bắt đầu, instance ID đích và URI backup vào biên bản. Mọi lệnh xóa DB dưới đây chỉ chạy trên staging đã xác nhận.

1. Dựng staging từ `config/staging.example.yaml` bằng plan/apply. Không mở hai tunnel cùng local port 8080; đóng tunnel dev khi chuyển sang staging.
2. Cấp tạm `s3:GetObject` cho staging role trên **đúng prefix backup được chọn**; dùng policy riêng để có thể gỡ sau. Với SSE-S3 không cần KMS decrypt; nếu đã thay sang KMS phải cấp quyền key tương ứng.
3. Trong SSM staging, `sudo -i`, tạo `/var/backups/moodle-restore` mode 0700. Đặt `BACKUP_URI` là URI S3 cụ thể của set. Tải từng file:

```bash
install -d -m 0700 /var/backups/moodle-restore
set -Eeuo pipefail
cd /var/backups/moodle-restore
read -r -p 'S3 URI of the selected backup set: ' BACKUP_URI
for name in database.dump moodledata.tar.gz config.php code.txt runtime-image.txt runtime-Dockerfile SHA256SUMS manifest.json; do
  aws s3 cp "$BACKUP_URI/$name" "$name" --only-show-errors
done
sha256sum --check SHA256SUMS
cat manifest.json
git -C /var/www/moodle rev-parse HEAD
cat code.txt
cat runtime-image.txt
cat /var/lib/moodle-distribution/php-image-id
diff -u runtime-Dockerfile /opt/moodle-distribution/Dockerfile
```

4. Hai commit phải khớp và mọi checksum phải OK. Đối chiếu Dockerfile/base digest, PHP extension và ghi lại image ID. Nếu Dockerfile khác, dừng và khôi phục cấu hình runtime phù hợp trước; nếu chỉ image ID khác vì rebuild thì kiểm chứng đầy đủ chức năng, không ghi nhận là phục hồi đúng byte. Không trộn dump ngày A với file ngày B. Giữ `config.php` backup làm tài liệu riêng tư; **không ghi đè config staging** vì DB password mới khác password nguồn. Runbook này áp dụng set format 2; set cũ format 1 thiếu metadata runtime cần đối chiếu riêng với cấu hình nguồn đã lưu.
5. Dừng mọi writer và backup tự động. Chờ service đang chạy hoàn tất; xem `systemctl show moodle-cron.service moodle-backup.service -p ActiveState`. Với oneshot, `activating` nghĩa là vẫn đang chạy. Chỉ tiếp tục khi hai service inactive/failed và không còn process ghi dữ liệu.

```bash
set -Eeuo pipefail
systemctl stop moodle-backup.timer moodle-cron.timer
# Sau khi cron/backup đã hoàn tất như mô tả ở trên:
/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/maintenance.php --enable
systemctl stop moodle-web.service
read -r -p 'Type RESTORE-EMPTY-STAGING after checking target instance: ' CONFIRM_RESTORE
[[ "$CONFIRM_RESTORE" == RESTORE-EMPTY-STAGING ]] || exit 1
runuser -u postgres -- dropdb --if-exists moodle
runuser -u postgres -- createdb --owner=moodle --encoding=UTF8 --template=template0 moodle
runuser -u postgres -- pg_restore --exit-on-error --no-owner --role=moodle --dbname=moodle </var/backups/moodle-restore/database.dump
mv /var/lib/moodledata "/var/lib/moodledata.before-restore-$(date -u +%Y%m%dT%H%M%SZ)"
install -d -o www-data -g www-data -m 0770 /var/lib/moodledata
tar --no-same-owner -xzf /var/backups/moodle-restore/moodledata.tar.gz -C /var/lib/moodledata
chown -R www-data:www-data /var/lib/moodledata
/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/purge_caches.php
/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/maintenance.php --disable
systemctl start moodle-web.service moodle-cron.timer
/opt/moodle-distribution/health.sh
```

Archive chỉ được lấy từ backup do nhóm kiểm soát; không giải nén archive không rõ nguồn với root. Nếu có lỗi restore, giữ site đóng và xử lý; không bỏ qua lỗi `pg_restore` rồi tiếp tục mở web.

6. Đăng nhập bằng tài khoản trong backup nguồn; file mật khẩu admin ban đầu của staging không còn phản ánh DB đã restore. Đối chiếu course/user/enrolment, tải file và kiểm tra hash; chạy cron, tạo một bài nộp thử. Ghi thời gian phục hồi và lỗi phát hiện.
7. Gỡ quyền đọc S3 tạm, dọn bản credential khởi tạo staging đã lỗi thời sau khi bảo đảm còn đường quản trị. Chỉ bật lại backup timer khi muốn staging tạo backup riêng. Giữ bằng chứng restore; dọn thư mục dữ liệu cũ khi đã xác nhận khôi phục thành công.

**RTO** đo từ lúc bắt đầu xử lý sự cố đến khi người dùng thực hiện được nghiệp vụ. **RPO** là khoảng dữ liệu có thể mất tính từ điểm backup được chọn, không phải thời gian chạy restore. Backup hằng ngày chỉ gợi ý RPO gần 24 giờ khi mọi lần chạy thành công; không coi đó là bảo đảm.

## 5. Nâng cấp và rollback

Đây là runbook, chưa có lệnh upgrade/rollback tự động trong CLI.

1. Đọc release notes và yêu cầu PHP/DB/plugin. Không nâng production nếu staging chưa qua restore drill.
2. Khóa thay đổi; dừng backup timer và chờ backup hiện tại hoàn tất. Tạo backup nhất quán có manifest và kiểm tra tải về.
3. Dựng staging từ backup với code cũ; kiểm tra baseline. Cài bản code mới ở thư mục riêng, cùng plugin đã ghim, giữ cấu hình riêng tư và dataroot.
4. Bật maintenance, dừng web/cron, đổi code rồi chạy `/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/upgrade.php --non-interactive` (PHP chạy với www-data trong container). Nếu đổi PHP runtime phải chuẩn bị image mới và cập nhật image ID trong cửa sổ bảo trì; không thay khi web/cron vẫn hoạt động. Migration chỉ một runner thực hiện. Kiểm tra schema, cron, login, course, file và bài nộp.
5. Nếu thành công, lên lịch cửa sổ maintenance cho môi trường đích; mở lại dịch vụ và theo dõi.
6. Nếu migration lỗi hoặc kiểm thử không đạt: khôi phục **code + database + moodledata** từ cùng điểm backup. Chỉ `git checkout` bản cũ sau migration không phải rollback dữ liệu.

Lên 5.3 phải chuyển DB lên PostgreSQL >=17 và kiểm tra lại layout/đường dẫn CLI của Moodle mới; bộ script hiện tại không thực hiện bước này.

## 6. Cleanup cuối buổi

```powershell
python -m src.moodle_cloud --config config/dev.yaml plan --destroy
# Sau khi đã kiểm tra backup ở ngoài EC2 và xem destroy plan:
python -m src.moodle_cloud --config config/dev.yaml destroy --confirm moodle-lab-dev --allow-data-loss
```

Root EBS, Moodle, DB và backup local bị xóa. S3 backup ngoài state còn nguyên và tiếp tục có chi phí. Kiểm kê cả EC2 thủ công, EBS rời, snapshots, IP, bucket/version, CloudWatch và dịch vụ P1 nếu đã tạo. Không xóa state trước khi tài nguyên được xử lý xong.
