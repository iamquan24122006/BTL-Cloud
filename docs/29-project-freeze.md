# Quyết định chốt dự án — 15/11/2026

Người dùng yêu cầu: **“chốt dự án ở đây nhé, up tất cả các code lên github và dừng lại”**. Bản chốt gồm mã nguồn hiện có, IaC, kiểm thử, tài liệu, bằng chứng đã lọc và các sơ đồ được nhóm bổ sung. Nhánh bàn giao là `master` tại [GitHub BTL-Cloud](https://github.com/iamquan24122006/BTL-Cloud).

## Phạm vi và trách nhiệm

- Quân tiếp nhận vận hành; lịch giữ demo đã xác nhận đến hết 30/11/2026 UTC+7. Quân tự xóa tài nguyên khi cần.
- **Không triển khai tự xóa theo ngưỡng 150 USD và không có lịch cleanup tự động.** Yêu cầu tạo cơ chế đó đã bị người dùng hủy trước khi triển khai. Budget hiện có chỉ theo dõi/cảnh báo.
- Bản chốt sử dụng kết quả small và medium Sydney đã có bằng chứng. GUI Quân tự thực hiện và bổ sung ảnh. Benchmark so sánh, một số ca lỗi và vấn đề cảnh báo cron giữ nguyên là giới hạn theo [danh sách trạng thái](24-remaining-work.md).
- [Billing và bàn giao](28-cost-and-handover.md) chỉ chốt account Sydney trong kỳ ghi rõ ở hồ sơ; không chứng nhận tổng mọi account, hóa đơn cuối kỳ hoặc nghiệm thu đầy đủ P0+P1.

## Tác vụ Explore AWS đã dừng

Tác vụ học Explore AWS được dừng theo yêu cầu chốt. Snapshot cuối đã kiểm tra của tác vụ này ghi nhận DynamoDB hoàn thành, tổng thưởng hoạt động đã ghi nhận 80 USD và credit còn 144,69 USD. Lambda tạm đã tạo Function URL yêu cầu xác thực IAM và trả HTML thành công qua Invoke; tại snapshot đó bài Lambda chưa được AWS ghi nhận hoàn thành. Không tuyên bố đã nhận thêm credit cho Lambda hoặc Bedrock.

Các tài nguyên bài học tạm chưa chạy cleanup trước khi dừng: bảng `explore-aws-credit-table-20261115`, function `explore-aws-credit-web-20261115`, role cùng tên thêm hậu tố `-role` và log group `/aws/lambda/explore-aws-credit-web-20261115`, tại Sydney. Đây là tài nguyên riêng của bài học; Quân tự dọn khi cần. Chúng được tạo sau snapshot inventory/billing của biên bản bàn giao, nên không nằm trong dự toán cấu hình snapshot đó.

## Nội dung công bố

Đưa mã nguồn và tài liệu trong repository lên GitHub. Giữ ngoài Git các thư mục làm việc tạm, credential/token, raw API receipt, Terraform state/plan/tfvars thật và raw backup; không ép đưa `.work` lên GitHub. Bản chốt giữ nguyên cấu hình riêng đang vận hành trên máy, không tiếp tục thử nghiệm hoặc thay đổi AWS.

Lượt chốt chỉ kiểm tra tính nhất quán tài liệu, phép tính chi phí, checksum và cấu trúc sơ đồ; không gán đây là một lượt chạy lại CI/runtime/GUI. Lịch sử kiểm thử đúng commit vẫn được giữ trong hồ sơ kỹ thuật.
