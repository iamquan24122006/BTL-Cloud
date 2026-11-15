# Kiểm thử CLI từ cài pip đến Moodle public — 15/11/2026

Lab kiểm thử: `test-cli-tool-dev`, account `860366539351`, region `ap-southeast-1`.

URL đã kiểm thử: **https://d3icvsvd54j00n.cloudfront.net**. Lab và URL này đã được dọn sau kiểm thử theo yêu cầu ngày 15/11/2026.

## Phạm vi và cách cài

Đã xóa 10 tài nguyên của lần thử cũ bằng saved destroy plan của `mcloud`. AWS xác nhận EC2 `i-021c034e8054d5c4b` đã terminated, VPC cũ và root volume cũ không còn. State cũ đã rỗng trước khi lưu vào `.work/cli-e2e/old-test-cli-tool-dev` để đối chiếu.

Build wheel `moodle_cloud_distribution-0.3.0-py3-none-any.whl`, tạo virtualenv mới tại `.work/cli-e2e/venv`, rồi cài wheel bằng pip cùng dependency PyYAML 6.0.2. Các lệnh triển khai chạy ngoài thư mục source; đã xác nhận module được import từ `site-packages`, có đủ YAML, Terraform, lockfile và runtime scripts. Wheel không chứa `.work`, state hoặc credential riêng.

## Các bước đã chạy

| Bước | Lệnh / kiểm tra | Kết quả |
|---|---|---|
| Xóa lần thử cũ | `mcloud plan --destroy`, review, `mcloud destroy --confirm test-cli-tool-dev --allow-data-loss` | 10 tài nguyên bị xóa |
| Cài package | `pip install <wheel>` trong virtualenv mới | Đạt |
| Chọn môi trường | Profile `default`, account `860366539351`, `config/dev.yaml` | Đúng account triển khai |
| Kiểm tra máy | `mcloud doctor` | Đạt |
| Kiểm tra cấu hình | `mcloud validate`, `mcloud preflight`, `mcloud render` | Đạt |
| Tạo lại small | `mcloud plan`, review, `mcloud apply --confirm test-cli-tool-dev` | 10 tài nguyên mới; EC2 `i-08653d064e268bc01` |
| Chờ sẵn sàng | `mcloud health --wait --timeout 1800` | Cloud-init hoàn tất; database, admin và quyền file đạt |
| Kiểm thử Moodle nội bộ | `scripts.cloud_acceptance --seed` | Course, tài liệu, enrolment, vai trò, bài nộp, điểm, login/logout đạt |
| Tạo frontend | `mpublic plan`, review, `mpublic apply --confirm test-cli-tool-dev` | 7 tài nguyên mới, distribution `E2USTCPU087ALM`; có backup trước đổi URL |
| Đọc URL | `mpublic status` | Trả đúng URL CloudFront mới |
| HTTPS từ máy triển khai | Kiểm certificate, redirect, form, đăng nhập admin, cookie, admin settings, protected paths, logout | 12/12 đạt |
| Kiểm thử Moodle public | `scripts.cloud_acceptance` sau chuyển URL | Login và phân quyền, tài liệu đúng hash, bài nộp/điểm, chặn truy cập trái phép đạt |
| Backup | `mcloud backup --wait --timeout 1200` | Backup local hoàn tất; health sau backup đạt |
| Đồng bộ output URL | Review plan chỉ đổi output, `mcloud apply --confirm test-cli-tool-dev` | 0 thay đổi tài nguyên |
| Kiểm tra cuối | `mcloud plan`, `mcloud status` | Không còn thay đổi; CLI trả đúng URL |
| Unit tests | `python -m unittest discover -s tests -v` | 103 tests đạt |

Dữ liệu kiểm thử gồm khóa học `CLOUD-INTEGRATION`, tài liệu mẫu, teacher, hai student và một user ngoài khóa học. Kiểm thử HTTP xác nhận admin/teacher/student đọc được nội dung được phép; anonymous, user ngoài khóa học và học sinh khác không đọc được tài liệu/bài nộp riêng.

## Lỗi tìm thấy và đã sửa

Chạy `health --wait` ngay sau `apply` có thể gặp `InvalidInstanceId` vì EC2 đã running nhưng SSM chưa đăng ký. CLI đã được sửa để chờ đăng ký trong giới hạn `--timeout` khi AWS từ chối gửi lệnh với mã lỗi này. Lỗi quyền và lỗi không xác định vẫn được báo ngay; lệnh đã được AWS tiếp nhận không được gửi lại. Có regression test cho retry, timeout và không gửi lặp.

Các test cũ cố định tên project `moodle-lab` hoặc mặc định Sydney đã được cập nhật theo cấu hình đang chọn và mặc định `config/dev.yaml`.

## Thông tin bàn giao tại thời điểm kiểm thử

Các lệnh sau đã dùng để chọn cấu hình khi lab còn hoạt động; sau cleanup, lab không còn instance hoặc frontend để đọc status:

```powershell
. .\.work\use-test-cli-tool.ps1
mpublic status
```

Username admin là `admin`. Mật khẩu khởi tạo được lưu riêng tại `.work/test-cli-tool-dev/private/admin.json`, và trên EC2 tại `/root/moodle-initial-admin.txt`; không có trong báo cáo này. Đổi mật khẩu sau khi nhận bàn giao.

Backup trong lượt thử nằm local trên EC2 vì `backup_bucket` rỗng và đã bị xóa cùng root volume khi cleanup. Lượt kiểm thử này chưa thử restore, đo tải hoặc kiểm tra bố cục bằng trình duyệt.

## Cleanup ngày 15/11/2026

Đã rollback URL về SSM, review và thực thi saved destroy plan cho 7 tài nguyên frontend, rồi destroy 10 tài nguyên core của `test-cli-tool-dev`. Kiểm tra AWS sau cleanup xác nhận EC2 `i-08653d064e268bc01` đã terminated, root volume và VPC đã xóa; CloudFront `E2USTCPU087ALM` trả `NoSuchDistribution`. Cả hai state không còn managed resource.

Origin secret được đánh dấu xóa với recovery window mặc định 7 ngày. Theo [tài liệu AWS](https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_delete-secret.html), secret đã đánh dấu xóa không bị tính phí. Chỉ số và thời điểm xác minh được ghi trong trường `cleanup` của kết quả bên dưới.

Kết quả máy đọc được: [results.json](results.json). Log thao tác và wheel nằm tại `.work/cli-e2e/`.

Hướng dẫn: [Tạo LMS](../../23-create-lms.md), [Cẩm nang CLI](../../24-cli-user-guide.md).
