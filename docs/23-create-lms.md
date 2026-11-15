# Hướng dẫn tạo một Moodle LMS mới bằng CLI

Hướng dẫn này tạo một Moodle **small** mới trên AWS, sau đó mở site bằng HTTPS qua CloudFront. Luồng dùng CLI và Terraform; người triển khai vẫn phải có AWS account, cấu hình YAML, quyền IAM phù hợp và review kế hoạch trước khi tạo tài nguyên.

Small phù hợp cho lab, lớp học nhỏ và demo: một EC2 chạy Moodle, PHP và PostgreSQL. Nó không có HA. Site public dùng CloudFront HTTPS ở phía người dùng; chặng CloudFront đến EC2 dùng HTTP được giới hạn bằng network rule và origin secret. Không dùng hướng dẫn này như cấu hình production.

Nếu chỉ muốn thử Moodle riêng tư, có thể bỏ qua bước 7 và truy cập qua SSM port forwarding. Nếu cần nhiều app node, xem [quy trình medium](10-medium-n2.md); medium cần chuẩn bị nhiều tài nguyên trước khi chạy CLI.

## 1. Chuẩn bị máy và AWS

Trên máy triển khai cần có:

- Python 3.11 trở lên và dependency trong `requirements.txt`.
- Terraform từ 1.10 đến trước 2.0, AWS CLI v2 và Session Manager plugin.
- AWS profile hợp lệ với quyền tạo các tài nguyên của small: VPC, EC2, EBS, IAM role/profile, SSM và các API liên quan. Để bật public URL, profile còn cần quyền CloudFront và Secrets Manager theo Terraform root `infra/small_public`.
- AWS region được chọn và ngân sách cho EC2, EBS, public IPv4, CloudFront, Secrets Manager và backup.

Tài nguyên chạy tiếp tục tính phí. Dùng account/lab được phép và không đưa access key, mật khẩu hay token vào YAML hoặc Git.

## 2. Clone repo và cài Python

Mở PowerShell:

```powershell
git clone https://github.com/iamquan24122006/BTL-Cloud.git
cd BTL-Cloud
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
mcloud --help
```

Nếu virtualenv của bạn dùng đường dẫn `.venv/bin/`, hãy kích hoạt virtualenv theo hệ điều hành trước khi cài. Cài Terraform, AWS CLI và Session Manager plugin riêng theo hệ điều hành; `mcloud doctor` kiểm tra chúng có trong `PATH` hay chưa.

## 3. Chọn cách tạo LMS

| Lựa chọn | Cấu hình có sẵn | Kết quả |
|---|---|---|
| **Small riêng tư** — lựa chọn thử đầu tiên | `config/dev.yaml` | Một EC2; truy cập qua SSM tunnel, không có URL public |
| **Small public HTTPS** | `config/dev.yaml` rồi chạy thêm bước 7 | Một EC2 và URL CloudFront HTTPS; có thêm phí CloudFront/Secrets Manager |
| **Medium nhiều app node** | `config/medium.example.yaml` | RDS/EFS/Redis/ASG; cần chuẩn bị nhiều tài nguyên và không dùng YAML mẫu để deploy nguyên trạng. Xem [quy trình medium](10-medium-n2.md) |

Với small, **không cần tạo hay copy file YAML mới**: các lệnh trong hướng dẫn này dùng trực tiếp `config/dev.yaml`. Không dùng `config/sydney.yaml` hoặc `config/sydney-staging.yaml` vì chúng trỏ tới môi trường nhóm đang có.

CLI hiện chưa có wizard hỏi các lựa chọn này. Với small, người dùng chọn truy cập riêng bằng cách bỏ qua bước 7, hoặc chọn URL public bằng cách chạy thêm bước 7. Medium có schema và runbook riêng.

`config/dev.yaml` hiện đặt `project: moodle-lab`, `environment: dev`, region `ap-southeast-1`, instance `t3.medium`, volume 30 GiB, Moodle 4.5.15 và `backup_bucket: ""`. Trước khi deploy, chọn giá trị phù hợp. Muốn đổi tên site, region, cỡ máy hoặc bucket thì mở và sửa trực tiếp `config/dev.yaml` (ví dụ `notepad config/dev.yaml`); giữ `wwwroot: http://localhost:8080` và Moodle version hiện được ghim ở `4.5.15`.

`project` phải là 3–24 ký tự thường, bắt đầu bằng chữ cái và chỉ chứa chữ thường, số hoặc dấu gạch ngang. `environment` chỉ hỗ trợ `dev` hoặc `staging`. Chọn `t3.small` cho lab ít tải để giảm chi phí; đánh giá tải trước khi dùng với lớp thật.

`backup_bucket: ""` chỉ phù hợp cho lần thử có thể bỏ đi: backup nằm trên EC2 và mất nếu EC2/EBS bị hủy. Nếu giữ dữ liệu học, dùng S3 bucket riêng, private, có encryption và versioning. Bước 4 có ví dụ tạo bucket bằng Terraform root `infra/backup`. Chọn bucket trước lần deploy đầu; đổi giá trị sau này có thể làm thay user-data và thay EC2. `config/dev.yaml` được Git theo dõi; không commit các chỉnh sửa riêng của môi trường nếu không định thay đổi cấu hình mẫu chung.

## 4. Chọn AWS profile và kiểm tra cấu hình

Chọn profile AWS đã được cấp quyền. Ví dụ sau theo region mẫu `ap-southeast-1` trong `config/dev.yaml`; thay account, region, project và profile bằng giá trị của bạn. Nếu muốn chỉnh YAML, sửa `config/dev.yaml` rồi đồng bộ các biến bên dưới:

```powershell
$env:AWS_PROFILE = 'my-lms-profile'
$Region = 'ap-southeast-1'
$Project = 'moodle-lab'
$Environment = 'dev'
$AccountId = '123456789012'
$Config = 'config/dev.yaml'
$env:MOODLE_CLOUD_CONFIG = (Resolve-Path $Config).Path
$env:MOODLE_CLOUD_ACCOUNT = $AccountId
$Name = "$Project-$Environment"
```

Nếu profile chưa đăng nhập và AWS CLI từ 2.32 trở lên, đăng nhập trước:

```powershell
aws login --profile my-lms-profile --region $Region
```

Sau đó xác nhận account và region:

```powershell
aws sts get-caller-identity --region $Region
```

Đối chiếu account ID từ STS với `$AccountId`. Nếu muốn backup ngoài EC2, tạo bucket trước khi validate/apply. Bucket phải có tên chưa được dùng trong toàn AWS:

```powershell
$BackupBucket = 'moodle-lab-backup-123456789012-abc123'
$BackupWorkspace = "$Project-backup"
$BackupPlan = (Join-Path (Resolve-Path '.work').Path "$Project-backup.tfplan")

terraform -chdir=infra/backup init
terraform -chdir=infra/backup workspace new $BackupWorkspace
# Nếu workspace này đã tồn tại, dùng lệnh select thay cho workspace new:
# terraform -chdir=infra/backup workspace select $BackupWorkspace
terraform -chdir=infra/backup plan "-var=region=$Region" "-var=project=$Project" "-var=bucket_name=$BackupBucket" "-out=$BackupPlan"
terraform -chdir=infra/backup show $BackupPlan
# Chỉ apply sau khi plan cho thấy bucket và chính sách mong muốn:
terraform -chdir=infra/backup apply $BackupPlan
```

`$Project` và `$Environment` phải trùng với YAML; `$Name` phải bằng `<project>-<environment>`. Nếu đã đổi `project` trong `config/dev.yaml`, đổi các biến tương ứng. Thay account suffix và chuỗi cuối bằng tên bucket thực sự duy nhất. Root backup bật Block Public Access, encryption, versioning và lifecycle hiện tại 14 ngày cho bản mới/7 ngày cho bản cũ; điều chỉnh và review retention nếu cần giữ dữ liệu lâu hơn. Sau khi tạo bucket, sửa `backup_bucket` trong YAML thành `$BackupBucket`.

Tiếp tục kiểm tra:

```powershell
mcloud doctor
mcloud validate
mcloud preflight
```

Trước khi tiếp tục, xác nhận region trong YAML đúng với `$Region`, và `doctor`, `validate`, `preflight` đều thành công. Preflight kiểm tra prerequisite và danh tính; nó không chứng nhận bạn có mọi quyền mutation cần cho apply.

## 5. Tạo Moodle small

Lập saved plan:

```powershell
mcloud plan
```

Đọc summary và Terraform plan. Dừng lại nếu account sai, có thay thế/xóa tài nguyên không mong muốn, hoặc cấu hình không phải site mới bạn định tạo. Chỉ sau khi review xong mới apply đúng plan một lần:

```powershell
mcloud apply --confirm $Name
mcloud health --wait
mcloud status
```

`apply` tạo network và EC2 rồi khởi chạy cài đặt Moodle qua cloud-init. Cài package, build PHP container và tải Moodle có thể mất thời gian; `apply` kết thúc chưa có nghĩa site đã sẵn sàng. Chờ `health --wait` thành công. `status` hiển thị outputs hạ tầng, không thay thế health check.

Nếu lệnh apply bị gián đoạn hoặc báo lỗi, đừng dùng lại saved plan cũ. Xem lỗi, chạy `plan` mới và review lại trước khi apply tiếp.

## 6. Lấy mật khẩu admin và đăng nhập

Lấy `instance_id` từ kết quả `status`, rồi mở SSM session:

```powershell
$InstanceId = 'i-THAY_BANG_INSTANCE_ID_TU_STATUS'
aws --region $Region ssm start-session --target $InstanceId
```

Trong shell SSM, đọc thông tin khởi tạo ở nơi riêng tư:

```bash
sudo cat /root/moodle-initial-admin.txt
```

Giữ mật khẩu ở nơi quản lý credential riêng; không chụp màn hình hoặc commit file chứa mật khẩu. Sau khi mở site ở bước 7 (hoặc mở tunnel riêng tư bên dưới), đăng nhập bằng username `admin`, đổi mật khẩu và cập nhật email quản trị. Site mới chỉ có tài khoản admin; cần tạo course, teacher và student trong Moodle.

## 7. Mở LMS bằng HTTPS public URL

Đảm bảo bước 5 đã hoàn thành và EC2 đang `running`. Lập plan riêng cho addon CloudFront:

```powershell
mpublic plan
```

Review plan. Addon này chỉ dành cho small; nếu plan có delete/replace thì dừng lại. Nếu hợp lý, apply bằng chính xác `<project>-<environment>` đã cấu hình:

```powershell
mpublic apply --confirm $Name
mpublic status
```

`apply` tạo CloudFront frontend, chờ distribution triển khai, tạo backup trước khi đổi URL chuẩn của Moodle, rồi cấu hình origin. Khi hoàn tất, lệnh in URL `https://...cloudfront.net`. Mở URL đó, đăng nhập bằng `admin`, đổi mật khẩu ban đầu và kiểm tra một trang course. CloudFront hostname do AWS cấp; custom domain không nằm trong luồng small này.

Đây là HTTPS giữa trình duyệt và CloudFront. Origin small được giới hạn bằng CloudFront prefix list và secret header, nhưng chặng CloudFront đến EC2 không dùng HTTPS. Cấu hình này dùng cho lab/demo, không phải TLS đầu cuối hoặc HA production. Giữ nguyên thư mục `.work`: state, plan và origin secret không được commit hay xóa khi frontend còn dùng.

### Chỉ truy cập riêng qua SSM

Nếu chưa muốn public site, bỏ qua bước 7. Thay vì CloudFront, mở port forwarding:

```powershell
aws --region $Region ssm start-session --target $InstanceId --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["8080"],"localPortNumber":["8080"]}'
```

Giữ terminal này mở và truy cập `http://localhost:8080` trên máy triển khai.

Đăng nhập bằng `admin`, đổi mật khẩu ban đầu và kiểm tra site trong trình duyệt.

## 8. Hoàn thiện nội dung và backup

Trong Moodle, đặt tên site, timezone và ngôn ngữ; tạo course; tạo tài khoản teacher/student; enrol đúng course; thử upload/tải lại học liệu và nộp bài. Thiết lập giới hạn upload trước khi mời người dùng.

Chạy kiểm tra và backup:

```powershell
mcloud -c $Config health --wait
mcloud -c $Config backup --wait
```

Backup thành công chưa chứng minh có thể restore; trước khi lưu dữ liệu quan trọng, làm restore drill theo [runbook backup/restore](05-operations.md). Nếu để trống `backup_bucket`, backup nằm local trên EC2.

## 9. Dừng lab và kiểm soát chi phí

EC2 dừng vẫn có thể phát sinh phí EBS, S3, CloudFront và các tài nguyên khác. Khi không còn cần site, backup dữ liệu cần giữ rồi làm theo [runbook backup/cleanup small](05-operations.md) và [hướng dẫn gỡ CloudFront](20-small-public.md). Hủy addon CloudFront và hủy hạ tầng small là hai phần riêng; không xóa `.work` hoặc chạy `destroy` khi chưa xác nhận đúng account, state và nguy cơ mất dữ liệu.

## Khi nào nên chọn medium?

Chọn medium khi cần nhiều app node và các dịch vụ dùng chung như RDS, EFS và Redis. Medium không phải biến thể “một lệnh” của small: cần chuẩn bị backend/state, S3, ECR image/bundle, Secrets Manager, AMI và các thiết lập mạng trước khi apply. HTTPS trực tiếp tại ALB cần domain/ACM. Xem [bàn giao medium](10-medium-n2.md) và [lab Sydney hiện có](21-medium-sydney.md); không dùng nguyên config hoặc tài khoản của lab nhóm cho site mới.
