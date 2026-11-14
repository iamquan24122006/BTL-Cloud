# Đặc tả tính năng và tiêu chí nghiệm thu Moodle Cloud

Ngày lập: 03/11/2026. Phạm vi kỹ thuật: small (P0) và medium (P1). Nhóm hiện có **4 thành viên** theo kế hoạch đã chốt; N1/N2/N3 trong tài liệu này là ba mảng công việc, không phải số thành viên. Phân công A/B/C/D nằm trong [kế hoạch nhóm](00-project-plan.md).

**Đối chiếu mới nhất 14/11:** [ma trận nghiệm thu](18-project-closeout.md). Các bảng “hiện trạng” và mục 1.2 bên dưới giữ snapshot ngày lập đặc tả, không còn mô tả trạng thái source/cloud hiện tại. Tiêu chí đích vẫn được giữ để không tự hạ phạm vi nghiệm thu.

## 1. Cách sử dụng tài liệu

Tài liệu mô tả **hệ thống cần làm được gì, phải xử lý lỗi thế nào và cần bằng chứng nào để kết luận hoàn thành**. Đây là đặc tả đích để triển khai và nghiệm thu, không phải tuyên bố các tính năng đã chạy trên AWS.

Mỗi yêu cầu có mã để liên kết với task, thay đổi mã nguồn, test và bằng chứng. Nhóm dùng các trạng thái: `Chưa làm`, `Đang làm`, `Chờ phụ thuộc`, `Chờ nghiệm thu`, `Đạt`, `Không đạt`. Chỉ ghi `Đạt` khi đã chạy trên môi trường tương ứng và lưu bằng chứng.

Quy ước trách nhiệm:

- **N1:** Người 1, phụ trách small và công cụ triển khai small.
- **N2:** Người 2, phụ trách medium và công cụ triển khai medium.
- **N3:** Người 3, phụ trách kiểm thử, quy trình/script vận hành, đo tải, chi phí và tổng hợp bằng chứng.
- Người phụ trách triển khai sửa lỗi trong phần mình. N3 kiểm tra lại; một lần thử chưa chạy hoặc thiếu môi trường phải ghi `Chờ nghiệm thu`, không ghi `Đạt`.

### 1.1. Phạm vi bắt buộc và giới hạn

| Phạm vi | Phải hoàn thành | Không tự suy rộng thành |
|---|---|---|
| P0 — Small | Cài tay; Terraform/CLI; Moodle trên một EC2; chức năng học tập; cron; S3 backup; restore sang máy mới; reboot; đo tải; hồ sơ bàn giao | Production, HA hoặc bảo đảm một số lượng người dùng chưa đo |
| P1 — Medium | Hai app node, ALB HTTPS, RDS, EFS, Redis, ASG; cron/release runner; state chung có khóa; quan sát; backup/restore nhiều node; đo so sánh | HA toàn hệ thống khi DB/cache/egress còn điểm lỗi đơn |
| P2 — Ngoài phạm vi bắt buộc | Large, Multi-AZ cho mọi phụ thuộc, failover DB/cache nâng cao, CDN, plugin bên ngoài, nâng cấp tự động | Điều kiện phải có để chốt P0 + P1 |

Tính năng học tập dùng Moodle chuẩn và theme Boost; không phải viết lại LMS. Đóng góp chính của đồ án là quy trình triển khai, vận hành, phục hồi và đánh giá có thể tái lập. Thanh toán, ứng dụng di động riêng, AI, SSO và email giao dịch không nằm trong phạm vi này.

### 1.2. Trạng thái được đối chiếu với repository

| Hạng mục | Bằng chứng đã ghi nhận | Phần còn phải hoàn thành |
|---|---|---|
| Docker/PHP và Moodle cục bộ | Nhật ký ngày 29/10/2026 ghi build, login, course/file, cron và dump/archive/restore local đạt; 29 unit test đạt ở lượt đó | Không thay thế kiểm thử EC2, systemd, SSM, S3, bài nộp/chấm điểm và đo tải |
| Terraform/CLI small | Có mã trong `infra/small/`, `src/moodle_cloud.py` và script liên quan | Kiểm chứng thực tế trên AWS và sửa lỗi phát hiện |
| Lab mới | Nhật ký ghi 6 tài nguyên mạng đã tạo; lần apply trước bị từ chối `iam:CreateRole`; chưa tạo EC2 mới | Kiểm tra lại quyền/trạng thái AWS, lập plan mới và tiếp tục đúng state |
| S3 backup/restore small | Có script backup và runbook restore; cấu hình lab mới để trống bucket | Bucket/quyền, lịch backup, thực thi và restore drill trên AWS |
| Medium | Có thiết kế trong tài liệu kiến trúc | Chưa có root/module Terraform và runtime medium hoàn chỉnh |
| CI | Có workflow kiểm tra cục bộ, không deploy AWS | Chưa có bằng chứng một lượt GitHub Actions đạt trong nhật ký |

Trạng thái này dựa trên mã và nhật ký đã lưu, **không phải kết quả gọi AWS lại ngày 03/11/2026**. Các phiên bản đang ghim là baseline của repo: Moodle 4.5.15, PHP 8.3, PostgreSQL 16, host Ubuntu 26.04. Trước đợt triển khai cần kiểm tra lại khả năng dùng baseline; nếu đổi phiên bản phải cập nhật đồng bộ code, test và tài liệu, không đổi âm thầm.

## 2. Người dùng và bộ dữ liệu nghiệm thu

### 2.1. Vai trò

| Vai trò | Cần làm được | Giới hạn phải kiểm tra |
|---|---|---|
| Người vận hành | Chọn YAML, plan/apply, xem trạng thái, mở SSM, backup/restore, xem log, cleanup | Chỉ thao tác đúng account/môi trường; không đưa credential vào Git hoặc YAML |
| Moodle admin | Quản lý user, course, enrolment, cấu hình và tác vụ nền | Mật khẩu khởi tạo phải đổi; thông tin quản trị không xuất hiện trong bằng chứng chia sẻ |
| Teacher của course | Quản lý nội dung, tạo assignment, xem/chấm bài trong course được giao | Không được cấp quyền quản trị toàn site chỉ để hoàn thành bài test |
| Student của course | Xem nội dung được phép, tải học liệu, nộp bài, xem điểm/phản hồi của mình | Không sửa course, tự đổi vai trò, chấm điểm hoặc đọc bài riêng của người khác |
| Người chưa đăng nhập | Thấy trang đăng nhập hoặc nội dung public đã cấu hình rõ | Không đọc được file course riêng, bài nộp hoặc trang quản trị |

### 2.2. Fixture chuẩn

Chuẩn bị hai course riêng tư `CLOUD-C01` và `CLOUD-C02`, một admin, một teacher của C01, hai student A/B của C01 và một student C chỉ thuộc C02. Không bật guest access cho fixture. Tạo một học liệu, một assignment chấm điểm riêng từng người và hai bài nộp có nội dung khác nhau.

Lưu tên fixture, enrolment, thiết lập assignment, ID đối tượng, điểm/phản hồi mẫu và SHA-256 của các file. Password và cookie giữ riêng. Small/medium dùng cùng fixture khi so sánh. Nếu có restore từ fixture nguồn, đối chiếu các ID được bảo toàn trong bản phục hồi; không yêu cầu ID trùng giữa hai site được seed độc lập.

## 3. Tính năng học tập phải hoạt động trên cả small và medium

Chủ trì cấu hình: N1 cho small, N2 cho medium. N3 chuẩn bị và chạy nghiệm thu. Tất cả yêu cầu LMS dưới đây thuộc P0, được chạy lại trên P1 và sau restore.

### LMS-01 — Đăng nhập, đăng xuất và phiên người dùng

**Hành vi:** admin, teacher và student đăng nhập bằng tài khoản riêng; tài khoản sai nhận lỗi; logout kết thúc phiên. Người chưa đăng nhập mở URL riêng tư được yêu cầu xác thực.

**Điều kiện đạt:** đúng người dùng/role sau login; login sai không tạo phiên hợp lệ; sau logout không truy cập được tài nguyên riêng tư bằng phiên vừa kết thúc. Kiểm tra bằng request mới, không chỉ nhìn trang đã nằm trong cache trình duyệt. Cookie/token/password không xuất hiện trong log được chia sẻ.

**Bằng chứng:** kết quả login đúng/sai/logout và truy cập URL riêng tư, cho cả ba vai trò. Medium cần thêm MED-05.

### LMS-02 — Course, enrolment và nội dung

**Hành vi:** admin tạo course, gán teacher và enrol student; teacher tạo section/nội dung/học liệu; student đọc phần được cấp quyền.

**Điều kiện đạt:** teacher C01 cập nhật được nội dung C01; student A/B thấy nội dung đã xuất bản; student C không thuộc C01 không đọc được nội dung riêng C01. Kiểm tra cả URL trực tiếp, không chỉ việc ẩn menu.

**Bằng chứng:** cấu hình enrolment, nội dung mẫu và kết quả truy cập của người có/không có quyền.

### LMS-03 — Upload/download có kiểm tra tính toàn vẹn

**Hành vi:** teacher đăng học liệu; student được phép tải đúng file. Ghi rõ các giới hạn upload của Moodle, PHP và web server trong cấu hình nghiệm thu.

**Điều kiện đạt:** file hợp lệ tải lại có SHA-256 trùng nguồn; có ít nhất một file văn bản và một file nhị phân; tên tiếng Việt/khoảng trắng hoạt động. File lớn hơn giới hạn đã công bố bị từ chối rõ ràng, không tạo học liệu/bài nộp giả thành công. Người chưa đăng nhập hoặc không có quyền không lấy được nội dung file bằng URL trực tiếp.

**Bằng chứng:** tên/kích thước/hash nguồn và đích, giới hạn cấu hình và kết quả ca vượt giới hạn. Không coi mọi HTTP 200 là tải đúng file: trang login HTML cũng có thể trả 200.

### LMS-04 — Student nộp bài, teacher chấm và phản hồi

**Hành vi:** teacher tạo assignment có hạn nộp và chính sách nộp rõ ràng; student A/B nộp file riêng; teacher xem, chấm và phản hồi; từng student xem kết quả của mình.

**Điều kiện đạt:** teacher tải đúng từng bài, hash khớp; điểm/phản hồi lưu sau tải lại trang; student A không xem bài riêng/điểm riêng của B trong fixture không cho chia sẻ. Student không chỉnh nội dung assignment hoặc điểm. Việc nộp lại tuân theo cấu hình assignment đã ghi, không tự yêu cầu cho sửa sau khi khóa bài.

**Bằng chứng:** thiết lập assignment, trạng thái bài nộp, hash, điểm/phản hồi và ca truy cập trái quyền. Đây là phần chưa được chứng minh bởi bài integration local hiện có.

### LMS-05 — Tác vụ nền có kết quả thực tế

**Hành vi:** tác vụ scheduled/ad hoc trong phạm vi thử nghiệm được xử lý; có thời điểm chạy thành công và log đối chiếu được.

**Điều kiện đạt:** không chỉ timer active; phải có lần cron hoàn tất và một tác vụ phù hợp được thực thi. Kiểm tra task failure/backlog, kể cả trường hợp tiến trình cron trả exit code 0 nhưng có task lỗi. Không dùng gửi email làm bằng chứng bắt buộc khi chưa cấu hình dịch vụ email.

**Bằng chứng:** journal/log đã lọc, trạng thái scheduled/ad hoc task và dấu thời gian. Medium cần MED-08.

### LMS-06 — Trải nghiệm sử dụng sẵn sàng cho demo

**Hành vi:** site có tên, course có tiêu đề/nội dung thật cho fixture, luồng đăng nhập → course → học liệu → bài nộp → điểm đi xuyên suốt trên Moodle chuẩn.

**Điều kiện đạt:** không có PHP warning/stack trace trên luồng nghiệm thu; URL/link/ảnh hoạt động; trang đọc được ở desktop và màn hình hẹp; thông báo sai mật khẩu, hết phiên, quá dung lượng và maintenance hiểu được. Không để tài khoản demo có quyền admin ngoài nhu cầu. Chỉ ghi các thiết bị/trình duyệt đã thử, không tuyên bố tương thích toàn bộ.

**Bằng chứng:** một walkthrough đủ luồng và ảnh các trạng thái lỗi chính đã lọc thông tin nhạy cảm. Không yêu cầu xây theme mới.

## 4. Công cụ triển khai và quản lý cấu hình

### CLI-01 — Validate và render offline

**Phạm vi/chủ trì:** P0: N1; mở rộng P1: N2; kiểm thử: N3.

**Hành vi đích:** kiểm tra YAML trước khi tạo tài nguyên; bắt khóa trùng/lạ, thiếu trường, sai kiểu/phạm vi, tên không an toàn, trường secret và preset chưa hỗ trợ. Thông báo nêu trường cần sửa và trả exit code khác 0. `validate`/`render` không gọi AWS.

**Điều kiện đạt:** test âm không tạo tài nguyên; dev/staging xuất cấu hình riêng; mọi input đi vào subprocess bằng argument array. Khi hỗ trợ medium phải có schema cho các thông tin thực sự cần, như domain/certificate, network, data service, artifact và backend; giữ việc từ chối production/large nếu chưa triển khai.

**Hiện trạng:** có validate/render small và test đầu vào; chưa có schema medium. Cấu hình medium mẫu chỉ được coi dùng được sau khi CLI và Terraform hỗ trợ thật.

### CLI-02 — Kiểm tra điều kiện trước deploy

**Hành vi đích:** hướng dẫn hoặc script preflight kiểm tra phiên AWS, account, region, công cụ cần dùng và các quyền/thành phần cần thiết cho bước sắp chạy. Có thể tách khỏi `doctor`; không bắt buộc một tên lệnh mới.

**Điều kiện đạt:** thiếu tool/phiên đăng nhập hoặc sai account bị phát hiện trước mutation. Không gọi tạo tài nguyên chỉ để thử quyền. Nếu không được phép simulate policy hoặc không thể xác minh quyền đầy đủ, ghi `chưa xác minh`; chỉ API thực tế mới chứng minh thao tác được phép. Phân biệt người deploy, role EC2 và người mở SSM.

**Hiện trạng:** `doctor` hiện chỉ kiểm tra tool trong PATH; không kiểm tra phiên hoặc IAM. Không mô tả kết quả `doctor` như chứng nhận đủ quyền AWS.

Bản bổ sung IAM trong tài liệu 10 chưa bao gồm quyền hủy IAM resource và backup S3. Phải kiểm tra/cấp đúng các quyền cho bước backup, restore và cleanup khi triển khai, không mặc định policy xử lý `CreateRole` đã bao phủ toàn bộ vòng đời lab.

### CLI-03 — Plan review và apply đúng kế hoạch

**Hành vi đích:** saved plan đi kèm identity/account, cấu hình và fingerprint các tệp ảnh hưởng deploy. Người vận hành nhìn được số tạo/sửa/xóa/thay thế, tài nguyên dữ liệu và chi phí có thể phát sinh trước apply.

**Điều kiện đạt:** từ chối apply khi config/source/lockfile/plan/account đổi hoặc confirm sai. Manifest dùng một lần kể cả apply lỗi; partial apply phải giữ state, lập plan mới và review lại. Không dùng `-target` hoặc bỏ qua kiểm tra để che dependency sai.

**Hiện trạng:** đã có các chốt chính cho small. Medium phải mở rộng fingerprint tới root/module/script/artifact reference có liên quan, tránh chỉ hash `infra/small` như hiện tại. Việc fingerprint đúng không thay thế kiểm tra môi trường AWS thực tế.

### CLI-04 — State riêng và cộng tác có khóa

**P0:** tiếp tục lab mới đúng `.work/moodle-lab-v2-dev/`; không dùng state lab cũ/rỗng để kết luận không có tài nguyên AWS. Sao lưu state trước thao tác quản lý backend.

**P1:** backend S3 riêng cho state, bật mã hóa/versioning và khóa, tách key theo account/project/environment/preset hoặc cơ chế cô lập tương đương. Không dùng cùng state cho small và medium. Sửa CLI đang ép local backend trước khi migrate; có quy trình bootstrap backend và phục hồi state độc lập.

**Điều kiện đạt:** thử hai phiên cùng ghi thì một phiên phải chờ hoặc bị từ chối bởi khóa; không tạo hai lượt apply đồng thời. Đối chiếu lineage/serial và inventory khi migrate, giữ bản sao có quyền hạn chế. Terraform S3 hỗ trợ khóa bằng `use_lockfile`; quyền lock phải được cấp theo cấu hình thực tế. [Tài liệu HashiCorp](https://developer.hashicorp.com/terraform/language/backend/s3).

### CLI-05 — Phân biệt hạ tầng, ứng dụng và công việc bất đồng bộ

**Hành vi đích:** kết quả `status` cho biết đang báo outputs hạ tầng; health và nghiệp vụ được kiểm tra riêng. Backup qua SSM trả command ID để theo dõi, không ghi thành công ngay khi nhận ID.

**Điều kiện đạt:** có quy trình kiểm tra command đến trạng thái cuối, timeout/lỗi có log và exit code đối chiếu. Terraform apply xong nhưng cloud-init/health lỗi phải ghi triển khai ứng dụng chưa đạt. Không bắt buộc viết CLI health mới nếu runbook/script hiện có đáp ứng.

### CLI-06 — Destroy và thay thế tài nguyên có kiểm soát

**Hành vi đích:** destroy dùng saved destroy plan, đúng confirm môi trường và xác nhận mất dữ liệu; kiểm tra backup/restore trước khi hủy dữ liệu cần giữ.

**Điều kiện đạt:** plan apply không dùng thay destroy plan và ngược lại; không xóa state để quên tài nguyên; sau cleanup có inventory đối chiếu. Mọi EC2 replacement ở small phải được xem là có thể mất DB/file trên root EBS, kể cả replacement do AMI/user-data hoặc đổi `backup_bucket`.

## 5. Small — yêu cầu hạ tầng và runtime

Chủ trì: N1; N3 nghiệm thu và vận hành phối hợp. Tất cả mục SMALL thuộc P0.

| Mã | Tính năng cần hoàn thiện | Điều kiện đạt và bằng chứng |
|---|---|---|
| SMALL-01 | EC2 và mạng đúng cấu hình | VPC/subnet/route hoạt động; SG không ingress; quản trị và web qua SSM; IMDSv2 bắt buộc; EBS gp3 mã hóa. Ghi account/region/AMI/instance type/volume thực tế, không chỉ giá trị YAML. |
| SMALL-02 | Cài trên Ubuntu sạch | Host đúng baseline đã chọn; PHP chạy trong container, PostgreSQL đúng major; cloud-init và bootstrap hoàn tất; web/CLI/cron dùng cùng image ID. Lưu phiên bản và log cài đặt thực tế. |
| SMALL-03 | Cài lại sau thành công và xử lý cài dở | Gọi bootstrap lại sau cài thành công không reset dữ liệu hoặc tạo admin mới; health vẫn đạt. Cài dở phải dừng với log và hướng phục hồi/dựng lại; không tuyên bố script tự sửa mọi trạng thái lỗi. |
| SMALL-04 | Systemd, cron và reboot | Web/DB/cron khởi động theo dependency; sau reboot staging tự hoạt động; kiểm tra LMS-01 đến LMS-05. Timer active chưa đủ nếu task không chạy. |
| SMALL-05 | Quyền file và bảo vệ mã nguồn | Web user ghi được dataroot/cache cần thiết nhưng không sửa code/config; `moodledata` ngoài webroot. Request `config.php`, `.git` và đường dẫn nhạy cảm không lộ nội dung; DB không mở Internet. |
| SMALL-06 | Cài tay và tự động đều tái lập | Có một lượt cài tay và một lượt tự động trên EC2 sạch với cấu hình/dataset đối chiếu được; ghi thời gian, thao tác và lỗi. Ghi AMI thực tế vì lookup hiện chọn bản mới nhất; không đòi plan luôn rỗng khi AMI thay đổi. |

Small có public IPv4 để phục vụ kết nối outbound theo thiết kế hiện tại nhưng không mở web public. URL nghiệm thu là `http://localhost:8080` qua tunnel; không yêu cầu domain/HTTPS public cho small.

Bucket S3 đang là input tham chiếu, Terraform small **không tự tạo bucket backup**. Phải phân công tạo/quản lý bucket riêng và cấu hình trước khi đưa dữ liệu cần giữ lên EC2, vì thay input này có thể dẫn tới EC2 replacement.

## 6. Medium — tính năng nhiều node phải triển khai

Chủ trì: N2; N3 nghiệm thu/vận hành; N1 hỗ trợ tích hợp. Tất cả mục MED thuộc P1 và hiện là **yêu cầu cần phát triển**, không phải khả năng sẵn có của CLI.

### MED-01 — Mạng private và đường đi rõ ràng

**Hành vi:** ALB ở public subnet tối thiểu hai AZ; app ở private subnet; DB/cache không public; EFS có mount target phù hợp các AZ sử dụng. App/runner truy cập được SSM, secret, log và artifact theo thiết kế egress đã chọn.

**Điều kiện đạt:** app không có public IP; port app chỉ nhận từ SG ALB; DB/EFS/Redis chỉ nhận từ các SG cần dùng. Không cấp đường Internet cho DB để chữa lỗi app. Kiểm tra route/SG và kết nối thực tế; endpoints AWS không được coi tự thay thế Internet tới mọi kho package bên ngoài.

### MED-02 — HTTPS, domain và proxy

**Hành vi:** endpoint người dùng có domain kiểm soát được, chứng chỉ ACM hợp lệ cho tên đó trong region ALB; HTTP chuyển HTTPS; `wwwroot` dùng URL HTTPS đúng.

**Điều kiện đạt:** không có redirect loop hoặc mixed content trên các luồng LMS; cookie và URL phản ánh HTTPS; login/logout/upload/download và giới hạn request nhất quán qua proxy. Không dùng nguyên Apache loopback/`Require local` của small cho app sau ALB. Thông tin proxy chỉ được tin trong đường mạng đã kiểm soát.

**Bằng chứng:** cấu hình DNS/certificate/listener, HTTP redirect và walkthrough LMS. Có thể dùng nhà cung cấp DNS khác Route 53 nếu nhóm đã quản lý domain ở đó; điều kiện bắt buộc là DNS đúng và chứng chỉ đã xác thực.

### MED-03 — RDS và thông tin kết nối

**Hành vi:** Moodle dùng RDS PostgreSQL thay DB local; app/cron/release/backup dùng credential phù hợp nhiệm vụ; secret được lấy lúc chạy theo role và bảo vệ khi lưu cục bộ.

**Điều kiện đạt:** DB không public; runtime không dùng tài khoản quản trị RDS để né cấp quyền; schema/install/upgrade được runner có quyền cần thiết thực hiện. Có bằng chứng phiên kết nối Moodle dùng TLS và cấu hình xác minh CA/hostname phù hợp; không chỉ thử bằng `psql` rồi mặc định PHP cũng tương tự. Chạy LMS, cron và backup/restore thật.

`sslmode=verify-full` và CA cần được tích hợp theo driver/phiên bản Moodle thực dùng; xác nhận cấu hình được Moodle truyền xuống driver. Không ghi chỉ `prefer` rồi kết luận không có khả năng fallback. [RDS PostgreSQL TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).

### MED-04 — File dùng chung trên EFS

**Hành vi:** mọi app/runner dùng cùng `moodledata` EFS, mount có TLS; UID/GID/ownership nhất quán; local cache đặt riêng theo cấu trúc Moodle hỗ trợ.

**Điều kiện đạt:** file tạo qua app A tải qua app B có hash trùng; bài nộp tồn tại sau thay node. Nếu EFS chưa mount, node không được ghi dữ liệu vào thư mục local thay thế rồi báo ready. Không tự chuyển các thư mục Moodle cần chia sẻ sang local chỉ vì tên chứa `cache` hoặc `temp`.

**Bằng chứng:** mount/config/ownership và ca ghi A → đọc B. Chứng minh app phục vụ request nào bằng log nội bộ, không mở debug endpoint public lộ metadata.

### MED-05 — Session dùng chung bằng Redis

**Hành vi:** session đăng nhập dùng Redis chung qua cấu hình session handler; PHP extension, endpoint, TLS/auth và timeout tương thích thực tế.

**Điều kiện đạt:** một phiên đi qua hai app vẫn giữ đúng user/quyền; thay một app không tự làm mất login chỉ vì session nằm local. Tắt stickiness khi chứng minh ca này. Redis không public, credential không lộ log. Không coi session phải sống sót khi mất toàn bộ Redis nếu chưa thiết kế/kiểm chứng khả năng đó.

**Nguồn cấu hình:** session driver là cấu hình riêng của Moodle, không tự có chỉ vì đã bật Redis extension. [Moodle session handling](https://docs.moodle.org/405/en/Session_handling).

### MED-06 — MUC cache nhất quán và độc lập với session

**Hành vi:** cấu hình cache store và mapping MUC theo nhu cầu chia sẻ giữa app; namespace tách theo site/môi trường và theo chức năng session/cache. Chọn mô hình Redis cụ thể tương thích cấu hình, không mặc định mọi dịch vụ đều hỗ trợ logical DB giống nhau.

**Điều kiện đạt:** các node thấy cập nhật course; purge cache không vô tình xóa session hay dữ liệu site khác; mapping kiểm tra được trong Moodle và lưu cấu hình tái lập. Không coi cài extension hoặc khai báo session handler là đã hoàn thành MUC.

**Bằng chứng:** cache mapping, request qua A/B trước/sau đổi nội dung và ca purge với một phiên đang đăng nhập. [Moodle caching](https://docs.moodle.org/405/en/Caching), [Redis cache store](https://docs.moodle.org/405/en/Redis_cache_store).

### MED-07 — Artifact thống nhất và ASG thay node

**Hành vi:** mọi app dùng cùng release commit và artifact bất biến, có định danh truy xuất được; ASG baseline min/desired 2, max 3 cho cửa sổ lab. Build artifact một lần rồi triển khai; không để từng node tự lấy `latest` khác nhau.

**Điều kiện đạt:** hai target phục vụ được; khi chủ động loại một app trong đợt thử, ASG tạo app thay thế từ cùng artifact; app mới mount storage, lấy cấu hình, đạt readiness và phục vụ LMS. Không chạy install/upgrade database trong user-data của từng app. Nếu artifact bị thiếu/không đọc được, node thất bại rõ ràng thay vì phục vụ bản không xác định.

**Bằng chứng:** launch template/artifact ID, ASG activity, thời gian thay node và kiểm tra dữ liệu sau thay. Image ID ghi trong metadata nhưng không tải lại được chưa đủ cho yêu cầu lưu artifact.

Để gọi là có **scale theo tải**, phải bổ sung policy, warmup/cooldown và metric/ngưỡng đã ghi rõ; thử tăng 2 → 3 và giảm về 2 trong cửa sổ được kiểm soát. Việc chỉ tạo ASG min/max hoặc đổi desired bằng tay chứng minh quản lý số node, chưa chứng minh policy tự scale. Dùng connection draining khi scale-in và ghi lỗi quan sát được, không hứa không gián đoạn trước khi đo.

### MED-08 — Cron runner và khóa tác vụ

**Hành vi:** cron chạy trên runner riêng của lab; app node không tự bật lịch cron. Các tiến trình cần phối hợp dùng cơ chế khóa Moodle có hiệu lực giữa các node; không dựa vào `flock` local để bảo vệ toàn cluster.

**Điều kiện đạt:** xác minh app không có lịch cron ngoài ý muốn; runner thực thi task; thử tranh chấp cùng một khóa từ hai tiến trình/node và chỉ một bên được xử lý tài nguyên đó. Cron/process lỗi phải có log và hướng khởi động lại, không tự xóa lock chưa xác minh.

Moodle Lock API hỗ trợ phối hợp giữa node; khóa tác vụ Moodle, khóa release và khóa Terraform là ba phạm vi khác nhau. [Moodle Lock API](https://moodledev.io/docs/4.5/apis/core/lock).

### MED-09 — Release/migration theo một luồng có kiểm soát

**Hành vi:** runner duy nhất thực hiện install/upgrade khi cần; có release lock chung, backup trước thay đổi dữ liệu, maintenance và trạng thái từng bước. App/cron dùng code tương thích schema đang chạy.

**Điều kiện đạt:** hai lượt release đồng thời không cùng migration; runner lỗi giữ trạng thái cần can thiệp và không công bố release thành công. Một release job rõ ràng phải cài/kiểm tra schema trong đợt dựng sạch; chỉ pin code trên hai app chưa đủ. Rollback sau migration phải có phương án DB + file + code/config phù hợp, không chỉ đổi lại image cũ.

Nghiệm thu P1 yêu cầu luồng release/schema và diễn tập restore có kiểm soát; không bắt buộc triển khai một lần nâng major Moodle hoặc nền tảng upgrade tự động P2.

### MED-10 — Readiness phản ánh ứng dụng

**Hành vi:** node chỉ báo ready khi code/config đúng release và các dependency cần thiết sử dụng được; kiểm tra nhẹ, có timeout, trả nội dung tối thiểu. Cơ chế chặn phục vụ khi bootstrap/maintenance phải nằm ở app hoặc lớp proxy phù hợp.

**Điều kiện đạt:** chưa mount EFS, cấu hình sai hoặc đang cài dở không được báo ready chỉ vì Apache còn sống. Health endpoint không lộ secret, đường dẫn riêng tư, instance ID hoặc stack trace. Phân biệt lỗi cục bộ một node với lỗi dependency chung để tránh vòng lặp thay mọi node không giải quyết được sự cố.

ALB có thể **fail open khi tất cả target đều unhealthy**; không dùng riêng trạng thái health check để bảo đảm maintenance/chặn ghi. Phải thử đường chặn ở tầng ứng dụng/proxy. [AWS ALB health checks](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html).

### MED-11 — Đưa dữ liệu baseline sang medium

**Hành vi:** chuyển fixture hoặc backup được chọn từ small sang DB/storage medium với code/schema tương thích; cấu hình đích dùng endpoint/secret/URL medium.

**Điều kiện đạt:** không chép đè `config.php` small làm medium quay về localhost/DB cũ; đối chiếu user/course/enrolment/bài nộp/điểm/file. Nếu dữ liệu có URL tuyệt đối nguồn, kiểm tra và chuyển bằng cơ chế phù hợp phiên bản Moodle, có backup trước; không sửa chuỗi mù trong dump. Tạo được dữ liệu mới sau chuyển.

Đây là bài kiểm tra tích hợp để dùng dataset đối chiếu. Nếu chọn seed medium độc lập, phải ghi rõ và chứng minh fixture tương đương; không gọi seed lại là di chuyển dữ liệu hoặc restore.

### MED-12 — Backup/restore toàn bộ medium

**Hành vi:** tạo được điểm backup nhất quán DB + EFS khi đã kiểm soát toàn bộ writer; lưu reference artifact/config cần thiết; restore sang môi trường medium mới.

**Điều kiện đạt:** qua toàn bộ OPS-01 đến OPS-05 áp dụng P1; kiểm tra lại LMS và session/file giữa hai node sau phục hồi. RDS snapshot đơn lẻ hoặc EFS backup đơn lẻ không tự chứng minh hai phía cùng một điểm dữ liệu.

## 7. Backup, restore và phục hồi lỗi

Chủ trì quy trình/script và kiểm chứng: N3. N1 tích hợp cho small; N2 tích hợp cho medium. Các yêu cầu áp dụng cả P0/P1 trừ phần đặc thù được ghi riêng.

### OPS-01 — Backup set đầy đủ và định danh được

**Hành vi:** mỗi lần backup có run ID, thời điểm UTC, môi trường nguồn và một set dữ liệu không trộn với các lần khác. Có DB dump, dữ liệu file bền vững, metadata code/runtime/config, checksum và manifest.

**Điều kiện đạt:** đọc manifest biết được nguồn, phiên bản/commit, định danh artifact, thời điểm và cách bảo đảm nhất quán. Tải về kiểm tra được checksum từng thành phần; file thiếu/sai checksum phải làm ca kiểm tra thất bại. Config chứa password phải được bảo vệ như backup dữ liệu; không đưa vào bộ bằng chứng công khai. Cache/session có thể tái tạo phải được phân loại rõ, không coi là học liệu/bài nộp cần khôi phục.

**Hiện trạng small:** `backup.sh` có dump/file/config/code/runtime metadata, checksum và manifest format 2; `restore_tested` được ghi `False`. Script không lưu image layers. Không sửa thành `True` chỉ vì dump/upload hoàn tất; kết quả restore phải có biên bản gắn đúng backup set.

### OPS-02 — Nhất quán dữ liệu và xử lý writer

**Small:** maintenance, dừng lịch cron, chờ cron đang chạy hoàn tất rồi dừng web trước dump/archive; không bắt đầu snapshot dữ liệu khi còn writer. Khi kết thúc hoặc lỗi backup, thử phục hồi dịch vụ về trạng thái thích hợp và báo rõ nếu recovery thất bại.

**Medium:** khóa đợt backup, chặn ghi trên mọi app và dừng/drain cron, ad hoc worker, release/migration cùng các writer khác đang bật. Xử lý app mới do ASG tạo trong cửa sổ backup: không cho nó mở lại đường ghi. Chỉ capture khi đã xác minh các writer dừng; không dùng nguyên script single-node.

**Điều kiện đạt:** thử có một task đang chạy và quan sát backup chờ/dừng đúng timeout; không kill tùy tiện task ghi dở rồi mặc định dữ liệu nhất quán. Đối với medium, log trạng thái từng writer và cách ngăn app mới ghi. Các bước có timeout và khóa; không backup đồng thời với release/schema change.

### OPS-03 — S3 upload, lịch và retention

**Hành vi:** backup ra S3 ngoài vòng đời EC2; bucket không public, có mã hóa và quyền giới hạn đúng prefix/môi trường. Manifest upload sau các thành phần để nhận biết set đã upload xong; kiểm tra đủ object và checksum trước sử dụng.

**Điều kiện đạt:** chứng minh có ít nhất một set đầy đủ trên S3, một lượt chạy theo lịch thật và cách phát hiện lượt lỗi/mất lịch. Có chính sách giữ/xóa bản local, S3 và version cũ phù hợp ngân sách; lưu ngày hết hạn/người phụ trách và không xóa bản đã xác minh cuối cùng trước khi có bản thay thế đạt. Có thể vận hành retention bằng runbook có kiểm soát, không bắt buộc thêm tự động xóa ngay.

Small hiện chỉ bật timer backup khi có bucket; giờ mặc định là 02:00 UTC. Backup local trên root EBS và một command ID SSM đều chưa đáp ứng yêu cầu backup ngoài máy. Manifest cuối không biến nhiều object S3 thành một giao dịch nguyên tử; vẫn phải kiểm tra nội dung set khi restore.

### OPS-04 — Restore sang đích sạch và kiểm tra trước ghi đè

**Hành vi:** chỉ restore vào staging/môi trường mới được chỉ rõ; kiểm tra account, instance/cluster, DB, storage và backup URI nguồn trước bước phá dữ liệu. Có xác nhận target rõ ràng và log bước đã thực hiện.

**Điều kiện đạt:** backup thiếu/hỏng hoặc code/schema không tương thích bị từ chối trước khi ghi đè. Restore dùng secret/config của đích; không chép password/endpoint nguồn đè lên. Trong khi restore giữ site đóng; khi DB/file phục hồi lỗi, không tự mở site như thể đã thành công.

Một runbook thủ công đầy đủ, có kiểm tra/xác nhận và đã thực thi, có thể đáp ứng phạm vi hiện tại. Nếu viết script, script phải giữ các kiểm tra này và trả lỗi đúng; không bắt buộc thêm lệnh CLI `restore` chưa tồn tại.

### OPS-05 — Nghiệm thu sau phục hồi và thời gian

**Hành vi:** dùng tài khoản trong backup để kiểm tra dữ liệu; chạy lại LMS-01 đến LMS-05. Đối chiếu user/course/enrolment, bài nộp, điểm/phản hồi và hash file; tạo/nộp một file mới sau restore; cron/health phải đạt.

**Điều kiện đạt:** phục hồi từ S3 sang tài nguyên mới, không chỉ attach lại disk nguồn hoặc kiểm tra dump đọc được. Medium kiểm tra lại ghi A/đọc B và session qua hai node. Artifact phục hồi phải có nguồn truy xuất được; nếu runtime rebuilt không trùng byte thì ghi đúng mức tái lập đã kiểm chứng.

Sau restore, người dùng có thể cần đăng nhập lại; không yêu cầu khôi phục các session đang mở từ môi trường nguồn. Điều cần bảo toàn là tài khoản, quyền và dữ liệu nghiệp vụ trong điểm backup được chọn.

**Thời gian:** lưu mốc bắt đầu xử lý → hạ tầng sẵn sàng → dữ liệu phục hồi → nghiệp vụ được xác minh. Thời gian đó là kết quả của drill với điều kiện đã ghi, chưa chứng minh RTO cam kết trong mọi sự cố. Ghi tuổi dữ liệu của backup tại mốc sự cố/drill; RPO không phải thời gian chạy restore và chưa có mục tiêu RPO được phê duyệt trong repo.

### OPS-06 — Thử lỗi và recovery có kiểm soát

| Ca lỗi | Hệ thống phải phản ứng | Bằng chứng cần lưu |
|---|---|---|
| Web service dừng ở small staging | Health phát hiện lỗi; sau khởi động lại LMS hoạt động | Health trước/sau, journal và request nghiệp vụ |
| Upload S3 bị từ chối ở staging | Backup báo lỗi; không công bố set hoàn tất; small thử mở lại web/cron và ghi rõ recovery có thành công không | Exit code, object inventory, trạng thái dịch vụ |
| Backup set thiếu file/sai checksum | Từ chối restore trước khi phá dữ liệu đích | Kết quả validation và xác minh đích chưa bị ghi đè |
| App medium bị loại khỏi ASG | App còn lại phục vụ; app mới được tạo và xác minh sẵn sàng | ASG activity, log request, session/file sau thay node |
| App medium thiếu mount hoặc secret/artifact | Không giả báo ready; không ghi nhầm vào local storage | Bootstrap/readiness và log đã lọc |
| Cron runner dừng | Phát hiện task không tiến triển; khởi động lại theo runbook; xác minh task xử lý tiếp | Metric/log task trước/sau và thời gian gián đoạn |
| Migration/restore thất bại | Giữ trạng thái cần can thiệp, không mở app với dữ liệu dở; phục hồi theo runbook | Step log, maintenance và kết quả restore xác minh lại |

Chỉ thử trên staging hoặc cửa sổ lab đã dành riêng, có backup; không làm đầy disk DB hoặc phá dữ liệu thật để tạo bằng chứng. Failover DB/cache toàn hệ thống thuộc P2 trừ khi nhóm bổ sung phạm vi riêng.

## 8. Quan sát, bảo vệ dữ liệu và chi phí

### OBS-01 — Log và thông tin điều tra

**P0:** truy xuất được cloud-init, bootstrap/install, web, cron và backup logs qua SSM; mỗi lần nghiệm thu ghi run ID, thời gian và môi trường. **P1:** bổ sung CloudWatch log group/retention phù hợp cho app/runner và log AWS service cần thiết.

**Điều kiện đạt:** từ một lỗi biết được node/service và bước thất bại; có rotation/retention tránh đầy disk. Không chia sẻ password, session token/cookie, authorization header hoặc config chứa secret. Log truy cập cũng cần được rà soát query string/dữ liệu cá nhân trước khi đưa vào báo cáo.

### OBS-02 — Metric, dashboard và cảnh báo có thử nghiệm

**P0:** thu thập CPU, RAM, disk, CPU credits, tình trạng DB/cron/backup bằng OS/CloudWatch phù hợp. **P1:** có dashboard cho app, ALB, RDS, Redis, EFS và runner; RAM/disk trong OS cần nguồn thu thập tương ứng, không mặc định có sẵn từ EC2.

**Điều kiện đạt P1:** có tín hiệu cho app unhealthy/5xx, disk cạn, DB/cache bất thường, cron không tiến triển và backup không thành công/không chạy quá hạn. Các tín hiệu job có thể cần custom metric/event, không tự có chỉ bằng tạo log group. Ghi metric, ngưỡng, cửa sổ đánh giá, xử lý missing data và cách nhận thông báo.

Phải tạo ít nhất một tình huống thử để chứng minh cảnh báo đến đúng nơi và trở lại trạng thái bình thường. Nếu chưa cấu hình kênh nhận, chỉ được ghi đã tạo alarm, chưa đạt cảnh báo vận hành. Ngưỡng resource/timeout cần chốt từ baseline và lịch tác vụ, tránh báo lỗi với job hợp lệ đang chạy dài.

### SEC-01 — Secret và quyền tối thiểu theo nhiệm vụ

**P0:** secret sinh trên EC2, file quyền phù hợp; đổi password admin khởi tạo; không lưu vào YAML/Git/user-data. **P1:** dùng secret runtime theo role, không đưa credential dài hạn AWS vào app. Quyền deploy khác quyền runtime, backup và restore.

**Điều kiện đạt:** ứng dụng không có quyền quản trị account; backup chỉ ghi nơi cần; restore chỉ đọc set/phạm vi được cấp và gỡ quyền tạm khi xong. Người không được cấp quyền không đọc được state/backup/secret. Không cho rằng gắn nhãn `sensitive` sẽ tự loại secret khỏi state/plan: phải kiểm tra cách tạo/đọc secret trong IaC và bảo vệ những artifact có thể chứa dữ liệu đó.

### SEC-02 — Mạng và kiểm tra quyền bằng hành vi

**Điều kiện đạt:** chỉ endpoint dự kiến có thể truy cập từ Internet; private service không mở rộng ingress để chữa lỗi. Kiểm tra quyền LMS ở tầng request, không chỉ ẩn nút. Kiểm tra file nhạy cảm không trả nội dung; backup/state không public; debug/developer mode dùng để tạo dataset phải trả về baseline trước demo/đo tải.

N1/N2 chịu trách nhiệm cấu hình tương ứng, N3 thực hiện kiểm tra âm và ghi bằng chứng. Không yêu cầu một bài penetration test đầy đủ ngoài phạm vi đồ án.

### COST-01 — Chi phí đo được và tài nguyên kiểm kê được

**Hành vi:** N3 giữ sổ chi phí tổng kỳ; N1/N2 cập nhật tài nguyên và giờ chạy. Ngày 07/11/2026 người dùng giảm ngân sách nhóm xuống 150 USD, phân bổ 112,50 USD kế hoạch và 37,50 USD dự phòng theo tỷ lệ cũ. Đây là hạn mức nội bộ, không phải báo giá dịch vụ đã xác minh.

**Điều kiện đạt:** trước deploy medium có estimate theo region/SKU/giờ dùng thật; tính cả NAT, ALB, RDS, Redis, EFS, EC2/runner, IPv4, EBS, artifact, S3/version, logs và máy phát tải nếu có. Báo cáo phân biệt estimate, chi phí ghi nhận và credit thực áp dụng; ghi ngày lấy số liệu vì billing có độ trễ.

Có budget/cảnh báo nếu quyền tài khoản cho phép và kiểm chứng kênh nhận; nếu thiếu quyền phải ghi rõ và theo dõi thủ công. Không mô tả budget như giới hạn chi tiêu cứng. Sau cleanup còn tài nguyên nào thì ghi owner, mục đích, ngày hết hạn và chi phí tiếp tục phát sinh.

## 9. Chất lượng mã, đo tải và tính tái lập

### QA-01 — Kiểm tra mã và CI phản ánh đúng phạm vi

**Điều kiện đạt:** unit test đầu vào/chốt plan, Terraform fmt/validate/mock test, Bash/PHP syntax và Docker runtime/integration liên quan đều đạt cho phần đã thay đổi. Medium phải thêm kiểm tra schema/config, module và các chốt plan tương ứng, không chỉ chạy lại test small.

Có ít nhất một lượt GitHub Actions đạt trên commit được bàn giao và artifact truy xuất được. CI hiện không deploy AWS; kết quả local/mock/CI không được thay cho nghiệm thu AWS. Nếu workflow thay đổi, mô tả rõ bước nào vẫn chỉ kiểm tra cục bộ.

Không lấy số lượng test làm tiêu chí chất lượng duy nhất; các lỗi mất dữ liệu, sai môi trường, truy cập trái quyền, backup giả thành công và release chạy trùng cần ca kiểm tra có ý nghĩa.

### QA-02 — Workload đúng nghiệp vụ

**Hành vi:** N3 tạo JMeter test plan từ fixture/dataset đã ghi; mỗi virtual user dùng tài khoản/session riêng phù hợp. Kiểm tra login token, cookie, đường dẫn file và assertion nội dung trước khi chạy nhiều user.

**Điều kiện đạt:** một user đi được toàn bộ script dự kiến; assertion phân biệt trang course thành công với trang login/lỗi trả 200. JMX thực sự dùng biến cấu hình nếu chạy bằng `-J...`; không giả định biến khai báo ở CLI tự có hiệu lực. Máy phát tải tách khỏi EC2 Moodle và được ghi cấu hình/vị trí mạng.

Workload chuẩn kế thừa test plan: 60% xem nội dung, 20% tải file nhỏ, 10% xem/nộp bài, 10% login/logout; think time 3–8 giây. Ghi định nghĩa tỷ lệ theo transaction/request trong JMX để người khác tái lập; không trộn tỷ lệ theo user với theo request. Quiz đồng thời là workload riêng, không bắt buộc cho baseline hiện tại.

### QA-03 — Ma trận đo và giới hạn diễn giải

| Bài đo | Mức tải | Thời gian và cách thực hiện | Điều kiện kết luận |
|---|---|---|---|
| Smoke workload | 1–2 user | Ramp-up 30 giây, ổn định 2 phút | Nghiệp vụ/assertion đúng trước khi tăng tải |
| So sánh baseline | 10 user | Ramp-up 2 phút, ổn định 10 phút | Cùng dataset/workload trên small và medium |
| So sánh tải 1 | 25 user | Ramp-up 3 phút, ổn định 10 phút | Lưu lỗi, tài nguyên và điều kiện chạy |
| So sánh tải 2 | 50 user | Ramp-up 5 phút, ổn định 15 phút | Không mất dữ liệu; dừng tăng tải khi lỗi kéo dài |
| Medium mở rộng | 100/200 user nếu còn khả năng và ngân sách | Chỉ sau baseline, ghi ramp-up/điều kiện riêng | Phép thử khám phá, không phải mức năng lực đã được bảo đảm |

Lặp tối thiểu ba lần cho mỗi mức dùng làm kết luận so sánh theo test plan; nếu không đủ phải ghi số lần thật và giới hạn. Một lần vượt ngưỡng/không chịu được tải vẫn là kết quả nghiên cứu, không sửa số liệu để đủ tiêu chí.

Lưu p50/p95/p99, throughput, số mẫu, lỗi nghiệp vụ theo loại transaction; CPU/RAM/disk, DB, cron, CPUCreditBalance đầu/cuối và cấu hình credit. Ghi cold/warm cache và chính sách scale; tách bài medium cố định hai app khỏi bài chứng minh autoscaling.

Small đo qua SSM còn ảnh hưởng tunnel/máy phát tải; medium qua HTTPS có đường mạng khác. Phải nêu khác biệt này khi so sánh end-to-end, không quy mọi chênh lệch thành hiệu quả ASG hoặc RDS. Số tài khoản đăng ký không tương đương user đồng thời.

**Ngưỡng nghiên cứu đang đề xuất trong repo:** p95 trang tương tác ≤ 3 giây, lỗi nghiệp vụ < 1%, không mất file/bài nộp, cron không lỗi kéo dài. Đây chưa phải ngưỡng đã được nhóm phê duyệt hoặc kết quả đã đạt; ghi mức tải/transaction/cửa sổ đánh giá khi chốt. Nếu không đạt phải báo kết quả, nguyên nhân và giới hạn; không tuyên bố mức tải đó được hỗ trợ.

### QA-04 — So sánh cài tay, tự động và phục hồi

**Điều kiện đạt:** có bảng thời gian đến Moodle ready, số thao tác cần quyết định, lỗi/thời gian sửa, khả năng dựng lại và thời gian restore. Định nghĩa mốc bắt đầu/kết thúc giống nhau hoặc tách rõ thời gian hạ tầng/cài ứng dụng; ghi baseline và dataset cho từng lần.

Không dùng thời gian Terraform apply làm thời gian ứng dụng ready; không dùng chi phí estimate làm hóa đơn thật. Số đo một lần phải được ghi là quan sát một lần.

## 10. Ca nghiệm thu đầu-cuối bắt buộc

Các mã AT dưới đây là kịch bản chạy thực tế, không thay thế mã yêu cầu. Một ca có thể cần nhiều lần chạy trên small, medium và môi trường sau restore.

| Mã | Kịch bản | Yêu cầu đối chiếu | Kết quả phải xác minh |
|---|---|---|---|
| AT-01 | YAML lỗi, preset chưa hỗ trợ, secret input | CLI-01 | Thất bại trước mutation, lỗi chỉ rõ đầu vào; offline không gọi AWS |
| AT-02 | Đổi config/source/plan/account hoặc confirm sai | CLI-03 | Apply bị từ chối; không tạo tài nguyên ngoài kế hoạch |
| AT-03 | Small từ EC2 sạch, rồi gọi bootstrap lại sau thành công | SMALL-01, SMALL-02, SMALL-03, CLI-05 | Runtime đúng, ứng dụng ready, dữ liệu không bị reset |
| AT-04 | Login đúng/sai/logout; course riêng và URL trực tiếp | LMS-01, LMS-02, SEC-02 | Đúng role và giới hạn truy cập |
| AT-05 | Upload/download, tên tiếng Việt, file quá giới hạn | LMS-03 | Hash khớp, vượt giới hạn không giả thành công |
| AT-06 | Hai student nộp bài; teacher chấm; thử đọc bài/điểm người khác | LMS-04 | Bài/điểm/phản hồi đúng, quyền riêng tư đúng fixture |
| AT-07 | Cron thực thi task và kiểm tra task lỗi | LMS-05, MED-08 | Có kết quả task, phát hiện failure kể cả exit code cron 0 |
| AT-08 | Reboot small staging | SMALL-04 | Web/cron/DB tự lên; login/file/bài nộp vẫn hoạt động |
| AT-09 | HTTP file nhạy cảm và quyền ghi OS | SMALL-05, SEC-01, SEC-02 | Không lộ mã/secret; web user không sửa code/config |
| AT-10 | Backup khi cron đang chạy, rồi thử lỗi S3 | OPS-01, OPS-02, OPS-03, OPS-06 | Backup drain đúng; lỗi có trạng thái rõ; dịch vụ được phục hồi đúng |
| AT-11 | Restore set thiếu/hỏng rồi set hợp lệ sang small staging mới | OPS-04, OPS-05 | Set hỏng bị từ chối; set hợp lệ phục hồi đủ và ghi tiếp được |
| AT-12 | Medium dựng sạch qua release runner | CLI-04, MED-01, MED-02, MED-03, MED-07, MED-09, MED-10 | State/lock đúng; HTTPS/DB/artifact/schema/readiness đúng |
| AT-13 | Giữ phiên, ghi file/bài nộp qua A rồi đọc qua B | MED-04, MED-05, MED-06 | Cùng user/quyền, hash đúng, nội dung nhất quán |
| AT-14 | Purge MUC khi có user đăng nhập | MED-06 | Cache làm mới, session/site khác không bị xóa ngoài ý muốn |
| AT-15 | Loại app, thử scaling policy và scale-in | MED-07, MED-10, OPS-06 | App thay thế đúng artifact; policy có bằng chứng hoạt động; ghi lỗi lúc chuyển |
| AT-16 | Hai tiến trình tranh cùng khóa và hai release đồng thời | MED-08, MED-09 | Không xử lý trùng tài nguyên hoặc migration |
| AT-17 | Backup medium với kiểm soát toàn writer, restore cluster mới | MED-11, MED-12, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05 | Đủ DB/file/nghiệp vụ, ghi mới được, hai app hoạt động sau restore |
| AT-18 | Thử alarm và tìm nguyên nhân từ log/metric | OBS-01, OBS-02, OPS-06 | Tín hiệu đến nơi nhận, nhận biết nguồn lỗi và recovery |
| AT-19 | JMeter small/medium và đo thao tác triển khai/phục hồi | QA-02, QA-03, QA-04 | Raw result, bảng tổng hợp và giới hạn diễn giải đầy đủ |
| AT-20 | Bàn giao, demo và cleanup theo từng môi trường | CLI-06, COST-01, DONE-01, DONE-02 | Người khác làm theo được; kiểm kê khớp tài nguyên còn giữ |

Giữ các ID F01–F13 trong [test plan hiện có](06-test-plan.md) khi cập nhật biên bản; bổ sung liên kết sang AT và mã yêu cầu thay vì đổi nghĩa ID cũ. Bảng AT là mức tối thiểu, không có nghĩa mọi kiểm thử cần thiết chỉ có 20 ca.

## 11. Bằng chứng và hồ sơ bàn giao

### 11.1. Mẫu bằng chứng cho mỗi lần chạy

```text
Run ID:
Ngày giờ bắt đầu/kết thúc (UTC):
Người thực hiện / người kiểm tra lại:
Mã yêu cầu và mã AT/F đối chiếu:
Trạng thái: Chờ nghiệm thu / Đạt / Không đạt
Git commit và các thay đổi chưa commit liên quan:
Preset / environment / account / region:
AMI / artifact ID / Moodle / PHP / PostgreSQL:
Dataset và thiết lập course/assignment:
Điều kiện trước khi chạy:
Các bước đã thực hiện:
Kết quả mong đợi:
Kết quả thực tế:
Log, ảnh, report, checksum và đường dẫn bằng chứng:
Lỗi còn tồn tại / cách xử lý / giới hạn:
```

Raw log, state, saved plan, credential, CSV user và backup giữ trong nơi riêng có kiểm soát quyền, ví dụ `.work/` cho artifact cục bộ. Bộ bằng chứng nộp/chia sẻ là bản đã loại secret. Nếu chạy trên working tree còn thay đổi chưa commit, ghi fingerprint/diff phù hợp để nhận diện code thật đã chạy; không chỉ ghi commit cũ rồi coi mọi thay đổi đều đã được kiểm thử.

### DONE-01 — Bộ bàn giao đầy đủ

| Thành phần | Nội dung tối thiểu | Chủ trì |
|---|---|---|
| Mã và cấu hình | Source, lockfile, YAML mẫu, script, workflow; ghi rõ phần đã hỗ trợ | N1 + N2 |
| Hướng dẫn dựng | Điều kiện công cụ/quyền, thứ tự bootstrap backend, small/medium, SSM/HTTPS, health và xử lý lỗi | N1 + N2 |
| Hướng dẫn vận hành | Backup, kiểm tra job, restore, maintenance, release, cảnh báo và cleanup | N3, N1/N2 kiểm tra phần tương ứng |
| Kiến trúc thực tế | Sơ đồ, role/secret/state, đường mạng, storage/session, điểm lỗi đơn | N2; N1 đối chiếu small |
| Chức năng và phục hồi | Biên bản test, hash, restore drill và các lỗi/giới hạn | N3 |
| Thực nghiệm | JMX, raw result riêng tư, report tổng hợp, metric và so sánh có điều kiện đo | N3 |
| Chi phí | Estimate, giả định/giờ chạy, chi phí ghi nhận, credit và inventory cuối | N3, N1/N2 xác nhận tài nguyên |
| Báo cáo và demo | Cài tay/auto, small/medium, kết quả thật, giới hạn; demo 12–15 phút và video/log provision | Cả nhóm, N3 tổng hợp |

Một thành viên khác người viết runbook phải thử làm theo phần bàn giao phù hợp. Ghi lại những bước phải hỏi thêm và sửa hướng dẫn trước khi đóng task. Không cần triển khai thêm một stack chỉ để hình thức nếu đã có lượt dựng/restore độc lập thực hiện theo runbook và đủ bằng chứng.

### DONE-02 — Cleanup và tài nguyên còn giữ

**Điều kiện đạt:** đã lưu bằng chứng và kiểm chứng backup ngoài tài nguyên sắp xóa; review destroy plan từng môi trường; ghi tài nguyên xóa được/không xóa được cùng nguyên nhân. Kiểm kê EC2 thủ công/lab cũ ngoài state, EBS, snapshot, IPv4, ALB/NAT, RDS/cache/EFS, S3/version, artifact và log còn tồn tại.

Không tự xóa lab cũ ngoài state để làm báo cáo sạch. Tài nguyên giữ lại phải được ghi rõ owner, mục đích và thời hạn; hạn chế quyền đúng nhu cầu. Bucket state/backend và backup có vòng đời riêng, không phá trước khi xong quản lý tài nguyên/khả năng phục hồi.

## 12. Cổng nghiệm thu và trách nhiệm cuối cùng

| Cổng | Điều kiện mở | Điều kiện đóng | Chịu trách nhiệm |
|---|---|---|---|
| G0 — Sẵn sàng triển khai | Đã xác định scope 3 người | Quyền/phiên/cấu hình/state đúng; rõ bucket/retention, secret/artifact và dự toán của bước sắp chạy | N1 cho small, N2 cho medium; N3 đối chiếu |
| G1 — Small triển khai | G0 small đạt | CLI/SMALL đạt; có cài tay và tự động; LMS và kiểm tra reboot trên AWS có bằng chứng | N1; N3 kiểm tra |
| G2 — Small phục hồi | G1 đạt | OPS cho small đạt, restore sang máy mới thành công; fixture/workload baseline đã chuẩn bị | N3; N1 tích hợp/sửa lỗi |
| G3 — Medium tích hợp | Small ổn và restore đạt; dự toán phù hợp | CLI P1 và MED đạt; LMS qua hai node; release/cron/lock đúng | N2; N3 kiểm tra |
| G4 — Medium vận hành | G3 đạt | Restore cluster mới, cảnh báo thử thật, thay node/scale policy và các ca lỗi bắt buộc có kết quả | N2 + N3 |
| G5 — Thực nghiệm và bàn giao | Có môi trường đạt cho phép đo | QA, COST và DONE đạt; kết luận khớp số liệu; báo cáo/demo/cleanup có bằng chứng | Cả nhóm, N3 tổng hợp |

Phát triển module medium, dữ liệu test, JMeter và runbook có thể làm song song trước G2. Không hiểu các cổng là bắt mọi người ngồi chờ nhau; chỉ chặn bước triển khai/nghiệm thu cần phụ thuộc chưa đạt. Nếu test không đạt, ghi lỗi và quay lại sửa, không đóng cổng bằng cách đổi nhãn.

Sau G2, phép đo tải small và tích hợp medium có thể làm song song trên các môi trường riêng, trong giới hạn ngân sách; toàn bộ kết quả đo dùng kết luận phải hoàn tất trước G5.

### 12.1. Quyết định phải ghi rõ trước bước liên quan

Các điểm dưới đây chưa được tài liệu cũ xác nhận đầy đủ. Đây là đầu vào cần chốt để tránh triển khai theo phỏng đoán; không phải câu hỏi buộc dừng công việc độc lập.

| Quyết định | Ai chủ trì | Cần chốt trước |
|---|---|---|
| Quyền AWS đã có hiệu lực, account/region và inventory lab cũ | N1 | Apply small |
| Bucket/prefix backup, lịch/retention và quyền restore | N3 + N1/N2 | Đưa dữ liệu cần giữ lên môi trường và backup drill |
| Giữ baseline phiên bản hay cập nhật có kiểm soát | N1 + N2 | Build/deploy dùng để nghiệm thu |
| Domain, certificate, DNS và SKU/engine/egress medium thật | N2 | Plan/apply medium |
| Backend/key/lock, secret runtime và nơi giữ artifact khôi phục được | N2 | Cộng tác deploy và bật ASG |
| Giới hạn upload, thiết lập assignment, timeout, alarm và chính sách scale | N1/N2 + N3 | Nghiệm thu ca tương ứng |
| Ngưỡng hiệu năng theo workload/mức tải và số lần lặp được dùng kết luận | N3 + cả nhóm | Đo chính thức và viết kết luận |
| Deadline, credit/ngân sách còn lại, thời điểm demo và cleanup | Cả nhóm | Lịch triển khai có tính phí và bàn giao |

### 12.2. Definition of Done của một tính năng

Một tính năng chỉ được đánh dấu hoàn thành khi đồng thời đáp ứng:

1. Hành vi đúng đặc tả trên đúng preset/môi trường, có cả đường thành công và lỗi/quyền truy cập liên quan.
2. Mã/cấu hình/runbook để tái lập đã được lưu; đầu vào và dependency được mô tả, không có bước ngầm chỉ một người biết.
3. Các kiểm tra liên quan đạt; không dùng mock/local thay cho bằng chứng AWS cần có.
4. Có run ID, expected/actual result, code/config nhận diện được và bằng chứng đã lọc secret.
5. Có người kiểm tra lại; lỗi quan trọng về mất dữ liệu, sai môi trường, phân quyền, backup/restore hoặc chạy trùng chưa được bỏ qua.
6. Trạng thái trong biên bản, hướng dẫn và báo cáo thống nhất với kết quả thực tế.

**Project đạt P0** khi các yêu cầu P0, thực nghiệm tương ứng và hồ sơ bàn giao được nghiệm thu. **Project đạt mục tiêu P0 + P1 của nhóm** khi toàn bộ yêu cầu P1 cũng đạt và báo cáo/cleanup hoàn tất. Nếu giảm phạm vi xuống P0 phải ghi rõ quyết định và lý do, không mô tả medium như đã triển khai.

## 13. Tài liệu đối chiếu

- [Phân công 3 người](11-phan-cong-3-nguoi.md).
- [Kiến trúc và kế hoạch mở rộng](02-architecture.md).
- [Lab cài thủ công](03-manual-lab.md).
- [Terraform và CLI](04-deployment.md).
- [Vận hành, backup và restore](05-operations.md).
- [Kiểm thử và bằng chứng nghiệm thu](06-test-plan.md).
- [Chi phí, báo cáo và demo](07-report-and-cost.md).
- [Nhật ký kiểm chứng](08-validation.md).
- [Hướng dẫn hoàn tất project](09-completion-guide.md).
- [Quyền IAM cho lab mới](10-iam-permissions.md).

Khi tài liệu cũ còn ghi nhóm 4 người, dùng phân công 3 người ở tài liệu 11. Với medium, bản đặc tả này chuẩn hóa baseline ASG hai app, max ba cho lab; các mức node/tải lớn hơn ở bản thiết kế cũ là hướng thử nghiệm, không tự áp dụng nếu chưa cập nhật dự toán và cấu hình. Các đề xuất ngưỡng chưa chốt vẫn phải được ghi là đề xuất.
