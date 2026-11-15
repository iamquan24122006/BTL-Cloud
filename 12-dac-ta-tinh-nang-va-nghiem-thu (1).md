# Đặc tả tính năng và tiêu chí nghiệm thu Moodle Cloud

Ngày lập: 03/11/2026. Phạm vi: nhóm 3 người, small (P0) và medium (P1).

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
