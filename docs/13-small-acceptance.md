# Biên bản nghiệm thu small

## Đối chiếu bằng chứng cục bộ ngày 08/11/2026

Chạy lại **63 unit test: đạt**. AWS CLI 2.39.4 báo phiên `moodle-project` hết hạn khi gọi STS/SSM; chưa có xác nhận cloud mới trong lượt này. Không suy ra trạng thái thực tế của ma trận từ state cục bộ `running`.

Đã đối chiếu các summary lưu tại `.work/live-matrix/20261107T153956Z-users-*-summary.json`:

| User | Lượt | Giây quan sát | Sample JTL | Lỗi | Course p95 (ms) | Summary |
|---|---|---:|---:|---:|---:|---|
| 10 | r1 | 719,892 | 1.701 | 0 | 139 | passed |
| 10 | r2 | 719,972 | 1.766 | 0 | 137 | passed |
| 10 | r3 | 719,756 | 1.784 | 0 | 136 | passed |
| 25 | r1 | 779,427 | 4.517 | 0 | 194 | passed |
| 25 | r2 | 780,058 | 4.557 | 0 | 210 | passed |
| 25 | r3 | 779,628 | 4.543 | 0 | 196 | passed |
| 50 | r1 | 1.199,996 | 13.394 | 0 | 414 | passed |
| 50 | r2 | 1.199,803 | 13.242 | 0 | 401 | passed |
| 50 | r3 | Chưa thu | — | — | — | Chờ xác minh |

Smoke riêng 2 user: 147,442 giây, 70 sample, 0 lỗi, Course p95 107 ms. `passed` xác nhận assertion, số user và thời lượng; chưa có SLA latency được chốt. Workload đọc course/download/xem assignment và logout/login trong VPC, không đo ghi bài nộp hoặc render trình duyệt; cache ấm giữa các lượt. Chưa có bộ metric đầy đủ được đối chiếu và chưa kết luận năng lực tối đa.

Đã bổ sung [demo từng bước](15-small-demo.md), [dịch vụ sử dụng](16-small-services.md) và `scripts/demo-small.ps1`. Script đã được kiểm tra cú pháp PowerShell; tunnel thực tế chưa chạy lại do phiên AWS hết hạn. Cần xác minh invocation ma trận/metric cũ trước khi khởi chạy lại, lưu kết quả, hoàn tất rotation/backup staging và cleanup máy tạm, kiểm tra GUI rồi người nhận kiểm tra chéo. **P0 chưa đóng** cho đến khi có đủ bằng chứng này.

## Cập nhật ngày 07/11/2026 UTC (08/11 tại máy người vận hành)

Cập nhật này thay thế trạng thái chờ của các mục tương ứng trong nhật ký 05/11 bên dưới. **Chưa ký đóng P0**; không dùng kết quả một phần của bài tải đang chạy làm kết luận cuối.

| Hạng mục | Trạng thái mới và bằng chứng |
|---|---|
| Ngân sách | Đã giảm tổng dự án còn **150 USD**: dự kiến 112,50 USD, dự phòng 37,50 USD. Budget AWS `moodle-sydney-small-202611` đã tạo, SNS→SSE-SQS confirmed và thử gửi/nhận nonce thành công. Scope toàn account, usage trước credit/refund; không có email, không tự ngắt EC2. Report riêng `.work/moodle-sydney-budget/channel-report.json`; xem tài liệu 07 |
| CI | Commit `904c113`, cả [push](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/42392570020) và [pull request](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/42392573502) success. Có 63 unit test, runtime/Moodle integration, PHP lint và Terraform mock tests cho small, backup, load fixture và budget |
| Cài từng bước | EC2 sạch cùng AMI, thao tác từng pha theo runbook qua SSM, không gọi toàn bộ bootstrap. Đã seed rồi verify đầy đủ nghiệp vụ/HTTP. Đây là lượt do agent vận hành, chưa phải lượt thử độc lập của thành viên nhóm. Tổng thời gian các pha remote ban đầu 343,509 giây; wall time gồm khoảng nghỉ nhiều ngày, không dùng để kết luận cài tay chậm hơn tự động |
| Admin | Đã đổi admin trên dev và máy cài thử, xác minh mật khẩu cũ bị từ chối, thu hồi phiên cũ, cập nhật fixture/quyền file và verify nghiệp vụ đầy đủ. Dev đã có backup mới `20261107T171622Z`; bộ mới chưa diễn tập restore. Staging chờ kết thúc bài tải trước khi đổi admin/backup. Bằng chứng đầy đủ: SSM `6f8bbae5-70a8-4427-9218-fd03ab4a3840`, `0079f489-5561-4c9e-a6a9-201863c0d49a`, `5adcb35a-4b5c-43aa-b731-780da24e146d` |
| Tải trong VPC | Generator riêng trong VPC staging, relay TCP có giới hạn peer qua SG tạm, không mở ingress public. Smoke 2-user và ba lượt 10/25-user đạt assertion, user count và thời lượng; tất cả sample không lỗi. Course p95 lần lượt 139/137/136 ms (10-user), 194/210/196 ms (25-user). Các lượt 50-user đang chạy; chưa kết luận ma trận hoàn tất. Summary riêng `.work/live-matrix/20261107T153956Z-users-*-summary.json`; không trộn với kết quả SSM tunnel cũ |
| Chi phí | Cost Explorer đã trả usage 5,4670580578 USD và credit −5,4670580635 USD cho toàn account, mọi region, cửa sổ 01/11 inclusive–07/11 exclusive; các ngày đều Estimated. Chênh lệch gần 0 do credit/làm tròn không có nghĩa không phát sinh usage. Estimate riêng tài nguyên core tại 15:33 UTC là 7,6216 USD, khác scope/cửa sổ với billing và không được cộng chồng; chưa phải hóa đơn cuối |
| Cleanup | Máy cài thử và generator được lập kế hoạch dọn riêng sau khi lưu kết quả. Chưa xác nhận đã xóa trong snapshot này. Dev/staging và monitor budget giữ để vận hành/demo; không xóa lab cũ ngoài state |
| Giao diện/kiểm tra chéo | Chưa đạt bằng chứng. Công cụ điều khiển Chrome tự dừng do không xác minh URL, không tiếp tục tự động hóa giao diện. Cần người nhận kiểm tra và ký; agent không ký thay. [Checklist bàn giao](14-small-handover.md) |

Rotation ban đầu chỉ hoàn tất phần PHP vì Docker interactive đọc mất phần script còn lại khi chạy `bash -s`; đã sửa runner riêng sang file script, stdin `/dev/null`. Lần tiếp theo phát hiện umask 077 làm fixture mới thiếu quyền group; đã đặt rõ 0640 root:www-data trước atomic replace. Chỉ các invocation verify đầy đủ nêu trên được tính là hoàn tất; log thử lỗi vẫn giữ để đối chiếu.

State theo dõi riêng: `.work/finish-small-state.json` (load/metric/cleanup), `.work/security/final-state.json` (rotation/backup staging sau tải). Không gửi các file secret/state/backup trong gói source. Khi bài tải kết thúc, phải đối chiếu các state và cập nhật biên bản trước khi gọi Small hoàn tất.

## Nhật ký trước đó — 05/11/2026

Ngày cập nhật: 05/11/2026. Môi trường thực tế: Sydney, `config/sydney.yaml` và `config/sydney-staging.yaml`. Đây là biên bản theo bằng chứng; chưa ký đóng P0 khi còn mục chờ.

## Kết quả đã chứng minh

| Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|
| EC2, cloud-init, PHP/PostgreSQL/Moodle, quyền file | Đạt trên dev/staging | Nhật ký 08, report cloud acceptance |
| Login/logout, course/file, student/teacher, bài nộp/điểm/phân quyền | Đạt trước/sau restore và reboot staging | `.work/moodle-sydney-staging/acceptance/20261105T073000Z-0719bbd1/report.json` và invocation reboot |
| Backup S3, lịch thật, checksum và restore | Đạt; thời gian lệnh restore quan sát một lần 64,496 giây | `.work/moodle-sydney-staging/recovered-restore-result.json` |
| Ghi file sau restore; reboot và dịch vụ tự khởi động | Đạt | Nhật ký 08, invocation ngày 05/11 lúc 07:31 và 07:33 UTC |
| Web dừng được health phát hiện, recovery đúng | Đạt, health exit 3 khi dừng; sau start health/nghiệp vụ đạt | `.work/moodle-sydney-staging/commands/20261105T074342Z-10ef3c/result.json` |
| S3 từ chối ghi backup | Đạt, `AccessDenied`, backup exit 1; web/cron trở lại active và health đạt | Cùng invocation thử lỗi; log riêng trên host |
| Backup thiếu file hoặc sai checksum | Đạt, restore exit 2 trước khi ghi đè; số user/course/submission không đổi, web vẫn active | Cùng invocation thử lỗi |
| Plan lần hai | Có replacement EC2 do `user_data_base64` đổi; chưa apply | Đối chiếu payload cũ/mới của `.work/small-final-plan.log`: chỉ file bundle `/opt/moodle-distribution/verify_backup.py` đổi, các khóa cloud-config khác giữ nguyên. `user_data_replace_on_change = true` buộc thay EC2; đây là thay đổi mã bootstrap trong plan đã lưu, không phải bằng chứng AMI đổi. Phải lập/review plan mới trước triển khai tiếp |
| Đọc qua SSM với 2 user | Các lượt đọc cũ đã đạt; chưa phải phép đo sức tải chính thức | Nhật ký 08 và summaries trong `.work/load/` |

Thử lỗi chạy riêng staging từ 07:43:45 đến 07:46:31 UTC. Prefix thử S3 nằm ngoài phạm vi role staging; không cấp thêm IAM. Script khôi phục `deploy.json`, web/cron/backup timer trong EXIT trap. Fixture thiếu/hỏng được tạo bằng bản sao của backup đã kiểm chứng, giữ nguyên bản nguồn. `StandardErrorContent` có lỗi curl khi web cố ý dừng, là kết quả mong đợi, không phải lỗi recovery.

## Smoke và metric đã thu

- Có 50 tài khoản student giả, enrol vào course fixture trên staging; credential chỉ ở dataroot riêng tư, object S3 private và `.work/load/staging-users-private.csv`.
- `python -m scripts.make_small_workload` sinh `tests/load/moodle-small.jmx`: 60% course, 20% download, 10% xem assignment, 10% chu kỳ logout/login. Tỷ lệ tính theo hành động logic; chu kỳ auth phát sinh nhiều HTTP request. Nộp bài/chấm điểm được kiểm tra ở acceptance riêng, chưa đo ghi bài dưới tải.
- Smoke hỗn hợp v3 trên staging: 2 user, ramp 30 giây, chạy 147,928 giây, 72 sample, 0 lỗi; summary báo `passed`. p95: Course 2.068 giây, Download 0.324 giây, Assignment view 1.681 giây, Login 2.940 giây, Logout 0.819 giây. Bằng chứng `.work/load/staging-mixed-smoke-v3-summary.json` và JTL riêng tư. Đây chỉ là smoke qua SSM tunnel.
- JMX smoke dùng kết nối HTTP mới cho mỗi request và không bật retry. Hai smoke cũ gặp lỗi tunnel; chỉ lượt v3 trên đây được tính.
- Metric OS/DB lấy mỗi 15 giây trong 46,4 phút, 186 mẫu, bao gồm smoke v3; CPU median 0,97%, max 13,26%; RAM dùng max 37,6%; swap 0; disk max 16,1%; DB connections max 3; scheduled/adhoc task failures đều 0. Bằng chứng riêng tư `.work/load/staging-metrics-20261105.jsonl`. Phần lớn khoảng này không có tải kiểm soát, nên metric không chứng minh giới hạn năng lực.

## Các mục chưa đủ bằng chứng để đóng P0

| Mục | Việc cần làm |
|---|---|
| Giao diện và demo | Công cụ browser tự dừng vì không xác minh được URL Chrome. Cần kiểm tra teacher/student bằng trình duyệt và lưu ảnh/video; chưa đánh dấu đạt |
| Load/metric chính thức | Smoke đạt. Đã đo ba lượt 10-user; hai lượt không lỗi, lượt ba bị tunnel ngắt. Chưa đủ bằng chứng đạt ma trận 10/25/50 user; cần phục hồi phiên AWS và đường hầm ổn định trước khi đo tiếp |
| Cài thủ công và so sánh | Runbook đã có; chưa có biên bản cài tay độc lập và thời gian đến ready để so sánh với tự động |
| CI trên commit bàn giao | Đạt trên commit `6eff8de`, nhánh `mq`: [run 1](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/41997113031) và [run 2](https://github.com/iamquan24122006/BTL-Cloud/actions/runs/41997120727) đều success, gồm unit tests, Docker runtime/Moodle integration và Terraform small/backup |
| Chi phí và cleanup | Cost Explorer đã trả dữ liệu toàn account nhưng không có service group trong khoảng 01–05/11, mọi ngày còn Estimated. Không coi đây là bằng chứng bill small bằng 0 USD. Cần số liệu billing khả dụng, inventory và lịch giữ/xóa tài nguyên được chốt |
| Kiểm tra chéo | Thành viên khác thực hiện runbook/demo và ký xác nhận; agent không tự ký thay người kiểm tra |

Hiện hai EC2 của small vẫn được giữ để đo/demo. Không tự xóa lab cũ ngoài state hoặc hủy lab đang dùng chỉ để đóng checklist. Kết quả P0 hiện tại: **chưa đóng nghiệm thu**, các chức năng nền tảng và ca lỗi nêu trên đã đạt.

## Kết quả baseline 10-user

Ba lượt dùng ramp 120 giây, thời lượng yêu cầu 720 giây, tài khoản riêng theo virtual user. Sample JTL bao gồm redirect subresults; console JMeter chỉ đếm sampler cha nên số lượng khác nhau.

| Lượt | Giây quan sát | Sample JTL | Lỗi | Course p95 | Kết quả |
|---|---:|---:|---:|---:|---|
| r1 | 721,053 | 1.411 | 0 | 2.439 ms | Đạt assertion/thời lượng; login p95 4.305 ms |
| r2 | 720,114 | 1.582 | 0 | 1.533 ms | Đạt assertion/thời lượng |
| r3 | 725,051 | 886 | 10 | 4.654 ms | Không đạt; socket timeout rồi localhost connection refused |

Log tunnel r3 ghi `An existing connection was forcibly closed by the remote host`. Vì vậy chưa thể quy lỗi cho Moodle hoặc kết luận sức tải EC2. Các summary riêng tư ở `.work/load/small-baseline-r*-summary.json`. JTL r3 thiếu header sau khi tái sử dụng đường dẫn của lượt đã dừng; đã bổ sung header chuẩn để phân tích, không sửa sample. Cần dùng đường dẫn mới cho mỗi lượt tiếp theo. CPUCreditBalance trước ma trận: 175,658 tại 09:27 UTC. Sau đo, snapshot SSM `df0111ea-21d0-4a29-8bfe-6a7b61887d53` xác nhận web/cron active, không swap hoặc task failures.

Đã đăng nhập lại AWS thành công sau khi người dùng xác thực. STS xác nhận account `828676179987`, role `AccountFullAccessRole`; dev và staging đều SSM Online. Health mới qua SSM đạt trên dev (`e2480fe2-03fc-4067-a357-01e28d4e5755`) và staging (`0a44cbbe-a1ed-4b71-bc45-494ae593f5eb`), exit 0; không cần đăng nhập lại cho bước tiếp theo khi phiên còn hạn. Chưa đo 25/50-user.

Bộ thu metric ma trận đã hoàn tất thành công, SSM `97231025-4583-4ccd-9f30-4675f251f9f0`; file riêng tư `.work/load/staging-matrix-metrics-20261105.jsonl`. Đối chiếu timestamp JTL cho từng lượt:

| Lượt | Mẫu OS hợp lệ | CPU median / max | RAM dùng max | Swap max | DB connections max | Scheduled/adhoc failures |
|---|---:|---:|---:|---:|---:|---|
| r1 | 48 | 9,95% / 13,57% | 38,16% | 0 KiB | 3 | 0 / 0 |
| r2 | 47 | 10,39% / 14,25% | 38,28% | 0 KiB | 3 | 0 / 0 |
| r3 | 49 | 7,08% / 13,99% | 38,47% | 0 KiB | 3 | 0 / 0 |

Không có lỗi sampler trong các cửa sổ này. Các mẫu OS chưa cho thấy cạn RAM/swap hoặc CPU cao trong lượt r3, nhưng chu kỳ lấy mẫu 15 giây và tunnel bị ngắt chưa đủ để khẳng định nguyên nhân của mọi response chậm. Summary riêng tư `.work/handover/metrics-baseline-summary.json`.

## Lệnh tiếp tục

Chọn `$env:AWS_PROFILE = 'moodle-project'`, kiểm tra STS đúng account trước mọi lệnh. Không apply plan đang có replacement EC2.

```powershell
gh auth status
python -m scripts.make_small_workload
java -jar .work/tools/apache-jmeter-5.6.3/bin/ApacheJMeter.jar -n -t tests/load/moodle-small.jmx -q .work/load/staging.properties -Jusers=2 -Jramp=30 -Jduration=150 -l .work/load/staging-mixed-smoke-v3.jtl -j .work/load/staging-mixed-smoke-v3.log
```

Đường dẫn Python/Java phải dùng bản đã cài trên máy; dùng đường dẫn JTL mới cho mỗi lượt. Summary hỗ trợ `--workload small --expected-users 2 --minimum-seconds 140 --ramp-seconds 30`; unit tests kiểm tra lượt ngắn/thiếu user bị từ chối và tách ramp/steady. Không đưa CSV password, state, saved plan, config.php hoặc backup vào Git/bộ nộp.
