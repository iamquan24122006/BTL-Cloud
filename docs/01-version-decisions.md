# ADR: phiên bản và phạm vi tự động hóa

Ngày đối chiếu nguồn: 08/10/2026. Cần kiểm tra lại lịch hỗ trợ và bản vá trước khi dùng cho một đợt triển khai mới.

## ADR-01: dùng Moodle 4.5.15 cho lab đầu tiên

Chọn Moodle 4.5.15 + PHP 8.3 trong container + PostgreSQL 16 trên Ubuntu Server 26.04. Moodle 4.5 yêu cầu PHP tối thiểu 8.1, hỗ trợ 8.3 và PostgreSQL tối thiểu 13; Sodium và `max_input_vars >= 5000` là yêu cầu cần kiểm tra. [Yêu cầu Moodle 4.5](https://moodledev.io/general/releases/4.5)

4.5 là nhánh LTS còn nhận cập nhật bảo mật đến 04/10/2027, đã hết sửa lỗi thông thường. Bảng phát hành liệt kê 4.5.15 ngày 05/10/2026. [Lịch phát hành và hỗ trợ](https://moodledev.io/general/releases)

Moodle 5.3 LTS đã phát hành ngày 05/10/2026; yêu cầu tối thiểu PHP 8.3 và PostgreSQL 17. Giữ 4.5 trong lab để tiếp tục kiểm chứng bộ cài và runbook PG16 đã chuẩn bị. Đổi sang 5.3 là một hạng mục nâng cấp riêng. [Yêu cầu Moodle 5.3](https://moodledev.io/general/releases/5.3)

**Hệ quả:** CLI khóa phiên bản 4.5.15. Muốn thay phiên bản phải sửa cả ma trận tương thích, bootstrap, đường dẫn webroot/CLI nếu release mới thay đổi, plugin và kiểm thử. Không thay mỗi `moodle_version` rồi coi là nâng cấp an toàn.

**Kiểm tra ở máy thật:** `git describe --tags --exact-match`, `sudo /opt/moodle-distribution/php-cli.sh -v`, cùng wrapper với `-m`, `/usr/lib/postgresql/16/bin/psql --version` và trang Environment của Moodle. Chưa chạy stack Linux trên EC2 trong phiên chuẩn bị này.

## ADR-02: Ubuntu 26.04 làm host, PHP 8.3 trong container

Theo yêu cầu nhóm, host là Ubuntu Server 26.04 LTS (`resolute`), amd64. Terraform tìm AMI Canonical có tên `ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-*`; lưu AMI ID thực tế của mỗi lần plan. [Cách tìm AMI Ubuntu](https://ubuntu.com/aws/docs/aws-how-to/instances/find-ubuntu-images/)

Gói `php` mặc định của Ubuntu 26.04 phụ thuộc PHP 8.5. Vì Moodle 4.5 chưa công bố hỗ trợ phiên bản này, không dùng `apt install php` cho ứng dụng. [Gói PHP của Ubuntu](https://packages.ubuntu.com/resolute/php)

Dockerfile dùng image chính thức `php:8.3-apache-bookworm`, ghim digest và bổ sung extension. Container có userland Debian Bookworm; kernel/host vẫn là Ubuntu 26.04. Docker chạy trên EC2 hiện tại, chưa có ECS/ECR hay dịch vụ tính phí mới. Dockerfile và hai file cấu hình PHP/Apache là nguồn cấu hình chung cho CLI và web. [Docker Official Image PHP](https://hub.docker.com/_/php)

`setup-host.sh` cài PostgreSQL 16 từ PGDG, kiểm tra fingerprint khóa ký và chỉ gắn khóa với kho `resolute-pgdg`. Không trỏ kho Ubuntu 24.04 vào máy 26.04. [PGDG hỗ trợ Ubuntu](https://www.postgresql.org/download/linux/ubuntu/)

Web dùng `moodle-web.service`; cron và công cụ bảo trì gọi `php-cli.sh` với UID/GID `33:33` trong container. Image ID sau build được lưu tại `/var/lib/moodle-distribution/php-image-id`; mọi runner dùng ID này. Code chỉ đọc, dataroot/cache ghi được. Docker socket không mount vào container; không thêm web user vào nhóm docker. Host networking cho phép nối PostgreSQL local; Apache chỉ bind `127.0.0.1:8080` và không publish port bằng Docker.

**Giới hạn tái lập:** digest ghim base image, nhưng APT khi build vẫn lấy bản package hiện hành. Hai lần build có thể cho image ID khác nhau. Lưu Dockerfile, image ID và Git commit làm bằng chứng; nếu cần tái lập đúng byte phải lưu image artifact/AMI riêng. Kiểm tra bản vá và rebuild có kiểm soát, rồi kiểm thử trước thay image đang phục vụ. Mã hiện tại chưa tự upgrade runtime của máy đã cài.

## ADR-03: SSM cho small, HTTPS cho bản public

Small lắng nghe `127.0.0.1:8080` và truy cập bằng SSM port forwarding. EC2 có public IPv4 để kết nối ra ngoài nhưng SG không có inbound. Browser truy cập đúng `http://localhost:8080`; dùng `127.0.0.1` thay cho hostname đó có thể bị Moodle chuyển hướng.

Bản public phải có DNS, chứng chỉ và HTTPS; không đưa preset này ra Internet bằng cách mở cổng 8080. [SSM port forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html)

## ADR-04: hạ tầng ứng dụng và backup có vòng đời khác nhau

Bucket backup được tạo và quản lý riêng, truyền tên qua `backup_bucket`. Terraform small không sở hữu bucket, nên `destroy` không xóa backup trên S3. Chính sách lifecycle, encryption và quyền đọc restore được cấu hình ở bucket đó. Đây là lựa chọn rõ ràng về vòng đời dữ liệu, không phải tài nguyên bị bỏ sót.

## ADR-05: một cron runner trong lab

Systemd timer gọi cron mỗi phút; một service đang chạy sẽ không bị systemd khởi động thêm cùng unit. Đây là cách tránh chồng lặp đơn giản ở small. Moodle có cơ chế khóa và hỗ trợ cron song song/nhiều máy; P1 dùng runner riêng với backend khóa dùng chung đã kiểm chứng. [Cron Moodle](https://docs.moodle.org/405/en/Cron)
