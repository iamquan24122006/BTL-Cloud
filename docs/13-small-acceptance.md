# Biên bản nghiệm thu small

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
| Plan lần hai | Đã review; có replacement EC2, chưa apply | `.work/small-final-plan.log`; phải giải thích nguyên nhân đầy đủ trước triển khai tiếp |
| Đọc qua SSM với 2 user | Các lượt đọc cũ đã đạt; chưa phải phép đo sức tải chính thức | Nhật ký 08 và summaries trong `.work/load/` |

Thử lỗi chạy riêng staging từ 07:43:45 đến 07:46:31 UTC. Prefix thử S3 nằm ngoài phạm vi role staging; không cấp thêm IAM. Script khôi phục `deploy.json`, web/cron/backup timer trong EXIT trap. Fixture thiếu/hỏng được tạo bằng bản sao của backup đã kiểm chứng, giữ nguyên bản nguồn. `StandardErrorContent` có lỗi curl khi web cố ý dừng, là kết quả mong đợi, không phải lỗi recovery.

## Phép đo tải đang chuẩn bị

- Có 50 tài khoản student giả, enrol vào course fixture trên staging; credential chỉ ở dataroot riêng tư, object S3 private và `.work/load/staging-users-private.csv`.
- `python -m scripts.make_small_workload` sinh `tests/load/moodle-small.jmx`: 60% course, 20% download, 10% xem assignment, 10% chu kỳ logout/login. Tỷ lệ tính theo hành động logic; chu kỳ auth phát sinh nhiều HTTP request. Nộp bài/chấm điểm được kiểm tra ở acceptance riêng, chưa đo ghi bài dưới tải.
- Smoke mới dừng sau khoảng 31 giây: hai Course gặp `NoHttpResponseException` qua SSM; không được dùng kết quả này để kết luận sức tải hoặc quy lỗi cho Moodle.
- Đã chuẩn bị biến thể không dùng HTTP keep-alive, không bật retry; **chưa chạy xác minh được** vì Windows từ chối tạo tiến trình ngoài sandbox với `Access is denied (os error 5)` hai lần. Chưa xác nhận nguyên nhân lỗi socket.
- Bộ thu `scripts/sample_metrics.py` lấy CPU theo delta, RAM/swap/disk, DB connections và faildelay mỗi 15 giây, không lấy query text/credential. Lệnh SSM `766d68c1-43f6-43d3-aad6-23e99f9e0d68` được gửi với giới hạn 9.300 giây; sampler tối đa 9.000 giây, rồi upload JSONL vào prefix staging. Có stop file `/run/moodle-load-small.stop` để kết thúc sớm. Chưa thu lại kết quả nên chưa kết luận metric đạt.

## Các mục chưa đủ bằng chứng để đóng P0

| Mục | Việc cần làm |
|---|---|
| Giao diện và demo | Công cụ browser tự dừng vì không xác minh được URL Chrome. Cần kiểm tra teacher/student bằng trình duyệt và lưu ảnh/video; chưa đánh dấu đạt |
| Load/metric chính thức | Xác minh smoke mới trước; chạy ma trận 10/25/50 user với thời gian/ramp và ba lần lặp theo tài liệu 06/12; lưu CPU credits và metric OS tương ứng. Dừng tăng tải nếu có lỗi kéo dài |
| Cài thủ công và so sánh | Runbook đã có; chưa có biên bản cài tay độc lập và thời gian đến ready để so sánh với tự động |
| CI trên commit bàn giao | Đã mở `gh auth login` theo xác nhận người dùng; chưa có xác nhận đăng nhập xong hoặc lượt CI mới đạt |
| Chi phí và cleanup | Cost Explorer đã trả dữ liệu toàn account nhưng không có service group trong khoảng 01–05/11, mọi ngày còn Estimated. Không coi đây là bằng chứng bill small bằng 0 USD. Cần số liệu billing khả dụng, inventory và lịch giữ/xóa tài nguyên được chốt |
| Kiểm tra chéo | Thành viên khác thực hiện runbook/demo và ký xác nhận; agent không tự ký thay người kiểm tra |

Hiện hai EC2 của small vẫn được giữ để đo/demo. Không tự xóa lab cũ ngoài state hoặc hủy lab đang dùng chỉ để đóng checklist. Kết quả P0 hiện tại: **chưa đóng nghiệm thu**, các chức năng nền tảng và ca lỗi nêu trên đã đạt.

## Lệnh tiếp tục khi quyền chạy công cụ được phục hồi

Chọn `$env:AWS_PROFILE = 'moodle-project'`, kiểm tra STS đúng account trước mọi lệnh. Không apply plan đang có replacement EC2.

```powershell
gh auth status
python -m scripts.make_small_workload
java -jar .work/tools/apache-jmeter-5.6.3/bin/ApacheJMeter.jar -n -t tests/load/moodle-small.jmx -q .work/load/staging.properties -Jusers=2 -Jramp=30 -Jduration=150 -l .work/load/staging-mixed-smoke-v2.jtl -j .work/load/staging-mixed-smoke-v2.log
```

Đường dẫn Python/Java phải dùng bản đã cài trên máy; không tái sử dụng file JTL có sẵn. Summary cũ `scripts.summarize_jmeter` mô tả workload đọc 50/50; cần cập nhật scope/kiểm tra đủ nhãn và thời lượng trước khi dùng để tổng hợp workload mới. Không đưa CSV password, state, saved plan, config.php hoặc backup vào Git/bộ nộp.
