# Terraform và CLI

## Điều kiện

Python >=3.11, PyYAML theo requirements, Terraform >=1.10,<2, AWS CLI, Session Manager plugin. Người vận hành cần quyền tạo/quản lý VPC, subnet/route/IGW/SG, EC2/EBS và IAM role/profile trong phạm vi đồ án; `iam:PassRole` chỉ role EC2 tương ứng. Quyền SSM StartSession/SendCommand chỉ instance lab và tài liệu SSM cần dùng. Chính sách chính xác phụ thuộc quyền tổ chức, không đề xuất gắn AdministratorAccess chỉ để tránh sửa lỗi quyền.

IAM role trên EC2 chỉ có SSM managed policy và quyền ghi prefix S3 khi cấu hình. Không có quyền quản trị hạ tầng hay đọc toàn bộ bucket. Role cấp cho người deploy khác role ứng dụng.

## Cấu hình và môi trường

Sửa `config/dev.yaml`; `ap-southeast-1` chỉ là giá trị mẫu. Copy `config/staging.example.yaml` thành cấu hình staging. Production chưa được CLI hỗ trợ; dùng tài liệu P1/P2 để triển khai phần đó sau.

| Khóa | Ý nghĩa |
|---|---|
| project/environment | Tên tài nguyên và đường dẫn state; không tái dùng cho AWS account khác |
| region | Region commercial AWS; phải nhất quán từ plan tới apply |
| size | Hiện chỉ `small` |
| instance_type | t3.small/medium/large; chỉ x86_64 |
| volume_gib | Số nguyên 20–200; mặc định mẫu 30 |
| moodle_version | Hiện khóa `4.5.15` |
| wwwroot | Hiện khóa `http://localhost:8080` |
| backup_bucket | Bucket S3 riêng có sẵn; rỗng nghĩa là backup local |
| tags | Chuỗi key/value, không chứa secret |

Không có trường mật khẩu, access key, plugin tự do hay lệnh shell. YAML có khóa lạ/khóa trùng bị từ chối. CLI dùng subprocess argument array, không nối đầu vào vào shell command.

## Luồng triển khai

```powershell
python -m src.moodle_cloud doctor
python -m src.moodle_cloud --config config/dev.yaml validate
aws sts get-caller-identity
python -m src.moodle_cloud --config config/dev.yaml plan
```

`plan` thực hiện init, lưu plan và manifest. Kiểm tra AWS account, region, EC2 type, AMI, dung lượng, replacement/destruction và IAM. Không chứa mật khẩu trong user-data. Saved plan vẫn phải bảo vệ vì có cấu hình và metadata hạ tầng. [Terraform saved plans](https://developer.hashicorp.com/terraform/cli/commands/plan)

```powershell
python -m src.moodle_cloud --config config/dev.yaml apply --confirm moodle-lab-dev
python -m src.moodle_cloud --config config/dev.yaml status
```

Manifest chỉ dùng một lần, kể cả apply lỗi; phải plan lại sau thao tác gián đoạn. CLI so sánh fingerprint cấu hình, file hạ tầng/script, provider lock, hash plan và AWS account trước apply. Terraform còn kiểm tra state có thay đổi kể từ lúc tạo plan. Không chạy đồng thời nhiều lệnh ghi cùng workspace.

**Thay bootstrap/user-data có thể thay EC2 và xóa DB/file local.** Cùng một cấu hình chưa bảo đảm plan luôn rỗng vì AMI lookup chọn bản mới nhất. Khi kế hoạch có replacement phải backup/restore-test trước, hoặc pin AMI cho một đợt thử nghiệm có kiểm soát. Thay đổi `backup_bucket` cũng làm user-data thay đổi; chọn bucket trước lần deploy đầu nếu cần giữ dữ liệu.

## Kiểm tra máy sau apply

Lấy instance ID từ `status`, mở SSM shell:

```bash
sudo cloud-init status --wait
sudo tail -n 80 /var/log/cloud-init-output.log
sudo /opt/moodle-distribution/health.sh
sudo systemctl start moodle-cron.service
sudo journalctl -u moodle-cron.service --no-pager -n 50
```

Khi thành công, mở đường hầm theo [lab thủ công](03-manual-lab.md), đăng nhập và làm bộ kiểm tra ứng dụng. Nếu cloud-init báo done nhưng health lỗi, vẫn coi triển khai thất bại. Xem `/var/log/moodle-install.log`, `sudo docker logs --tail 80 moodle-web` và journal của `moodle-web.service`/`moodle-cron.service`.

Preset hiện chọn Ubuntu 26.04, build image PHP 8.3 và lấy PostgreSQL 16 từ PGDG. Build lần đầu cần Internet tới Docker Hub, Debian mirror, PGDG, Ubuntu và GitHub; Terraform apply có thể xong trước bước build này. Máy đã có marker installed chỉ chạy health khi gọi lại bootstrap, không tự nâng OS/PHP. Khi chuyển một lab Ubuntu cũ, tạo plan mới và kiểm tra replacement; phục hồi dữ liệu sang máy mới theo runbook.

## State, provider lock và cộng tác nhóm

State của CLI đặt tại `.work/<project>-<environment>/terraform.tfstate`; dữ liệu init tại `terraform-data` riêng. Không commit `.work` hoặc mất thư mục này trước khi cleanup. Local backend chỉ phù hợp một người vận hành trong lab.

File `.terraform.lock.hcl` được commit để pin provider thực tế. Khi thêm hệ điều hành cho nhóm/CI, dùng `terraform providers lock -platform=windows_amd64 -platform=linux_amd64` và kiểm tra diff. Không xóa lock để né một lỗi provider.

P1 nên đổi backend sang S3 riêng mã hóa, bật versioning và cơ chế khóa phù hợp phiên bản Terraform. Bucket state khác bucket backup, quyền đọc state giới hạn; chỉ migrate bằng `terraform init -migrate-state` sau sao lưu. Cập nhật CLI để không ép local backend trước khi dùng backend khác. [S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3)

## Bảng lệnh

| Lệnh | Tác động |
|---|---|
| doctor | Kiểm tra tool trong PATH, không xác nhận IAM |
| validate | Kiểm tra YAML offline |
| render | Sinh tfvars JSON offline |
| init | Tải provider, khởi tạo backend local |
| plan / plan --destroy | Đọc AWS và tạo saved plan |
| apply --confirm … | Tạo/thay đổi AWS theo saved plan |
| status | Đọc outputs Terraform; không kiểm tra live health |
| backup | Gửi SSM command, trả command ID; chưa coi là thành công |
| destroy --confirm … --allow-data-loss | Áp dụng destroy plan, mất EC2/EBS/DB local |

Lỗi trả exit code khác 0. AWS có thể trả lỗi quyền, quota, AMI availability hoặc package mirror; lưu thông tin lỗi cần thiết nhưng không chép credential vào issue.
