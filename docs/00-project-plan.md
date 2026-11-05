# Kế hoạch đồ án chi tiết

Các bước và lệnh để tiếp tục từ mã hiện tại nằm trong [hướng dẫn hoàn tất project](09-completion-guide.md). Trạng thái dưới đây chỉ đổi khi nhóm có bằng chứng thực nghiệm.

## 1. Đề tài và câu hỏi nghiên cứu

**Tên đề xuất:** Xây dựng công cụ triển khai và vận hành Moodle LMS trên Amazon Web Services bằng Infrastructure as Code.

**Bài toán:** cài thủ công dễ khác biệt giữa các lần thực hiện; dữ liệu gồm database và file phải khôi phục cùng nhau; việc tăng số web node đòi hỏi tách trạng thái dùng chung. Đồ án đo xem tự động hóa giảm bao nhiêu thao tác và thời gian, đồng thời đánh giá chi phí, tính tái lập và khả năng phục hồi.

Ba câu hỏi để trả lời bằng bằng chứng:

1. Cùng cấu hình đầu vào có dựng lại được một site tương đương không?
2. Sau mất máy chủ, có phục hồi được khóa học, bài nộp và file từ backup không?
3. Khi tải tăng, giới hạn nằm ở CPU/PHP, database, file hay dịch vụ dùng chung?

## 2. Phạm vi đã chọn

Thông tin đã xác nhận: **nhóm 4 người, ngân sách AWS 400 USD, dùng tài khoản AWS thường** (xác nhận ngày 13/10/2026). Tạm hiểu 400 USD là tổng ngân sách cho đồ án; chưa xác nhận ngân sách theo tháng, credit hoặc deadline. Giữ lịch 4 tuần làm kế hoạch làm việc và kiểm tra quyền dịch vụ trước khi chọn cấu hình cloud cuối cùng.

| Mức | Sản phẩm cần có | Trạng thái trong repository |
|---|---|---|
| P0 — bắt buộc | Cài thủ công 1 EC2; lưu lệnh và kiểm tra | Runbook và script tương ứng |
| P0 | Terraform dựng small, CLI YAML validate/plan/apply/status | 29 unit test đạt; lab mới `moodle-lab-v2-dev` đã apply 6 tài nguyên mạng, còn 4 tài nguyên do bị chặn `iam:CreateRole`; EC2 chưa tạo |
| P0 | Cron, backup nhất quán, thử restore sang máy mới | Docker local đã qua cron và dump/archive/restore sang dữ liệu mới ngày 29/10/2026; script systemd/S3 và restore EC2 chưa được nghiệm thu |
| P0 | Báo cáo, kịch bản demo, bảng đo tải/chi phí | Có mẫu và tiêu chí; chưa có số liệu thực nghiệm |
| P1 — mở rộng | ALB, private app, RDS, EFS, Redis, ASG | Thiết kế; chưa có Terraform triển khai |
| P2 — nâng cao | Multi-AZ cho các thành phần, AMI, plugin, upgrade tự động | Backlog; không đưa vào tuyên bố đã hoàn thành |

Với nguồn lực hiện tại, chọn **P0 + P1 làm mục tiêu triển khai của nhóm**: small là baseline bắt buộc, medium là phần tích hợp tuần 3 sau khi small đã restore thành công và có dự toán vừa hạn mức. Large chỉ thiết kế; chưa đặt mục tiêu chứng minh 5.000 người dùng. Mã nguồn hiện vẫn chỉ hỗ trợ small, việc đổi mục tiêu kế hoạch không có nghĩa medium đã được cài đặt.

Không đưa dữ liệu sinh viên thật vào lab. Không cam kết SLA hoặc chứng nhận production từ kết quả demo.

## 3. Yêu cầu chức năng

| ID | Yêu cầu | Cách nghiệm thu |
|---|---|---|
| FR01 | Kiểm tra YAML; từ chối khóa lạ/secret và cấu hình ngoài phạm vi | Test đầu vào không hợp lệ, không gọi AWS |
| FR02 | Sinh biến hạ tầng; cô lập dev và staging | Hai thư mục state khác nhau |
| FR03 | Lập kế hoạch trước thay đổi | Có saved plan, tài khoản AWS và fingerprint |
| FR04 | Áp dụng đúng kế hoạch đã xem | Từ chối nếu source/config/plan/account đổi |
| FR05 | Tự cài stack và Moodle | Health + đăng nhập + tạo khóa học thành công |
| FR06 | Chạy tác vụ nền | Nhật ký cron, scheduled task chạy thành công |
| FR07 | Backup database + file cùng thời điểm dừng ghi | Checksum và manifest; restore thực tế |
| FR08 | Hủy tài nguyên có chủ đích | Có destroy plan và xác nhận mất dữ liệu |
| FR09 | Phân biệt hạ tầng tồn tại với ứng dụng sẵn sàng | Status không tự tuyên bố healthy |

## 4. Yêu cầu phi chức năng

- **Tái lập:** cố định Moodle tag; ghi AMI ID, phiên bản OS/PHP/database và provider lock. AMI lookup lấy bản Canonical mới tại thời điểm plan, vì vậy phải lưu ID nếu so sánh hai lần triển khai.
- **Bí mật:** không đưa password vào YAML, user-data hay biến Terraform; mật khẩu được sinh trên EC2; code chỉ đọc với web user.
- **Khôi phục:** backup có database, `moodledata`, tham chiếu code và config; thử restore trên staging trước nâng cấp.
- **Quan sát:** có log cloud-init, Apache, cron, backup. CloudWatch agent/alarms là hạng mục P1, không có sẵn ở P0.
- **Vận hành:** script cài lại sau thành công chạy health; cài dở phải điều tra hoặc dựng máy sạch. Không giả định script sửa được mọi trạng thái lỗi.
- **Chi phí:** chỉ bật lab khi làm việc, tính cả storage, IPv4 và lưu backup; Budget alert không phải giới hạn cứng.

## 5. Phân công 4 người và lịch 4 tuần

A/B/C/D là ký hiệu để thay bằng tên thành viên. Mỗi người có sản phẩm kỹ thuật và viết phần báo cáo tương ứng; D tổng hợp báo cáo, không phải người duy nhất viết tài liệu.

| Người | Trách nhiệm chính | Đầu ra sở hữu | Người kiểm tra chéo |
|---|---|---|---|
| A — hạ tầng | AWS networking, IAM, Terraform, RDS, ALB, ASG | Module IaC, sơ đồ mạng, plan và cleanup | C |
| B — Moodle | Cài tay trên Ubuntu 26.04, Docker/PHP, bootstrap, EFS, Redis/session, cron | Runbook cài, image/runtime, bài kiểm tra đa node | D |
| C — công cụ và vận hành | CLI/YAML, CI, quản lý state, backup/restore, đóng gói release | CLI, tests, pipeline, biên bản phục hồi | A |
| D — kiểm chứng và chi phí | JMeter, metric/log/alarms, đo tải, theo dõi ngân sách, demo | Workload, bảng kết quả, dashboard, dự toán và báo cáo tổng hợp | B |

Mỗi môi trường chỉ có một người thực hiện Terraform apply tại một thời điểm. A điều phối hạ tầng dùng chung; C kiểm tra plan và state. Khi chuyển sang làm việc nhóm trên medium, phải hoàn tất backend chia sẻ có khóa và cập nhật CLI tương ứng trước khi nhiều máy cùng vận hành. D tổng hợp chi phí, cả nhóm chịu trách nhiệm dọn tài nguyên mình tạo.

| Ngày | Công việc | Chủ trì / phối hợp | Đầu ra/điều kiện qua cổng |
|---|---|---|---|
| 1 | Chốt quyền tài khoản, region, Budget và sổ chi phí | A / D | Xác định 400 USD tổng hay theo tháng, credit hay tiền; dịch vụ được phép |
| 2 | Đối chiếu phiên bản và thiết kế small/medium | A / B, C | ADR, mạng, hợp đồng module, kế hoạch state |
| 3 | Cài Moodle thủ công; D lập smoke test; C đọc luồng cài | B / D, C | Nhật ký lệnh, phiên bản và thao tác kiểm tra |
| 4 | Quyền file, cron, lỗi thường gặp; A chuẩn bị IaC | B / A, D | Login/course/upload/cron hoạt động |
| 5 | Backup và restore thủ công sang máy sạch | C / B, D | G1 và biên bản restore đầu tiên |
| 6–7 | IaC small; CLI và CI làm song song trên máy cá nhân | A / C | fmt/validate, test CLI, plan đã xem |
| 8 | Tích hợp bootstrap; D kiểm tra log/health | B / A, D | Deploy sạch bằng cloud-init |
| 9 | Hoàn thiện CLI; chốt state nhóm và input module P1 | C / A | Chốt account/plan, quy trình deploy có khóa |
| 10 | Dựng lại small, restore staging; chốt dự toán P1 | C / D, A | G2/G3 cho small; dự toán phần còn lại <= hạn mức khả dụng |
| 11 | P1: RDS; chuyển dữ liệu và thử kết nối ứng dụng | A / B, C | DB private, TLS, backup nhất quán |
| 12 | P1: ALB/HTTPS, private app; log/metric | A / B, D | DNS/chứng chỉ hợp lệ, health và dashboard |
| 13 | P1: EFS, Redis session/MUC; thử request qua 2 node | B / A, D | Upload A/đọc B, session không mất khi đổi node |
| 14 | P1: ASG, release/migration riêng và cron runner | A / B, C | Thay node không mất dữ liệu, migration không chạy trùng |
| 15 | Restore P1 và cổng quyết định phạm vi demo | C / D, cả nhóm | Medium đạt kiểm tra hoặc chốt small với lý do rõ ràng |
| 16 | Tạo dữ liệu thử và xác minh JMeter | D / B | JMX, assertion nghiệp vụ, dữ liệu giả |
| 17 | Đo tải, lặp và phân tích điểm nghẽn | D / A, B | Metric theo workload, giới hạn và lỗi |
| 18 | Thử thay node/restore; tổng hợp RTO và chi phí | C / D, A | Bằng chứng vận hành; số tiền còn lại |
| 19 | Viết phần báo cáo của từng người, kiểm tra chéo | Cả nhóm / D biên tập | Báo cáo có nguồn, số đo và đúng trạng thái thực hiện |
| 20 | Demo, backup cuối và cleanup | Cả nhóm | Video/bằng chứng; danh sách tài nguyên còn tính phí |

### Hạn mức cho từng tuần

| Giai đoạn | Hạn mức USD | Người theo dõi |
|---|---:|---|
| Tuần 1 — lab thủ công và restore đầu | 40 | D tổng hợp, B/C ghi tài nguyên |
| Tuần 2 — Terraform/CLI và dựng lại small | 60 | D tổng hợp, A/C ghi tài nguyên |
| Tuần 3 — tích hợp medium | 120 | D tổng hợp, A điều phối |
| Tuần 4 — đo tải, restore và demo | 80 | D tổng hợp, cả nhóm cleanup |
| Dự phòng toàn đồ án | 100 | Cả nhóm xem xét trước khi sử dụng |
| **Tổng** | **400** | |

Đây là phân bổ hạn mức, không phải giá AWS đã xác nhận. Tiền chưa dùng có thể chuyển sang tuần sau sau khi cập nhật sổ chi phí. Không nhân ngân sách thành 400 USD/người. Chi tiết cấu hình, giờ chạy và điều kiện mở P1 nằm trong [kế hoạch chi phí](07-report-and-cost.md).

## 6. Cổng nghiệm thu

**G1 — cài thủ công:** login được, tạo course, upload và tải đúng checksum, cron chạy. **G2 — tự động hóa:** dựng từ cấu hình trên máy mới, chức năng như G1, sai cấu hình bị từ chối. **G3 — phục hồi:** restore sang staging, đối chiếu course/user/file và thời gian. **G4 — báo cáo:** mỗi kết luận có log, metric hoặc ảnh đã che thông tin nhạy cảm.

Chỉ đánh dấu hoàn thành sau khi có bằng chứng thực tế. Repository hiện là bộ triển khai và tài liệu chuẩn bị; kết quả cloud chưa được thực hiện.

## 7. Rủi ro và cách xử lý

| Rủi ro | Biểu hiện | Xử lý |
|---|---|---|
| Không có quyền IAM/SSM/EC2 | AccessDenied khi plan hoặc kết nối | Kiểm tra trước ngày 3, nhờ quản trị cấp đúng quyền |
| Hết ngân sách | Dịch vụ chạy qua đêm, storage dư | Budget + kiểm kê sau buổi làm, xem mục cleanup |
| Backup chưa đồng bộ | File tồn tại nhưng DB thiếu tham chiếu | Dừng mọi writer, dùng cùng backup set |
| Cài dở | DB migration một phần | Giữ log, restore/dựng lại máy lab mới |
| P1 vượt thời gian | ASG/EFS/Redis chưa ổn | Ưu tiên G1–G4 cho P0, ghi P1 là hướng phát triển |
| Đo tải sai | Chỉ đo trang login/redirect | Assertion cho trang khóa học và thao tác đăng nhập thật |
