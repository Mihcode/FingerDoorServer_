DATABASE.PY ĐỂ KẾT NỐI DB
MODELS.PY ĐỊNH NGHĨA CÁC BẢNG
SCHEMAS.PY ĐỊNH NGHĨA DỮ LIỆU TRẢ VỀ JSON
MAIN.PY NƠI CHẠT CODE CHÍNH
.ENV CHỨA MẬT KHẨU DB #AE ĐỪNG ĐỂ LỘ NHÉ
_______________
Android:
xem được thông tin cơ bản nhân viên
xem được lịch sử chấm công
đăng nhập các kiểu oke rồi
sắp tới triển khai cho xem số tiền hiện tại kiếm được trong tháng

DB thì trong env rồi, edit được trên supabase luôn, ae đỡ phải lại thêm tech khác

Logic tạm thời triển khai cơ bản như này cho nhanh, phức tạp quá sợ không kịp
+ Ca làm 9h sáng đến 17h chiều, thông luôn, ăn trưa công ty. đi làm muộn 1 phút thôi là tính vắng luôn, mất một ngày công, về sớm 1 phút thôi cũng vậy ( chưa làm cái về sớm tính là mất công )
+ OT thì phải checkout sau 18h mới tính được là OT
+ Lương thì có lương tháng với lương OT, lương OT thì cứ ngày nào OT thì ngày đấy được cộng tiền OT, coi một tháng 30 ngày, 22 ngày công => lương một ngày = lương tháng/22
  tính số tiền kiếm được đến hiện tại = số ngày đi làm * lương 1 ngày + số ngày ot * lương ot
+ Dự kiến khi mà chấm công gửi bản chấm công lên server, server xử lý tìm cặp (id user, ngày tháng năm chấm công) để cập nhật bản chấm công hiện tại, nếu chưa có thì tạo      mới để logic một ngày, một người chỉ có một bản ghi chấm cộng, server sẽ xử lý logic cập nhật check out cho phù hợp ( mà cũng chỉ check out được 1 lần thôi, công ty         nghiêm khắc không cho ra vào, nếu về sớm phải trả giá)

