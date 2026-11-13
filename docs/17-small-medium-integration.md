# Small và medium trong một bản tích hợp

Ngày 12/11/2026: tích hợp small từ master `b1bcbe2` với medium từ khoi `82e95c9`. Giữ lịch sử hai nhánh, cấu hình/state Sydney của small, runtime medium và bằng chứng AWS cũ. Ngân sách toàn dự án giữ **150 USD** theo master. Lab medium Singapore đã cleanup ngày 10/11; hợp nhất source không tạo lại tài nguyên AWS.

## Chọn đúng môi trường

| Hợp đồng | Small | Medium |
|---|---|---|
| Cấu hình | Mặc định `config/sydney.yaml`; staging `config/sydney-staging.yaml` | Luôn truyền `--config`; mẫu `config/medium.example.yaml` chỉ dùng validate/offline |
| Terraform | `infra/small/`, local state riêng theo project/environment | `infra/medium/`, S3 backend có lockfile, key theo account/project/environment |
| Workspace | `.work/<project>-<environment>` giữ nguyên | `.work/<project>-<environment>-<account_id>-medium` |
| Preflight | Bắt buộc `--expected-account` | Dùng `account_id` trong YAML; nếu truyền `--expected-account` thì phải trùng YAML |
| Backup và command-status | Gửi đến EC2 small, hỗ trợ `--wait` | Gửi đến runner medium, hỗ trợ `--wait` |
| Health | Cloud-init và script health small | Cloud-init runner, cron/backup timers và HTTPS readiness của site đã deploy; không thay thế nghiệm thu cả hai app |
| Restore | Chỉ staging, exact confirm, `--allow-data-loss`, bộ backup small có timestamp | Chỉ staging, exact confirm, `--allow-data-loss`, prefix nguồn medium cho phép, DB/EFS đích phải trống |
| Nghiệm thu chức năng | `scripts.cloud_acceptance` chỉ nhận small | `scripts.acceptance.aws_seed`, `http_check`, `https_check` theo runbook N2 |

Không tự migrate state hay dữ liệu giữa hai preset. Plan cũ không còn hợp lệ sau thay source; tạo/review plan mới trước apply. CLI giữ kiểm tra account, hash source/config/plan, báo nguy cơ xóa/thay compute/data và yêu cầu `--allow-data-loss` khi có nguy cơ; plan được sử dụng một lần và apply dùng bản bytes đã kiểm tra để không bị đổi bởi re-plan chạy đồng thời.

```powershell
python -m src.moodle_cloud --config config/sydney.yaml validate
python -m src.moodle_cloud --config config/medium.example.yaml validate
python -m src.moodle_cloud --config config/sydney.yaml preflight --expected-account $AccountId
# Với YAML medium thật, đã chuẩn bị backend/AMI/artifact/secret/chứng chỉ:
python -m src.moodle_cloud --config config/medium.dev.yaml preflight
python -m src.moodle_cloud --config config/medium.dev.yaml health --wait
python -m src.moodle_cloud --config config/medium.dev.yaml backup --wait
```

`$AccountId` là account small đã xác minh; chọn AWS profile trước khi chạy preflight/operation. Preflight chỉ đọc prerequisite, không chứng minh toàn bộ quyền mutation. YAML medium mẫu chứa placeholder; không apply lên AWS. Xem [prerequisite và release N2](10-medium-n2.md), [cách dựng lại sau cleanup](14-n3-acceptance-guide.md).

Restore medium qua CLI dùng `--backup-uri s3://<bucket>/<restore_source_prefix>/<timestamp>`, timestamp `YYYYMMDDTHHMMSS` (hoặc có `Z`). Lệnh gọi runner restore và giữ maintenance. Sau khi kiểm tra dữ liệu/hash/fixture trên DB/EFS mới, người vận hành chạy `operation.sh resume --confirm <project>-<environment>-med` theo runbook; CLI không tự mở site sau restore. Không dùng bộ backup small cho medium hoặc chạy seeding trước restore.

## Kiểm chứng

- **89 unit test đạt** khi ghép cả hai bộ test và thêm regression cho routing runner, prefix restore, preflight/account, lựa chọn Sydney mặc định và data-loss guard medium. Không gọi AWS thật.
- Workflow CI giữ kiểm tra small (runtime, backup/restore, small/backup/budget/load Terraform) và bổ sung medium (schema, bundle, runtime hai app, Terraform medium/backend/support/builder).
- Mock test medium kiểm tra **plan**, với dữ liệu mock có sẵn từ plan. Cách này kiểm tra cả hai frontend và các assertion hạ tầng mà không tạo mock state cần destroy, giữ nguyên `prevent_destroy` EFS và deletion protection RDS. [HashiCorp: provider mocking](https://developer.hashicorp.com/terraform/language/tests/mocking).

Các bằng chứng AWS ngày 09–10/11 của medium là hồ sơ triển khai trước hợp nhất. Không tuyên bố đã chạy lại deploy/restore AWS cho commit tích hợp; việc đó cần cửa sổ lab, credential và prerequisite được tạo lại. CI/offline không thay thế nghiệm thu live, phép đo tải hoặc kiểm tra chéo N3.

## Cập nhật khoi ngày 14/11/2026

PR #2 đã merge vào master `699dfc6`; CI của cả hai lượt PR và merge commit đều thành công. Sau đó tích hợp commit N3 `2440d08` (13/11) mà vẫn giữ CLI, state và mock tests đã sửa của master.

Builder thêm tùy chọn `python -m scripts.medium_lab prepare --builder-instance-type t3.small ...`; mặc định `t3.medium` và các bước plan/review theo state hiện có giữ nguyên. Runtime integration thêm canary trên namespace Redis khác trước/sau purge MUC để phát hiện flush dữ liệu ngoài site. Load runner tạo thư mục `results` nếu generator mới chưa có; thư mục từng lượt vẫn tạo độc quyền để không ghi đè kết quả cũ.

Hồ sơ [AWS N3](evidence/aws-n3-2026-11-11/README.md) và [offline](evidence/offline-2026-11-11/README.md) giữ đúng commit, account và thời điểm riêng. Không gộp phép đo N3 với Sydney; đặc biệt 50-user r2/r3 có p95 vượt ngưỡng dù sample không báo lỗi nghiệp vụ. Medium của lượt N3 còn chờ DNS/ACM tại thời điểm ghi hồ sơ; đây không phải kiểm chứng lại live cho bản source tích hợp này.
