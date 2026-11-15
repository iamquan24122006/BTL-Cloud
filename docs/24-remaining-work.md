# Trạng thái công việc — 15/11/2026

Đối chiếu commit `d3df8cf`, review kỹ thuật ban đầu, [bổ sung vận hành](evidence/medium-operations-2026-11-14/README.md) và kiểm tra AWS mới. Chưa nghiệm thu đầy đủ P0+P1; không tính tỷ lệ hoàn thành bằng cách cộng các ca có phạm vi khác nhau.

## Đã có bằng chứng

- Small dev/staging: chức năng LMS, quyền, cron, reboot staging và backup.
- Medium: 47/47 kiểm tra HTTPS, dữ liệu/session/cache xuyên node, khóa, ASG thay app và restore vào RDS/EFS mới.
- Dashboard 11 widget, 14 alarm vận hành; probe metric thật nhận ALARM và OK qua SNS/SQS.
- Policy target tracking đã tự tăng 2→3 và giảm về 2; target lab 200 request/app/phút, burst 20 user/8 phút có 4.890 lượt đọc và không lỗi. Ba target healthy lúc `19:34:51 UTC`, trở lại hai lúc `19:55:58 UTC`.
- Tên miền Dynu → ALB Sydney HTTPS/ACM đã hoàn tất, 47/47 ca nghiệp vụ và ba tài khoản demo đạt. Hai app cùng runner mới bootstrap đúng URL/release, ASG refresh Successful, hai target healthy, cron sạch và full plan không drift. [Bằng chứng](evidence/current-review-2026-11-15/README.md), [runbook tên miền](25-domain-cutover.md).

## Còn phải hoàn thành

| Ưu tiên | Công việc | Điều kiện đóng |
|---|---|---|
| 1 | QA-03 / AT-19: so sánh small/medium | Cùng dataset/workload/đường HTTPS, đủ lượt 10/25/50 user; lưu percentile, lỗi và metric. Ma trận trước bị dừng, chưa đủ kết luận |
| 1 | LMS-06 / AT-05: GUI | Walkthrough desktop/viewport hẹp, teacher upload, student xem/nộp/điểm, kiểm tra quyền; lưu ảnh và browser/version |
| 2 | AT-03/05/10/11/16/17: coverage còn thiếu | Dựng sạch/idempotence bản hiện tại, upload/limit sau restore, tranh cron/lỗi backup, restore bộ small mới, concurrent release/interrupted migration và ghi nghiệp vụ mới sau restore |
| 2 | QA-04: cài tay so với tự động | Timing cùng mốc bắt đầu/kết thúc, số thao tác/lỗi/thời gian sửa và giới hạn số lần đo |
| 2 | COST-01 / AT-20: chi phí và vòng đời | Billing toàn kỳ mọi account, owner/end date từng tài nguyên giữ lại và kiểm kê sau cleanup |
| 2 | DONE: bàn giao nhóm | Tên thành viên/reviewer, chạy lại demo độc lập, quyết định phạm vi và chữ ký |

## Kết quả điều tra scaling

AWS đọc lại lúc `2026-11-14T19:20:32Z` (15/11 giờ UTC+7): hai app healthy, desired=2, target tracking=600 request/app/phút. Trong burst `18:06–18:12 UTC`, `RequestCountPerTarget` cao nhất 311/phút, chưa vượt ngưỡng 600 trong ba chu kỳ một phút của alarm tăng máy. Vì vậy chưa quan sát scale-out không phải bằng chứng policy bị lỗi.

Burst có 20 user, 3.571 lượt đọc course, không lỗi, p95 khoảng 3.073 ms; kết quả này vượt ngưỡng nghiên cứu p95 3 giây được đề xuất trong repo, không dùng để chứng nhận sức tải. Burst tách khỏi workload benchmark chuẩn. Journal dừng benchmark ghi yêu cầu dừng lúc `18:13 UTC`; watcher tiếp tục chạy và ghi timeout sau đó, nên không coi cả 35 phút là tải liên tục.

Đã áp dụng ngưỡng lab 200 qua saved plan (0 create, 1 update, 0 delete/replace). Burst mới có 20 user, 4.890 lượt đọc, không lỗi, p95 khoảng 2.967 ms; policy tự tăng lên ba app healthy lúc `19:34:51 UTC` và trở lại hai lúc `19:55:58 UTC`. Sau đó, rollout tên miền và 47/47 kiểm tra nghiệp vụ xác nhận dữ liệu/quyền/file/bài nộp/điểm vẫn đúng. Không giữ một cookie đang đăng nhập xuyên cả scale-in và đổi hostname trong cùng drill; không suy SLA hay khả năng không gián đoạn từ ca này. Burst tách khỏi benchmark chuẩn. Không sửa alarm target tracking hoặc ép desired capacity để giả lập policy.

## Lỗi small và sửa smoke trong lượt tiếp tục

Smoke small phát hiện HTTP 500. Dịch vụ và database vẫn chạy, dung lượng đĩa còn đủ; lỗi PHP là `invalid_dataroot_permissions`. Thư mục `moodledata/cache/cachestore_file` và một số file cache cục bộ do root sở hữu. Đã sửa owner riêng các mục do root sở hữu trong hai cây cache về `www-data:www-data`, giữ nguyên dữ liệu nghiệp vụ; health check sau sửa đạt và hết cảnh báo quyền cache.

Ma trận small trước đó dừng ngay smoke vì không chọn ngẫu nhiên tới `Assignment view` (HTTP không lỗi). Đã bổ sung `-Jsmoke=true` để chạy tuần tự bốn loại thao tác; 10/25/50 user vẫn chọn ngẫu nhiên. Summary có `failure_reasons` và đánh dấu smoke để không trộn vào benchmark. Smoke small và medium đều đạt đủ bốn luồng, hai user và thời lượng. Kiểm thử sau bổ sung cutover: 103 unit (101 đạt, 2 skip quyền file Linux trên Windows), 3 Terraform mock đạt, Bash syntax đạt. Đây là kiểm thử local/live mới, không gán kết quả này cho CI commit lịch sử.

## Nếu không dùng tên miền riêng

Hai site vẫn dùng được HTTPS bằng hostname `*.cloudfront.net`; không cần mua domain để đăng nhập, học, nộp bài hoặc demo. Giữ distribution hiện có giúp giữ URL.

Phần phân tích này mô tả lựa chọn ban đầu nếu chỉ dùng CloudFront: TLS kết thúc ở viewer, origin HTTP chưa đạt MED-02. Chủ dự án sau đó chọn tên miền Dynu cũ và đã hoàn tất HTTPS tại ALB. URL CloudFront legacy vẫn được giữ để chuyển hướng, không còn là URL chuẩn của medium.

Tham chiếu AWS: [default CloudFront certificate](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesGeneral.html), [HTTPS đến custom origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-cloudfront-to-custom-origin.html).

## GUI trong lượt tiếp tục

Computer Use đã kiểm kê được ứng dụng Windows; browser provider trả `The browser access host is unavailable`. Chưa có walkthrough GUI mới được chứng nhận trong lượt này. HTTP acceptance và ảnh lịch sử giữ phạm vi riêng.
