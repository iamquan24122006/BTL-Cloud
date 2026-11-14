# Small với URL Amazon HTTPS

## Site đã chuyển ngày 14/11/2026

**URL: https://d1cnnw3mivc0q5.cloudfront.net**

Đây là lab small Sydney dev đang có, không phải medium hoặc EC2 mới. Dữ liệu và tài khoản Moodle giữ nguyên. Không cần SSM tunnel để mở site public. Staging vẫn dùng SSM như trước.

Luồng truy cập: browser HTTPS → CloudFront → nginx trên EC2 cổng 8081 → Apache/PHP loopback 8080 → PostgreSQL/file hiện có. Origin chỉ nhận managed prefix list CloudFront và kiểm tra header riêng; credential header lưu Secrets Manager, không đi trong SSM parameters. Cache CloudFront bị tắt cho Moodle, forward cookie/query/header và tất cả HTTP method. HTTP viewer chuyển HTTPS; response headers security policy bật.

TLS kết thúc tại CloudFront. Chặng CloudFront tới nginx dùng HTTP, được giới hạn mạng và header riêng; đây là lựa chọn lab, chưa phải TLS đầu cuối/production. Muốn HTTPS ở cả origin cần hostname/certificate tương ứng và cấu hình khác. CloudFront request/transfer và Secrets Manager có thể phát sinh phí; đây không phải cấu hình HA.

## Kiểm chứng

- Terraform public root: 7 tài nguyên thêm, không thay EC2/EBS hoặc quản lý DB.
- 95 unit test và 2 Terraform mock test small đạt, gồm guard account/confirmation, plan hash/single-use và giữ SG public khi render small.
- HTTPS từ máy người vận hành đạt: TLS mặc định có kiểm chain/hostname; HTTP 301 giữ path/query; Secure/HttpOnly cookie; HSTS; không có asset/form HTTP hoặc localhost trong trang login.
- Verifier nghiệp vụ trên site sau chuyển URL đạt các role, course/file hash, bài nộp/điểm, privacy, protected paths và logout.
- [Evidence public](evidence/small-public-2026-11-14/README.md). Đây là kiểm thử protocol/nghiệp vụ; chưa thay thế walkthrough GUI desktop/mobile.

## Cấu hình và state

Giữ `config/sydney.yaml` là cấu hình bootstrap gốc với `wwwroot: http://localhost:8080`; không đổi user-data chỉ để chuyển URL vì có thể replace EC2 và mất dữ liệu. Frontend được quản lý bởi `infra/small_public/` và `scripts.small_public`, state riêng tại `.work/<project>-<environment>/public/`.

Sau activate, `.work/<project>-<environment>/public-runtime.json` lưu URL/distribution/SG công khai, không có secret. CLI đọc marker để `status` hiển thị public URL và `render` giữ SG origin khi lập plan small về sau. Không xóa marker hoặc state chỉ để xử lý drift; addon gắn SG vào cùng ENI nên cần giữ cả hai phần state đồng bộ. Các chốt replacement/data-loss của small vẫn áp dụng; review AMI/user-data trước mọi apply.

`.work/.../public/` có origin token, tfvars, saved plans và state nhạy cảm. Không đưa các file này vào Git hoặc gói bàn giao công khai. EC2 cần đọc đúng secret origin qua policy IAM riêng; không cấp quyền đọc các secret khác.

## Lệnh vận hành

PowerShell, Python/PyYAML/Terraform/AWS CLI đã sẵn sàng, profile đúng account:

```powershell
$env:AWS_PROFILE = 'moodle-project'
$Config = 'config/sydney.yaml'
$AccountId = '<ACCOUNT_ID_CUA_LAB>'
python -m scripts.small_public --config $Config --expected-account $AccountId status
```

Cho small lab khác đã triển khai thành công: chọn đúng YAML/account rồi chạy `plan`, review, `apply --confirm <project>-<environment>`. Công cụ từ chối account/tag/plan/source thay đổi và các public plan có delete/replace. Apply tạo frontend, đợi CloudFront deploy, backup mới rồi cấu hình origin. `activate --confirm ...` dùng để retry bước host sau partial failure; không gọi apply lặp hoặc tái dùng manifest đã consumed.

Nếu EC2 bị stop/start và public DNS đổi, lập/review public plan mới để cập nhật origin rồi activate/kiểm tra lại. CloudFront URL ổn định khi distribution vẫn được giữ; origin DNS tự cấp của EC2 không phải địa chỉ cố định.

## Rollback về SSM

```powershell
python -m scripts.small_public --config $Config --expected-account $AccountId disable --confirm moodle-sydney-dev
```

Lệnh bỏ public override khỏi config hiện tại, giữ DB credential, cập nhật deploy settings về URL gốc, tắt nginx public route, purge cache và kiểm tra health. Không restore DB hoặc tự xóa AWS resources. Sau đó mở SSM tunnel theo runbook cũ; các browser session cần đăng nhập lại khi đổi hostname.

Rollback chưa được thực thi trên site đang demo trong lượt bàn giao này; unit test đã kiểm tra confirm sai không gửi remote command. Chỉ dùng khi thực sự muốn trả site về chế độ SSM.

Để ngừng phí frontend: rollback trước, rồi lập/review saved destroy plan cho **root small_public với đúng state/tfvars**; tuyệt đối không destroy root small để chỉ gỡ frontend. Giữ token/state cho tới khi cleanup hoàn tất. Secret mặc định có recovery window 7 ngày. Không coi `disable` ứng dụng là đã dọn CloudFront/secret.

Tài liệu AWS đã đối chiếu: [origin custom headers](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/add-origin-custom-headers.html), [giới hạn origin bằng prefix list và header](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html). Nguyên tắc được áp dụng cho nginx origin của lab; không có ALB trong small.
