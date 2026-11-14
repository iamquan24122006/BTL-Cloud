# Biên bản nghiệm thu kỹ thuật — 14/11/2026

Cập nhật tiếp theo: đường thông báo ALARM/OK, dashboard và việc đổi mật khẩu admin/dùng chung tài khoản đã có [bằng chứng bổ sung](evidence/medium-operations-2026-11-14/README.md). Policy scaling đã triển khai; bài kiểm thử scale-out/in dưới tải và HTTPS tên miền vẫn cần kết quả riêng. Biên bản bên dưới phản ánh đúng lượt review ban đầu, không tự đổi thành nghiệm thu đầy đủ.

## Kết luận

**Chưa đủ điều kiện nghiệm thu đầy đủ P0 + P1 theo đặc tả hiện hành.** Phần chức năng LMS, vận hành cơ bản và các đường phục hồi đã kiểm tra có bằng chứng đạt; bản small/medium hiện dùng được cho demo. Kết luận này giữ nguyên các yêu cầu đích, không coi URL CloudFront là thay thế cho HTTPS tại ALB hoặc ASG thay node là bằng chứng autoscaling theo tải.

Nghiệm thu được thực hiện theo yêu cầu chủ dự án bằng kiểm tra tự động, đối chiếu source/IaC, API AWS và bằng chứng thực chạy. Đây không phải chữ ký của giảng viên hoặc xác nhận reviewer độc lập của nhóm.

| Thông tin | Giá trị |
|---|---|
| Commit được kiểm tra | `27aae962054219de7b8f3478647995cf012a31cd` |
| Đặc tả | [Đặc tả tính năng/nghiệm thu](12-dac-ta-tinh-nang-va-nghiem-thu.md); SHA-256 ghi trong [summary](evidence/acceptance-review-2026-11-14/summary.json) |
| Môi trường live | Sydney `ap-southeast-2`, account `828676179987`; small dev/staging và medium dev |
| Runtime medium | Release/image ghim từ `2130963`; hai app private và runner riêng |
| Small public | https://d1cnnw3mivc0q5.cloudfront.net |
| Medium public | https://dc988tccg64gh.cloudfront.net |
| Thời điểm | Các lượt mới từ khoảng 15:29 UTC ngày 14/11; timestamp chi tiết trong từng evidence |
| Phạm vi thao tác | Kiểm tra source, CI, HTTP, cron, DB privilege, S3, billing/inventory; reboot riêng small staging; không đổi DNS, mật khẩu, scaling hay alarm configuration |

## Kết quả kiểm tra mới

- **96/96 unit tests đạt**, CI đúng commit kiểm tra [43609941053](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/43609941053) thành công với runtime/integration/Terraform checks. [unit](evidence/acceptance-review-2026-11-14/unit.json), [CI](evidence/acceptance-review-2026-11-14/ci.json).
- **Small dev và staging đạt kiểm tra chức năng**: admin/teacher/student login, course/enrolment, hash học liệu, bài nộp/điểm/riêng tư, logout và đường dẫn nhạy cảm. [dev](evidence/acceptance-review-2026-11-14/small-dev.json), [staging](evidence/acceptance-review-2026-11-14/small-staging-after-reboot.json).
- **Reboot small staging đạt**: đã đối chiếu backup hiện có trước thao tác; boot ID thay đổi và sau reboot giữ nguyên IDs/hash cùng kết quả bài nộp/điểm. Không reboot small dev hoặc medium trong lượt này. [Reboot](evidence/acceptance-review-2026-11-14/staging-reboot.json).
- **Medium đạt 47/47 kiểm tra HTTPS** trong lượt lại; giữ nguyên file/bài nộp/điểm và kiểm tra quyền. Lượt đầu gặp lỗi DNS `getaddrinfo`; đã giữ nguyên báo cáo lỗi, sau đó DNS/curl hoạt động và bộ kiểm tra lại đạt. Không xóa lỗi khỏi hồ sơ. [Kết quả](evidence/acceptance-review-2026-11-14/medium-http.json), [lượt lỗi](evidence/acceptance-review-2026-11-14/medium-http-attempt-1.json).
- **TLS/cookie/redirect và HTTP sensitive-path probes đạt trên hai site**; nginx small từ chối header thiếu/sai bằng 403. Các probe chỉ ghi status/kích thước và dấu hiệu lộ nội dung, không ghi response body/cookie. [HTTP](evidence/acceptance-review-2026-11-14/http-surface.json), [origin](evidence/acceptance-review-2026-11-14/small-origin-protection.json).
- **Cron kiểm tra đạt ở cả ba site**: timer active, scheduled/ad hoc failure và backlog quá hạn đều bằng 0 tại snapshot. App medium tắt cron/backup timer; runner bật. DB runtime `moodle_runtime` dùng TLS `verify-full`, không superuser/createdb/createrole/quyền CREATE object trong schema public. [Cron](evidence/acceptance-review-2026-11-14/cron-review.json), [runtime](evidence/acceptance-review-2026-11-14/medium-runtime.json).
- **S3 kiểm tra đạt trong phạm vi probe**: bốn bucket được kiểm có public-access block, versioning và mã hóa; đọc ẩn danh đúng object state/backup bị 403. [Storage](evidence/acceptance-review-2026-11-14/storage-security.json).

Các ca đa node, backup/restore vào RDS/EFS mới, khóa, purge và ASG replacement **đã chạy trong cùng ngày ở lượt triển khai trước**, được tái đối chiếu, không tuyên bố đã lặp các thao tác phá/thay môi trường đó trong lượt review này. [Bộ bằng chứng medium](evidence/medium-sydney-2026-11-14/README.md).

## Các mục chặn chốt đầy đủ

| Mã | Quan sát / mức thiếu | Điều kiện đóng |
|---|---|---|
| F-01 — MED-02 / AT-12 | ALB chỉ có **80/HTTP**, chưa có listener 443/ACM. HTTPS viewer CloudFront hoạt động | Có quyền DNS, ACM đúng region được cấp, listener HTTPS và kiểm thử domain/proxy đạt |
| F-02 — MED-07 / AT-15 | **0 scaling policy** trên ASG; ca thay app đã đạt nhưng chưa có scale theo tải | Policy có metric/ngưỡng/warmup/cooldown; đo tăng 2→3 và giảm về 2, lưu lỗi và dữ liệu sau chuyển |
| F-03 — OBS-02 / AT-18 | **7 alarm, 0 AlarmActions, 0 dashboard** ở API trả về; chưa chứng minh thông báo đến nơi nhận và recovery | Dashboard đủ các thành phần, receiver có cấu hình, thử ALARM đến receiver và trở lại OK; bổ sung tín hiệu còn thiếu theo đặc tả |
| F-04 — LMS-06 / AT-05 | GUI mới **chưa xác minh**; Computer Use không kết nối được native pipe | Walkthrough desktop/mobile, teacher upload và student xem/nộp/điểm/quyền; ghi browser/version/ảnh không có credential |
| F-05 — QA-03/04 / AT-19 | Có ma trận small lịch sử; chưa có ma trận medium so sánh cùng điều kiện và đủ bằng chứng timing cài tay/tự động | Chạy đúng dataset/workload/cửa sổ và số lần lặp; lưu raw/private, p50/p95/p99/lỗi/metric và giới hạn |
| F-06 — COST-01 / DONE-02 | Billing chỉ Sydney; hai account khác chưa xác thực được; generator/manual-drill còn chạy và chưa có end date được xác nhận | Đối chiếu tổng kỳ ở mọi account, owner/end date từng tài nguyên giữ lại và sổ ngân sách |
| F-07 — SEC-01 | Hạn quyền runtime/storage đã có bằng chứng; **chưa có bằng chứng rotation admin khởi tạo** trong lượt review | Lưu record đổi mật khẩu và kiểm tra mật khẩu mới/cũ an toàn; không xuất password vào báo cáo |

[Quan sát AWS thực tế](evidence/acceptance-review-2026-11-14/operational-gaps.json), [findings có điều kiện đóng](evidence/acceptance-review-2026-11-14/findings.json). “Chưa xác minh” mô tả thiếu bằng chứng, không tự suy thành lỗi sản phẩm hoặc kết quả đạt.

## Ma trận AT-01–AT-20

`Đạt` áp dụng trong phạm vi chứng cứ ghi ở từng dòng. `Một phần` chưa đáp ứng toàn bộ ca; `H` là bằng chứng lịch sử/CI được dẫn rõ, không phải một lượt AWS mới. Không dùng số dòng đạt để tính phần trăm hoàn thành sản phẩm.

| Ca | Kết luận | Phạm vi/giới hạn |
|---|---|---|
| AT-01 | Đạt | Input/schema/offline guard; unit/CI |
| AT-02 | Đạt | Guard account/config/source/saved-plan/single-use; unit/CI |
| AT-03 | Một phần | Có bằng chứng cài nhỏ/CI; không dựng lại EC2 small sạch và chạy idempotence trong review này |
| AT-04 | Đạt | Login/role/course trên small dev/staging và medium |
| AT-05 | Một phần | File/hash/deny đạt; chưa đủ GUI upload/limit ở mọi môi trường hiện tại/sau restore |
| AT-06 | Đạt | Bài nộp/điểm/privacy và chứng cứ bảo toàn fixture sau restore |
| AT-07 | Đạt | Cron/timer/task failure/backlog, phân vai app/runner |
| AT-08 | Đạt | Reboot staging mới, boot ID đổi, nghiệp vụ/hash/IDs giữ nguyên |
| AT-09 | Đạt phạm vi probe | HTTP nhạy cảm, origin, file permission từ health, DB runtime và anonymous S3 deny; không phải pentest toàn bộ |
| AT-10 | Một phần | Backup nhất quán có chứng cứ; chưa lặp đủ tình huống backup tranh cron/lỗi S3 trong review này |
| AT-11 | Có bằng chứng H/CI | Small restore/corrupt-set có hồ sơ trước; chưa restore lại chính bộ AWS small mới nhất |
| AT-12 | **Chưa đạt toàn ca** | Thiếu ALB HTTPS theo F-01 |
| AT-13 | Đạt theo chứng cứ cùng ngày | Session/file/cache qua cả hai app nguồn và restore |
| AT-14 | Đạt theo chứng cứ cùng ngày | Purge giữ cookie/namespace khác |
| AT-15 | Một phần | ASG thay app đạt; policy scale-out/in chưa có (F-02) |
| AT-16 | Một phần | Lock liên node/S3 đạt; chưa đủ concurrent-release/interrupted-migration coverage |
| AT-17 | Một phần | Fresh restore/IDs/hash/47 HTTPS/hai node đạt; chưa độc lập ghi nhận đủ flow ghi nghiệp vụ mới sau restore trong review này |
| AT-18 | **Chưa đạt** | Thiếu dashboard/receiver/alarm delivery-recovery (F-03) |
| AT-19 | Một phần | Có small matrix H; thiếu medium comparison và timing đủ phạm vi |
| AT-20 | Một phần | Có tài liệu/cleanup/billing/inventory; tổng account, reviewer/chữ ký/end date chưa đủ |

Chi tiết liên kết từng ca: [matrix.json](evidence/acceptance-review-2026-11-14/matrix.json), [CSV](evidence/acceptance-review-2026-11-14/matrix.csv). [Summary](evidence/acceptance-review-2026-11-14/summary.json) có trạng thái máy đọc được và checksum đặc tả.

## Chi phí và tài nguyên giữ lại

Cost Explorer tra **14/11/2026**, cửa sổ **01/10–14/11 exclusive**, trả usage Sydney trước credit/refund làm tròn **29,06 USD**; các kỳ còn Estimated. Dòng credit không phải số credit còn dùng được. **Chưa gồm charges ngày 14/11 và account N2/N3**, nên không kết luận tổng đồ án đã nằm trong ngân sách 150 USD. [Billing](evidence/acceptance-review-2026-11-14/billing.json), [budget](evidence/acceptance-review-2026-11-14/budgets.json), [giới hạn truy cập account](evidence/acceptance-review-2026-11-14/other-account-access.json).

Inventory mới có small dev/staging, medium hai app/runner và hai EC2 tên `moodle-sydney-load-generator`, `moodle-sydney-manual-drill` còn chạy. Lượt review không dừng/hủy hai máy này khi chưa có quyết định vòng đời của nhóm. [Danh sách](evidence/acceptance-review-2026-11-14/running-compute.json). Restore lab/builder của lượt medium đã được dọn theo [hồ sơ cleanup](evidence/medium-sydney-2026-11-14/restore-cleanup.json).

## Quyết định bàn giao

1. Có thể dùng small/medium hiện tại để trình diễn các chức năng đã kiểm chứng và đưa kết quả thực vào báo cáo, giữ các giới hạn nêu trên.
2. **Chưa đánh dấu hoàn thành nghiệm thu đầy đủ P0+P1** hoặc SLA/công suất production. Đóng F-01/02/03 và bổ sung coverage còn thiếu, rồi chạy lại đúng các ca chịu ảnh hưởng.
3. Người phụ trách nhóm ghi quyết định chấp nhận phạm vi, tên/chữ ký và lịch giữ/dừng tài nguyên. Biên bản tự động này không tự tạo các thông tin chưa được cung cấp đó.

Không có password, cookie, state, plan hoặc raw backup trong [bộ bằng chứng review](evidence/acceptance-review-2026-11-14/README.md).
