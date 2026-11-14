# Chuẩn bị release medium và kiểm tra GUI — 14/11/2026

## Kết quả mới

- Đã tạo checkout sạch riêng tại commit `2130963f7fc3fd76007498ab766a0942b9db3f59`; không sửa lab small hoặc trộn tài liệu đang chỉnh vào release.
- Build image `moodle-medium:release-2130963` thành công, revision đúng source, Linux amd64. [Metadata image](build.json) là thông tin image **cục bộ**, chưa phải digest đã publish ở ECR.
- Bundle SHA-256: `a5ec8210a307fc409fdb8caab503da59e04f8674754eae81c9072a9d30625604`; Moodle upstream `215f44380bdc3ccf852a3a22e34f8423ff64033a` được kiểm tra khi build.
- [Integration runtime](runtime-report.json) có `status: passed`: PostgreSQL TLS, Redis TLS, hai app node, DB TLS proof, MUC/file xuyên node, lock tranh chấp, login xuyên node, purge giữ session và namespace khác, readiness 503 khi mất session dependency và phục hồi sau restart, maintenance gate chặn truy cập.
- Container/network/volume thử nghiệm được script dọn khi kết thúc. Private fixture credential và log thô không đưa vào evidence này.

Đây là kiểm thử container cục bộ trên image release thật, chưa kiểm chứng EFS, IAM, SSM, ALB, ASG hoặc cloud restore của một môi trường medium mới. Chi tiết tham chiếu ở [release.json](release.json).

## Giao diện

SSM tunnel tới dev Sydney đã mở thành công tại `http://localhost:8080`. Công cụ trình duyệt không có browser host; thử mở tab trả `browser access host is unavailable`. **Chưa kiểm tra được bố cục GUI và chưa có ảnh walkthrough mới.** Không dùng HTTP verifier hoặc kết quả integration thay cho nghiệm thu GUI.

## Phụ thuộc để triển khai AWS

- Phiên Sydney còn hợp lệ; chưa có ACM certificate và Route 53 zone trong kết quả list tại account đã kiểm. Quota On-Demand Standard EC2 Sydney là 16 vCPU tại thời điểm đọc; chưa chứng nhận đủ mọi quota/quyền mutation.
- Đã gửi nhóm câu hỏi chọn account và tên miền/quyền DNS. Chưa có câu trả lời; chưa cấp certificate, tạo secret hoặc apply tài nguyên medium.
- `prepare` cho phương án Sydney đã hoàn tất tại `.work/medium-release-src/.work/medium-live/`. Gói AWS CLI kiểm ZIP integrity đạt, CloudWatch Agent đúng định dạng Debian archive; cả hai khớp hash đã ghim. AMI Canonical, source/gói EFS và hash ở [dependency-pins.json](dependency-pins.json). Saved plan chỉ được ghi hoàn tất sau khi Terraform trả thành công; không đưa state/plan vào hồ sơ công khai.
- Chưa publish ECR/S3 artifact và chưa có môi trường medium mới để nghiệm thu live.

### Saved plan prerequisite đã tạo

Phương án dùng account Sydney hiện đang kết nối, region `ap-southeast-2`, project riêng `moodle-medium`:

| Root | Tạo | Sửa | Xóa | Bằng chứng metadata |
|---|---:|---:|---:|---|
| medium_support | 20 | 0 | 0 | [support-plan.json](support-plan.json) |
| medium_builder | 10 | 0 | 0 | [builder-plan.json](builder-plan.json) |

Terraform plan thành công; không apply. Root support chuẩn bị bucket/ECR/secret metadata, builder là máy tạm `t3.small` phục vụ AMI. Đây chưa phải main plan ALB/ASG/RDS/EFS/Redis và chưa phải dự toán toàn topology. Main plan còn cần account được nhóm chọn, certificate/DNS và những reference chỉ có sau khi prerequisite thực sự được tạo.

Saved plan, state bootstrap và log thô giữ riêng tại `.work/medium-release-src/.work/medium-live/`. Không dùng root của lab small hoặc bỏ guard để tiếp tục. Nếu đổi account/project/region hoặc source, phải prepare/plan lại; không apply nguyên kế hoạch Sydney sang account khác.

Để tiếp tục, nhóm chọn account đích và hostname có quyền DNS. Nếu dùng lại hostname Dynu, cần xác nhận quyền quản lý và hoàn tất bản ghi ACM validation; không gửi mật khẩu qua chat. Các bước sau là prepare/plan prerequisite, build AMI, publish artifact/secret reference, preflight/plan/apply main, release và nghiệm thu live theo [runbook N2](../../10-medium-n2.md).
