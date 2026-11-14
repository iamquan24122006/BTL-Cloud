# Small public HTTPS — 14/11/2026

URL hoạt động: **https://d1cnnw3mivc0q5.cloudfront.net**. Distribution `EN889ZM5KZQ2S`, trạng thái Deployed; vẫn là EC2 Sydney dev cũ, không thay máy/volume/database.

| Kiểm tra | Kết quả | Evidence |
|---|---|---|
| Terraform public addon | Apply 7 added, 0 changed, 0 destroyed; CF HTTPS, managed prefix list origin, secret header và IAM scoped | [distribution.json](distribution.json), [runtime.json](runtime.json) |
| HTTPS từ máy người vận hành | Login 200, default TLS validation, Secure/HttpOnly session, HSTS, không có HTTP/localhost asset/form; HTTP301 giữ path/query | [https.json](https.json) |
| Nghiệp vụ qua public URL | Admin/teacher/student A/B login, course/file hash, enrolment/privacy, bài nộp/điểm, logout và protected paths đạt | [acceptance.json](acceptance.json) |
| Origin protection và health | Request với header thiếu/sai bị 403; basic health sau cutover | [origin-protection.json](origin-protection.json) |
| Kiểm tra code | 95 unit tests đạt; 2 Terraform small mock tests đạt; Terraform fmt đạt | [local-checks.json](local-checks.json) |

Backup trước đổi URL đã lên S3: `moodle-sydney-dev/20261114T095700Z`, SSM `ace4d3c2-d4b9-4e91-ac5d-6be96a352b69` thành công. Chính bộ backup này chưa restore-test. Origin configure thành công ở SSM `f9c61192-39cb-427f-bce1-0f39d8399b4c`. Không reset mật khẩu hoặc dữ liệu fixture.

Source mới là các thay đổi local tiếp theo baseline `2130963`, không tuyên bố GitHub CI của baseline đã chạy các thay đổi public này. Hash tệp trong `local-checks.json` để đối chiếu. State/saved plan/tfvars/secret/cookie/login HTML giữ riêng trong `.work`, không đóng gói ở đây.

TLS viewer kết thúc tại CloudFront, chặng origin HTTP được giới hạn CloudFront prefix list và header riêng; chưa phải TLS đầu cuối. Không có ALB/RDS trong addon small này. GUI desktop/mobile chưa được walkthrough mới; protocol test không thay đánh giá bố cục. [Runbook vận hành/rollback](../../20-small-public.md).
