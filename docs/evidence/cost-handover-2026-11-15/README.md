# Billing Sydney và xác nhận tiếp nhận — 15/11/2026

Phạm vi do người dùng chốt: **chỉ billing account hiện có** (`828676179987`, profile `moodle-project`). Không cộng hoặc suy chi phí N2/N3. Quân nhận vận hành và giữ demo đến hết 30/11/2026 (UTC+7), theo xác nhận trong hội thoại.

- [Billing](billing.json): 01/10/2026 inclusive → 15/11/2026 exclusive, mọi region/dịch vụ của account; trước credit/refund **35.31 USD**, ròng làm tròn **0.00 USD**; vẫn Estimated. Tổng nhóm dịch vụ bằng tổng loại phí và tổng truy vấn DAILY độc lập (delta bằng 0).
- [Inventory](inventory.json): Sydney cộng S3/CloudFront global; không có lỗi API trong phạm vi thu thập. Không phải kiểm kê toàn bộ mọi dịch vụ/region hay chứng nhận cleanup. Địa chỉ IPv4 được lược bỏ; chỉ công bố số lượng đã khử trùng và allocation ID.
- [Giá](prices.json): AWS Price List API, tra 15/11/2026. [Phép tính](calculate.py) chạy offline bằng Decimal; [dự toán](projection.json) giả định cấu hình không đổi đến hết 30/11: khoảng **10.02 USD/ngày**, tổng billing đã ghi nhận + kỳ chưa billing khoảng **192.74 USD**, trước credit/thuế và chưa gồm các khoản loại trừ.
- [Xác nhận](handover.json): người nhận/lịch giữ đã xác nhận; không ký thay GUI, quyền truy cập, chuyển credential/state hay toàn bộ yêu cầu nghiệm thu.
- [Sổ vòng đời](retention.csv): từng tài nguyên có Quân phụ trách, mốc giữ và ngày review sau demo. Gán trách nhiệm trong hồ sơ; không thay AWS tags và không lập lịch xóa tự động.
- [Checksum](checksums.json): toàn bộ file công bố của thư mục, trừ chính manifest checksum.

Lệnh tái tính: `python docs/evidence/cost-handover-2026-11-15/calculate.py`. Không gọi AWS hoặc ghi dữ liệu lên cloud. Dữ liệu gốc và receipt API nằm trong `.work/cost-handover-2026-11-15/` trên máy vận hành, ngoài Git. Hồ sơ này không chứa mật khẩu, cookie, secret value, Terraform state/plan hoặc raw backup.

Biên bản dùng khi báo cáo: [chi phí và bàn giao](../../28-cost-and-handover.md).
