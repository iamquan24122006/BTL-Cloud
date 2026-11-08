# Demo Small trên AWS

Môi trường: Sydney `ap-southeast-2`, profile `moodle-project`. Dev là `config/sydney.yaml`; staging là `config/sydney-staging.yaml`. Mỗi môi trường dùng một EC2 `t3.small`, 30 GiB EBS gp3. [Biên bản nghiệm thu](13-small-acceptance.md) là nguồn kết luận kết quả; phần này là kịch bản thao tác.

## Chuẩn bị trước buổi demo

Mở PowerShell tại gốc repository. Cần Python có PyYAML, Terraform, AWS CLI v2 và Session Manager plugin trong PATH. Nếu dùng venv chuẩn, kích hoạt bằng `.\.venv\Scripts\Activate.ps1`. Kiểm tra:

```powershell
$env:AWS_PROFILE = 'moodle-project'
python -m src.moodle_cloud --config config/sydney.yaml doctor
python -m src.moodle_cloud --config config/sydney.yaml preflight --expected-account 828676179987
python -m src.moodle_cloud --config config/sydney.yaml validate
python -m src.moodle_cloud --config config/sydney.yaml status
python -m src.moodle_cloud --config config/sydney.yaml health --wait
.\scripts\demo-small.ps1 -Environment dev -ExpectedAccount 828676179987 -CheckOnly
```

Nếu AWS báo session expired, đăng nhập lại đúng profile bằng `aws login --profile moodle-project`, xác thực trên trình duyệt rồi chạy lại preflight. Nếu EC2 đang stopped, khởi động đúng instance của môi trường trong EC2 Console rồi đợi SSM Online. `status` đọc Terraform outputs; health mới kiểm tra ứng dụng. Không apply saved plan cũ để mở demo: plan từng ghi nhận replacement EC2.

Mở đường hầm bằng terminal thứ nhất và giữ terminal chạy:

```powershell
.\scripts\demo-small.ps1 -Environment dev -ExpectedAccount 828676179987
```

Script tự đối chiếu account với `-ExpectedAccount`, đọc region/project/URL từ YAML, tìm duy nhất EC2 đang chạy theo tên môi trường, kiểm tra SSM Online và kiểm tra cổng 8080. Có thể chọn executable Python bằng `-Python` và profile bằng `-Profile`. Script chỉ mở session vào lab có sẵn. Mở `http://localhost:8080/login/index.php`; URL phải giữ đúng `localhost:8080` vì Moodle đã ghim `wwwroot`. Không đổi sang IP public hoặc một local port khác.

Chuẩn bị riêng mật khẩu các tài khoản giả `student`, `studentb`, `teacher`, `outsider` từ `/etc/moodle/acceptance.json` trên đúng EC2 qua phiên SSM của người vận hành. Admin hiện hành ở `/root/moodle-initial-admin.txt`. Không chiếu terminal xem credential hoặc bật quay màn hình khi lấy mật khẩu. Dùng cửa sổ/profile trình duyệt riêng cho student và teacher để tránh lẫn phiên; tắt lưu mật khẩu. Không chạy lại seed trên site đã có dữ liệu.

## Kịch bản 12–15 phút

| Phút | Thao tác | Điều cần cho người xem thấy |
|---|---|---|
| 0–2 | Mở YAML và [danh sách dịch vụ](16-small-services.md), giải thích sơ đồ | Một EC2 chạy web/PHP, PostgreSQL và cron; EBS chứa dữ liệu; S3 giữ backup; truy cập qua SSM |
| 2–4 | Chạy validate, status, health ở terminal thứ hai | YAML hợp lệ, đúng đích dev, health exit 0; provision dùng log/video đã chuẩn bị |
| 4–7 | Đăng nhập `student`, My courses → **Cloud Integration Lab** → **Fixture download** | Tải được `fixture.txt`, nội dung có dòng tiếng Việt; student mở được course đã enrol |
| 7–9 | Mở **Cloud Recovery Assignment**; student xem bài nộp/điểm; teacher mở View all submissions hoặc Grade | Student có bài nộp và điểm fixture 87/100, feedback `Reviewed student`; teacher thấy hai bài, studentb 93/100 |
| 9–11 | Xem cron và log backup; chạy backup sau khi kết thúc thao tác student | Cron/timer active, backup thành công, đủ file trên S3; web phục hồi sau khoảng dừng ghi |
| 11–13 | Đóng tunnel dev bằng Ctrl+C; mở tunnel staging, vào lại site | Dữ liệu course/file/bài nộp/điểm đã restore tồn tại; nêu bằng chứng restore/reboot đã lưu |
| 13–15 | Mở bảng tải, billing/budget và checklist bàn giao | Nói đúng số lượt đã có bằng chứng, workload, giới hạn một node và lịch cleanup |

Fixture đã có bài nộp và điểm để kiểm chứng restore. Nếu giảng viên cần thao tác nộp/chấm trực tiếp, teacher tạo một assignment riêng **Demo trực tiếp** trong course (bật file submissions, comments, grade 100); student nộp `demo-small.txt`; teacher chấm và lưu, student tải lại trang để xem kết quả. Giữ nguyên **Cloud Recovery Assignment** để acceptance tiếp tục đối chiếu điểm/hash cố định. Chụp màn hình trước/sau để thấy thay đổi.

Thử quyền: đăng xuất student rồi mở lại URL file đã copy; Moodle phải yêu cầu đăng nhập hoặc từ chối. Đăng nhập `outsider`, mở course **Cloud Integration Lab** bằng URL đã copy; tài khoản này không được enrol nên không đọc được nội dung. Đăng nhập lại student, kiểm tra không thấy chức năng quản trị/chấm bài của teacher.

## Cron, backup và staging

Mở SSM shell bằng terminal thứ hai, thay ID bằng kết quả script/status:

```powershell
$instanceId = 'i-THAY-BANG-ID-TU-STATUS'
aws --profile moodle-project --region ap-southeast-2 ssm start-session --target $instanceId
```

Trong shell Ubuntu, các lệnh chỉ đọc sau có thể trình chiếu:

```bash
sudo systemctl is-active moodle-web.service moodle-cron.timer moodle-backup.timer
sudo systemctl show moodle-cron.service --property=Result --property=ExecMainStatus
sudo systemctl list-timers --all 'moodle-*'
sudo journalctl -u moodle-cron.service -n 15 --no-pager
```

Tạo backup bằng Python CLI ở PowerShell khi không còn thao tác ghi qua trình duyệt:

```powershell
python -m src.moodle_cloud --config config/sydney.yaml backup --wait
python -m src.moodle_cloud --config config/sydney.yaml health --wait
aws --profile moodle-project --region ap-southeast-2 s3 ls s3://moodle-sydney-backup-828676179987/moodle-sydney-dev/
```

Backup dừng web/cron trong giai đoạn dump/archive để DB và file nhất quán, rồi mở lại trước upload. Chọn timestamp được báo bởi lệnh backup; dùng `s3 ls` prefix đó để trình bày tám file: `database.dump`, `moodledata.tar.gz`, `config.php`, `code.txt`, `runtime-image.txt`, `runtime-Dockerfile`, `SHA256SUMS`, `manifest.json`. Không tải/mở nội dung `config.php` khi trình chiếu. Manifest upload cuối đánh dấu bộ hoàn chỉnh; checksum đạt không đồng nghĩa đã thử restore bộ mới.

Để minh họa staging, đóng tunnel dev rồi chạy:

```powershell
python -m src.moodle_cloud --config config/sydney-staging.yaml health --wait
.\scripts\demo-small.ps1 -Environment staging -ExpectedAccount 828676179987
```

Đăng nhập bằng credential staging hiện hành; password admin có thể khác dev. Dùng biên bản restore và reboot trong [nghiệm thu](13-small-acceptance.md) để giải thích phục hồi. Thực hiện restore trước buổi demo theo [runbook](05-operations.md) nếu cần; restore sẽ ghi đè staging nên không chạy trên site đang trình diễn. Không diễn giải bộ backup mới nhất là đã restore-tested khi chưa có report tương ứng.

## Bằng chứng và xử lý sự cố

Lưu ảnh: course sau login; file tải về; bài nộp/điểm của student; màn hình chấm bài teacher; bị chặn sau logout/outsider; health/cron; danh sách tám object backup; staging sau phục hồi; bảng tải và budget. Ghi ngày, môi trường, commit (`git rev-parse --short HEAD`), người thao tác và kết quả. Người kiểm tra độc lập ký vào hồ sơ bàn giao sau khi tự chạy.

| Hiện tượng | Cách xử lý |
|---|---|
| Session expired | Đăng nhập lại đúng profile, xác minh STS rồi tiếp tục |
| Không có EC2 running hoặc SSM Offline | Kiểm tra đúng region/tên môi trường, trạng thái EC2, agent/role và đường ra mạng |
| Port 8080 bận | Đóng tunnel cũ bằng Ctrl+C; không mở đồng thời dev/staging trên cùng cổng |
| Connection refused | Xác nhận terminal tunnel còn chạy; chạy health; xem `moodle-web.service` qua SSM |
| Redirect sai hoặc đăng nhập lẫn site | Dùng đúng `http://localhost:8080`; đóng tunnel trước khi đổi môi trường; đăng xuất hoặc dùng profile trình duyệt riêng |
| Không thấy course/bài nộp | Kiểm tra đúng tài khoản và môi trường; đối chiếu report acceptance, không seed lại dữ liệu |

Sau demo, đóng tunnel, giữ backup/state trong kho riêng có kiểm soát quyền và thực hiện lịch giữ/xóa theo [bàn giao](14-small-handover.md). EC2 dừng vẫn còn EBS; budget cảnh báo không tự dừng tài nguyên.
