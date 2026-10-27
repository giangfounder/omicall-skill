"""Bóc chữ từ tài liệu nghiệp vụ (PDF, DOCX, XLSX, TXT, MD) ra MỘT file văn bản để agent đọc và trích nguồn.

  python <thư mục skill>/scripts/extract_text.py <file...> --out <scratch>/source.txt

- PDF qua pymupdf (`import pymupdf`, bản cũ `fitz`): mỗi trang một khối `=== <file> | trang N ===`.
- DOCX qua python-docx: đoạn văn theo thứ tự, mỗi bảng một khối `--- bảng N ---` (ô cách nhau bằng ` | `).
- XLSX qua openpyxl: mỗi sheet một khối `--- sheet <tên> ---`, dòng đầu là tiêu đề cột, ô cách nhau bằng ` | `.
- TXT, MD, CSV: đọc nguyên văn (UTF-8, thử thêm UTF-8-BOM và cp1258).
In ra stdout một dòng thống kê cho mỗi file: số trang, số bảng / sheet, số ký tự.
Trang PDF không có chữ -> `WARN ... cần OCR / Cần xác nhận` (không tự đoán nội dung).
Thiếu thư viện -> in lệnh pip cần chạy (không tự cài) và bỏ qua file đó (exit 1).
Không gọi mạng. --out bắt buộc; nên đặt trong thư mục scratch, không ghi vào thư mục skill.
Exit: 0 xong; 1 có file không đọc được (thiếu thư viện, định dạng lạ, lỗi đọc) — không đọc được file nào thì
không ghi --out (file cũ cùng tên, nếu có, được báo WARN chứ không xoá); 2 sai cách gọi.
"""
import argparse
import os
import sys

PIP = {'fitz': 'pip install pymupdf', 'docx': 'pip install python-docx', 'openpyxl': 'pip install openpyxl'}


class Missing(Exception):
    pass


def _need(mod):
    try:
        return __import__(mod)
    except ImportError:
        raise Missing('thiếu thư viện %s: chạy `%s` rồi chạy lại' % (mod, PIP[mod]))


def _cell(v):
    if v is None:
        return ''
    s = str(v).replace('\r', ' ').replace('\n', ' / ').strip()
    return s


def _pymupdf():
    try:
        import pymupdf  # tên mới (PyMuPDF >= 1.24)
        return pymupdf
    except ImportError:
        return _need('fitz')


def read_pdf(path):
    fitz = _pymupdf()
    blocks, warns = [], []
    doc = fitz.open(path)
    try:
        n = doc.page_count
        for i in range(n):
            text = doc.load_page(i).get_text('text') or ''
            if not text.strip():
                warns.append('WARN %s trang %d không có chữ — cần OCR / Cần xác nhận nội dung trang này'
                             % (os.path.basename(path), i + 1))
            blocks.append('=== %s | trang %d ===\n%s' % (os.path.basename(path), i + 1, text.strip()))
    finally:
        doc.close()
    return blocks, {'trang': n, 'bang': 0}, warns


def read_docx(path):
    docx = _need('docx')
    d = docx.Document(path)
    out = ['=== %s ===' % os.path.basename(path)]
    body = d.element.body
    tables = {t._tbl: t for t in d.tables}
    paras = {p._p: p for p in d.paragraphs}
    nt = 0
    for child in body.iterchildren():
        if child in paras:
            t = paras[child].text.strip()
            if t:
                out.append(t)
        elif child in tables:
            nt += 1
            out.append('--- bảng %d ---' % nt)
            for row in tables[child].rows:
                out.append(' | '.join(_cell(c.text) for c in row.cells))
    return ['\n'.join(out)], {'trang': None, 'bang': nt}, []


def read_xlsx(path):
    openpyxl = _need('openpyxl')
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = ['=== %s ===' % os.path.basename(path)]
    ns = 0
    try:
        for ws in wb.worksheets:
            ns += 1
            out.append('--- sheet %s ---' % ws.title)
            for row in ws.iter_rows(values_only=True):
                cells = [_cell(v) for v in row]
                while cells and not cells[-1]:
                    cells.pop()
                if cells:
                    out.append(' | '.join(cells))
    finally:
        wb.close()
    return ['\n'.join(out)], {'trang': None, 'bang': ns, 'sheet': ns}, []


def read_txt(path):
    raw = open(path, 'rb').read()
    for enc in ('utf-8-sig', 'utf-8', 'cp1258'):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode('utf-8', 'replace')
    return ['=== %s ===\n%s' % (os.path.basename(path), text.strip())], {'trang': None, 'bang': 0}, []


READERS = {'.pdf': read_pdf, '.docx': read_docx, '.xlsx': read_xlsx, '.xlsm': read_xlsx,
           '.txt': read_txt, '.md': read_txt, '.csv': read_txt}


def extract(paths):
    """Trả về (văn bản gộp, danh sách dòng thống kê/WARN, số file lỗi)."""
    parts, report, bad = [], [], 0
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        name = os.path.basename(p)
        if not os.path.isfile(p):
            report.append('LỖI %s: không thấy file' % p)
            bad += 1
            continue
        fn = READERS.get(ext)
        if fn is None:
            report.append('LỖI %s: chưa hỗ trợ đuôi %s (.doc/.xls cũ: lưu lại thành .docx/.xlsx)' % (name, ext or '(trống)'))
            bad += 1
            continue
        try:
            blocks, st, warns = fn(p)
        except Missing as e:
            report.append('LỖI %s: %s' % (name, e))
            bad += 1
            continue
        except Exception as e:  # file hỏng, có mật khẩu...
            report.append('LỖI %s: không đọc được (%s: %s)' % (name, type(e).__name__, str(e)[:120]))
            bad += 1
            continue
        text = '\n\n'.join(blocks)
        parts.append(text)
        bits = []
        if st.get('trang') is not None:
            bits.append('%d trang' % st['trang'])
        if 'sheet' in st:
            bits.append('%d sheet' % st['sheet'])
        else:
            bits.append('%d bảng' % st['bang'])
        bits.append('%d ký tự' % len(text))
        report.append('OK %s: %s' % (name, ', '.join(bits)))
        report.extend(warns)
    return '\n\n'.join(parts) + ('\n' if parts else ''), report, bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='+')
    ap.add_argument('--out', required=True, help='file văn bản đầu ra (đặt trong scratch)')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    text, report, bad = extract(a.files)
    out = os.path.abspath(a.out)
    if bad >= len(a.files):  # không đọc được file nào: không để lại file rỗng dễ bị coi là kết quả
        for line in report:
            print(line)
        print('Không đọc được file nào — không ghi %s.' % out)
        if os.path.isfile(out):
            print('WARN: %s đã có từ lần chạy trước, KHÔNG phải kết quả của lần này — đừng dùng.' % out)
        return 1
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    for line in report:
        print(line)
    print('Đã ghi %s (%d ký tự). Trích nguồn theo khối "=== file | trang ===" khi phân tích.' % (out, len(text)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
