# Bàn giao Small

Môi trường vận hành: Sydney (`ap-southeast-2`), profile `moodle-project`; dev dùng `config/sydney.yaml`, staging dùng `config/sydney-staging.yaml`. Chọn rõ cấu hình trước mỗi lệnh. Kết quả và các mục còn chờ ký nằm trong [biên bản nghiệm thu](13-small-acceptance.md); medium/large chưa triển khai.

## Nhận mã và kiểm tra

Nhánh bàn giao là `mq`. Cài Python theo `requirements.txt`, Terraform, AWS CLI và Session Manager plugin; kiểm tra phiên bằng STS. So khớp account với hồ sơ riêng của lab trước khi thực hiện thao tác AWS. Không dùng profile mặc định của máy nếu chưa đối chiếu.

```powershell
$env:AWS_PROFILE = 'moodle-project'
aws sts get-caller-identity --region ap-southeast-2
python -m src.moodle_cloud --config config/sydney.yaml doctor
python -m src.moodle_cloud --config config/sydney.yaml validate
python -m src.moodle_cloud --config config/sydney.yaml status
python -m src.moodle_cloud --config config/sydney.yaml health --wait
```

`status` chỉ trả kết quả hạ tầng. Dùng health và [cloud acceptance](06-test-plan.md) để kiểm tra ứng dụng. Không apply saved plan cũ: plan đã lưu của dev có thay thế EC2 do bundle bootstrap đổi; replacement sẽ ảnh hưởng DB/file trên máy.

## Mở site và kiểm tra giao diện

Lấy instance ID từ `status`, thay `<INSTANCE_ID>` trong lệnh sau rồi giữ terminal chạy:

```powershell
aws --region ap-southeast-2 ssm start-session --target <INSTANCE_ID> --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["8080"],"localPortNumber":["8080"]}'
```

Mở `http://localhost:8080`. Mỗi lần chỉ forward một môi trường vào cổng này vì `wwwroot` đã ghim URL đó. Không mở ingress public để demo. Xem credential qua SSM bằng tài khoản người vận hành được phép; không ghi mật khẩu vào video, báo cáo, chat hay Git. Credential admin hiện hành được giữ ở `/root/moodle-initial-admin.txt`; quy tắc sau restore xem [vận hành](05-operations.md).

Người kiểm tra độc lập thực hiện và lưu ảnh/video đã che thông tin nhạy cảm:

- Student đăng nhập, mở khóa học, tải tài liệu, nộp bài và xem điểm/phản hồi.
- Teacher xem bài nộp, chấm điểm và kiểm tra student chỉ xem được dữ liệu phù hợp.
- Đăng xuất, kiểm tra file riêng không còn truy cập được và giao diện không có lỗi bố cục.
- Ghi tên người kiểm tra, thời điểm, commit, môi trường và kết quả; sửa runbook nếu phải hỏi thêm.

HTTP acceptance đã kiểm tra login/logout, enrolment, file, submission/grade và phân quyền. Nó không đánh giá bố cục trình duyệt. Công cụ điều khiển Chrome đã tự dừng vì không xác minh được URL; phần giao diện chưa được agent ký đạt.

## Backup, state và phục hồi

Giữ riêng các state `.work/moodle-sydney-dev`, `.work/moodle-sydney-staging`, `.work/moodle-sydney-backup` và `.work/moodle-sydney-budget`, cùng credential fixture và dữ liệu backup. Chuyển giao qua kho riêng có kiểm soát quyền, không đưa vào gói source.

```powershell
python -m src.moodle_cloud --config config/sydney.yaml backup --wait
```

Backup mới không tự có nghĩa đã restore-tested. Bộ đã diễn tập restore, thời gian và kết quả sau reboot được ghi ở biên bản. Fixture credential phải khớp phiên bản DB dump, đặc biệt trước/sau đổi mật khẩu admin; không thay fixture cũ bằng object `latest` rồi kết luận restore hỏng.

## Chi phí và vòng đời

Tổng ngân sách dự án **150 USD**: dự kiến 112,50 USD, dự phòng 37,50 USD. Budget AWS tháng 11/2026 theo dõi usage trước credit/refund của toàn account; cảnh báo nội bộ actual >75% và forecast >100% qua SNS→SQS. Không có email recipient và budget không tự dừng tài nguyên. Xem [chi phí](07-report-and-cost.md) và [module budget](../infra/budget/README.md).

Dev/staging giữ để demo, owner là nhóm thực hiện đồ án. Mốc giữ mặc định: đến khi kết thúc demo; người nhận ghi ngày cụ thể vào hồ sơ riêng. Tắt EC2 khi không dùng nếu phù hợp lịch backup; EBS và một số tài nguyên vẫn tính phí. Sau demo, tạo/kiểm chứng backup ngoài EC2, review destroy plan từng state rồi dọn. Không xóa lab cũ ngoài state hoặc bucket backup/state chỉ để làm sạch checklist. Generator và máy cài thử là tài nguyên tạm, được dọn sau khi lưu bằng chứng.

Budget kỳ hiện tại kết thúc 01/12/2026 UTC. Nếu dự án kéo dài qua tháng, cập nhật kỳ theo số tiền còn lại của tổng 150 USD; không coi tháng mới là được cấp thêm 150 USD.

## Demo 12–15 phút

Theo [kịch bản báo cáo](07-report-and-cost.md): giới thiệu kiến trúc và YAML; validate/health; student/teacher và file/bài nộp; cron/backup; staging sau restore; kết quả tải, chi phí và cleanup. Dùng log của lượt dựng sạch để trình bày provision; ghi rõ phần live và phần quay trước. Không chạy restore/destroy trực tiếp lên site đang trình diễn chỉ để minh họa.
