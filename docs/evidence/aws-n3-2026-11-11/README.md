# N3 AWS acceptance — bắt đầu 11/11/2026 UTC

**Lượt chạy đang thực hiện; chưa ký nghiệm thu toàn dự án.** Small đã có kết quả chức năng/restore bên dưới. JMeter đã hoàn tất ma trận đầy đủ; medium đang chờ xác thực DNS ACM. Kết quả cập nhật xem mục cuối. Người thực hiện: Codex; chưa có reviewer độc lập.

## Môi trường và nguồn mã

- Profile `default`, account `333091152670`, region `ap-southeast-1`. Đây là account khác hồ sơ N2 cũ. Account đang Free plan; không nâng cấp billing.
- Source small có sẵn: `i-02f94043ce763d4ce`, `moodle-lab-dev`, `t3.small`, Ubuntu 26.04.1, Moodle 4.5.15, PHP 8.3.35, PostgreSQL 16.15. URL SSM `http://localhost:8081` → remote localhost:8080.
- Staging mới: `i-0a2d4365b51114ed9`, `moodle-lab-staging`, `t3.small`, 30 GiB, cùng baseline; URL localhost:8080 bên trong staging/generator.
- Mã small lấy từ checkout riêng nhánh `mq`, commit `2d4288921b23940de6d8aef5fa5888f48451fcd5`. Mã medium/runtime từ commit `82e95c9849ec4ac4a061b6650c5ab2cbe01d995e`.
- Nghiệm thu small dùng `tests/integration/moodle.php` của mq, đổi shortname thành CLOUD-C01/CLOUD-C02. Verifier nguồn giữ URL/cookie localhost:8081 và dùng CURLOPT_CONNECT_TO tới loopback:8080; verifier staging dùng localhost:8080. Sau khi thêm resource nhị phân, chọn resource văn bản theo tên `Fixture download` để tránh truy vấn mơ hồ nhiều resource.

## Kết quả small đã hoàn tất

| Ca/phạm vi | Kết quả và giới hạn | Bằng chứng |
|---|---|---|
| Health source | Cloud-init done, web/DB/cron hoạt động, quyền file và URL nhạy cảm đạt | [source-health.json](source-health.json) |
| AT-04/06 — LMS | Login admin/teacher/student A/B; outsider bị chặn; enrolment, hash học liệu, bài nộp, điểm87/93, phản hồi và quyền riêng tư đúng | [source-acceptance.json](source-acceptance.json) |
| HTTP từ máy người vận hành | 18/18 kiểm tra đạt; có sai mật khẩu, student không sửa course/vào admin và cookie cũ bị từ chối sau logout | [http-through-tunnel.json](http-through-tunnel.json) |
| SMALL-01/05 | SG không ingress ở baseline trước fixture load, IMDSv2 bắt buộc, EBS gp3 mã hóa; cả hai máy dùng CPU credit standard | [security-inventory.json](security-inventory.json) |
| Backup nguồn | Bộ `20261111T153406Z` tải qua SSM, xác minh SHA-256 và chuyển private S3; không chia sẻ payload | [download-verified.json](download-verified.json) |
| AT-11 — restore âm/dương | Sửa byte database.dump: restore từ chối trước mutation, số course giữ nguyên. Bộ đúng phục hồi sang staging, giữ ID/file/bài/điểm và ghi file mới đạt | [restore.json](restore.json) |
| AT-03 — bootstrap lại | Đã cài thành công thì chạy health, không reset course/user/submission; chạy lại LMS đạt | [staging-rebootstrap.json](staging-rebootstrap.json) |
| AT-08 — reboot | Boot ID đổi; web/DB/cron tự lên, LMS và dữ liệu vẫn đúng | [trước](pre-reboot.json), [sau](post-reboot.json), [LMS sau reboot](staging-after-reboot.json) |
| AT-05 — upload/download | Teacher upload multipart file nhị phân tên tiếng Việt có khoảng trắng, 60 MiB; student tải lại đúng SHA-256 | [staging-upload.json](staging-upload.json) |
| AT-05 — quá giới hạn | Limit Moodle/PHP64 MiB; file65 MiB bị từ chối bằng JSON rõ ràng dù HTTP200: “The file you tried to upload is too large for the server to process.” | [oversize-message.json](oversize-message.json) |
| Timer backup thật | Drop-in runtime kích hoạt sau30 giây; timer tự chạy service thành công, drain cron, payload đủ/hash đúng, upload S3; đã trả lịch gốc | [scheduled-backup.json](scheduled-backup.json) |

Backup nguồn `moodle-lab-dev/20261111T153406Z` là bộ đã restore-test. Bộ scheduled staging `moodle-lab-staging/20261111T160706Z` là lượt backup riêng, chưa restore-test chính bộ đó. Không suy RPO=0 từ fixture tĩnh. Restore không chép config.php nguồn lên cấu hình đích.

Upload được kiểm qua HTTP multipart thật và Moodle API để xuất bản resource; đây chưa phải thao tác file picker bằng trình duyệt. Chưa ký toàn bộ LMS-06 hoặc tương thích desktop/mobile. Công cụ browser hiện chưa mở được tab IAB vì browser access host unavailable.

## Đo tải đang chạy

- Người dùng chọn đầy đủ: smoke2user/30s ramp/150s tổng, rồi10user/120s/720s,25user/180s/780s,50user/300s/1200s; mỗi mức so sánh lặp3 lần. Thời gian tổng có ramp, tương ứng cửa sổ steady của đặc tả.
- Generator riêng `i-05aa2853614b5a32b`, `moodle-n3-small-load-generator`, `t3.small`, EBS20 GiB, Java21 và JMeter5.6.3 kiểm SHA-512 chính thức. Một CSV với50 user giả, mỗi user/session riêng, giữ private.
- Đường private cùng subnet: generator loopback8080 → staging private8081 → web loopback8080. Relay chỉ nhận peer chỉ định và SG chỉ cho generator; có lifetime hữu hạn. Không đo qua tunnel từ laptop.
- JMX workload small của mq: 60%course,20%download,10%assignment view,10%logout/login theo **logical actions**, think3–8s, HTTP keep-alive tắt và không retry. Không có submission writes trong tải; các lượt nộp/chấm được kiểm tra chức năng riêng.
- Chạy từ `2026-11-11T16:22:10Z`. Smoke đạt lúc16:24:50Z; bắt đầu10user lần1. Chưa kết luận hiệu năng hoặc mức user được hỗ trợ từ trạng thái đang chạy.
- Lượt10user lần1 đạt:719,694 giây quan sát, đủ10user; pha steady có534 mẫu Course,0 lỗi,p95 thành công160ms. Đây chưa phải kết luận từ3 lần lặp. Checkout mq đạt63/63 unit test sau khi dùng cho lượt này.
- Đến17:01:40Z đã đủ3/3 lượt10user đạt; bắt đầu25user lần1. Các summary còn lại sẽ được đối chiếu sau khi matrix kết thúc.
- Generator thu vmstat; staging thu CPU/RAM/disk/DB connections/task failures mỗi15s. Sẽ bổ sung CPU credit và tổng hợp p50/p95/p99/error theo transaction sau chạy.

**Lỗi runner đã phát hiện và sửa:** script mq chưa tạo thư mục cha `results`, khiến lần khởi chạy đầu dừng trước khi phát tải. Patch thêm tạo parent, giữ việc tạo directory từng run độc quyền và không ghi đè raw result: [load-runner.patch](load-runner.patch). Bản chạy có SHA-256 `c3a7bbec040d850ebbe9f13f48deb11e2e1af973b2c5c65cdc256dffe7518a6c`, ghi trong tooling manifest trên generator. Bash syntax đạt; [Terraform fixture mock1/1 đạt](load-mock-tests.log).

## Medium và cleanup tạm thời

- Support/bucket/ECR/secret cho test đã tạo riêng; artifact đúng commit, image digest ghim, bundle checksum; giá trị secret không nằm trong YAML/evidence.
- AWS từ chối builder `t3.medium` vì account Free plan. Đã thêm input `--builder-instance-type t3.small` với mặc định cũ giữ nguyên, lập plan mới sau partial apply và build AMI thành công. Terraform validate đạt; [40/40 unit test sau sửa](post-builder-change-unit.log).
- Bổ sung canary namespace khác trên cùng Redis cache trước/sau purge MUC vào integration local. [47/47 bước đạt](medium-cache-isolation.json), gồm session sau purge; đã dọn container/volume/network. Canary chứng minh purge không flush dữ liệu ngoài namespace, chưa phải một site Moodle thứ hai hay bằng chứng AWS.
- AMI `ami-0394cfc65ef612683`, snapshot `snap-0f4577af49c815f81`. Builder đã dọn bằng saved destroy plan:10 tài nguyên xóa, không xóa AMI đang cần dùng. Main medium chưa deploy vì ACM còn PENDING_VALIDATION cho hostname Dynu.
- Còn chạy: dev có sẵn, staging và generator mới. Support storage/secrets/AMI còn tồn tại; chưa cleanup cuối. Không coi đây là biên bản ngừng phí.
- Quota On-Demand Standard hiện8vCPU. Cần tính cả dev có sẵn và máy phát tải khi lập lịch medium/scaling; không mặc định account còn chỗ chỉ từ số app trong ASG.

## Bảo vệ dữ liệu và phần còn chờ

Người dùng đã cho phép cụ thể việc chuyển backup/config/credential fixture và CSV load qua các vị trí private trong cùng account và `.work` cục bộ. Các thư mục private cục bộ giới hạn ACL cho người vận hành và SYSTEM. Không copy password, cookie, CSV, dump, moodledata, config.php, signed URL, state hoặc plan vào evidence. Máy chủ chuyển backup loopback và tunnel tải backup đã đóng sau khi kiểm hash.

Còn chờ: medium HTTPS/multiple-node/release/restore/alarms/scaling; walkthrough browser; bằng chứng cài tay/CI remote/reviewer độc lập; số liệu chi phí và cleanup cuối. Các trạng thái AT toàn dự án chưa tự chuyển thành Đạt chỉ vì các bước small ở trên thành công.


## Cập nhật kết quả ngày 13/11/2026 (giờ Việt Nam)

Ma trận kết thúc lúc `2026-11-11T18:43:53Z` (01:43:53 ngày 12/11 giờ Việt Nam).
Đã thu kết quả ngày 13/11: systemd inactive, Result=success, ExecMainStatus=0;
smoke và đủ 9 lượt 10/25/50 user đều hoàn tất, đủ user và thời lượng.
Trạng thái `passed` của runner chỉ xác nhận tính hợp lệ/lỗi nghiệp vụ của lượt chạy,
không có nghĩa đạt ngưỡng p95 ≤3 giây.

| User | Lượt | Tổng sample | Lỗi | p95 Course steady (ms) | p95 Login steady (ms) | p95 Assignment steady (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1 | 1710 | 0 | 160 | 408 | 260 |
| 10 | 2 | 1706 | 0 | 152 | 346 | 281 |
| 10 | 3 | 1690 | 0 | 170 | 477 | 196 |
| 25 | 1 | 4438 | 0 | 263 | 581 | 328 |
| 25 | 2 | 4364 | 0 | 242 | 563 | 306 |
| 25 | 3 | 4412 | 0 | 228 | 629 | 285 |
| 50 | 1 | 13217 | 0 | 631 | 1579 | 862 |
| 50 | 2 | 5039 | 0 | 18477 | 41230 | 26620 |
| 50 | 3 | 4845 | 0 | 17705 | 41025 | 27164 |

10/25 user có độ trễ thấp trong workload này. 50 user lượt 2–3 không đạt ngưỡng
p95 tương tác ≤3 giây dù không có lỗi nghiệp vụ. Chưa kết luận nguyên nhân
CPU credit khi chưa đối chiếu toàn bộ metric theo thời điểm từng lượt.
Không dùng lượt 50 user đầu tiên để tuyên bố small hỗ trợ ổn định 50 user.
Các sample gồm transaction cha/con; không cộng thành số thao tác người dùng độc lập.

Bằng chứng: [trạng thái cuối](load-progress-final.json), [timeline](progress.jsonl),
[tooling manifest](tooling-manifest.json), các `users-*-summary.json` cùng thư mục.
Raw JTL, CSV user và credential giữ private trong `.work`/S3.

Ca âm backup S3 trên staging: `2026-11-12T17:38:14Z`–`17:40:58Z`;
prefix ngoài IAM scope bị AccessDenied, cấu hình gốc được phục hồi,
health và verifier LMS (login, hash file, điểm, quyền riêng tư, logout) đều đạt.
Xem [staging-backup-denied.json](staging-backup-denied.json).
Một probe HTTP chạy khi backup đang maintenance báo Missing login token;
không tính probe đó là ca đạt. Verifier sau recovery đạt như bằng chứng trên.

Bộ unit hiện tại được chạy lại: 40/40 đạt với PyYAML pure-Python đã mô tả
trong hồ sơ offline. Không thay dependency. Chứng chỉ ACM vẫn PENDING_VALIDATION
tại lần kiểm tra này; chưa chạy main medium. Browser QA chưa đạt: công cụ dừng
do trình duyệt Windows hiện tại chưa hỗ trợ thực thi chính sách URL.
Chưa cleanup cuối, chưa ký nghiệm thu toàn dự án.
