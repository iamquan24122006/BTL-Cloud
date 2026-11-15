# Bằng chứng lượt tiếp tục 15/11/2026

Thời gian JSON là UTC ngày 14/11, tương ứng ngày 15/11 UTC+7. Chưa nghiệm thu đầy đủ dự án.

**Tên miền đã hoàn tất:** https://www.moodle-cloud-distribution.mywire.org. [47/47 ca nghiệp vụ](domain-http.json), [11 kiểm tra HTTPS/redirect](domain-https.json), [ba tài khoản demo](domain-demo-logins.json) đều đạt. [Hai app/runner bootstrap đúng URL/release](domain-nodes.json), [refresh Successful và hai target healthy](domain-inventory.json), [cron/timer/TLS database](domain-runtime-audit.json) đạt, [plan cuối không drift](domain-final-plan.json). [Thay đổi đã review và backup trước cutover](domain-reviewed-changes.json).

- [Small smoke](small-smoke.json), [medium smoke](medium-smoke.json): hai user, đủ bốn loại thao tác và thời lượng; chạy tuần tự để không ngẫu nhiên bỏ sót branch. Không dùng tỷ lệ smoke làm tỷ lệ workload benchmark.
- [Sửa cache small](small-cache-repair.json): sửa các mục cache do root sở hữu về www-data; health sau sửa đạt. Chưa xác định tiến trình nào đã tạo sai owner.
- [Điều tra scaling cũ](previous-scaling-diagnosis.json): metric cao nhất 311 request/app/phút, dưới target cũ 600.
- [Drill mới](scaling-drill.json): target 200, burst 20 user trong tám phút; quan sát ba healthy rồi trở lại hai, không ép desired capacity. Burst không lỗi; 47/47 nghiệp vụ sau rollout tên miền giữ nguyên dữ liệu/quyền/file/bài nộp/điểm. Không suy SLA hoặc cookie liên tục qua việc đổi hostname.
- [Plan giai đoạn HTTPS](domain-stage-plan.json): bước đầu chỉ thêm listener/ingress 443. Sau đó full plan giữ CloudFront, thay runner/roll app để đổi URL; plan cuối không drift. Không dùng preset CloudFront thuần để vận hành site đã chuyển ACM.
- [Verification](verification.json): 103 unit (101 pass, 2 skip Windows/Linux permission), 3 Terraform mock và Bash syntax đạt. Probe TLS ban đầu HTTP 303 được giữ dưới `initial_tls_probe`; kết quả hoàn tất nằm trong các file domain ở trên. Đây là kiểm thử local/live, không gán cho CI commit lịch sử.

Lượt probe redirect đầu tiên so sánh chuỗi URL quá chặt, coi cổng HTTPS mặc định `:443` là khác URL mong đợi. Đã đối chiếu Location thật và kiểm lại scheme/hostname/port/path/query; HTTPS `:443` hợp lệ, cả hai redirect giữ nguyên path/query và không lặp. Lượt chưa đạt vẫn nằm trong journal riêng. Không đổi tiêu chí hostname hoặc bỏ xác minh TLS để đạt kiểm tra.

Không chứa password/cookie, raw JTL, Terraform state/plan, SSM receipt hoặc backup. Các lỗi và lượt chưa đạt giữ trong journal riêng; [checksum](checksums.json) chỉ bao phủ các JSON công bố trong thư mục này.
