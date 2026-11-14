# Bằng chứng bổ sung vận hành medium

Thời gian ghi trong JSON là UTC ngày 14/11/2026; một phần kiểm tra diễn ra ngày 15/11 theo giờ địa phương UTC+7. Không chứa mật khẩu, cookie hoặc SQS receipt handle.

- [Plan triển khai](deployment-plan.json): 15 create, 8 update, 0 delete/replace. Không thay thế dữ liệu hoặc compute.
- [Thông báo](monitoring-delivery.json): CloudWatch đánh giá metric thật; nhận cả ALARM và OK qua SNS/SQS. Dashboard có 11 widget, 14 alarm vận hành có cả alarm/recovery actions.
- [Dashboard](dashboard.json), [alarm thực tế](alarms.json), [inbox mã hóa/retention](inbox.json), [output](outputs.json).
- [Policy](autoscaling-policy.json), [giới hạn/trạng thái ASG](asg.json): policy tồn tại, giới hạn 2–3 app; bằng chứng này **chưa chứng nhận scale-out/in dưới tải**.
- [Tài khoản chung](common-demo-login-check.json): admin/teacher/student đăng nhập được cả small và medium; mật khẩu admin cũ của medium bị từ chối. Secret admin đã cập nhật và runner refresh thành công, credential bàn giao trong file riêng của nhóm.
- [47 kiểm tra HTTPS medium sau đồng bộ](http-after-common-accounts.json): giữ nguyên quyền/file/bài nộp/điểm của fixture `cloud_*`. Small cũng đã chạy lại acceptance thành công; journal riêng `20261114T172704Z-5ef7a771`.
- [ACM](certificate-status.json): chứng chỉ đang chờ xác minh DNS, không ghi nhận ALB HTTPS đã hoàn thành.
- [Tổng hợp](summary.json): dự án vẫn chưa được đánh dấu nghiệm thu đầy đủ. Unit local: 97 pass, 2 test quyền file Linux được skip trên Windows; Terraform mock: 2 pass.

Các kiểm tra không đạt trong quá trình thực hiện được giữ trong journal riêng; chỉ công bố kết quả đã kiểm chứng sau sửa. Mã nguồn có regression test để việc refresh secret dưới `umask 077` vẫn tạo file đúng mode `0640`. Hướng dẫn tái lập ở [vận hành medium](../../23-medium-operations.md).
