# Lab 1: cài và hiểu Moodle trên một EC2

## Chuẩn bị

Tạo một EC2 Ubuntu Server 26.04 LTS x86_64 của Canonical, đề xuất `t3.medium`, EBS gp3 30 GiB mã hóa. Đặt trong public subnet có route tới Internet Gateway và public IPv4 để tải package. SG không có inbound; outbound phục vụ package và AWS API. Gắn instance profile có `AmazonSSMManagedInstanceCore`. Đây là thao tác lab thủ công, **tách khỏi EC2 do Terraform quản lý**; tự gắn tag Project/Environment và ghi ID để dọn cuối buổi.

Kiến trúc lab: Ubuntu 26.04 chạy Docker và PostgreSQL 16; Apache/PHP 8.3 chạy trong container Debian Bookworm. Không cài PHP mặc định của Ubuntu. Giải thích tương thích ở [ADR phiên bản](01-version-decisions.md).

Trên máy vận hành cài AWS CLI và Session Manager plugin, dùng AWS SSO/profile được cấp quyền. Không lưu access key vào repository. Region mẫu `ap-southeast-1` có thể thay trong YAML. Kiểm tra:

```powershell
aws sts get-caller-identity
aws --region ap-southeast-1 ssm describe-instance-information
aws --region ap-southeast-1 ssm start-session --target <INSTANCE_ID>
```

Nếu instance không online, kiểm tra SSM Agent, instance role, DNS/outbound và thời gian máy trước khi xử lý Moodle. [Yêu cầu Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html)

## 1. Chuyển các file hỗ trợ

Trong repository chạy `python -m scripts.manual_bundle config/dev.yaml`. File `.work/manual-transfer.sh` chứa mã nguồn và cấu hình không có secret. Mở file đó, copy vào phiên SSM sau `sudo -i`. Bundle chỉ tạo file dưới `/opt/moodle-distribution` và `/etc/moodle`, chưa cài phần mềm.

**Lần học đầu:** đọc `bootstrap.sh`, thực hiện từng khối dưới đây và ghi lệnh/kết quả. **Lần kiểm tra tự động hóa:** dùng EC2 sạch khác, chạy `sudo bash /opt/moodle-distribution/bootstrap.sh` và so sánh. Không dùng `bash -x` hoặc ghi hình khi xem credential.

## 2. Chuẩn bị host Ubuntu 26.04 và build PHP

Chạy với root trên EC2. Đọc `setup-host.sh`, thực hiện lần lượt các khối kiểm tra OS/architecture, APT cơ bản, khóa ký PGDG, khai báo kho `resolute-pgdg`, cài PostgreSQL 16 và bật Docker/PostgreSQL. Nếu đã hiểu từng khối, có thể gọi cả script:

```bash
cat /etc/os-release
dpkg --print-architecture
bash /opt/moodle-distribution/setup-host.sh
docker version
/usr/lib/postgresql/16/bin/psql --version
docker build --tag moodle-php:8.3 /opt/moodle-distribution
docker run --rm --network none --entrypoint php moodle-php:8.3 -v
docker run --rm --network none --entrypoint php moodle-php:8.3 -m
docker run --rm --network none --entrypoint apache2ctl moodle-php:8.3 configtest
```

Kết quả cần có: host Ubuntu 26.04/amd64, PHP 8.3, PostgreSQL 16 và Apache `Syntax OK`. Dockerfile kiểm tra các extension cần thiết ngay lúc build. Build lần đầu tải image và biên dịch extension; dành đủ thời gian và dung lượng, ghi nhận lỗi nếu có. Không thay digest bằng `latest` để né lỗi build.

## 3. Tạo thư mục và thông tin khởi tạo

```bash
install -d -m 0750 /var/lib/moodle-distribution
docker image inspect --format '{{.Id}}' moodle-php:8.3 >/var/lib/moodle-distribution/php-image-id
install -d -m 0755 /var/www /opt/moodle-distribution
install -d -o root -g www-data -m 0750 /etc/moodle
install -d -o www-data -g www-data -m 0770 /var/lib/moodledata /var/cache/moodle
```

Trong `bootstrap.sh`, thực hiện nguyên khối Python từ chú thích **Generate secrets ON THE INSTANCE** đến `chmod 0640 /etc/moodle/bootstrap.json`. Khối này sinh mật khẩu DB/admin, lưu JSON chỉ root/web group đọc được và lưu thông tin admin riêng ở `/root/moodle-initial-admin.txt` mode 0600. Không in JSON ra terminal hay chèn password vào SQL bằng tay.

## 4. Tạo PostgreSQL role và database

Thực hiện khối `systemctl enable --now postgresql` và pipeline Python/psql ngay sau chú thích **SQL receives only…**. Script tạo role `moodle`, database `moodle` UTF-8, dùng password hex vừa sinh. Những câu SQL không nhận đầu vào tự do từ YAML.

```bash
runuser -u postgres -- psql -d postgres -c '\du moodle'
runuser -u postgres -- psql -d postgres -c '\l moodle'
ss -ltn
```

DB chỉ phục vụ máy local trong mô hình này. Không mở cổng 5432 ra Internet. Ứng dụng kết nối TCP `127.0.0.1`, dùng role `moodle`, không dùng tài khoản postgres superuser.

## 5. Lấy code và tạo config

```bash
git clone --depth 1 --branch v4.5.15 https://github.com/moodle/moodle.git /var/www/moodle
git -C /var/www/moodle describe --tags --exact-match
docker run --rm --network none --entrypoint php \
  --mount type=bind,src=/etc/moodle,dst=/etc/moodle,readonly \
  --mount type=bind,src=/var/www/moodle,dst=/var/www/moodle \
  --mount type=bind,src=/opt/moodle-distribution,dst=/opt/moodle-distribution,readonly \
  moodle-php:8.3 /opt/moodle-distribution/configure.php
chown -R root:www-data /var/www/moodle
find /var/www/moodle -type d -exec chmod 0750 {} +
find /var/www/moodle -type f -exec chmod 0640 {} +
```

`configure.php` sinh `config.php` với DB, URL, dataroot, localcachedir và quyền thư mục. Code/config không cho web user ghi; `moodledata` writable và nằm ngoài webroot. Nếu clone/tag thất bại, dừng lại và kiểm tra bản phát hành; không tự chuyển sang `master`/`latest`. [Hướng dẫn cài Moodle](https://docs.moodle.org/405/en/Installing_Moodle)

## 6. PHP và Apache

Đọc `moodle.ini` và `moodle-apache.conf`, đã được COPY vào image ở bước 2. Các thiết lập quan trọng: `max_input_vars=5000`, memory 256 MiB, upload 64 MiB, OPcache, tắt hiển thị lỗi. Apache giữ PHP slash arguments, không list directory và chặn truy cập file cấu hình/metadata.

```bash
/opt/moodle-distribution/php-cli.sh -r 'echo PHP_VERSION, " ", ini_get("max_input_vars"), PHP_EOL;'
docker run --rm --network none --entrypoint apache2ctl moodle-php:8.3 configtest
```

Kết quả: `Syntax OK`, PHP 8.3 và giá trị ít nhất 5000. CLI/web dùng cùng image và bộ ini; vẫn đối chiếu trang Environment/PHP info trong giao diện quản trị. Wrapper CLI do root gọi Docker nhưng tiến trình PHP trong container chạy `33:33`, tương ứng www-data trên host. Không gọi `php` trực tiếp trên host hoặc cho www-data quyền Docker.

## 7. Cài schema và tài khoản quản trị

```bash
/opt/moodle-distribution/php-cli.sh /opt/moodle-distribution/install-db.php
```

Wrapper đọc file riêng tư và truyền password vào bộ cài trong bộ nhớ tiến trình PHP. Không để password xuất hiện trong OS command line. Khi lỗi, giữ lại log, kiểm tra Environment/PHP/DB; cài dở không phải trạng thái có thể tự ý chạy lại migration vô hạn. [CLI Moodle](https://docs.moodle.org/405/en/Administration_via_command_line)

## 8. Cron và health

Tạo các systemd service/timer theo đúng năm khối `cat` cuối bootstrap: web service, cron service/timer, backup service/timer. Sau đó:

```bash
systemctl daemon-reload
systemctl enable --now moodle-web.service moodle-cron.timer
date -u +%FT%TZ >/var/lib/moodle-distribution/installed
rm -f -- /etc/moodle/bootstrap.json
/opt/moodle-distribution/health.sh
systemctl start moodle-cron.service
journalctl -u moodle-cron.service --no-pager -n 50
docker logs --tail 50 moodle-web
ss -ltn
```

Phải thấy web chỉ nghe `127.0.0.1:8080`, không có `0.0.0.0:8080`. Thấy timer active chưa đủ: kiểm tra task thực sự hoàn tất và trang Scheduled tasks. Không cấu hình thêm crontab nếu đã dùng systemd timer này. Nếu cấu hình S3, bật `moodle-backup.timer` sau khi chạy backup thủ công thành công; xem [runbook vận hành](05-operations.md).

## 9. Mở site và nghiệm thu

Mở terminal mới ở máy vận hành:

```powershell
aws --region ap-southeast-1 ssm start-session --target <INSTANCE_ID> --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["8080"],"localPortNumber":["8080"]}'
```

Giữ phiên port forwarding mở và vào `http://localhost:8080`. Nếu PowerShell/CLI phiên bản đang dùng xử lý JSON khác, lưu JSON tương tự vào file và dùng `--parameters file://ports.json`. Đọc admin credential bằng `sudo cat /root/moodle-initial-admin.txt` trong phiên SSM riêng tư; không đưa vào ảnh báo cáo. Đăng nhập, đổi password và admin email.

Tạo course `Cloud Lab`, tạo user học viên giả, enrol, upload một PDF tự tạo, tải lại và đối chiếu SHA-256. Chạy backup/restore theo runbook trước khi kết luận lab thành công.

## 10. Nhật ký mỗi lần cài

Lưu mã lần chạy, thời gian bắt đầu/kết thúc, AMI ID, instance type/region, OS, Git tag/commit, Docker image ID, PHP/DB version, bước lỗi, cách sửa và kết quả kiểm tra. Che account/instance ID nếu chính sách của lớp yêu cầu; luôn bỏ password/token/private key khỏi bằng chứng.
