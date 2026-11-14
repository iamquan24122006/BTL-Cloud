# Bằng chứng nghiệm thu kỹ thuật — 14/11/2026

**Kết luận: chưa đủ điều kiện nghiệm thu đầy đủ P0+P1.** [Biên bản](../../22-technical-acceptance.md) đối chiếu đầy đủ AT-01–20, giữ riêng ca đạt, một phần, bằng chứng trước và chưa đạt. Các JSON ghi timestamp UTC.

## Kiểm tra chạy lại

- [Small dev](small-dev.json), [staging trước](small-staging-before-reboot.json)/[sau reboot](small-staging-after-reboot.json), [boot ID và đối chiếu dữ liệu](staging-reboot.json).
- [Medium 47 ca HTTPS đạt](medium-http.json), [lượt DNS lỗi được giữ nguyên](medium-http-attempt-1.json).
- [TLS/cookie/redirect và URL nhạy cảm](http-surface.json), [nginx origin từ chối header sai/thiếu](small-origin-protection.json).
- [Cron ở ba site](cron-review.json), [phân vai runtime/DB/TLS ở ba node medium](medium-runtime.json), [S3 encrypted/versioned/public-block và anonymous 403](storage-security.json).
- [96 unit tests](unit.json), [CI success đúng commit 27aae96](ci.json).

## Kết quả đối chiếu

- [Ma trận JSON](matrix.json) / [CSV](matrix.csv); [findings và điều kiện đóng](findings.json).
- [Scaling policies, alarm actions, dashboards và ALB listeners từ AWS](operational-gaps.json).
- [GUI chưa xác minh do công cụ native pipe unavailable](gui-limitation.json).
- [Billing Sydney](billing.json), [budgets](budgets.json), [inventory EC2](running-compute.json), [account access còn thiếu](other-account-access.json).
- [Tổng hợp small load lịch sử](historical-small-load.json) chỉ dẫn dữ liệu 07/11, không phải bài đo medium/public mới.
- [Summary/verdict](summary.json), [hash file](checksums.json).

Bằng chứng medium restore, lock, purge, thay node và cleanup đã chạy cùng ngày được giữ trong [bộ triển khai medium](../medium-sydney-2026-11-14/README.md); review không lặp lại các thao tác thay/hủy cluster đó. Ma trận nêu rõ các coverage chưa đủ, gồm flow ghi nghiệp vụ mới sau restore và các ca lỗi đầy đủ.

Chỉ công bố metadata/kết quả giả lập. Credential/cookie, raw backup và Terraform state/plan giữ riêng. Kiểm tra pattern AWS access key/private key không có match trong tree commit được review; đây là kiểm tra có giới hạn, không phải chứng nhận bảo mật toàn bộ lịch sử Git.
