# Medium Sydney — bằng chứng live và restore

Ngày kiểm tra **14/11/2026**, timestamps trong JSON là UTC. URL nguồn đang được giữ cho demo: **https://dc988tccg64gh.cloudfront.net**. [Cấu hình/vận hành](../../21-medium-sydney.md).

## Kết quả thực chạy

| Phạm vi | Kết quả | Bằng chứng |
|---|---|---|
| Nguồn HTTPS | **47/47 đạt**, gồm roles, private files/hash, bài nộp/điểm và logout/replay cookie | [source-http.json](source-http.json) |
| Viewer TLS | CA/hostname hợp lệ, TLS 1.3, HTTP redirect, Secure/HttpOnly, HSTS và readiness | [viewer-https.json](viewer-https.json) |
| Hai app nguồn | TLS RDS `verify-full`, file và MUC ghi A/đọc B; cùng session/file dùng được ở hai node | [app A](source-cluster-a.json), [app B](source-cluster-b.json) |
| Vận hành | Cron có task vừa chạy/audit clear; purge giữ namespace khác; cả hai app trả 503 ở login/readiness khi maintenance; backup nhất quán lên S3 | [operations.json](operations.json) |
| Session sau purge | Cookie trước purge/backup tiếp tục đọc profile và file | [session-after-purge](source-session-after-purge.json) |
| Khóa | Một `ACQUIRED`, hai `BUSY` (exit 3 dự kiến); S3 lock từ chối plan thứ hai bằng HTTP 412 | [distributed-lock.json](distributed-lock.json), [state-lock.json](state-lock.json) |
| Restore riêng | DB/EFS mới, cùng image/source, kiểm checksum, giữ maintenance để đối chiếu IDs/file/điểm; 820 cột không overflow khi đổi URL | [restore](restored-restore.json), [review](restored-review-resume.json) |
| HTTPS sau restore | **47/47 đạt** trên target mới | [restored-http.json](restored-http.json) |
| Hai app sau restore | Session mới/file/cache dùng được ở cả hai node, RDS TLS `verify-full` | [app A](restored-cluster-a.json), [app B](restored-cluster-b.json) |
| ASG replacement nguồn | Hai target healthy sau **139,67 giây**; cùng cookie/file dùng được trên app thay thế | [asg-replacement.json](asg-replacement.json), [replacement-session](source-replacement-session.json) |
| Cleanup | 71 resource restore và final snapshot tạm đã xóa; builder 10 resource đã xóa; source/data/backup giữ nguyên | [restore-cleanup.json](restore-cleanup.json) |
| Inventory cuối | Ba node private, hai target healthy, ASG không còn process suspended; RDS/EFS/Redis mã hóa và RDS deletion protection còn bật | [final-inventory.json](final-inventory.json) |
| CI | Source `93bdc8b`, success; 96 unit, small/medium runtime và Terraform checks | [ci.json](ci.json), [GitHub run](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/43605256815) |

Release source **`2130963f7fc3fd76007498ab766a0942b9db3f59`**, ECR image ghim digest; bundle SHA-256 và refs ở [release.json](release.json). Fixture là dữ liệu giả lập seed độc lập, không phải migration small → medium. Các username/IDs/file/hash công khai ở [fixture.json](fixture.json); password/cookie không được đưa vào hồ sơ.

Backup đã restore-test là **`moodle-medium-dev-med/20261114T115610`** trong bucket backup Sydney. [Manifest đã lọc](backup-manifest.json) giữ hash/refs, không xuất runtime secret. [Operator restore có review URL](reviewed-restore-operator.sh) bổ sung kiểm tra cột trước khi cho Moodle replace dùng `--shorten`; không sửa host bundle/image đang ghim và không thay chuỗi trong dump.

## Thời gian và các giới hạn

- [restore-timing.json](restore-timing.json) phân biệt nạp backup vào target đã dựng, bước review/resume và tuổi backup. Thời gian dựng toàn stack có gián đoạn do phiên AWS hết hạn; không dùng thời gian nạp ngắn để tuyên bố RTO end-to-end hoặc production. Fixture không có ghi nghiệp vụ mới sau backup nên không suy bảo đảm RPO bằng 0.
- Lượt HTTPS đầu trên target gặp một `TimeoutError` sau các ca đăng nhập; giữ nguyên [kết quả lỗi](restored-http-attempt-1.json). Sau đó hai node đều healthy, kiểm tra trực tiếp xuyên node đạt và lượt HTTPS lại đạt 47/47. Chưa kết luận nguyên nhân timeout hoặc sức tải/độ ổn định từ những lượt chức năng này.
- Phiên mới được tạo sau khi nguồn mở lại rồi dùng xuyên đợt ASG replacement; không tuyên bố cookie cũ sống qua cửa sổ pause dài vượt session TTL.
- Free Plan buộc dùng **3 × t3.small** và RDS backup retention **1 ngày**; nguồn vẫn là topology medium nhiều app. Chưa benchmark so sánh tải với small trong lượt này.
- **MED-02 còn pending:** CloudFront viewer có HTTPS, origin ALB dùng HTTP giới hạn prefix list; chưa có owned DNS/ACM listener tại ALB Sydney. Domain Dynu cũ chưa chuyển.
- **GUI mới chưa xác minh:** Windows Computer Use tự động dừng do không xác định được URL trình duyệt đủ chắc chắn để thực thi chính sách. HTTP/integration không thay walkthrough desktop/mobile.
- Dự toán cơ bản riêng medium khoảng **6,42 USD/ngày**, trước credit/thuế và chưa gồm lưu lượng/các dịch vụ biến đổi hoặc lab khác; [phép tính và đơn giá](cost-base.json). Không phải hóa đơn hoặc tổng chi phí toàn đồ án.

Raw backup, Terraform state/plan, credential, cookie và log riêng giữ ngoài Git. [verification.json](verification.json) và [checksums.json](checksums.json) ghi phạm vi và hash file của bộ hồ sơ này.
