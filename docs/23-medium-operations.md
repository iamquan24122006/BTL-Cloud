# Vận hành autoscaling và cảnh báo medium

IaC medium bổ sung policy target tracking theo `ALBRequestCountPerTarget`, dashboard CloudWatch và đường thông báo CloudWatch → SNS → SQS. Cấu hình đã áp dụng trên lab Sydney ngày 14/11/2026; bài thử thông báo đã nhận cả ALARM và OK sau khi CloudWatch đánh giá metric thật.

## Tự mở rộng

```yaml
app_requests_per_target: 600
```

Giá trị là số request trung bình trên **mỗi app trong một phút**. ASG giữ tối thiểu 2, tối đa 3 app; runner không thuộc nhóm. Đây là giá trị khởi đầu cho lab, cần hiệu chỉnh bằng workload đại diện, không phải chứng nhận công suất hay SLA. AWS quản lý các alarm của policy; không sửa trực tiếp các alarm này.

Instance warmup là 300 giây. ALB chờ readiness trước khi chuyển traffic; Redis/EFS giữ session và file khi số app thay đổi. Terraform bỏ qua thay đổi `desired_capacity` do policy quản lý, nên lần apply sau không ép nhóm từ 3 về 2. EC2 health check vẫn được giữ để lỗi database/cache dùng chung không tạo vòng lặp thay toàn bộ app.

## Dashboard và thông báo

**Hiệu chỉnh lab 15/11:** cấu hình Sydney hiện dùng target **200 request/app/phút**. Burst 20 user trong tám phút có 4.890 lượt đọc, không lỗi; policy tự tăng ba target healthy rồi trở lại hai. Sau chuyển tên miền, hai app mới/runner giữ cùng release, 47/47 ca nghiệp vụ đạt. Đây là drill scaling, không phải ma trận benchmark chuẩn hoặc chứng nhận công suất. [Bằng chứng](evidence/current-review-2026-11-15/README.md), [cutover tên miền và giữ URL cũ](25-domain-cutover.md).

Các output `dashboard_name`, `alarm_topic_arn`, `alarm_queue_url`, `scaling_policy_arn` được trả bởi `status`. Dashboard có 11 widget: trạng thái alarm; latency p95, request/lỗi ALB; healthy targets/desired capacity; CPU app/runner; CPU và bộ nhớ/dung lượng RDS; Redis; EFS; bộ nhớ/đĩa host; cron/backup.

14 alarm vận hành gửi cả ALARM và OK đến SNS. Inbox SQS mã hóa bằng SSE-SQS, lưu 14 ngày, chỉ cho topic của site gửi tin. Topic chỉ cho CloudWatch alarm của site/account/region publish. Message chỉ chứa metadata tài nguyên và metric. Người vận hành cần kiểm tra inbox hoặc bổ sung subscription email đã được chủ email xác nhận; SQS không tự gửi push đến người trực.

Kiểm tra bằng credential chain của operator, không dùng role của app:

```bash
python -m scripts.check_medium_observability \
  --config /private/medium.yaml \
  --output .work/monitoring-delivery.json
```

Bài kiểm tra chỉ ghi `NotificationProbe`: tạo ALARM rồi phục hồi OK bằng metric thật, nhận và xác nhận đúng hai thông báo. Không ép trạng thái alarm sức khỏe hoặc scaling. Chờ tối đa 6 phút cho mỗi pha; không nhận đủ thì trả lỗi. Inbox có thể còn các thông báo vận hành khác; bài kiểm tra không xóa chúng.

Probe là alarm thứ 15, tách khỏi 14 alarm vận hành. Dashboard và đường nhận tin đã được xác minh; bằng chứng scale-out/in dưới tải và benchmark phải được ghi riêng, không suy ra từ việc policy tồn tại.

## Chi phí và thay đổi

Lần áp dụng bổ sung 15 tài nguyên và cập nhật 8 cấu hình, không thay thế/xóa EC2, RDS, EFS hay Redis. Alarm, metric và dashboard có thể phát sinh phí CloudWatch; SNS/SQS tính theo lượng sử dụng. Khi scale-out, app thứ ba bổ sung EC2/EBS và lưu lượng; giới hạn 3 app không phải giới hạn toàn bộ chi phí tài khoản.

Kiểm tra và review plan qua CLI trước apply. Xóa các khối vận hành khỏi IaC rồi review plan nếu muốn dọn riêng chúng; không destroy cả root medium để gỡ dashboard. Backup/restore và HTTPS tên miền tiếp tục theo [runbook medium](10-medium-n2.md) và [hồ sơ Sydney](21-medium-sydney.md).

## Tài khoản demo sau khi đổi mật khẩu admin

Theo yêu cầu của chủ dự án, hai demo Sydney dùng chung username `admin`, `teacher`, `student` và mật khẩu tương ứng. Mỗi site giữ dữ liệu và phiên đăng nhập riêng. Teacher/student trên medium được ghi danh vào `CLOUD-C01`, với quyền editing teacher/student; các user fixture `cloud_*` vẫn giữ nguyên IDs, bài nộp và điểm.

Mật khẩu được bàn giao bằng file riêng của nhóm, không đưa vào repository. Secret admin của medium được cập nhật sau khi đăng nhập HTTPS bằng mật khẩu mới đạt và mật khẩu cũ bị từ chối. Runner nạp lại secret; app role không có quyền đọc admin secret.

Kiểm thử fixture cũ sau khi đổi mật khẩu admin cần truyền **hai nguồn credential riêng**:

```bash
python -m scripts.acceptance.http_check \
  --url https://your-moodle-domain.example \
  --fixture /private/fixture.json \
  --admin-credentials /private/admin.json \
  --fixture-credentials /private/fixture-medium-accounts.json \
  --output .work/http-after-admin-rotation.json
```

File fixture credentials có dạng `{ "users": { "teacher": { "username": "...", "password": "..." }, "student_a": { ... }, "student_b": { ... }, "student_c": { ... } } }`, lưu ở nơi riêng. Các khóa ở đây là vai trò của fixture, không phải ba username demo dùng chung. Nếu bỏ tùy chọn này, chương trình giữ cách suy ra mật khẩu fixture từ **mật khẩu admin ban đầu** để tương thích các lượt seed cũ; không dùng cách đó với admin đã đổi mật khẩu.
