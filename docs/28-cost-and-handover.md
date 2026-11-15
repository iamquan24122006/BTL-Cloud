# Chốt billing và bàn giao vận hành — 15/11/2026

**Đã xác nhận người nhận: Quân; giữ demo đến hết 30/11/2026, UTC+7.** Phạm vi billing được người dùng chọn là **chỉ account Sydney hiện có**, không phải tổng các account của cả nhóm. Đây là xác nhận tiếp nhận và lịch giữ tài nguyên, chưa phải ký đạt mọi yêu cầu P0+P1.

**Quyết định chốt sau đó trong ngày 15/11:** người dùng yêu cầu dừng phát triển và tự xóa tài nguyên khi cần. Đề nghị tự xóa ở ngưỡng 150 USD đã được hủy trước khi triển khai; không có Lambda/Scheduler hay lịch tự xóa nào được tạo cho cơ chế đó. Các bước cleanup bên dưới là hướng dẫn để Quân tự thực hiện. [Hồ sơ bản chốt](29-project-freeze.md).

## 1. Phạm vi và kết quả billing

| Mục | Kết quả |
|---|---|
| Account / profile | `828676179987` / `moodle-project` |
| Kỳ truy vấn | `2026-10-01` inclusive → `2026-11-15` exclusive (UTC), gồm hết 14/11 |
| Phạm vi dữ liệu | Toàn account, mọi region/dịch vụ; lọc đúng LINKED_ACCOUNT để không cộng nhầm account khác |
| Thời điểm thu | `2026-11-15T08:36:28.560349+00:00` |
| Chi phí trước credit/refund | **35.31 USD** (gốc `35.3129951942`) |
| Credit đã ghi nhận | `-35.3129952361` USD |
| Thuế đã ghi nhận | `0` USD |
| Ròng sau credit | **0.00 USD**, làm tròn hai chữ số; số gốc `-4.19E-8` USD |
| Trạng thái | Estimated; không phải hóa đơn cuối kỳ hoặc số dư credit còn lại |
| Kiểm tra đối chiếu | Tổng dịch vụ = tổng loại phí = tổng DAILY độc lập; delta `0E-10` USD |
| Account N2/N3 | Ngoài phạm vi chốt theo lựa chọn của người dùng; không đặt chi phí bằng 0 |

Tháng 10 không có nhóm phí trong kết quả; chi phí ghi nhận nằm ở tháng 11. Không gán toàn bộ khoản của account cho riêng Moodle nếu chưa có cost allocation tương ứng. [Billing gốc đã lọc](evidence/cost-handover-2026-11-15/billing.json).

| Dịch vụ | Trước credit/refund (USD, 6 chữ số) |
|---|---:|
| Amazon Elastic Compute Cloud - Compute | 24.537747 |
| Amazon Virtual Private Cloud | 4.740794 |
| EC2 - Other | 4.654138 |
| Amazon ElastiCache | 0.576000 |
| Amazon Elastic Load Balancing | 0.365475 |
| Amazon Relational Database Service | 0.337782 |
| Các dịch vụ còn lại | 0.101058 |
| **Tổng theo dữ liệu chưa làm tròn** | **35.31** |

Không cộng các snapshot billing cũ vào bảng này vì chúng chồng kỳ. Dữ liệu có độ trễ và có thể được điều chỉnh; hóa đơn là căn cứ số tiền phải trả cuối cùng. [AWS: khác biệt Billing và Cost Explorer](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/differences-billing-data-cost-explorer-data.html).

## 2. Giữ demo đến 30/11 và ngân sách

Ngân sách tham chiếu của đồ án là 150 USD. Usage account đã ghi nhận chiếm **23.54%**; phần 150 USD trừ usage đã biết là **114.69 USD**. Đây không phải số dư AWS credit hoặc phần tiền chắc chắn còn lại cho mọi account. Budget AWS tháng 11 vẫn là 150 USD, actual `35.313` USD, loại credit/refund; forecast API chưa có.

Nếu giữ nguyên **7 EC2 running**, RDS, hai Redis và hạ tầng hiện tại, giá cơ bản khoảng **10.02 USD/ngày**. Từ cutoff billing `15/11 00:00 UTC` đến `01/12 00:00 UTC+7` có **377.0 giờ** cần ước tính. Tổng usage đã biết cộng kỳ chưa billing khoảng **192.74 USD**, vượt mốc 150 USD khoảng **42.74 USD** trước credit và các khoản chưa tính.

Đây là mô hình cấu hình giữ nguyên, **không phải forecast AWS hoặc hóa đơn**. EBS/RDS storage phân bổ 730 giờ/tháng, EFS dự phòng 1 GiB; IPv4 khử trùng EC2/Elastic IP và cộng tối thiểu hai địa chỉ ALB. Chưa tính ALB LCU, NAT/transfer GB, CPU surplus, snapshot/S3/ECR, secret, log/metric/alarm, thuế và thay đổi ASG. Credit đã áp dụng cho usage cũ không bảo đảm sẽ bù usage tương lai. [Dự toán và giả định](evidence/cost-handover-2026-11-15/projection.json), [giá tra 15/11](evidence/cost-handover-2026-11-15/prices.json).

| Thành phần dự toán | Số lượng | Đơn giá USD | USD/ngày |
|---|---:|---:|---:|
| EC2 running t3.small (7 at capture) | 7 | 0.0264000000 / Hrs | 4.4352 |
| RDS PostgreSQL db.t4g.micro Single-AZ | 1 | 0.0250000000 / Hrs | 0.6000 |
| Redis cache.t4g.micro | 2 | 0.0240000000 / Hrs | 1.1520 |
| Application Load Balancer (hours only) | 1 | 0.0252000000 / Hrs | 0.6048 |
| NAT Gateway (hours only) | 1 | 0.0590000000 / Hrs | 1.4160 |
| Public IPv4: EC2/EIP union + minimum 2 ALB | 9 | 0.0050000000 / Hrs | 1.0800 |
| EBS gp3 provisioned storage | 200 | 0.0960000000 / GB-Mo | 0.6312 |
| RDS gp3 provisioned storage | 20 | 0.1380000000 / GB-Mo | 0.0907 |
| EFS Standard, 1 GiB planning allowance | 1 | 0.3600000000 / GB-Mo | 0.0118 |

Quân cần ưu tiên review máy phát tải và máy cài thử khi không còn sử dụng; có thể review việc stop staging sau khi giữ đủ bằng chứng phục hồi. Các phương án đó chưa được thực hiện trong lượt bàn giao. Stop EC2 không xóa phí EBS/EIP độc lập; stop app bằng EC2 riêng lẻ cũng không bảo đảm ASG ngừng tạo máy thay thế. RDS, Redis, ALB và NAT vẫn có phí riêng khi app không có request. Không coi việc giữ nguyên mọi tài nguyên đến 30/11 là cam kết dưới 150 USD.

## 3. Tài nguyên Quân tiếp nhận

Snapshot tại `2026-11-15T08:36:28.560349+00:00`; inventory Sydney và S3/CloudFront global, không có API lỗi trong phạm vi đã đọc. [Danh sách máy và dịch vụ](evidence/cost-handover-2026-11-15/inventory.json), [sổ vòng đời từng tài nguyên](evidence/cost-handover-2026-11-15/retention.csv).

| EC2 | Chức năng | Trạng thái |
|---|---|---|
| `i-0de15ad67341ff026` | moodle-sydney-staging | running |
| `i-0d0b4ae0bf5167d27` | moodle-sydney-load-generator | running |
| `i-093f1efa8a5546034` | moodle-medium-dev-med-app | running |
| `i-08254d31ea012c8dc` | moodle-sydney-dev | running |
| `i-070badc9a77dfa33a` | moodle-sydney-manual-drill | running |
| `i-0d43470f88eb13a58` | moodle-medium-dev-med-runner | running |
| `i-0a67f2d6b579eae5e` | moodle-medium-dev-med-app | running |

Ngoài EC2: 7 volume gp3 (tổng lấy trong dự toán), 1 AMI/1 EBS snapshot, 1 RDS PostgreSQL Single-AZ 20 GiB, 2 Redis, 1 EFS, 1 ALB, 1 NAT, 3 Elastic IP allocation, 1 ASG, 4 bucket S3, 1 ECR repository, 6 secret metadata, 1 log group, 17 alarm và 2 CloudFront distribution. `Owner` trên AWS còn có các tag lịch sử (`student`, `N2`, `Team`); người chịu trách nhiệm trong **biên bản này** là Quân, chưa retag cloud.

| Nhóm tài nguyên | Mốc giữ | Sau demo |
|---|---|---|
| Small dev và medium nguồn + phụ thuộc | Đến hết 30/11/2026 UTC+7 | Từ 01/12: Quân review backup, destroy plan và danh sách tài nguyên còn tính phí |
| Small staging, generator, manual drill | Trần lịch giữ là 30/11; có thể review dừng sớm khi hết nhu cầu | Không tự stop/xóa trong lượt này |
| Backup/state/artifact/ECR/AMI/snapshot/secret | Giữ phục vụ demo và khôi phục đến 30/11 | Quân chốt retention sau demo; không tự xóa cùng compute |
| Logs, alarms, network, CloudFront và IP | Theo lab đang giữ đến 30/11 | Review riêng sau cleanup compute/data; kiểm kê xác nhận lại |

Mốc 30/11 là lịch đã xác nhận, **không phải lịch tự động tắt/xóa**. Chưa chứng nhận cleanup sau demo vì thời điểm đó chưa xảy ra.

## 4. Điểm nhận mã, dữ liệu và vận hành

- Repository: [BTL-Cloud](https://github.com/iamquan24122006/BTL-Cloud), nhánh `master`; HEAD mã nguồn trước lượt cập nhật tài liệu: `dfee3246d352fd57a27a68a8b77d0fe924b64576`. Tài liệu và evidence lượt bàn giao là phần bổ sung sau HEAD này.
- Small public: https://d1cnnw3mivc0q5.cloudfront.net; `config/sydney.yaml`. Staging: `config/sydney-staging.yaml`, truy cập theo [runbook small](14-small-handover.md).
- Medium public: https://www.moodle-cloud-distribution.mywire.org; cấu hình thật `.work/medium-sydney-live/medium.yaml`; [runbook Sydney](21-medium-sydney.md), [release host bundle](27-host-bundle-deploy.md).
- State small: `.work/moodle-sydney-dev`, `.work/moodle-sydney-staging`; backup/budget: `.work/moodle-sydney-backup`, `.work/moodle-sydney-budget`. State public addon và các root hỗ trợ có vòng đời riêng; không xóa `.work` để cleanup cloud.
- Medium dùng backend S3 có khóa; metadata apply tại `.work/moodle-medium-dev-828676179987-medium`. Không đưa backend/state/tfvars thật vào gói công khai.
- Tài khoản demo `admin`, `teacher`, `student`; mật khẩu, quyền AWS, state và raw backup chỉ chuyển qua kênh riêng có kiểm soát. Lượt này **không kiểm chứng việc chuyển secret/state hoặc quyền của một người dùng AWS mới**.
- Bằng chứng kỹ thuật giữ đúng ngày/commit: [chốt kỹ thuật](18-project-closeout.md), [hostfix](evidence/hostfix-2026-11-15/README.md), [báo cáo](19-final-report.md). Không chạy lại acceptance hoặc kiểm tra GUI trong lượt billing này.

## 5. Xác nhận bàn giao

| Nội dung | Trạng thái xác nhận |
|---|---|
| Người nhận/chịu trách nhiệm vận hành | **Quân — đã xác nhận qua hội thoại ngày 15/11/2026** |
| Lịch giữ demo | **Đến hết 30/11/2026 (UTC+7) — đã xác nhận** |
| Phạm vi billing | **Chỉ account Sydney hiện có — người dùng đã chọn** |
| Hình thức xác nhận | Lưu chỉ dẫn: “Người nhận: Quân, giữ đến 30/11”; “chỉ billing acc hiện có” |
| Hồ sơ kỹ thuật và danh sách tài nguyên | Đã lập, liên kết ở trên; checksum evidence kèm theo |
| Walkthrough GUI/reviewer độc lập | Quân tự thực hiện và bổ sung ảnh/kết quả; chưa ghi đạt trước khi có bằng chứng |
| Chuyển quyền AWS/credential/state và nhận gói riêng | Chưa kiểm chứng; không đồng nhất với xác nhận tên người nhận |
| Nghiệm thu mọi yêu cầu P0+P1/chữ ký giảng viên | Không ký thay hoặc suy ra từ xác nhận tiếp nhận |
| Cleanup sau demo | Quân phụ trách review từ 01/12; chưa chạy và chưa lập lịch tự động |

**Kết luận bàn giao:** đã chốt người nhận, mốc giữ và billing trong phạm vi account được chọn. Có thể dùng hồ sơ này để viết phần chi phí và bàn giao của báo cáo. Các ca GUI, benchmark, cảnh báo cron và coverage lỗi còn mở vẫn nằm trong [danh sách hiện hành](24-remaining-work.md).
