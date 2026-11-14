# Hồ sơ chốt dự án — 14/11/2026

Đây là điểm đọc trạng thái hiện tại, thay cho các bảng tiến độ lịch sử trong tài liệu kế hoạch. Phạm vi mục tiêu vẫn là small P0 và medium P1; chưa thu hẹp yêu cầu để biến các mục thiếu bằng chứng thành đạt.

## Kết luận cho nhóm

**Mã nguồn tích hợp đã qua CI đầy đủ; small Sydney đang chạy và đạt kiểm tra chức năng trên cả dev/staging.** Bộ bằng chứng tải Sydney đã được thu đủ 3 × 10/25/50 user và có metric đi kèm. Có thể dùng [báo cáo tổng hợp](19-final-report.md) để biên tập và trình bày kết quả đã làm.

**Chưa đủ cơ sở ký “toàn bộ P0 + P1 đạt mọi tiêu chí”.** Còn walkthrough GUI small, kiểm tra chéo của thành viên, benchmark so sánh small/medium, một số ca lỗi medium và chi phí ở các account khác. Medium có bằng chứng AWS/GUI/restore lịch sử; không có môi trường medium live được xác minh trong lượt này. Các mục đó cần được thực hiện hoặc được nhóm/giảng viên chấp nhận là giới hạn khi chốt.

## Phiên bản và kiểm chứng

| Nội dung | Kết quả |
|---|---|
| Source ứng dụng/công cụ | `2130963f7fc3fd76007498ab766a0942b9db3f59` |
| CI | [Run 43480887498](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/43480887498), conclusion `success`, đúng head SHA |
| Unit local | 89/89 đạt trong lượt rà soát 14/11 |
| Validate YAML | Sydney small và medium example đạt |
| AWS live | Profile `moodle-project`, Sydney; STS/account đúng, dev/staging SSM Online |
| Moodle live | Moodle 4.5.15, PHP 8.3.35, PostgreSQL 16.15 trên cả hai site |
| Chức năng | Login/logout, role/enrolment, học liệu/hash, bài nộp/điểm, quyền riêng tư: dev/staging đạt |
| Vận hành | Cron có scheduled task vừa chạy, 0 task failure; backup tự động 14/11 và kiểm toàn vẹn đạt |
| Thay đổi trong lượt chốt | Kiểm tra, thu hồi evidence và hoàn thiện tài liệu; không apply lại hạ tầng, không reset/restore dữ liệu |

Toàn bộ chứng cứ mới: [final-audit-2026-11-14](evidence/final-audit-2026-11-14/README.md). Thông tin credential, raw backup và Terraform state được giữ ngoài Git.

**Lượt tiếp tục medium/GUI:** image medium từ checkout sạch đã build và vượt qua integration hai app cục bộ trên máy này; [evidence release](evidence/medium-release-2026-11-14/README.md). Chưa apply medium mới. GUI chưa kiểm tra được vì browser access host không hoạt động; nhóm còn cần chọn account và hostname/quyền DNS cho HTTPS.

**Small public đã triển khai:** dev hiện truy cập trực tiếp tại https://d1cnnw3mivc0q5.cloudfront.net, không cần tunnel. Addon giữ nguyên EC2/dữ liệu; HTTPS, nghiệp vụ và origin protection đã kiểm chứng; 95 unit và 2 mock tests đạt. [Runbook](20-small-public.md), [evidence](evidence/small-public-2026-11-14/README.md). GUI vẫn là tiêu chí riêng; thay đổi public local chưa có lượt CI remote mới.

## Ma trận nghiệm thu theo đặc tả

“Đạt phần đã đo” không đồng nghĩa tất cả môi trường hoặc mọi điều kiện của mã yêu cầu đã đạt. H = hồ sơ lịch sử; L = kiểm tra live ngày 14/11; CI = kiểm thử tự động đúng source.

| Ca | Trạng thái | Căn cứ và phần cần bổ sung |
|---|---|---|
| AT-01 — input YAML | Đạt CI | Schema small/medium và test từ chối input sai, secret, khóa lạ/khóa trùng |
| AT-02 — plan guard | Đạt CI | Account/config/source/plan hash, exact confirm, manifest một lần, snapshot plan |
| AT-03 — dựng sạch/bootstrap | Đạt small H; health L | Hồ sơ cài từng pha và tự động; bootstrap không reset đã có. Chưa dựng sạch lại commit tích hợp trong lượt này |
| AT-04 — login/role/course | Đạt small L; medium H | Small dev/staging đạt; medium 47 kiểm tra HTTP trong hồ sơ N2 |
| AT-05 — file/upload/limit | Đạt từng phần H/L | Hash/file access small L; binary 60 MiB và từ chối 65 MiB N3 H; GUI HTTPS medium H. Chưa chứng nhận đủ cả hai preset sau restore |
| AT-06 — bài nộp/điểm/privacy | Đạt small L; medium H | Verifier small và bộ HTTP medium nguồn/restore |
| AT-07 — cron/task | Đạt small L; medium H | Task scheduled có timestamp mới, task lỗi 0; runner/lock medium theo evidence N2 |
| AT-08 — reboot | Đạt small H | Hồ sơ Sydney/N3 giữ dữ liệu và tự khởi động; không reboot lại trong lượt chốt |
| AT-09 — file/config/network | Đạt phạm vi đã kiểm | Protected paths/permission small L, inventory/IMDSv2/EBS; staging có SG relay private của fixture tải, không phải baseline không-ingress tuyệt đối |
| AT-10 — backup/recovery | Đạt small H/L; medium H | Backup mới có checksum và manifest; ca AccessDenied/recovery có hồ sơ. Bộ 14/11 chưa restore-test |
| AT-11 — restore small | Đạt H | Bộ hỏng bị từ chối; bộ đúng phục hồi fixture, ghi mới và reboot. Không lấy checksum để thay restore |
| AT-12 — medium deployment/TLS/state | Đạt H, chưa tái kiểm L | ALB HTTPS/ACM, private data, release và S3 lock có bằng chứng; lab N2 đã cleanup |
| AT-13 — đa node/session/file | Đạt H | Node logs, cookie xuyên node, file/hash nguồn và restore |
| AT-14 — purge cache isolation | Đạt từng phần | Session sau purge trên AWS H; namespace khác có canary CI. Chưa chạy ca namespace khác trên medium live mới |
| AT-15 — thay node/scaling | Đạt thay node H, thiếu so sánh scaling tải | ASG replacement có evidence; không suy scale policy dưới tải đã được nghiệm thu đầy đủ |
| AT-16 — lock/release tranh chấp | Đạt từng phần H | Lock liên node/state có bằng chứng; một số ca gián đoạn migration/release còn thiếu |
| AT-17 — restore medium | Đạt H | Cluster riêng, DB/EFS mới, fixture/hash/ghi mới qua app; bộ backup cuối trước cleanup chưa restore-test |
| AT-18 — alarm/recovery | Đạt từng phần | Budget SNS→SQS có thử kênh; không phải thông báo vận hành đến người nhận. Chưa đủ toàn bộ alarm/failure scenarios |
| AT-19 — đo tải/so sánh | Đạt ma trận small; chưa đủ so sánh | Sydney đủ 9 lượt; N3 có 2 lượt 50-user chậm. Chưa benchmark medium và so sánh cài tay/tự động cùng phương pháp |
| AT-20 — bàn giao/cleanup/chi phí | Chờ nhóm chốt | Có báo cáo, inventory và chi phí Sydney; còn reviewer, quyết định vòng đời lab, chi phí N2/N3 |
| LMS-06 — GUI | Medium H; small chờ | Medium có ảnh desktop/mobile viewport. Small chưa có walkthrough GUI mới; HTTP không thay kiểm tra bố cục |

Yêu cầu gốc: [đặc tả nghiệm thu](12-dac-ta-tinh-nang-va-nghiem-thu.md). Các tiêu chí có phần chưa chạy được giữ nguyên trạng thái; không tính tỷ lệ hoàn thành bằng cách cộng các phép kiểm không tương đương.

## Những việc nhóm cần làm trước khi ký

1. **Reviewer độc lập** chạy [demo small](15-small-demo.md): teacher/student, tải học liệu, bài nộp/điểm và lỗi truy cập. Lưu ảnh desktop và viewport hẹp, ghi browser/version/ngày; không đưa mật khẩu vào ảnh.
2. **Chốt phạm vi trình bày medium**: dùng bằng chứng triển khai lịch sử và nói rõ lab đã cleanup; nếu rubric yêu cầu live medium/bộ ca còn thiếu, cần cửa sổ dựng lại và kiểm thử tương ứng. Không dùng account Sydney để chạy mẫu Singapore khi SCP đang từ chối region đó.
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
