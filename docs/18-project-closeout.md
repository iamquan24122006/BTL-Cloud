# Hồ sơ chốt dự án — 14/11/2026

Đây là điểm đọc trạng thái hiện tại, thay cho các bảng tiến độ lịch sử trong tài liệu kế hoạch. Phạm vi mục tiêu vẫn là small P0 và medium P1; chưa thu hẹp yêu cầu để biến các mục thiếu bằng chứng thành đạt.

## Kết luận cho nhóm

**Mã nguồn tích hợp đã qua CI đầy đủ; small Sydney đang chạy và đạt kiểm tra chức năng trên cả dev/staging.** Bộ bằng chứng tải Sydney đã được thu đủ 3 × 10/25/50 user và có metric đi kèm. Có thể dùng [báo cáo tổng hợp](19-final-report.md) để biên tập và trình bày kết quả đã làm.

**Medium Sydney đã được dựng lại và nghiệm thu trong lượt tiếp tục:** URL https://dc988tccg64gh.cloudfront.net, 47/47 ca HTTPS trên nguồn và target restore mới, file/session/MUC xuyên node, cron, lock, maintenance gate và ASG thay app. [Runbook và giới hạn](21-medium-sydney.md), [bằng chứng](evidence/medium-sydney-2026-11-14/README.md).

**Chưa đủ cơ sở ký “toàn bộ P0 + P1 đạt mọi tiêu chí”.** Còn MED-02 DNS/ACM trực tiếp tại ALB của lab mới, walkthrough GUI mới, kiểm tra chéo của thành viên, benchmark so sánh small/medium, một số ca lỗi và chi phí ở các account khác. Các mục đó cần được thực hiện hoặc được nhóm/giảng viên chấp nhận là giới hạn khi chốt.

## Phiên bản và kiểm chứng

| Nội dung | Kết quả |
|---|---|
| Source runtime / công cụ | Image medium ghim `2130963`; công cụ/IaC đã qua CI tại `93bdc8b` |
| CI mới | [Run 43605256815](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/43605256815), conclusion `success`, đúng head `93bdc8b` |
| Unit | CI 96/96; bộ local liên quan retention/CLI 36/36 đạt |
| Validate YAML | Sydney small và medium example đạt |
| AWS live | Profile `moodle-project`, Sydney; STS/account đúng, dev/staging SSM Online |
| Moodle live | Moodle 4.5.15, PHP 8.3; PostgreSQL small 16.15, medium Sydney 16.13 |
| Chức năng | Login/logout, role/enrolment, học liệu/hash, bài nộp/điểm, quyền riêng tư: dev/staging đạt |
| Vận hành | Cron có scheduled task vừa chạy, 0 task failure; backup tự động 14/11 và kiểm toàn vẹn đạt |
| Thay đổi trong lượt chốt | Small public và medium Sydney đã được triển khai bằng state riêng; medium restore vào target mới và target được cleanup sau kiểm chứng |

Toàn bộ chứng cứ mới: [final-audit-2026-11-14](evidence/final-audit-2026-11-14/README.md). Thông tin credential, raw backup và Terraform state được giữ ngoài Git.

**Lượt tiếp tục medium/GUI:** dùng release `2130963` đã test/publish, dựng medium tại Sydney. CI mới [43605256815](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/43605256815) thành công tại source `93bdc8b`, gồm **96 unit tests**, runtime small/medium và Terraform checks. GUI Windows bị hệ thống tự động dừng vì không xác định được URL trình duyệt đủ chắc chắn để thực thi chính sách; không dùng kết quả HTTP thay cho walkthrough.

**Small public đã triển khai:** dev hiện truy cập trực tiếp tại https://d1cnnw3mivc0q5.cloudfront.net, không cần tunnel. Addon giữ nguyên EC2/dữ liệu; HTTPS, nghiệp vụ và origin protection đã kiểm chứng. CI mới `93bdc8b` bao gồm thay đổi public, với 96 unit và các Terraform/runtime checks. [Runbook](20-small-public.md), [evidence](evidence/small-public-2026-11-14/README.md). GUI vẫn là tiêu chí riêng.

## Ma trận nghiệm thu theo đặc tả

“Đạt phần đã đo” không đồng nghĩa tất cả môi trường hoặc mọi điều kiện của mã yêu cầu đã đạt. H = hồ sơ lịch sử; L = kiểm tra live ngày 14/11; CI = kiểm thử tự động đúng source.

| Ca | Trạng thái | Căn cứ và phần cần bổ sung |
|---|---|---|
| AT-01 — input YAML | Đạt CI | Schema small/medium và test từ chối input sai, secret, khóa lạ/khóa trùng |
| AT-02 — plan guard | Đạt CI | Account/config/source/plan hash, exact confirm, manifest một lần, snapshot plan |
| AT-03 — dựng sạch/bootstrap | Đạt small H; health L | Hồ sơ cài từng pha và tự động; bootstrap không reset đã có. Chưa dựng sạch lại commit tích hợp trong lượt này |
| AT-04 — login/role/course | Đạt small/medium L | Small dev/staging đạt; medium Sydney nguồn và restore 47/47 HTTPS |
| AT-05 — file/upload/limit | Đạt từng phần H/L | Hash/file access small L; binary 60 MiB và từ chối 65 MiB N3 H; GUI HTTPS medium H. Chưa chứng nhận đủ cả hai preset sau restore |
| AT-06 — bài nộp/điểm/privacy | Đạt small/medium L | Verifier small và bộ HTTPS medium nguồn/restore; giữ IDs và hash/điểm khi phục hồi |
| AT-07 — cron/task | Đạt small/medium L | Medium có task gần thời điểm kiểm tra, audit không có failure; timer app disabled, runner enabled |
| AT-08 — reboot | Đạt small H | Hồ sơ Sydney/N3 giữ dữ liệu và tự khởi động; không reboot lại trong lượt chốt |
| AT-09 — file/config/network | Đạt phạm vi đã kiểm | Protected paths/permission small L, inventory/IMDSv2/EBS; staging có SG relay private của fixture tải, không phải baseline không-ingress tuyệt đối |
| AT-10 — backup/recovery | Đạt small H/L; medium H | Backup mới có checksum và manifest; ca AccessDenied/recovery có hồ sơ. Bộ 14/11 chưa restore-test |
| AT-11 — restore small | Đạt H | Bộ hỏng bị từ chối; bộ đúng phục hồi fixture, ghi mới và reboot. Không lấy checksum để thay restore |
| AT-12 — medium deployment/TLS/state | Đạt live theo phạm vi lab; MED-02 pending | Sydney private compute/data, TLS viewer/RDS/Redis và S3 lock; ALB origin dùng HTTP qua CloudFront, chưa có domain/ACM mới |
| AT-13 — đa node/session/file | Đạt H/L | Kiểm tra trực tiếp cả hai app nguồn và hai app sau restore; file/hash và session dùng chung |
| AT-14 — purge cache isolation | Đạt ca đã đo H/L | Canary namespace khác sống sau purge trên Sydney; cookie nguồn còn dùng được sau purge/backup |
| AT-15 — thay node/scaling | Đạt thay node H/L, thiếu so sánh scaling tải | Sydney trở lại hai target healthy sau 139,67 giây; cookie/file dùng được ở node mới; chưa nghiệm thu scale policy dưới tải |
| AT-16 — lock/release tranh chấp | Đạt từng phần H/L | Sydney một ACQUIRED, hai BUSY và S3 lock 412; một số ca gián đoạn migration/release còn thiếu |
| AT-17 — restore medium | Đạt H/L trong phạm vi đã đo | Backup `20261114T115610` phục hồi vào RDS/EFS mới; giữ IDs, file, bài nộp/điểm; 47/47 HTTPS và kiểm tra xuyên node; không suy cam kết RPO/RTO production |
| AT-18 — alarm/recovery | Đạt từng phần | Budget SNS→SQS có thử kênh; không phải thông báo vận hành đến người nhận. Chưa đủ toàn bộ alarm/failure scenarios |
| AT-19 — đo tải/so sánh | Đạt ma trận small; chưa đủ so sánh | Sydney đủ 9 lượt; N3 có 2 lượt 50-user chậm. Chưa benchmark medium và so sánh cài tay/tự động cùng phương pháp |
| AT-20 — bàn giao/cleanup/chi phí | Chờ nhóm chốt | Có báo cáo, inventory và chi phí Sydney; còn reviewer, quyết định vòng đời lab, chi phí N2/N3 |
| LMS-06 — GUI | Medium H; small chờ | Medium có ảnh desktop/mobile viewport. Small chưa có walkthrough GUI mới; HTTP không thay kiểm tra bố cục |

Yêu cầu gốc: [đặc tả nghiệm thu](12-dac-ta-tinh-nang-va-nghiem-thu.md). Các tiêu chí có phần chưa chạy được giữ nguyên trạng thái; không tính tỷ lệ hoàn thành bằng cách cộng các phép kiểm không tương đương.

## Những việc nhóm cần làm trước khi ký

1. **Reviewer độc lập** chạy [demo small](15-small-demo.md): teacher/student, tải học liệu, bài nộp/điểm và lỗi truy cập. Lưu ảnh desktop và viewport hẹp, ghi browser/version/ngày; không đưa mật khẩu vào ảnh.
2. **Chốt phạm vi trình bày medium**: dùng lab Sydney hiện tại và bộ bằng chứng mới; phân biệt CloudFront viewer HTTPS với yêu cầu HTTPS trực tiếp tại ALB. Hồ sơ Singapore vẫn là lịch sử; không dùng IDs/ARN của nó cho lab Sydney.
3. **Bổ sung chi phí N2/N3** và xác nhận lịch giữ/dừng/hủy tài nguyên. Hai profile còn lại đã được kiểm tra: `default` hết hạn, `mquann` trả token không hợp lệ; chưa có phiên hợp lệ để lấy billing account khác. Số 27,31 USD Sydney chưa đại diện tổng 150 USD của nhóm. Không xóa lab đang demo hoặc backup/state để đóng checklist.
4. Điền tên nhóm, mã sinh viên/lớp, người kiểm tra và quyết định nghiệm thu vào phần dưới. Đây là thông tin và phê duyệt của nhóm, không do agent tự tạo.

## Biên bản nhóm

| Mục | Nhóm điền sau review |
|---|---|
| Thành viên A/B/C/D, mã sinh viên, lớp | Chưa cung cấp |
| Reviewer và ngày chạy lại demo | Chưa xác nhận |
| Bằng chứng walkthrough small | Chưa bổ sung |
| Phạm vi được chấp nhận: small / small + medium lịch sử / full P0+P1 | Chưa quyết định |
| Giới hạn được chấp nhận và lý do | Chưa quyết định |
| Chi phí các account còn lại | Chưa cung cấp |
| Lịch dừng/hủy lab sau demo và người chịu trách nhiệm | Chưa chốt |
| Kết luận và chữ ký | Chờ nhóm |
