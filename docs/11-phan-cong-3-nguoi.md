# Phân công công việc cho nhóm 3 người

Ngày lập: 03/11/2026.

Tiêu chí chi tiết cho từng tính năng, ca kiểm thử và điều kiện hoàn thành nằm trong [Đặc tả tính năng và tiêu chí nghiệm thu](12-dac-ta-tinh-nang-va-nghiem-thu.md). Dùng tài liệu này để chia người phụ trách; dùng đặc tả để lập task và xác nhận kết quả.

## 1. Mục tiêu và phạm vi

Hoàn thành đồ án triển khai Moodle trên AWS theo trình tự:

**Small → Medium → Đo tải và so sánh → Báo cáo, demo → Bàn giao và cleanup.**

- **P0 — Small:** cài thủ công, triển khai tự động bằng Terraform/CLI, kiểm tra chức năng, backup/restore và đo tải có bằng chứng.
- **P1 — Medium:** nhiều app node sau ALB, dùng RDS, EFS và Redis; kiểm chứng session/file dùng chung, thay node và phục hồi dữ liệu.
- **P2 — Hướng phát triển:** large, HA toàn hệ thống, plugin và nâng cấp tự động; không bắt buộc để hoàn thành phạm vi hiện tại.

Theo nhật ký repository trước khi lập tài liệu, kiểm thử Moodle và restore trong Docker cục bộ đã đạt. Small trên AWS chưa được nghiệm thu; lab mới `moodle-lab-v2-dev` đã tạo 6 tài nguyên mạng nhưng lần apply trước bị chặn tại `iam:CreateRole`. Medium hiện mới có thiết kế. Đây là trạng thái đã ghi nhận, chưa phải kết quả kiểm tra lại AWS ngày lập tài liệu.

Tài liệu này phân công lại cho **3 người**, thay cho phương án 4 người trong kế hoạch ban đầu. Các tên Người 1, Người 2, Người 3 cần được thay bằng tên thành viên thực tế.

## 2. Tổng quan phân công

| Thành viên | Vai trò chính | Sản phẩm chịu trách nhiệm |
|---|---|---|
| Người 1 | Hoàn thành small | Cài tay, Terraform/CLI small, bootstrap, cron, triển khai AWS và hướng dẫn dựng lại |
| Người 2 | Hoàn thành medium | Terraform/CLI medium, RDS, EFS, Redis, ALB/HTTPS, ASG, cron và release runner |
| Người 3 | Kiểm thử, vận hành và đánh giá | Bộ kiểm thử, backup/restore, JMeter, metric, chi phí, bằng chứng nghiệm thu và tổng hợp báo cáo/demo |

Mỗi người viết phần báo cáo tương ứng với công việc mình thực hiện. Người 3 tổng hợp báo cáo, không phải người duy nhất viết báo cáo.

## 3. Người 1 — Hoàn thành small

### Công việc

- [ ] Kiểm tra phiên AWS, account, region và phối hợp quản trị viên xử lý quyền IAM/EC2/SSM còn thiếu.
- [ ] Tiếp tục đúng lab mới bằng `config/small-new.yaml`, giữ state tại `.work/moodle-lab-v2-dev/`; lập plan mới và kiểm tra diff trước apply.
- [ ] Hoàn thành EC2, cloud-init, Docker/PHP, PostgreSQL, Moodle và truy cập qua SSM.
- [ ] Thực hiện cài Moodle thủ công trên EC2 sạch; ghi thao tác, thời gian, phiên bản, lỗi và cách xử lý.
- [ ] Hoàn thiện Terraform/CLI và script small nếu phát hiện lỗi khi triển khai thực tế.
- [ ] Kiểm tra health, cron, quyền thư mục và việc chặn truy cập file cấu hình/mã nguồn nhạy cảm.
- [ ] Phối hợp Người 3 nghiệm thu đăng nhập, course, enrolment, upload/download, bài nộp và phân quyền.
- [ ] Phối hợp Người 3 cấu hình backup S3, restore sang staging mới và kiểm tra sau reboot.
- [ ] Kiểm chứng dựng lại small từ cấu hình; ghi thời gian và số thao tác để so sánh cài tay với tự động.
- [ ] Hoàn thiện hướng dẫn triển khai và xử lý sự cố small.

### Sản phẩm bàn giao

- Small hoạt động trên AWS, có bằng chứng cloud-init và ứng dụng sẵn sàng.
- Mã Terraform/CLI/script small đã sửa và các kiểm tra liên quan đạt.
- Nhật ký cài tay và triển khai tự động, cấu hình mẫu không chứa secret.
- Bằng chứng chức năng, cron, reboot và biên bản backup/restore cùng Người 3.
- Phần báo cáo về cài tay, small và tự động hóa triển khai.

### Điều kiện hoàn thành

Small dựng lại được trên máy sạch, nghiệp vụ chính hoạt động, web/cron tự khởi động sau reboot, dữ liệu được backup ra ngoài EC2 và restore thành công sang staging mới. Kết quả phải có bằng chứng; Terraform apply thành công riêng lẻ chưa đủ.

## 4. Người 2 — Hoàn thành medium

### Công việc

- [ ] Chốt input/output giữa các module, cách quản lý secret, artifact triển khai và cấu hình Moodle.
- [ ] Bổ sung backend Terraform dùng chung có khóa state; mở rộng CLI/YAML cho medium và cô lập state theo môi trường.
- [ ] Viết hạ tầng mạng hai AZ: ALB public, app/DB private, security group và đường egress phù hợp.
- [ ] Tách database sang RDS PostgreSQL; cấu hình secret và kết nối TLS.
- [ ] Tích hợp EFS cho `moodledata`, thống nhất quyền file giữa các node.
- [ ] Tích hợp Redis cho session và MUC; bổ sung extension/cấu hình cần thiết.
- [ ] Thiết lập domain, chứng chỉ ACM và ALB HTTPS; cấu hình proxy và listener của app.
- [ ] Tạo artifact dùng chung và ASG với hai app node; kiểm tra node mới tự sẵn sàng.
- [ ] Tách cron runner; chỉ chạy install/upgrade/migration qua runner có kiểm soát, tránh chạy trùng trên app node.
- [ ] Phối hợp Người 3 triển khai backup nhất quán trên nhiều node và thử restore.
- [ ] Bổ sung log, metric và cảnh báo cần thiết, phối hợp Người 3 kiểm tra tín hiệu thực tế.
- [ ] Phối hợp Người 3 kiểm chứng session/file khi đổi node và khả năng ASG thay thế node lỗi.
- [ ] Hoàn thiện hướng dẫn triển khai, vận hành và xử lý sự cố medium.

### Sản phẩm bàn giao

- Mã Terraform/module, CLI/YAML và cấu hình ứng dụng medium.
- Medium hoạt động qua HTTPS với hai app node và các dịch vụ dữ liệu dùng chung.
- Quy trình release/migration, cron và artifact triển khai thống nhất.
- Bằng chứng phối hợp kiểm tra đổi node, thay node và backup/restore.
- Sơ đồ kiến trúc thực tế và phần báo cáo thiết kế, triển khai medium.

### Điều kiện hoàn thành

Hai app node phục vụ qua ALB; đổi node vẫn giữ session và đọc được file dùng chung; ASG thay thế node; cron/migration không chạy trùng; backup/restore thành công. Không kết luận HA toàn hệ thống chỉ từ việc thay thế app node.

## 5. Người 3 — Kiểm thử, vận hành và đánh giá

### Công việc có thể bắt đầu ngay

- [ ] Chuyển test plan thành checklist pass/fail có người thực hiện và đường dẫn bằng chứng.
- [ ] Chuẩn bị dữ liệu giả: admin, teacher, student, course, enrolment, bài nộp và file mẫu có checksum.
- [ ] Chuẩn bị kịch bản kiểm thử đăng nhập, course, file, bài nộp và phân quyền.
- [ ] Kiểm tra CI; phối hợp sửa lỗi và lưu kết quả GitHub Actions cùng artifact.
- [ ] Hoàn thiện quy trình/script backup/restore, kiểm tra manifest/checksum và cách đối chiếu dữ liệu sau phục hồi.
- [ ] Chuẩn bị JMeter workload, xác thực cookie/token và assertion nghiệp vụ trước khi phát tải.
- [ ] Lập mẫu thu thập metric, kết quả đo, thời gian deploy/restore và chi phí.
- [ ] Chuẩn bị sổ chi phí và phối hợp thiết lập budget/cảnh báo nếu tài khoản có quyền.

### Khi small sẵn sàng

- [ ] Nghiệm thu các mục chức năng F01–F13 trong test plan cùng Người 1.
- [ ] Thử backup S3 và restore sang EC2 staging mới; đối chiếu user/course/bài nộp/file và thử ghi dữ liệu mới.
- [ ] Ghi thời gian phục hồi, thời điểm backup và giới hạn của phép đo RTO/RPO.
- [ ] Kiểm tra sau reboot và các tình huống lỗi có kiểm soát trên staging.
- [ ] Đo tải small để lấy baseline, ghi cả ảnh hưởng của SSM tunnel và CPU credits.

### Khi medium sẵn sàng

- [ ] Nghiệm thu chức năng cùng Người 2, kiểm tra session/file khi request qua hai node.
- [ ] Thử thay app node, kiểm tra cron và phối hợp restore môi trường mới.
- [ ] Đo tải medium với cùng dataset/workload dùng cho small.
- [ ] So sánh latency, throughput, tỷ lệ lỗi nghiệp vụ, tài nguyên, thời gian phục hồi và chi phí.
- [ ] Xác định điểm nghẽn, giới hạn thử nghiệm và các yêu cầu chưa đạt.

### Cuối dự án

- [ ] Tổng hợp bảng kiểm thử, kết quả tải, chi phí và bằng chứng đã loại thông tin nhạy cảm.
- [ ] Viết phần thực nghiệm, vận hành, chi phí và đánh giá; ghép các phần báo cáo của cả nhóm.
- [ ] Chuẩn bị kịch bản demo 12–15 phút, video/log provision và nội dung demo trực tiếp.
- [ ] Phối hợp kiểm kê sau cleanup; ghi tài nguyên còn lưu, mục đích và chi phí tiếp tục phát sinh.

### Sản phẩm bàn giao

- Checklist kiểm thử và biên bản nghiệm thu có bằng chứng.
- Quy trình/script backup/restore, biên bản restore drill cho small và medium.
- JMeter test plan, kết quả đo và bảng so sánh hiệu năng–chi phí.
- Sổ chi phí, dự toán có giả định và chi phí thực tế đã ghi nhận.
- Phần báo cáo thực nghiệm/đánh giá, bản báo cáo tổng hợp và kịch bản demo.

### Điều kiện hoàn thành

Các kết luận có log, ảnh hoặc số liệu đối chiếu được; có restore thực tế; workload đo đúng nghiệp vụ; báo cáo phân biệt rõ phần đã chạy, phần chưa đạt và giới hạn. Người 3 cần tham gia viết script và kiểm chứng kỹ thuật, không chỉ tổng hợp tài liệu.

## 6. Thứ tự phối hợp

| Giai đoạn | Người 1 | Người 2 | Người 3 | Điều kiện chuyển giai đoạn |
|---|---|---|---|---|
| Chuẩn bị | Xử lý quyền, tiếp tục lab small | Thiết kế module và phát triển medium cục bộ | Chuẩn bị dữ liệu, checklist, CI, backup/restore và JMeter | Công cụ sẵn sàng, trách nhiệm rõ ràng |
| Hoàn thành small | Cài tay và triển khai tự động, sửa lỗi small | Tiếp tục phát triển medium; thống nhất giao diện cấu hình | Kiểm thử small, restore drill và đo baseline | Small chạy ổn, restore thành công |
| Hoàn thành medium | Hỗ trợ tích hợp, giữ small làm baseline | Triển khai medium, xử lý lỗi hạ tầng/ứng dụng | Kiểm tra nhiều node, restore và metric | Medium đạt bài nghiệm thu |
| Thực nghiệm | Hỗ trợ chạy/sửa small, cung cấp số liệu cài đặt | Hỗ trợ chạy/sửa medium, phân tích tài nguyên | Điều phối đo tải và tổng hợp so sánh | Có kết quả đối chiếu cùng workload/dataset |
| Bàn giao | Viết phần small, chuẩn bị demo và cleanup tài nguyên small | Viết phần medium, chuẩn bị demo và cleanup tài nguyên medium | Viết thực nghiệm, ghép báo cáo, kiểm kê chi phí/bằng chứng | Báo cáo, demo và hồ sơ bàn giao đầy đủ |

Người 2 có thể phát triển medium song song ngay từ đầu. Chỉ triển khai/nghiệm thu medium sau khi small đã ổn định, restore thành công và dự toán phần còn lại phù hợp ngân sách.

## 7. Quy tắc làm việc chung

- Mỗi môi trường chỉ có một người thực hiện Terraform apply tại một thời điểm; thống nhất người vận hành trước mỗi lượt.
- Giữ small làm baseline; medium có cấu hình và state riêng. Không dùng state rỗng hoặc cấu hình lab cũ để quản lý lab mới.
- Người 1/2 chịu trách nhiệm sửa lỗi triển khai trong phần mình; Người 3 kiểm thử lại và lưu bằng chứng.
- Backup/restore cần phối hợp: Người 3 phụ trách quy trình và kiểm chứng; Người 1/2 phụ trách tích hợp quyền, dịch vụ và điều khiển writer trong kiến trúc mình quản lý.
- Mỗi người cập nhật hướng dẫn và viết phần báo cáo của mình khi thực hiện, không dồn toàn bộ tài liệu cho Người 3 cuối kỳ.
- Dùng dữ liệu giả. Credential, state, saved plan và backup dữ liệu giữ riêng; chỉ đưa bằng chứng đã lọc vào báo cáo.
- Theo dõi ngân sách chung 400 USD của nhóm; chỉ mở rộng sau khi kiểm tra phần chi phí còn lại và khoản dự phòng.
- Chỉ cleanup sau khi lưu đủ bằng chứng và kiểm chứng backup ngoài EC2; kiểm kê cả tài nguyên độc lập còn tính phí. Không xóa state trước khi xử lý hết tài nguyên liên quan.

## 8. Checklist chốt hoàn thành project

- [ ] Small: cài tay, triển khai tự động, chức năng, reboot, dựng lại và backup/restore có bằng chứng.
- [ ] Medium: hai app node, dữ liệu/session dùng chung, HTTPS, thay node, cron/release runner và backup/restore được kiểm chứng.
- [ ] Kiểm thử chức năng và CI có kết quả; lỗi còn tồn tại được ghi rõ.
- [ ] Có kết quả đo tải small/medium với điều kiện đo và so sánh phù hợp.
- [ ] Có dự toán, chi phí thực tế đã ghi nhận và danh sách tài nguyên còn giữ.
- [ ] Có báo cáo, sơ đồ, hướng dẫn dựng lại, biên bản restore và bằng chứng nghiệm thu.
- [ ] Đã diễn tập demo và bàn giao được cho người khác làm theo.
- [ ] Đã cleanup tài nguyên không cần giữ và kiểm kê sau cleanup.

Hoàn thành toàn bộ checklist trên là đạt phạm vi **P0 + P1**. Large và các hạng mục P2 được ghi trong hướng phát triển.

## 9. Tài liệu liên quan

- [Đặc tả tính năng và tiêu chí nghiệm thu](12-dac-ta-tinh-nang-va-nghiem-thu.md).

- [Kiến trúc small và medium](02-architecture.md).
- [Triển khai Terraform và CLI](04-deployment.md).
- [Vận hành, backup và restore](05-operations.md).
- [Kiểm thử và bằng chứng nghiệm thu](06-test-plan.md).
- [Chi phí, báo cáo và demo](07-report-and-cost.md).
- [Nhật ký kiểm chứng](08-validation.md).
- [Hướng dẫn hoàn tất project](09-completion-guide.md).
- [Quyền IAM cho lab mới](10-iam-permissions.md).
