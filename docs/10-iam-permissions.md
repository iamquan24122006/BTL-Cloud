# Bổ sung quyền cho lab mới

Người thực hiện cần quyền quản trị IAM trong account `987673221265`. User nhận quyền là `mquann`. Policy bổ sung phục vụ tiếp tục deploy và vận hành SSM cho `moodle-lab-v2-dev`, sử dụng cùng các quyền EC2 hiện có của user.

## Thao tác trong AWS Console

1. Đăng nhập account `987673221265` bằng tài khoản có quyền quản trị IAM.
2. Mở **IAM → Policies → Create policy → JSON**.
3. Thay nội dung editor bằng toàn bộ file [moodle-lab-v2-permissions.json](../config/iam/moodle-lab-v2-permissions.json).
4. Chọn **Next**, đặt tên `MoodleLabV2DeployAndSSM`, xem kết quả validation rồi chọn **Create policy**.
5. Vào **IAM → Users → mquann → Permissions → Add permissions → Attach policies directly**.
6. Tìm `MoodleLabV2DeployAndSSM`, đánh dấu, chọn **Next → Add permissions**.

Đây là customer managed policy. Bước tạo policy và bước gắn vào user là hai thao tác riêng. Hướng dẫn chính thức: [tạo policy trong JSON editor](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_create-console.html), [thêm quyền cho identity](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_manage-attach-detach.html).

## Phạm vi của policy

- `CreateAndReadLabRoles` và `CreateAndReadLabInstanceProfiles`: tạo, đọc và gắn tag cho role/profile có tên bắt đầu `moodle-lab-v2-dev-` trong account này. Tên có hậu tố do Terraform sinh.
- `AttachOnlySSMCoreToLabRoles`: chỉ cho gắn managed policy `AmazonSSMManagedInstanceCore` vào các role của lab. Điều kiện dùng `iam:PolicyARN` theo [hướng dẫn IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_controlling.html).
- `PassOnlyLabRolesToRequiredServices`: PassRole giới hạn theo prefix role và các service EC2/SSM mà baseline/reference yêu cầu.
- `ReadSSMStatusInLabRegion`: đọc thông tin managed node và kết quả lệnh trong Singapore. Hai action này không hỗ trợ ARN tài nguyên cụ thể nên dùng `Resource: "*"` cùng giới hạn region.
- `OperateOnlyTaggedLabNodes`: gửi lệnh, mở session và kiểm tra kết nối trên EC2 trong account/region này, chỉ khi có đồng thời tag `Project=moodle-lab-v2` và `Environment=dev`.
- `UseRunShellCommandDocument` và `UseShellAndPortForwardSessionDocuments`: cho dùng các document cụ thể để chạy shell, mở shell session và chuyển tiếp cổng. Quyền document tách riêng khỏi điều kiện tag của máy.
- `ManageOwnSessions`: mở data channel, tiếp tục và kết thúc session thuộc chính user gọi API, theo [ví dụ Session Manager của AWS](https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-restrict-access-quickstart.html).

Quyền IAM được lấy từ baseline của IAM Policy Autopilot rồi thu hẹp theo các resource type trong Service Authorization Reference. Quyền SSM của người vận hành được đối chiếu với cùng nguồn và ví dụ AWS. Bản này bổ sung quyền cho bước tạo mới/đọc/tag và thao tác SSM; quyền hủy IAM resource và backup S3 không thuộc phạm vi bản bổ sung này.

Đã kiểm tra JSON, tên action, phạm vi ARN và kích thước policy tại máy cục bộ; chưa gắn vào AWS và chưa xác nhận quyền hiệu lực sau khi admin cấp. Sau khi gắn, kiểm tra lại bằng profile `mquann`, lập plan mới với `--config config/small-new.yaml`, rồi tiếp tục từ state hiện tại.
