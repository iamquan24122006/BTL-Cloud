# Cẩm nang sử dụng CLI Moodle Cloud

CLI đọc YAML, gọi Terraform/AWS CLI và dùng SSM để vận hành máy. Đây là công cụ chạy trên máy của người triển khai, không phải giao diện web hay REST API.

## 1. Cài CLI và chọn AWS profile

Cài package trong virtual environment để có các lệnh `mcloud`, `mpublic` và `mmedium`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

`pip install -e .` cài từ bản repo đang mở và tự cài PyYAML. Nếu đã đẩy phiên bản lên GitHub, có thể cài trực tiếp bằng `python -m pip install "git+https://github.com/iamquan24122006/BTL-Cloud.git"`. Package chưa được publish lên PyPI, nên `pip install moodle-cloud-distribution` chưa dùng được.

Chọn cấu hình, AWS profile và account một lần trong PowerShell hiện tại:

```powershell
$env:MOODLE_CLOUD_CONFIG = (Resolve-Path 'config/dev.yaml').Path
$env:MOODLE_CLOUD_ACCOUNT = '123456789012'
$Project = 'moodle-lab'
$Environment = 'dev'
$Name = "$Project-$Environment"
$Region = 'ap-southeast-1'
$env:AWS_PROFILE = 'my-aws-profile'
```

Đổi account/profile theo AWS của bạn. Không dùng `config/sydney.yaml` hoặc `config/sydney-staging.yaml` nếu không định thao tác lên lab hiện có. Cấu hình mặc định là `config/dev.yaml`; đổi cấu hình bằng `MOODLE_CLOUD_CONFIG` hoặc truyền `-c config/ten-file.yaml`. `MOODLE_CLOUD_ACCOUNT` giúp `mpublic` và `mmedium` lấy account ID mặc định. Các biến trên chỉ tồn tại trong PowerShell hiện tại; muốn giữ lâu dài, thêm chúng vào PowerShell profile.

Khi cài từ pip bình thường, dữ liệu Terraform lưu ở `~/.moodle-cloud/work`; có thể đổi bằng `MOODLE_CLOUD_WORKDIR`. Khi cài editable trong repo, dữ liệu tiếp tục nằm ở `.work` như trước.

Kiểm tra công cụ và phiên AWS:

```powershell
mcloud --help
mcloud doctor
aws sts get-caller-identity --region $Region
```

`doctor` kiểm tra Terraform, AWS CLI và Session Manager plugin; nó không kiểm tra quyền IAM đầy đủ.

## 2. Luồng triển khai small/medium

Chạy theo thứ tự. CLI dùng cấu hình đã chọn ở trên; có thể thêm `-c config/ten-file.yaml` vào lệnh để đổi riêng một lần.

```powershell
mcloud validate
mcloud render
mcloud preflight
mcloud plan
```

| Lệnh | Tác dụng |
|---|---|
| `validate` | Kiểm tra YAML offline; không gọi AWS |
| `render` | Sinh tfvars từ YAML; không apply tài nguyên |
| `preflight` | Kiểm tra danh tính/account và prerequisite. Small cần `MOODLE_CLOUD_ACCOUNT` hoặc `--expected-account`; medium đối chiếu `account_id` trong YAML |
| `init` | Khởi tạo Terraform thủ công. Thường không cần gọi riêng vì `plan` tự init |
| `plan` | Khởi tạo Terraform nếu cần, đọc AWS và lưu saved plan dùng một lần |

Đọc kỹ plan: account/region, tài nguyên tạo-sửa-xóa-thay thế, dữ liệu có nguy cơ mất và chi phí phát sinh. Dừng nếu plan không khớp mục tiêu. Apply plan đã review:

```powershell
mcloud apply --confirm $Name
mcloud health --wait
mcloud status
```

`--confirm` phải đúng bằng `<project>-<environment>`. Saved plan chỉ dùng một lần; nếu apply lỗi/gián đoạn, chạy `plan` lại và review lại. `status` đọc outputs Terraform, còn `health --wait` mới gửi kiểm tra tới máy qua SSM. Apply kết thúc không tự chứng minh Moodle đã sẵn sàng.

Ngay sau khi tạo EC2, `health --wait` chờ SSM agent đăng ký nếu AWS trả `InvalidInstanceId`, sau đó chờ cloud-init và kiểm tra Moodle. Giới hạn tổng thời gian bằng `--timeout`, ví dụ `mcloud health --wait --timeout 1800`. Lỗi quyền AWS vẫn được báo ngay; CLI không gửi lại một lệnh đã được AWS tiếp nhận.

Nếu plan có delete/replace tài nguyên dữ liệu, CLI có thể yêu cầu `--allow-data-loss`. Chỉ dùng sau khi đã xác nhận backup ngoài tài nguyên và hiểu rõ tác động; không dùng cờ này để bỏ qua review.

Với small, lấy `instance_id` từ `status`; có thể mở shell bằng `aws ssm start-session --target <instance-id> --region $Region`. Mật khẩu admin khởi tạo được giữ trên EC2 tại `/root/moodle-initial-admin.txt`; chỉ đọc qua SSM trong phiên riêng tư, sau đó đổi mật khẩu.

## 3. Lệnh vận hành

### Health, backup và theo dõi SSM

```powershell
mcloud health --wait
mcloud backup --wait
```

Không dùng `backup` thành công để kết luận đã thử restore. Nếu bỏ trống `backup_bucket`, backup small chỉ nằm trên EC2 và mất khi hủy EBS.

Không dùng `--wait` thì CLI trả `CommandId`; theo dõi lệnh đó đến trạng thái cuối:

```powershell
$CommandId = '00000000-0000-0000-0000-000000000000'
mcloud command-status --command-id $CommandId --wait
```

`Pending`, timeout hoặc SSM `Success` chưa đủ để chứng minh nghiệp vụ Moodle đạt. Kiểm tra output/exit code và chạy health hoặc acceptance tương ứng.

### Restore staging

Restore chỉ nhận cấu hình `staging`, S3 backup URI theo đúng bucket/prefix và yêu cầu `--allow-data-loss` cùng xác nhận chính xác. Thay `$Config`, `$Name` và URI bằng staging/backup thật:

```powershell
# Chuẩn bị YAML staging riêng từ config/staging.example.yaml trước:
# environment phải là staging, project trùng nguồn, backup_bucket trỏ đúng S3 bucket.
$Config = 'config/my-lms-staging.yaml'
$Name = 'moodle-lab-staging'
$BackupUri = 's3://my-private-backup-bucket/moodle-lab-staging/20261114T120000Z'
mcloud -c $Config restore --backup-uri $BackupUri --confirm $Name --allow-data-loss --wait
```

Restore ghi đè môi trường staging. Không chạy trên site đang dùng hoặc site demo đang giữ dữ liệu cần bảo toàn. Medium restore có bước kiểm tra/resume riêng; làm theo [runbook medium](10-medium-n2.md).

### Destroy lab small

```powershell
mcloud plan --destroy
# Review destroy plan và xác nhận backup ở ngoài EC2 trước:
mcloud destroy --confirm $Name --allow-data-loss
```

Destroy xóa EC2/EBS và dữ liệu local. S3 backup ngoài state không tự bị xóa. Nếu đã bật CloudFront small, trước tiên rollback bằng `mpublic disable --confirm $Name`, rồi review/destroy root CloudFront theo [cleanup addon](20-small-public.md); sau đó mới destroy root small. Giữ thư mục work đến khi đã kiểm kê và xử lý tất cả state/tài nguyên.

## 4. Small public CloudFront

Frontend là lệnh riêng `mpublic`; dùng account từ `MOODLE_CLOUD_ACCOUNT` hoặc truyền `--expected-account`. Với small đã health tốt:

```powershell
mpublic plan
# Review plan riêng của CloudFront, secret origin và security group:
mpublic apply --confirm $Name
mpublic status
```

`apply` tạo frontend và cấu hình URL Moodle; sau đó kiểm tra URL HTTPS, login và học liệu thật. `mpublic activate --confirm $Name` chỉ dùng để retry host setup sau partial failure. `mpublic disable --confirm $Name` trả site về SSM nhưng không xóa CloudFront/secret; cleanup tài nguyên theo runbook riêng. Chặng viewer tới CloudFront dùng HTTPS; origin small dùng HTTP được giới hạn theo cấu hình lab.

## 5. Medium và trợ giúp

CLI chính dùng được với medium sau khi YAML và prerequisite đã sẵn sàng. `config/medium.example.yaml` có placeholder, không deploy nguyên trạng. Medium cần state/backend S3, artifact/image ECR, Secrets Manager, AMI và cấu hình mạng; lệnh chuẩn bị là `mmedium prepare`, `mmedium plan` và `mmedium apply`. Dùng [quy trình N2](10-medium-n2.md), không áp dụng nguyên cấu hình của lab nhóm.

Xem đầy đủ tùy chọn của lệnh bằng:

```powershell
mcloud --help
mcloud restore --help
mpublic --help
```

Hướng dẫn triển khai site mới theo từng bước: [Tạo một Moodle LMS mới](23-create-lms.md).
