# Trạng thái công việc — 15/11/2026

**Dự án đã được người dùng yêu cầu chốt tại trạng thái hiện có để làm báo cáo.** Danh sách bên dưới giữ lại các giới hạn/chưa kiểm chứng, không phải chỉ thị tiếp tục chạy tác vụ AWS. Quân tự kiểm tra GUI và tự xóa tài nguyên khi cần; không triển khai tự xóa theo budget. [Quyết định chốt](29-project-freeze.md).

Đối chiếu commit `ae885c1`, review kỹ thuật ban đầu, [bổ sung vận hành](evidence/medium-operations-2026-11-14/README.md), lượt cutover tên miền và lượt deploy bản sửa host buổi tối 15/11. Chưa nghiệm thu đầy đủ P0+P1; không tính tỷ lệ hoàn thành bằng cách cộng các ca có phạm vi khác nhau.

**Chốt phạm vi bàn giao 15/11:** Quân đã xác nhận tiếp nhận, giữ demo đến hết 30/11/2026 UTC+7 và chọn chỉ billing account Sydney hiện có. Billing trước credit **35,31 USD**, ròng làm tròn **0,00 USD**; có sổ vòng đời và dự toán giữ cấu hình **192,74 USD** trước credit/thuế và khoản chưa tính. [Biên bản](28-cost-and-handover.md). GUI do Quân tự kiểm tra/bổ sung ảnh; chưa coi là đã đạt.

## Đã có bằng chứng

- Small dev/staging: chức năng LMS, quyền, cron, reboot staging và backup.
- Medium: 47/47 kiểm tra HTTPS, dữ liệu/session/cache xuyên node, khóa, ASG thay app và restore vào RDS/EFS mới.
- Dashboard 11 widget, 14 alarm vận hành; probe metric thật nhận ALARM và OK qua SNS/SQS.
- Policy target tracking đã tự tăng 2→3 và giảm về 2; target lab 200 request/app/phút, burst 20 user/8 phút có 4.890 lượt đọc và không lỗi. Ba target healthy lúc `19:34:51 UTC`, trở lại hai lúc `19:55:58 UTC`.
- Tên miền Dynu → ALB Sydney HTTPS/ACM đã hoàn tất, 47/47 ca nghiệp vụ và ba tài khoản demo đạt. Hai app cùng runner mới bootstrap đúng URL/release, ASG refresh Successful, hai target healthy, cron sạch và full plan không drift. [Bằng chứng](evidence/current-review-2026-11-15/README.md), [runbook tên miền](25-domain-cutover.md).
- Bản sửa backup/cron đã lên live (không chỉ nằm trong repo): bundle host `ae885c1d238f` với SHA riêng, image/release giữ nguyên; `moodle_runtime` nay có `TRUNCATE` trên **494/494 bảng**, `tag_cron_task` chạy lại thành công (`faildelay=0`), cron kết thúc `cron-completed-and-task-audit-clear`, plan cuối không drift và 47/47 ca HTTPS vẫn đạt. Small dev/staging được cập nhật `verify_backup.py` và backup dev chạy đủ. [Bằng chứng](evidence/hostfix-2026-11-15/README.md), [runbook](27-host-bundle-deploy.md).

## Còn phải hoàn thành

| Ưu tiên | Công việc | Điều kiện đóng |
|---|---|---|
| 1 | QA-03 / AT-19: so sánh small/medium | Cùng dataset/workload/đường HTTPS, đủ lượt 10/25/50 user; lưu percentile, lỗi và metric. Ma trận trước bị dừng, chưa đủ kết luận |
| 1 | LMS-06 / AT-05: GUI | Walkthrough desktop/viewport hẹp, teacher upload, student xem/nộp/điểm, kiểm tra quyền; lưu ảnh và browser/version |
| 2 | AT-03/05/10/11/16/17: coverage còn thiếu | Dựng sạch/idempotence bản hiện tại, upload/limit sau restore, restore bộ small mới, concurrent release/interrupted migration và ghi nghiệp vụ mới sau restore. AT-10 đã có thêm bằng chứng live (backup small chờ cron drain; release medium tự backup baseline trước upgrade), còn thiếu ca lỗi upload/S3 |
| 2 | QA-04: cài tay so với tự động | Timing cùng mốc bắt đầu/kết thúc, số thao tác/lỗi/thời gian sửa và giới hạn số lần đo |
| Sau demo | COST-01 / AT-20: vòng đời và số cuối kỳ | Billing Sydney, người nhận Quân và mốc giữ 30/11 đã chốt theo phạm vi người dùng chọn; từ 01/12 review cleanup và đối chiếu hóa đơn. N2/N3 ngoài phạm vi, không ghi là 0 |
| Phần kiểm chứng còn lại | DONE: demo độc lập/quyền và dữ liệu riêng | Tiếp nhận và lịch giữ đã xác nhận; Quân bổ sung GUI, xác minh quyền/state/credential qua kênh riêng. Chưa ký đạt mọi yêu cầu P0+P1 |

## Deploy bản sửa host và quyền cron (tối 15/11)

Bản sửa trong repo chưa từng lên live trước lượt này: runtime đang chạy thiếu nhánh cấp `TRUNCATE` và `tag_cron_task` có `faildelay=7680`, `lastruntime=0`; cron dừng ở `cron-audit.php`, để lại `worker-pending.json` và chặn operation kế tiếp.

Đã phát hành bundle host `ae885c1d238f` (SHA-256 `f135174d…`) dưới key mới, giữ nguyên image digest và release tag vì bootstrap so label image với `artifact.release`. Runner được thay (`i-0d43470f88eb13a58`), ASG refresh `Successful` lúc `07:07:40Z`; sau recovery review (container worker không còn, 0 session DB) marker được gỡ và release chạy `07:08:46–07:09:13Z` với cửa sổ chặn ghi khoảng 27 giây.

Kết quả: tag task chạy thành công, `faildelay=0`, `scheduled_with_faildelay=0`, `adhoc_queued=0`, **494/494 bảng có `TRUNCATE`**, cron `cron-completed-and-task-audit-clear`, 47/47 ca HTTPS đạt lại và plan cuối `No changes`. Small dev/staging nhận `verify_backup.py` mới qua SSM; backup dev chạy đủ, upload S3, manifest ghi `cron drained`. Không thay EC2 small vì root volume giữ database và `moodledata`. [Bằng chứng](evidence/hostfix-2026-11-15/README.md), [runbook](27-host-bundle-deploy.md).

## Sự cố vận hành ngay sau deploy (07:18–07:33Z 15/11)

`unattended-upgrades` trên runner nâng `libc6`/`perl`/kernel từ `07:20:22Z`; containerd restart lúc `07:20:41Z` và kill container `cron.php` đang chạy dưới cluster lock. Wrapper giữ `worker-pending.json` (đúng thiết kế an toàn) nên mọi lượt cron sau đó fail-fast; Moodle cron dừng khoảng 15 phút. Đã review (không còn container worker, 0 session DB, không còn process `cron.php`), gỡ marker và chạy lại cron `07:33:35Z`; chu kỳ timer kế `07:36:38Z` sạch. [Bằng chứng sự cố](evidence/hostfix-2026-11-15/cron-incident.json).

Hai việc còn mở từ sự cố:

- Cấu hình cửa sổ hoặc loại trừ `unattended-upgrades` trên runner để bản nâng cấp không tự restart containerd trong giờ vận hành; nếu giữ nguyên thì phải dùng runbook xử lý ở [27](27-host-bundle-deploy.md).
- Alarm `CronSuccess-missing` (period 600 giây, treat missing = breaching) **không ghi ALARM** trong khoảng trống 15 phút, dù metric `CronSuccess` thiếu hẳn. Cần rà cấu hình và làm một ca thử có kiểm soát trước khi coi alarm này là lưới an toàn.

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
