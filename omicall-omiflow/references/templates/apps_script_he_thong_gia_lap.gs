/**
 * HIS GIẢ LẬP — Bệnh viện ABC (demo OMICall)
 * Cách dùng: dự án Apps Script độc lập trỏ tới Sheet SHEET_ID; chạy hàm setup() một lần,
 * rồi Triển khai > Ứng dụng web (Thực thi: Tôi, Ai có quyền truy cập: Bất kỳ ai) và gửi URL /exec.
 *
 * Endpoint (GET hoặc POST JSON, cùng tham số):
 *   ?action=lookup&phone=0912...        -> bệnh nhân + lịch hẹn sắp tới của SĐT (cho Callbot gọi vào)
 *   ?action=tomorrow                    -> danh sách lịch hẹn ngày mai (xem thử, không gửi đi)
 *   ?action=push_tomorrow               -> gửi từng lịch hẹn ngày mai sang quy trình OMIFlow (nhắc lịch)
 *   ?action=update_status&ma_lich=LH..&trang_thai=Xác nhận đi khám -> ghi trạng thái về sheet
 *   ?action=flush_sync                  -> gửi hàng đợi đồng bộ CRM (trigger 1 phút tự chạy)
 */
var TZ = 'Asia/Ho_Chi_Minh';
var SH = { BN: 'BenhNhan', LH: 'LichHen', CH: 'CauHinh', HD: 'HangDoiDongBo', NK: 'NhatKy' };

function doGet(e) { return handle_(e && e.parameter ? e.parameter : {}); }
function doPost(e) {
  var p = (e && e.parameter) ? JSON.parse(JSON.stringify(e.parameter)) : {};
  try { if (e && e.postData && e.postData.contents) { var b = JSON.parse(e.postData.contents); for (var k in b) p[k] = b[k]; } } catch (err) {}
  return handle_(p);
}

function handle_(p) {
  var out;
  try {
    var a = String(p.action || 'lookup');
    if (a === 'lookup') out = lookup_(p.phone);
    else if (a === 'tomorrow') out = { ok: true, items: tomorrowItems_(false) };
    else if (a === 'push_tomorrow') out = pushTomorrow_();
    else if (a === 'update_status') out = updateStatus_(p.ma_lich, p.trang_thai, p.ghi_chu);
    else if (a === 'flush_sync') out = flushSync();
    else if (a === 'sync_upcoming') out = syncUpcoming_();
    else out = { ok: false, error: 'action không hợp lệ' };
  } catch (err) { out = { ok: false, error: String(err) }; }
  log_(p.action || 'lookup', JSON.stringify(p), JSON.stringify(out).slice(0, 400));
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

// ---------- tiện ích ----------
var SHEET_ID = '<ID_GOOGLE_SHEET>'; // thay bằng id trong URL của Sheet
function ss_() { return SpreadsheetApp.openById(SHEET_ID); }
function normPhone_(s) {
  var d = String(s || '').replace(/\D/g, '');
  if (d.indexOf('84') === 0 && d.length >= 11) d = '0' + d.slice(2);
  if (d && d.charAt(0) !== '0' && d.length === 9) d = '0' + d;
  return d;
}
function fmtDate_(v) { return (v instanceof Date) ? Utilities.formatDate(v, TZ, 'dd/MM/yyyy') : String(v || ''); }
function fmtTime_(v) { return (v instanceof Date) ? Utilities.formatDate(v, TZ, 'HH:mm') : String(v || ''); }
function ymd_(v) {
  if (v instanceof Date) return Utilities.formatDate(v, TZ, 'yyyy-MM-dd');
  var m = String(v || '').match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  return m ? m[3] + '-' + ('0' + m[2]).slice(-2) + '-' + ('0' + m[1]).slice(-2) : String(v || '');
}
function todayPlus_(n) { return Utilities.formatDate(new Date(Date.now() + n * 86400000), TZ, 'yyyy-MM-dd'); }
function rows_(name) {
  var v = ss_().getSheetByName(name).getDataRange().getValues(), h = v.shift();
  return v.map(function (r, i) { var o = { _row: i + 2 }; h.forEach(function (k, j) { o[k] = r[j]; }); return o; });
}
function config_() {
  var c = {}; rows_(SH.CH).forEach(function (r) { c[r.khoa] = r.gia_tri; }); return c;
}
function log_(a, inp, out) {
  try { ss_().getSheetByName(SH.NK).appendRow([new Date(), a, inp, out]); } catch (e) {}
}
function apptOut_(l) {
  return { ma_lich: l.ma_lich, ngay_hen: fmtDate_(l.ngay_hen), gio_hen: fmtTime_(l.gio_hen), khoa: l.khoa,
           bac_si: l.bac_si, phong: l.phong, trang_thai: l.trang_thai };
}

// ---------- tra cứu theo SĐT ----------
function lookup_(phone) {
  var sdt = normPhone_(phone);
  if (!sdt) return { ok: false, found: false, tom_tat: 'Thiếu số điện thoại.' };
  var bns = rows_(SH.BN).filter(function (b) { return normPhone_(b.sdt_phu_huynh) === sdt; });
  if (!bns.length) return { ok: true, found: false, sdt: sdt, tom_tat: 'Không tìm thấy hồ sơ bệnh nhân nào đăng ký số điện thoại này.' };
  var today = todayPlus_(0), lhs = rows_(SH.LH);
  var parts = [], first = null;
  bns.forEach(function (b) {
    var up = lhs.filter(function (l) { return l.ma_bn === b.ma_bn && ymd_(l.ngay_hen) >= today && l.trang_thai !== 'Huỷ lịch'; })
                .sort(function (x, y) { return (ymd_(x.ngay_hen) + fmtTime_(x.gio_hen)).localeCompare(ymd_(y.ngay_hen) + fmtTime_(y.gio_hen)); });
    var l = up[0];
    var item = { ma_bn: b.ma_bn, ho_ten_tre: b.ho_ten_tre, ngay_sinh: fmtDate_(b.ngay_sinh), gioi_tinh: b.gioi_tinh,
                 ho_ten_phu_huynh: b.ho_ten_phu_huynh, sdt: sdt, lich_hen: l ? apptOut_(l) : null };
    if (!first) first = item;
    parts.push(l ? ('Bé ' + b.ho_ten_tre + ' (mã ' + b.ma_bn + ') có lịch khám ' + l.khoa + ' lúc ' + fmtTime_(l.gio_hen) + ' ngày ' + fmtDate_(l.ngay_hen) +
                    ', bác sĩ ' + l.bac_si + ', ' + l.phong + ', trạng thái: ' + l.trang_thai + '.')
                 : ('Bé ' + b.ho_ten_tre + ' (mã ' + b.ma_bn + ') hiện chưa có lịch hẹn sắp tới.'));
    if (l) queueSync_(item, 'tra_cuu');
  });
  var res = { ok: true, found: true, so_benh_nhan: bns.length, tom_tat: parts.join(' ') };
  for (var k in first) res[k] = first[k];
  return res;
}

// ---------- đồng bộ CRM: xếp hàng rồi gửi ngoài cuộc gọi (không làm chậm Callbot) ----------
function payload_(it, mucDich) {
  var l = it.lich_hen || {};
  return { muc_dich: mucDich, sdt: it.sdt, ho_ten_phu_huynh: it.ho_ten_phu_huynh, ma_bn: it.ma_bn, ho_ten_tre: it.ho_ten_tre,
           ngay_sinh: it.ngay_sinh, ma_lich: l.ma_lich || '', ngay_hen: l.ngay_hen || '', ngay_hen_iso: ymd_(l.ngay_hen || ''), gio_hen: l.gio_hen || '',
           khoa: l.khoa || '', bac_si: l.bac_si || '', phong: l.phong || '', trang_thai: l.trang_thai || '' };
}
function queueSync_(it, mucDich) {
  ss_().getSheetByName(SH.HD).appendRow([new Date(), JSON.stringify(payload_(it, mucDich)), '']);
}
function flushSync() {
  var url = config_().FLOW_HIS_CRM_URL, sh = ss_().getSheetByName(SH.HD), sent = 0;
  if (!url) return { ok: false, error: 'Chưa khai FLOW_HIS_CRM_URL trong tab CauHinh' };
  rows_(SH.HD).forEach(function (r) {
    if (r.da_gui) return;
    var code = post_(url, JSON.parse(r.du_lieu));
    sh.getRange(r._row, 3).setValue(new Date() + ' HTTP ' + code); sent++;
  });
  return { ok: true, sent: sent };
}
function post_(url, body) {
  var r = UrlFetchApp.fetch(url, { method: 'post', contentType: 'application/json', payload: JSON.stringify(body), muteHttpExceptions: true });
  return r.getResponseCode();
}

// ---------- nhắc lịch T+1 ----------
function tomorrowItems_(onlyAllowed) {
  var t = todayPlus_(1), c = config_();
  var allow = String(c.DS_SO_THU || '').split(/[,;\s]+/).map(normPhone_).filter(String);
  var bn = {}; rows_(SH.BN).forEach(function (b) { bn[b.ma_bn] = b; });
  return rows_(SH.LH).filter(function (l) { return ymd_(l.ngay_hen) === t && l.trang_thai === 'Đã đặt'; })
    .map(function (l) {
      var b = bn[l.ma_bn] || {};
      return { ma_bn: l.ma_bn, ho_ten_tre: b.ho_ten_tre, ngay_sinh: fmtDate_(b.ngay_sinh), ho_ten_phu_huynh: b.ho_ten_phu_huynh,
               sdt: normPhone_(b.sdt_phu_huynh), lich_hen: apptOut_(l) };
    })
    // an toàn demo: chỉ gọi ra số nằm trong DS_SO_THU, tránh gọi nhầm số giả là số thật của người khác
    .filter(function (it) { return !onlyAllowed || allow.indexOf(it.sdt) >= 0; });
}
// đồng bộ mọi lịch hẹn sắp tới (Đã đặt) sang CRM để quy trình 8h (trước 1 ngày so với Ngày hẹn) tự gọi nhắc
function syncUpcoming_() {
  var url = config_().FLOW_HIS_CRM_URL, c = config_(), today = todayPlus_(0);
  if (!url) return { ok: false, error: 'Chưa khai FLOW_HIS_CRM_URL trong tab CauHinh' };
  // an toàn demo: chỉ đồng bộ số trong DS_SO_THU vì CRM sẽ gọi ra mọi khách có hẹn ngày mai
  var allow = String(c.DS_SO_THU || '').split(/[,;\s]+/).map(normPhone_).filter(String);
  var bn = {}; rows_(SH.BN).forEach(function (b) { bn[b.ma_bn] = b; });
  var res = [];
  rows_(SH.LH).forEach(function (l) {
    var b = bn[l.ma_bn] || {}, sdt = normPhone_(b.sdt_phu_huynh);
    if (ymd_(l.ngay_hen) < today || l.trang_thai !== 'Đã đặt' || allow.indexOf(sdt) < 0) return;
    var it = { ma_bn: l.ma_bn, ho_ten_tre: b.ho_ten_tre, ngay_sinh: fmtDate_(b.ngay_sinh), ho_ten_phu_huynh: b.ho_ten_phu_huynh, sdt: sdt, lich_hen: apptOut_(l) };
    res.push({ ma_lich: l.ma_lich, http: post_(url, payload_(it, 'dong_bo')) });
  });
  return { ok: true, da_gui: res.length, chi_tiet: res };
}
function pushTomorrow_() {
  var url = config_().FLOW_HIS_CRM_URL;
  if (!url) return { ok: false, error: 'Chưa khai FLOW_HIS_CRM_URL trong tab CauHinh' };
  var items = tomorrowItems_(true), res = [];
  items.forEach(function (it) { res.push({ ma_lich: it.lich_hen.ma_lich, http: post_(url, payload_(it, 'nhac_lich')) }); });
  return { ok: true, ngay: todayPlus_(1), da_gui: res.length, tong_lich_ngay_mai: tomorrowItems_(false).length, chi_tiet: res };
}

// ---------- ghi trạng thái xác nhận ----------
function updateStatus_(maLich, trangThai, ghiChu) {
  if (!maLich || !trangThai) return { ok: false, error: 'Thiếu ma_lich hoặc trang_thai' };
  var sh = ss_().getSheetByName(SH.LH), h = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
  var r = rows_(SH.LH).filter(function (l) { return l.ma_lich === maLich; })[0];
  if (!r) return { ok: false, error: 'Không có mã lịch ' + maLich };
  sh.getRange(r._row, h.indexOf('trang_thai') + 1).setValue(trangThai);
  sh.getRange(r._row, h.indexOf('cap_nhat_luc') + 1).setValue(new Date());
  if (ghiChu) sh.getRange(r._row, h.indexOf('ghi_chu') + 1).setValue(ghiChu);
  return { ok: true, ma_lich: maLich, trang_thai: trangThai };
}

// ---------- khởi tạo dữ liệu giả lập ----------
function setup() {
  var s = ss_();
  s.rename('HIS giả lập - Bệnh viện ABC (demo OMICall)');
  s.setSpreadsheetTimeZone(TZ);
  function sheet(name, header, data) {
    var sh = s.getSheetByName(name) || s.insertSheet(name);
    sh.clear(); sh.getRange(1, 1, 1, header.length).setValues([header]).setFontWeight('bold').setBackground('#dbeafe');
    if (data.length) sh.getRange(2, 1, data.length, header.length).setValues(data);
    sh.setFrozenRows(1); sh.autoResizeColumns(1, header.length);
    return sh;
  }
  var bn = [
    ['BN000101', 'Nguyễn Minh Khang', '12/03/2021', 'Nam', 'Nguyễn Thu Hà', '0900000101', 'Đống Đa, Hà Nội'],
    ['BN000102', 'Trần Bảo Ngọc', '05/08/2019', 'Nữ', 'Trần Văn Hùng', '0900000102', 'Cầu Giấy, Hà Nội'],
    ['BN000103', 'Lê Gia Huy', '20/11/2022', 'Nam', 'Lê Thị Mai', '0900000103', 'Thanh Xuân, Hà Nội'],
    ['BN000104', 'Phạm Khánh An', '01/01/2020', 'Nữ', 'Phạm Quốc Toàn', '0900000104', 'Hà Đông, Hà Nội'],
    ['BN000105', 'Vũ Đức Minh', '15/06/2018', 'Nam', 'Vũ Thị Lan', '0900000105', 'TP Bắc Ninh'],
    ['BN000106', 'Đỗ Hà My', '30/09/2023', 'Nữ', 'Đỗ Văn Nam', '0900000106', 'Long Biên, Hà Nội'],
    ['BN000107', 'Hoàng Anh Tuấn', '22/02/2017', 'Nam', 'Hoàng Thị Hoa', '0900000107', 'TP Hải Dương'],
    ['BN000108', 'Bùi Phương Linh', '10/10/2021', 'Nữ', 'Bùi Văn Long', '0900000108', 'Hoàng Mai, Hà Nội'],
    ['BN000109', 'Ngô Thành Đạt', '08/04/2020', 'Nam', 'Ngô Thị Thảo', '0900000109', 'TP Nam Định'],
    ['BN000110', 'Đặng Tuệ Nhi', '25/12/2022', 'Nữ', 'Đặng Minh Quân', '0900000110', 'Tây Hồ, Hà Nội']
  ];
  // ngày hẹn tính theo hôm nay để luôn có lịch T+1 khi demo
  function d(n) { return Utilities.formatDate(new Date(Date.now() + n * 86400000), TZ, 'dd/MM/yyyy'); }
  var lh = [
    ['LH250001', 'BN000101', d(1), '08:00', 'Khoa Hô hấp', 'BS. Nguyễn Văn Bình', 'Phòng khám 12, Nhà A', 'Đã đặt', '', ''],
    ['LH250002', 'BN000102', d(1), '09:30', 'Khoa Tiêu hoá', 'BS. Trần Thị Thu', 'Phòng khám 7, Nhà A', 'Đã đặt', '', ''],
    ['LH250003', 'BN000103', d(1), '14:00', 'Khoa Tim mạch', 'BS. Lê Hoàng Phúc', 'Phòng khám 21, Nhà B', 'Đã đặt', '', ''],
    ['LH250004', 'BN000104', d(2), '08:30', 'Khoa Dinh dưỡng', 'BS. Phạm Thanh Hương', 'Phòng khám 3, Nhà A', 'Đã đặt', '', ''],
    ['LH250005', 'BN000105', d(3), '10:00', 'Trung tâm Quốc tế', 'BS. Đỗ Minh Trí', 'Tầng 2, Nhà Quốc tế', 'Đã đặt', '', ''],
    ['LH250006', 'BN000106', d(1), '15:30', 'Khoa Sơ sinh', 'BS. Vũ Thị Ngọc', 'Phòng khám 5, Nhà C', 'Đã đặt', '', ''],
    ['LH250007', 'BN000107', d(5), '09:00', 'Khoa Thần kinh', 'BS. Hoàng Văn Sơn', 'Phòng khám 15, Nhà B', 'Đã đặt', '', ''],
    ['LH250008', 'BN000108', d(-3), '08:00', 'Khoa Hô hấp', 'BS. Nguyễn Văn Bình', 'Phòng khám 12, Nhà A', 'Đã khám', '', ''],
    ['LH250009', 'BN000109', d(7), '13:30', 'Khoa Tai Mũi Họng', 'BS. Bùi Thị Hằng', 'Phòng khám 9, Nhà A', 'Đã đặt', '', ''],
    ['LH250010', 'BN000110', d(1), '10:30', 'Khoa Da liễu', 'BS. Ngô Quang Huy', 'Phòng khám 18, Nhà B', 'Đã đặt', '', '']
  ];
  sheet(SH.BN, ['ma_bn', 'ho_ten_tre', 'ngay_sinh', 'gioi_tinh', 'ho_ten_phu_huynh', 'sdt_phu_huynh', 'dia_chi'], bn)
    .getRange('C:C').setNumberFormat('@'); // giữ dạng văn bản
  s.getSheetByName(SH.BN).getRange('F:F').setNumberFormat('@');
  s.getSheetByName(SH.BN).getRange(2, 1, bn.length, 7).setValues(bn);
  var shl = sheet(SH.LH, ['ma_lich', 'ma_bn', 'ngay_hen', 'gio_hen', 'khoa', 'bac_si', 'phong', 'trang_thai', 'cap_nhat_luc', 'ghi_chu'], []);
  shl.getRange('C:D').setNumberFormat('@'); shl.getRange(2, 1, lh.length, 10).setValues(lh);
  var ch = s.getSheetByName(SH.CH);
  if (!ch) sheet(SH.CH, ['khoa', 'gia_tri', 'ghi_chu'], [
    ['FLOW_HIS_CRM_URL', '', 'URL kết nối (webhook) của quy trình "HIS -> CRM" trên OMICall'],
    ['DS_SO_THU', '', 'Các SĐT được phép gọi ra nhắc lịch (cách nhau dấu phẩy). Trống = không gọi ai']
  ]);
  sheet(SH.HD, ['thoi_gian', 'du_lieu', 'da_gui'], []);
  if (!s.getSheetByName(SH.NK)) sheet(SH.NK, ['thoi_gian', 'action', 'dau_vao', 'ket_qua'], []);
  var d0 = s.getSheetByName('Sheet1') || s.getSheetByName('Trang tính1'); if (d0 && s.getSheets().length > 1) s.deleteSheet(d0);
  // trigger 1 phút gửi hàng đợi đồng bộ CRM
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'flushSync') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('flushSync').timeBased().everyMinutes(1).create();
  caiHenGioNhacLich();
}
// mỗi giờ đồng bộ lịch hẹn sắp tới sang CRM; việc gọi nhắc lúc 8h do quy trình OMIFlow (trước 1 ngày so với Ngày hẹn) đảm nhận
function caiHenGioNhacLich() {
  ScriptApp.getProjectTriggers().forEach(function (t) { if (/^(nhacLich|dongBoLichHen)/.test(t.getHandlerFunction())) ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('dongBoLichHen').timeBased().everyHours(1).create();
}
function dongBoLichHen() { log_('dongBoLichHen', '', JSON.stringify(syncUpcoming_()).slice(0, 400)); }

// tự kiểm nhanh: chạy trong trình soạn thảo, xem Nhật ký thực thi
function selfTest() {
  if (normPhone_('84900000101') !== '0900000101' || normPhone_('+84 900 000 101') !== '0900000101') throw 'normPhone lỗi';
  var r = lookup_('0900000101'); if (!r.found || !r.lich_hen) throw 'lookup lỗi: ' + JSON.stringify(r);
  if (lookup_('0999999999').found) throw 'lookup số lạ phải found=false';
  Logger.log('OK ' + r.tom_tat + ' | ngày mai: ' + tomorrowItems_(false).length + ' lịch');
}
