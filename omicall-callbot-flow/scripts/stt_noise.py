"""Giả lập chữ do STT tiếng Việt ghi ra từ cuộc gọi tổng đài (dùng chung mọi dự án).

- STT chỉ ra tiếng Việt: từ tiếng Anh, tên sản phẩm/ứng dụng bị phiên âm.
- Âm thanh điện thoại + giọng vùng miền: nghe nhầm âm gần (gi/d, n/ng, t/c cuối, hỏi/ngã).
- Lời nói tự nhiên: từ đệm, lặp từ đầu câu, ngắt lời, câu bị cắt cuối.
Đoạn thực thể đánh dấu [..]: phiên âm/nghe nhầm áp dụng cả trong đoạn (để khớp chữ STT),
từ đệm/lặp/cắt câu chỉ ngoài đoạn. Tên riêng của dự án thêm bằng extend().
"""
import random
import re

# tiếng Anh hay gặp khi gọi điện → cách STT tiếng Việt ghi ra
EN_VI = [
    (r"\bhotline\b", ["hót lai", "hốt lai", "hót lây"]),
    (r"\bdeadline\b", ["đét lai"]),
    (r"\bonline\b", ["on lai", "ôn lai"]),
    (r"\boffline\b", ["óp lai"]),
    (r"\bzalo\b", ["da lô", "za lô"]),
    (r"\bfacebook\b", ["phây búc", "phê búc"]),
    (r"\bemail\b", ["i meo", "e meo"]),
    (r"\bmail\b", ["meo"]),
    (r"\bvoucher\b", ["vau chơ", "vâu chơ"]),
    (r"\bcode\b", ["cốt", "cốp"]),
    (r"\blink\b", ["linh", "lin"]),
    (r"\bcheck\b", ["chéc", "chẹc"]),
    (r"\bbooking\b", ["búc kinh", "bút kinh"]),
    (r"\bbook\b", ["búc"]),
    (r"\border\b", ["o đơ", "ọt đơ"]),
    (r"\bship\b", ["síp", "síp"]),
    (r"\bshipper\b", ["síp pơ", "síp bơ"]),
    (r"\bshop\b", ["sốp", "shốp"]),
    (r"\bsale\b", ["seo", "sêu"]),
    (r"\bcancel\b", ["ken xồ", "can xồ"]),
    (r"\bcard\b", ["các", "cạc"]),
    (r"\bvisa\b", ["vi sa"]),
    (r"\bwifi\b", ["oai phai", "quai phai"]),
    (r"\binternet\b", ["in tơ nét"]),
    (r"\bapp\b", ["áp", "ép"]),
    (r"\bfree\b", ["phri", "phờ ri", "pri"]),
    (r"\bok\b", ["ô kê", "ô kê", "ô kế", "ô cê"]),
    (r"\bsms\b", ["ét em ét"]),
    (r"\botp\b", ["ô tê pê"]),
    (r"\bqr\b", ["qui a", "cu a"]),
]
# nghe nhầm âm gần (từ → cách STT có thể ghi). Không đưa từ phổ biến mà mô hình ngôn ngữ luôn sửa đúng ("rồi", "giờ")
# và không đổi làm câu lệch sang ý định khác ("quà" → "qua").
CONFUSE = [
    (r"\bgiùm\b", ["dùm"]), (r"\bgiấy\b", ["dấy"]), (r"\bvậy\b", ["dậy", "dị"]), (r"\bkhông\b", ["hông", "hổng"]),
    (r"\bnghen\b", ["nhen", "nghe"]), (r"\bbao nhiêu\b", ["bao nhiu"]), (r"\bnhiêu\b", ["nhiu"]), (r"\bchút\b", ["chúc"]),
    (r"\bbiết\b", ["biếc"]), (r"\bmuốn\b", ["muống"]), (r"\bthứ bảy\b", ["thứ bẩy"]), (r"\bchủ nhật\b", ["chủ nhựt"]),
    (r"\bkỹ\b", ["kĩ"]), (r"\bkỳ\b", ["kì"]), (r"\btổng đài\b", ["tổng đái"]), (r"\bphí\b", ["phi"]),
    (r"\bnhân viên\b", ["nhân viêng"]), (r"\bđường\b", ["đườn"]), (r"\bnói\b", ["nối"]), (r"\bbảo dưỡng\b", ["bảo dưởng"]),
    (r"\bưu đãi\b", ["ưu đải", "ưu đài"]), (r"\bhạn\b", ["hạng"]),
]
FILLERS = ["ờ", "à", "ừm", "ơ", "alo", "alo alo", "hả", "dạ dạ", "ờ ờ", "à à", "ủa", "ơ kìa"]
INTERRUPT = ["khoan khoan", "từ từ", "chờ chút", "hả gì", "khoan đã"]
P = dict(confuse=.45, filler=.30, interrupt=.05, repeat=.12, truncate=.10)


def extend(en_vi=None, confuse=None, fillers=None):
    """Thêm bảng riêng của dự án: en_vi/confuse = [[regex, [cách ghi...]], ...]."""
    for pat, opts in (en_vi or []):
        EN_VI.insert(0, (pat, list(opts)))  # tên riêng dài khớp trước
    for pat, opts in (confuse or []):
        CONFUSE.append((pat, list(opts)))
    FILLERS.extend(fillers or [])


def _sub_once(text, rules, k=1):
    hits = [(pat, opts) for pat, opts in rules if re.search(pat, text)]
    random.shuffle(hits)
    for pat, opts in hits[:k]:
        text = re.sub(pat, lambda m: random.choice(opts), text, count=1)
    return text


def phonetize(text):
    """Chỉ phiên âm tiếng Anh/tên riêng (STT luôn làm)."""
    for pat, opts in EN_VI:
        text = re.sub(pat, lambda m, o=opts: random.choice(o), text)
    return text


def stt(marked, noisy=True):
    """marked: câu có thể chứa [đoạn thực thể]. Trả câu dạng STT (giữ dấu [..])."""
    t = phonetize(marked)
    if not noisy:
        return t
    if random.random() < P["confuse"]:
        t = _sub_once(t, CONFUSE, k=random.choice([1, 1, 2]))
    head, sep, rest = t.partition("[")
    if random.random() < P["filler"]:
        head = random.choice(FILLERS) + " " + head
    if random.random() < P["interrupt"]:
        head = random.choice(INTERRUPT) + " " + head
    w = head.split()
    if w and random.random() < P["repeat"] and w[0] not in ("alo",):
        w.insert(0, w[0])
    head = " ".join(w)
    t = (head + " " + sep + rest).strip() if sep else head
    words = t.split()
    if words and "]" not in words[-1] and len(words) > 5 and random.random() < P["truncate"]:
        t = " ".join(words[:-1])
    return re.sub(r"\s+", " ", t).strip()


def has_english(text):
    return any(re.search(pat, text) for pat, _ in EN_VI)
