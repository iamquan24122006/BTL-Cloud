# Chi phí, báo cáo và demo

## 1. Dự toán theo thời gian dùng thực tế

Đã xác nhận **4 thành viên, ngân sách AWS 400 USD và tài khoản AWS thường** (13/10/2026). Tạm hiểu đây là tổng ngân sách đồ án, không phải 400 USD/người hoặc 400 USD/tháng. Chưa biết credit và deadline; lịch dưới đây dùng giả định 4 tuần, region `ap-southeast-1` như cấu hình mẫu.

Phân bổ **300 USD cho kế hoạch triển khai và 100 USD dự phòng**. Đây là hạn mức nội bộ, không phải báo giá, hóa đơn dự kiến đã tính đủ hoặc cam kết đủ tiền cho mọi cấu hình. Nếu thanh toán bằng tiền, dự phòng còn phải bao gồm thuế/tỷ giá và phí chưa tính; nếu dùng credit, kiểm tra phạm vi áp dụng và ngày hết hạn.

| Giai đoạn | Hạn mức USD | Công việc được ưu tiên |
|---|---:|---|
| Tuần 1 | 40 | Small thủ công, dữ liệu giả, backup/restore đầu tiên |
| Tuần 2 | 60 | IaC/CLI, dựng lại small, staging tạm thời |
| Tuần 3 | 120 | Medium: ALB, RDS, EFS, Redis, ASG và cron runner |
| Tuần 4 | 80 | Đo tải, restore drill, diễn tập và demo |
| Dự phòng | 100 | Sửa lỗi, chi phí lưu lại, phát sinh và nghĩa vụ thanh toán |
| **Tổng** | **400** | **Mục tiêu chi có kế hoạch: tối đa 300 USD** |

Ubuntu 26.04 và Docker/PHP chạy trên EC2 small đã dự toán; chưa thêm ECS, ECR hay máy riêng cho container. Tính cả giờ build image, EBS chứa Docker layers/build cache và lưu lượng tải image/package. Theo dõi đĩa trước backup/restore; ngân sách 400 USD không tự tăng theo thay đổi hệ điều hành.

### Cấu hình và thời lượng để đưa vào Calculator

Dùng [AWS Pricing Calculator](https://calculator.aws/) tại region đã chọn, lưu link estimate/export và ngày tra cứu. Đơn giá theo region cho các SKU dưới đây chưa được chốt trong repository; các trang giá đã được đối chiếu về cách tính phí, không lấy ví dụ giá US East làm giá Singapore.

| Hạng mục | Giả định nhập để lập dự toán |
|---|---|
| Small | 1 EC2 t3.medium, 30 GiB gp3; tối đa 80 instance-hours cho các đợt lab đầu |
| Staging small tạm | Tối đa 40 instance-hours cộng dồn để thử restore, không giữ thêm một bản suốt tháng |
| Medium app | 2 EC2 t3.medium, ASG min/desired 2 và max 3; tối đa 140 giờ tồn tại stack ở tuần 3–4 |
| Scale-out | Dành thêm tối đa 12 instance-hours cho node thứ ba; tính riêng |
| Cron runner | 1 EC2 t3.small trong cùng cửa sổ medium; không đặt task migration trong mọi app node |
| Database | RDS PostgreSQL 16 Single-AZ, bắt đầu dự toán db.t4g.small, 20 GiB gp3; kiểm tra SKU/engine khả dụng |
| File/cache | EFS Regional, dữ liệu demo mục tiêu <=2 GiB; Redis node-based loại nhỏ tương thích engine/TLS của region, chốt SKU trước apply |
| ALB | 1 ALB trong 2 AZ, dùng 1 LCU trung bình làm giả định ban đầu và thêm kịch bản tải cao |
| Egress | 1 NAT Gateway cho lab, tính giờ + GB + IPv4; tính cả lưu lượng qua AZ nếu có |
| Storage/app | Khoảng 60 GiB EBS cho 2 app + cron; bổ sung volume của node scale-out theo giờ tồn tại |
| Lưu lâu hơn stack | S3 <=50 GiB mục tiêu tính cả versions, snapshot và EBS còn giữ; nhập thời gian lưu đủ 4 tuần |
| Quan sát và kiểm thử | CloudWatch logs có retention, secrets, DNS/chứng chỉ/domain nếu cần và máy phát tải riêng |

140 giờ là **tổng thời gian dịch vụ tồn tại và bị tính phí**, bao gồm giờ chờ dựng/xóa và các đêm còn bật; không chỉ đếm giờ nhóm ngồi làm. Ví dụ 7 cửa sổ 20 giờ dễ kiểm kê hơn việc giữ medium chạy 24/7. Với 2 app chạy 140 giờ phải nhập 280 instance-hours, chưa gồm cron và scale-out. Trước P1, đối chiếu tổng dự toán phần còn lại với tiền thực còn lại sau khi giữ khoản dự phòng; giảm giờ chạy nếu không vừa.

Một NAT, RDS Single-AZ và một cache node giúp giảm phạm vi lab nhưng còn điểm lỗi đơn. Mục tiêu medium là chứng minh nhiều app node và state dùng chung; chưa được gọi là HA toàn hệ thống. Không bật RDS/Redis Multi-AZ hoặc CloudFront trong cấu hình mặc định của kế hoạch này. Chỉ làm thử nghiệm HA ngắn khi còn ngân sách, P1 đã ổn và có mục tiêu đo cụ thể.

### Cơ chế kiểm soát ngân sách của nhóm

- D cập nhật sổ chi phí mỗi buổi: số đã ghi nhận, phần chưa cập nhật, tài nguyên còn chạy/lưu, dự toán đến lúc cleanup và tiền dự phòng còn lại. A xác nhận danh sách tài nguyên, C xác nhận backup trước thao tác xóa.
- Mốc lũy kế 200 USD: kiểm tra lại dự toán. 280 USD: dừng bổ sung dịch vụ/phép thử ngoài kế hoạch. 300 USD: đóng phần triển khai có kế hoạch; chỉ dùng dự phòng cho nhu cầu cụ thể đã thống nhất. 340 USD: ưu tiên hoàn tất bằng chứng và cleanup. Không đợi số hiển thị chạm 400 USD.
- Với tài khoản có quyền Billing, tạo budget theo **toàn kỳ đồ án** hoặc theo dõi lũy kế xuyên tháng, không để mốc reset hàng tháng làm mất dấu tổng 400 USD. Thêm cảnh báo actual và forecast theo các mốc phù hợp. Cảnh báo có độ trễ và không phải giới hạn cứng. [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- Với AWS Academy/Learner Lab, trước hết kiểm tra quy định tài khoản, số credit còn lại và quyền dịch vụ/role được cấp. Terraform small hiện tự tạo IAM role/profile; nếu tài khoản chỉ cho dùng role có sẵn thì phải điều chỉnh IaC trước deploy. Chưa giả định mọi dịch vụ hoặc quyền tạo Budget đều được phép.
- Dùng một môi trường tích hợp chung; dev cá nhân chủ yếu validate/mock tests ở local. Khi cần staging phục hồi thì tạo tạm, không giữ bốn stack AWS riêng cho bốn thành viên.

### Các khoản dễ bị bỏ sót

Public IPv4 có mức 0,005 USD/địa chỉ-giờ theo trang giá AWS đã tra. ALB public hai AZ và NAT có thể dùng nhiều địa chỉ; đếm tài nguyên thực tế thay vì tính một địa chỉ cho cả VPC. NAT còn có phí theo giờ và GB xử lý. [Giá VPC](https://aws.amazon.com/vpc/pricing/)

ALB tính riêng giờ hoạt động và LCU; RDS dòng T có thể phát sinh CPU credit vượt baseline; EFS và cache cần tính theo loại đã chọn. Kiểm tra các nguồn tương ứng khi chốt Calculator: [ALB](https://aws.amazon.com/elasticloadbalancing/pricing/), [RDS PostgreSQL](https://aws.amazon.com/rds/postgresql/pricing/), [EFS](https://aws.amazon.com/efs/pricing/), [ElastiCache](https://aws.amazon.com/elasticache/pricing/).

RDS đã stop vẫn tính storage/backup và tự khởi động lại sau 7 ngày nếu không chủ động start. Do đó kế hoạch cleanup không thể chỉ ghi “stop DB rồi để đó”. [Dừng RDS tạm thời](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_StopInstance.html)

| Khoản | Small hiện tại | Medium/large khi triển khai | Đơn vị cần lấy giá |
|---|---|---|---|
| EC2 | 1 instance + cron cùng máy | App node + cron runner + máy phát tải | Instance-hour |
| EBS | 30 GiB mẫu | Root/cache trên từng node | GiB-month, IOPS/throughput thêm nếu có |
| Public IPv4 | 1 địa chỉ khi instance chạy | ALB/NAT và địa chỉ khác theo topology | Address-hour |
| Database | Trong EC2 | RDS instance, Multi-AZ, storage, backup | Instance-hour + GiB-month |
| ALB | Không | ALB-hour + LCU | Theo request/connection/byte |
| EFS | Không | Data, throughput/IO theo cấu hình | GiB-month và usage |
| Redis | Không | Node/serverless theo phương án chọn | Node-hour hoặc usage |
| Egress | Public EC2, không NAT | NAT Gateway hoặc VPC endpoints | Giờ + GB xử lý + endpoint/AZ |
| S3 | Backup tùy chọn | Backup/artifact, version cũ | GiB-month + request + retrieval nếu có |
| Observability | Local log | CloudWatch ingestion/retention/alarms | GB + alarm/metric |
| DNS/Internet | Không cần domain cho lab | Hosted zone/domain/data transfer | Theo dịch vụ |

Công thức khung:

```text
Chi phí = tổng(instance-hours × giá/giờ)
        + storage trung bình × giá/GiB-month
        + chi phí IP + request + data transfer + log + dịch vụ bổ sung
        - credit/discount thực tế áp dụng
```

Không nhân giá tháng của EBS với 40/730 chỉ vì EC2 chạy 40 giờ: volume vẫn tồn tại khi stop. Hủy EC2 small sẽ xóa root volume theo cấu hình; snapshot, S3 và các tài nguyên độc lập có thể còn tính phí. Cần kiểm kê sau mỗi buổi.

Kiểm tra địa chỉ nhận cảnh báo và quyền xem chi phí của D; chưa có budget/alert nào được tạo trong tài khoản AWS bởi lần cập nhật tài liệu này.

Không kết luận Free Tier đủ dựa trên tên instance: xem quyền lợi, credit, ngày mở tài khoản và giá dịch vụ của chính tài khoản. Trong bài báo cáo trình bày cả giá trước credit để người khác có thể tái lập dự toán.

## 2. Dàn ý báo cáo đề xuất

| Chương | Nội dung | Minh chứng chính |
|---|---|---|
| 1. Giới thiệu | Vấn đề, mục tiêu, phạm vi, câu hỏi nghiên cứu | FR/NFR và kế hoạch |
| 2. Cơ sở kỹ thuật | Moodle code/DB/file/cron/cache; IaC; AWS thành phần dùng thật | Tài liệu chính thức và ma trận phiên bản |
| 3. Phân tích thiết kế | Small và đường mở rộng, trust boundary, IAM, state, secret | Sơ đồ và ADR |
| 4. Cài đặt | Cài tay, script, Terraform, CLI, xử lý lỗi | Cấu trúc repo, ví dụ YAML và flow |
| 5. Thực nghiệm | Chức năng, tái lập, tải, backup/restore, chi phí | Bảng kết quả gốc, hình và logs |
| 6. Đánh giá | Trả lời câu hỏi nghiên cứu, giới hạn, so sánh mục tiêu | Số đo, sự cố và nguyên nhân |
| 7. Kết luận | Đóng góp đã chứng minh và P1/P2 chưa hoàn thành | Checklist nghiệm thu |
| Phụ lục | Lệnh cài, hướng dẫn chạy, cấu hình mẫu, nguồn | Không kèm state/secret |

Nếu nhóm chỉ hoàn tất small, chương 5 chỉ đánh giá small. Medium/large để trong thiết kế/hướng phát triển. Tránh đưa sơ đồ nhiều dịch vụ rồi mô tả như mọi dịch vụ đã được dựng và kiểm chứng.

## 3. So sánh thủ công và tự động

| Chỉ tiêu | Cài tay | CLI + Terraform | Cách đo |
|---|---|---|---|
| Thời gian đến Moodle ready | Chưa đo | Chưa đo | Cùng mốc bắt đầu/kết thúc |
| Số thao tác người dùng | Chưa đếm | Chưa đếm | Ghi thao tác có quyết định, không đếm từng dòng output |
| Lỗi cấu hình | Chưa đo | Chưa đo | Nhật ký lỗi và thời gian sửa |
| Khả năng dựng lại | Chưa thử | Chưa thử | Hai lần trên EC2 sạch |
| Thời gian restore | Chưa đo | Chưa đo | Cùng dataset và backup format |
| Chi phí một buổi lab | Chưa đo | Chưa đo | Billing thực tế/estimate có giả định |

Không điền số minh họa như kết quả thật. Nếu không đủ thời gian đo lặp, ghi rõ đó là quan sát một lần, chưa đủ cơ sở suy rộng.

## 4. Demo 12–15 phút

| Thời lượng | Nội dung |
|---|---|
| 0–2 phút | Nêu bài toán, phạm vi P0 và sơ đồ small |
| 2–4 phút | YAML, validate, một lỗi cấu hình bị bắt, saved plan |
| 4–7 phút | Mở site đã dựng, login, khóa học, upload/download |
| 7–9 phút | Cron journal, quyền thư mục và health |
| 9–12 phút | Backup set/checksum và staging đã restore; đối chiếu file |
| 12–15 phút | Số liệu tải/chi phí, giới hạn, destroy plan |

Provision EC2 + cài package có thể vượt thời gian demo, nên chuẩn bị video/log của lần dựng sạch và live site đang hoạt động. Trình bày rõ đoạn nào live, đoạn nào ghi trước. Không dùng dữ liệu/mật khẩu thật trên màn hình. Không chạy destroy site đang demo trước khi đã chốt bằng chứng và backup.

## 5. Câu hỏi phản biện cần trả lời

1. Tại sao Moodle cần backup cả DB và moodledata, và vì sao hai snapshot độc lập chưa chắc cùng một điểm nhất quán?
2. Vì sao thêm web node đòi hỏi session/file/lock dùng chung?
3. Vì sao ALB/ASG không làm database single-AZ trở thành HA?
4. Secrets nằm ở đâu trong small, và sẽ đổi thế nào khi chuyển sang Secrets Manager/RDS?
5. Khi đã chạy migration, vì sao rollback chỉ code là chưa đủ?
6. Số tài khoản, người dùng online và concurrent request khác nhau thế nào trong kết quả đo?
7. Terraform state mất thì ảnh hưởng gì? Vì sao backup bucket có vòng đời riêng?
8. Kết quả đo qua SSM bị ảnh hưởng bởi những thành phần nào?

## 6. Hồ sơ bàn giao

Repository + cấu hình mẫu; hướng dẫn dựng; phiên bản/lockfile; ảnh sơ đồ; log test cục bộ; bằng chứng cài tay/auto; biên bản restore; kết quả JMeter tổng hợp; calculator estimate; báo cáo và video demo. Lưu credential, state, saved plan và backup dữ liệu ở nơi riêng có kiểm soát quyền.
