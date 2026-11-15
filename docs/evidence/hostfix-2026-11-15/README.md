# Deploy host bundle và sửa quyền cron medium — 15/11/2026

Lượt triển khai bản sửa vận hành trên lab Sydney (`828676179987`, `ap-southeast-2`). Mục tiêu: đưa mã chạy trên host đang có trong repo lên medium, cấp `TRUNCATE` cho role runtime và xác nhận lại nghiệp vụ. Không đổi cấu hình Moodle, image, database hay dữ liệu nghiệp vụ.

**Kết luận trong phạm vi lượt này:** bản sửa đã lên môi trường live, tag task chạy lại thành công, 47/47 ca HTTPS đạt sau deploy và plan cuối không drift. Đây không phải nghiệm thu đầy đủ P0+P1; các mục GUI, benchmark và bàn giao vẫn ở [danh sách công việc](../../24-remaining-work.md).

## Vấn đề phát hiện lại trên live

`\core\task\tag_cron_task` chưa từng chạy thành công (`lastruntime=0`, `faildelay=7680`), và role `moodle_runtime` **không có `TRUNCATE` trên bất kỳ bảng nào trong 494 bảng** của schema `public`. Runtime đang chạy là bundle cũ (`operations.py` `0d64cfe3…`), không có nhánh cấp `TRUNCATE`. Vì vậy cron tại `06:32Z` dừng ở `cron-audit.php`, để lại `worker-pending.json` và chặn các operation sau.

## Thay đổi đã phát hành

| Hạng mục | Giá trị |
|---|---|
| Host source commit | `ae885c1d238f966a9fe36a9e7698a5dded43f43e` |
| Bundle key mới | `releases/2130963f…/host-ae885c1d238f.tar.gz` (không ghi đè key cũ `medium.tar.gz`) |
| Bundle SHA-256 | `f135174dc8a4d7b192f81c558211d162825d74ca88f59a942e9e155e597ea323` |
| Release tag / image label | `2130963f7fc3fd76007498ab766a0942b9db3f59` — **không đổi** |
| Image digest | `…moodle@sha256:5eebbc7b…` — **không đổi** |

Bootstrap kiểm tra label image bằng `artifact.release`, nên khi chỉ đổi mã chạy trên host thì giữ nguyên image/release và phát hành bundle ở key mới có SHA riêng; hai nguồn được ghi tách biệt trong [bundle.json](bundle.json).

## Trình tự và kết quả

1. [Plan](plan-before.json): 1 create, 6 update, 1 delete/replace (runner), `data_loss_risk=true` do thay EC2 runner; app giữ nguyên release nên gate không đóng.
2. [Apply](apply.json): `1 added, 6 changed, 1 destroyed`; runner mới `i-0d43470f88eb13a58`, ASG refresh `Successful` lúc `07:07:40Z`.
3. [Runner nhận bundle](runner-node.json) và [hai app sau refresh](app-nodes.json): SHA thực tế bằng SHA mong đợi, `operations.py` `a77536d8…`, app chỉ chạy `moodle-web`, timer cron/backup tắt trên app.
4. [Recovery review](worker-recovery.json): container worker không còn, 0 session DB, marker được gỡ theo đúng quy trình; timer cron dừng trong cửa sổ release.
5. [Release](release.json): maintenance `07:08:46Z`, backup baseline `20261115T070856`, upgrade không cần đổi version, hoàn tất `07:09:13Z`. Cửa sổ chặn ghi khoảng 27 giây.
6. [Sau sửa](cron-after.json): tag task chạy trực tiếp thành công, `faildelay=0`, `scheduled_with_faildelay=0`, `adhoc_queued=0`, **494/494 bảng có `TRUNCATE`**, cron operation kết thúc `cron-completed-and-task-audit-clear`, timer bật lại.
7. [Nghiệp vụ](medium-http.json): 47/47 ca HTTPS trên tên miền đạt sau deploy.
8. [Plan cuối](final-plan.json): `No changes`, không drift.
9. [Inventory](inventory.json): 2 app healthy, refresh Successful, 17 alarm đều có action, policy target 200.

## Small

- [Hotfix host](small-hotfix.json): `verify_backup.py` trên dev/staging từ `d2cbdbad…` → `59063f33…`, khớp file trong repo; không thay EC2, không mất dữ liệu.
- [Backup dev](small-backup.json): chạy đủ, upload `s3://moodle-sydney-backup-828676179987/moodle-sydney-dev/20261115T071316Z`, manifest `consistency: single node, web stopped, cron drained`, `restore_tested: false`, timer và web bật lại.
- [Đăng nhập demo](small-logins.json): admin/teacher/student đều vào `/my/` qua HTTPS.

## Giới hạn

- Không chạy lại GUI walkthrough; HTTP không thay kiểm tra bố cục.
- Không benchmark lại sau deploy; số liệu tải cũ giữ nguyên phạm vi.
- Ảnh/bundle cũ vẫn được giữ để rollback; rollback chưa được diễn tập trong lượt này.
- Không xác nhận chi phí các account N2/N3 hoặc chữ ký của nhóm.

Bộ JSON trong thư mục này không chứa password, cookie, state/plan Terraform hay raw backup; [checksums.json](checksums.json) chỉ phủ các JSON công bố.
