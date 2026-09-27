#!/usr/bin/env python3
"""انتقال پست‌های کانال عمومی تلگرام به کانال بله (اجرا روی GitHub Actions).

- پست‌ها از صفحه‌ی عمومی https://t.me/s/<channel> خوانده می‌شوند (بدون نیاز به API تلگرام).
- متن تبلیغ ربات پیش‌بینی حذف می‌شود.
- پست‌های تبلیغاتی (به‌ویژه شرط‌بندی/قمار) با فیلتر گسترده رد می‌شوند.
- اگر پستی در تلگرام پاسخ به پست دیگری باشد، در بله هم به همان پیام ریپلای می‌شود.
- چند عکس/ویدیوی پشت‌سرهم با کپشن مشترک (آلبوم) در یک پیام ادغام می‌شوند.
- آخرین پست پردازش‌شده و نگاشت پیام‌ها در state.json ذخیره می‌شود.
"""
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

TG_CHANNEL = os.getenv("TG_CHANNEL", "total_fut").strip().lstrip("@")
STATE_FILE = Path(os.getenv("STATE_FILE", "state.json"))
FIRST_RUN_SEND = int(os.getenv("FIRST_RUN_SEND", "0") or 0)
EXTRA_AD_KEYWORDS = [k.strip() for k in os.getenv("EXTRA_AD_KEYWORDS", "").split(",") if k.strip()]
MAX_MEDIA_BYTES = 45 * 1024 * 1024
MSG_MAP_KEEP = 500  # حداکثر تعداد نگاشت‌های ذخیره‌شده برای ریپلای (جدیدترین‌ها نگه داشته می‌شوند)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# ───────────────────────── حذف متن ثابت ─────────────────────────

REMOVE_LINE_KEYS = [
    "totalpishbinibot",
    "پیشبینیبازیهایلیگبرتر",
]

FOOTER_INLINE_RE = re.compile(
    r"🎖️?\s*پیش[\u200c\s]*بینی[\u200c\s]+بازی[\u200c\s]*های[\u200c\s]+لیگ[\u200c\s]+برتر"
    r"[^\n|]*\|?\s*@?Total_pishbinibot",
    re.IGNORECASE,
)


def squash(s: str) -> str:
    """نرمال‌سازی برای مقایسه: حذف فاصله/نیم‌فاصله/کشیدگی، یکسان‌سازی ی و ک، حروف کوچک."""
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = re.sub(r"[\u0640\u200b\u200c\u200d\u200e\u200f\ufe0f\s\-_.]+", "", s)
    return s.lower()


def clean_text(text: str) -> str:
    text = FOOTER_INLINE_RE.sub("", text)
    kept = []
    for line in text.split("\n"):
        n = squash(line)
        if any(k in n for k in REMOVE_LINE_KEYS):
            continue
        kept.append(line.rstrip())
    out = "\n".join(kept)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


# ───────────────────────── تشخیص تبلیغ (شرط‌بندی/قمار) ─────────────────────────
#
# چون تبلیغ شرط‌بندی/قمار در کانال بله جرم محسوب می‌شود، این فیلتر عمداً
# گسترده و چندلایه نوشته شده: کلمات فارسی/عربی/انگلیسی رایج، اسم سایت‌های
# شناخته‌شده، و بازی‌های قمار محبوب (مثل «انفجار»، «پاسور شرطی»). اگر
# کلمه‌ی جدیدی دیدی که رد نشده، به EXTRA_AD_KEYWORDS (در Variables ریپو،
# با کاما جدا) اضافه‌اش کن؛ نیازی به تغییر کد نیست.

AD_PATTERNS = [
    # کلمه‌ی مستقل «بت» (نه بخشی از «ثبت»/«ثابت» و…)
    r"(?<![\u0600-\u06FF])بت(?![\u0600-\u06FF])",
    r"شرط[\u200c\s]*بند",
    r"شرط[\u200c\s]*بندی",
    r"بتینگ|betting",
    r"کازینو|casino",
    r"قمار|gambl",
    r"پوکر[\u200c\s]*(آنلاین|شرطی)?",
    r"رولت(?!\s*کاری)",  # روتل/رولت شرط‌بندی؛ حواسش به کلمات بی‌ربط هست
    r"بازی[\u200c\s]*انفجار|انفجار[\u200c\s]*شرطی",
    r"پاسور[\u200c\s]*شرطی|تخته[\u200c\s]*نرد[\u200c\s]*شرطی",
    r"بونوس|بونس",
    r"کد[\u200c\s]*هدیه|کد[\u200c\s]*تخفیف[\u200c\s]*شرط",
    r"کد[\u200c\s]*پروموشن|پرومو[\u200c\s]*کد",
    r"کد[\u200c\s]*معرف",
    r"برداشت[\u200c\s]*آنی|واریز[\u200c\s]*(و|,)?\s*برداشت",
    r"درگاه[\u200c\s]*(بانکی|واریز|شارژ)",
    r"شارژ[\u200c\s]*حساب",
    r"سایت[\u200c\s]*شرط|اپلیکیشن[\u200c\s]*شرط|اپ[\u200c\s]*شرط",
    r"مینی[\u200c\s]*اپ",  # اصطلاح رایج تبلیغ ربات‌های شرط‌بندی تلگرامی
    r"ضریب[\u200c\s]*(بالا|سود|برد)",
    r"برد[\u200c\s]*تضمینی|سود[\u200c\s]*تضمینی",
    r"ثبت[\u200c\s]*نام[\u200c\s]*رایگان[\u200c\s]*(و|,)?\s*(دریافت)?[\u200c\s]*(بونوس|هدیه)",
    # سه عدد اعشاری پشت‌سرهم مثل «8.71  5.40  1.30» یعنی ضریب شرط‌بندی
    r"\b\d{1,2}\.\d{1,2}\s+\d{1,2}\.\d{1,2}\s+\d{1,2}\.\d{1,2}\b",
    r"تبلیغ",
    r"وینکو[\u200c\s]*بت|wincobet",
    r"اسپورت[\u200c\s]*نود|sport[\u200c\s]*90|sportnavad",
    # اسم سایت‌های شناخته‌شده‌ی شرط‌بندی (فارسی/انگلیسی)
    r"1[\u200c\s]*x[\u200c\s]*bet|bet[\u200c\s]*365|bet[\u200c\s]*winner|mel[\u200c\s]*bet|"
    r"most[\u200c\s]*bet|1[\u200c\s]*win|pin[\u200c\s-]*up|pari[\u200c\s]*match|line[\u200c\s]*bet|"
    r"22[\u200c\s]*bet|dafa[\u200c\s]*bet|wolf[\u200c\s]*bet|tiny[\u200c\s]*bet|"
    r"تک[\u200c\s]*بت|حضرات[\u200c\s]*بت|بتفا|سیب[\u200c\s]*بت|هیجان[\u200c\s]*بت|تتل[\u200c\s]*بت",
    r"\bbonus\b|promo[\s_-]?code",
]
AD_RE = re.compile("|".join(AD_PATTERNS), re.IGNORECASE)

AD_HOST_KEYWORDS = [
    "bet", "1win", "pinup", "pin-up", "casino", "gambl", "parimatch", "melbet",
    "mostbet", "dafabet", "linebet", "22bet", "1xbet", "wolfbet", "tinybet",
]
AD_HOST_RE = re.compile("|".join(re.escape(k) for k in AD_HOST_KEYWORDS), re.IGNORECASE)


def is_ad(text: str, links: list) -> bool:
    t = text.replace("ي", "ی").replace("ك", "ک")
    if AD_RE.search(t):
        return True
    sq = squash(t)
    if any(squash(k) in sq for k in EXTRA_AD_KEYWORDS):
        return True
    for href in links:
        host = urlparse(href).netloc
        if host and host not in ("t.me", "telegram.me") and AD_HOST_RE.search(host):
            return True
    return False


# ───────────────────────── خواندن از تلگرام ─────────────────────────


@dataclass
class Post:
    id: int
    text: str = ""
    links: list = field(default_factory=list)
    photos: list = field(default_factory=list)
    videos: list = field(default_factory=list)
    audios: list = field(default_factory=list)
    reply_to: int = None  # آیدی پستی که این پست در تلگرام پاسخ آن است (اگر باشد)


def element_to_text(el):
    if el is None:
        return "", []
    links = []
    for br in el.find_all("br"):
        br.replace_with("\n")
    for a in el.find_all("a", href=True):
        href = a["href"]
        label = a.get_text().strip()
        if href.startswith("http"):
            links.append(href)
            if label and not label.startswith(("@", "#", "http")) and "t.me" not in href:
                a.replace_with(f"{label} ({href})")
    return el.get_text().strip(), links


REPLY_ID_RE = re.compile(r"/(\d+)(?:\?single)?/?$")


def extract_reply_id(w) -> int:
    """اگر این پست در تلگرام پاسخ به پست دیگری در همین کانال باشد، آیدی آن
    پست را برمی‌گرداند؛ وگرنه None."""
    a = w.select_one("a.tgme_widget_message_reply")
    if not a:
        return None
    href = a.get("href", "")
    m = REPLY_ID_RE.search(href)
    return int(m.group(1)) if m else None


def fetch_posts() -> list:
    r = requests.get(f"https://t.me/s/{TG_CHANNEL}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    posts = []
    for w in soup.select("div.tgme_widget_message"):
        data_post = w.get("data-post", "")
        if "/" not in data_post:
            continue
        try:
            pid = int(data_post.split("/")[-1])
        except ValueError:
            continue
        text_el = w.select_one("div.tgme_widget_message_text.js-message_text")
        text, links = element_to_text(text_el)
        p = Post(id=pid, text=text, links=links, reply_to=extract_reply_id(w))
        for a in w.select("a.tgme_widget_message_photo_wrap"):
            m = re.search(r"url\(['\"]?([^'\")]+)['\"]?\)", a.get("style", ""))
            if m:
                p.photos.append(m.group(1))
        p.videos = [v["src"] for v in w.select("video[src]")]
        p.audios = [a["src"] for a in w.select("audio[src]")]
        posts.append(p)
    return posts


# ───────────────────────── ارسال به بله ─────────────────────────


class Bale:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://tapi.bale.ai/bot{token}"
        self.chat_id = chat_id

    def call(self, method: str, data=None, files=None, retries=3):
        data = dict(data or {})
        data["chat_id"] = self.chat_id
        for attempt in range(1, retries + 1):
            r = requests.post(f"{self.base}/{method}", data=data, files=files, timeout=180)
            try:
                j = r.json()
            except ValueError:
                j = {}
            if r.ok and j.get("ok", True):
                return j
            if r.status_code == 429:
                wait = j.get("parameters", {}).get("retry_after", 5)
                time.sleep(min(int(wait), 60))
                continue
            if attempt == retries:
                raise RuntimeError(f"{method} failed [{r.status_code}]: {r.text[:300]}")
            time.sleep(2 * attempt)

    @staticmethod
    def _msg_id(resp):
        if not resp:
            return None
        result = resp.get("result") if isinstance(resp, dict) else None
        if isinstance(result, dict):
            return result.get("message_id")
        return None

    def send_text(self, text: str, reply_to_message_id=None):
        last_id = None
        for i in range(0, len(text), 4000):
            data = {"text": text[i : i + 4000]}
            if reply_to_message_id and i == 0:
                data["reply_to_message_id"] = reply_to_message_id
            last_id = self._msg_id(self.call("sendMessage", data)) or last_id
        return last_id

    def send_media(self, kind: str, url: str, caption: str = "", reply_to_message_id=None):
        """kind: photo | video | audio. فایل دانلود و آپلود می‌شود. آیدی پیام ارسال‌شده را برمی‌گرداند."""
        resp = requests.get(url, headers=HEADERS, timeout=120, stream=True)
        resp.raise_for_status()
        size = int(resp.headers.get("Content-Length", 0))
        if size > MAX_MEDIA_BYTES:
            raise RuntimeError("media too large")
        content = resp.content
        if len(content) > MAX_MEDIA_BYTES:
            raise RuntimeError("media too large")
        ext = {"photo": "jpg", "video": "mp4", "audio": "ogg"}[kind]
        method = {"photo": "sendPhoto", "video": "sendVideo", "audio": "sendAudio"}[kind]
        data = {"caption": caption} if caption else {}
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        try:
            r = self.call(method, data, files={kind: (f"file.{ext}", content)})
        except Exception as e:
            print(f"  {method} failed ({e}); trying sendDocument")
            r = self.call("sendDocument", data, files={"document": (f"file.{ext}", content)})
        return self._msg_id(r)


def send_post(bale: Bale, post: Post, text: str, reply_to_message_id=None):
    """پست را می‌فرستد و آیدی پیامِ حامل کپشن (برای نگاشتِ ریپلای در آینده) را برمی‌گرداند."""
    media = (
        [("photo", u) for u in post.photos]
        + [("video", u) for u in post.videos]
        + [("audio", u) for u in post.audios]
    )
    sent_any = False
    caption_fits = len(text) <= 1000
    last_msg_id = None
    for i, (kind, url) in enumerate(media):
        last = i == len(media) - 1
        cap = text if (last and caption_fits) else ""
        rid = reply_to_message_id if i == 0 else None
        try:
            last_msg_id = bale.send_media(kind, url, cap, reply_to_message_id=rid) or last_msg_id
            sent_any = True
            if last and caption_fits:
                return last_msg_id
        except Exception as e:  # اگر مدیا نرفت، حداقل متن ارسال شود
            print(f"  media skipped: {e}")
    if text:
        last_msg_id = bale.send_text(text, reply_to_message_id=reply_to_message_id) or last_msg_id
    elif not sent_any and media:
        print("  nothing could be sent for this post")
    return last_msg_id


# ───────────────────────── حالت و اجرای اصلی ─────────────────────────


def load_state():
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
        except ValueError:
            return {"last_id": None, "msg_map": {}}
        if "msg_map" not in data:
            data["msg_map"] = {}
        return data
    return {"last_id": None, "msg_map": {}}


def save_state(state):
    # فقط جدیدترین نگاشت‌ها را نگه می‌داریم تا فایل بی‌نهایت بزرگ نشود
    if len(state["msg_map"]) > MSG_MAP_KEEP:
        items = list(state["msg_map"].items())[-MSG_MAP_KEEP:]
        state["msg_map"] = dict(items)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def merge_albums(posts):
    """چند پست پشت‌سرهم با آیدی متوالی که بخشی از یک آلبوم عکس/ویدیوی
    تلگرام هستند را در یک پست ادغام می‌کند تا کپشن فقط یک‌بار فرستاده شود.

    تلگرام گاهی کپشن مشترک را روی هر عضو آلبوم تکرار می‌کند و گاهی فقط
    روی یکی از آن‌ها می‌گذارد (بقیه متن خالی دارند)؛ هر دو حالت اینجا
    پوشش داده می‌شود. فقط زمانی ادغام می‌شود که آیدی‌ها دقیقاً پشت‌سرهم
    باشند و آیتم بعدی هم رسانه (عکس/ویدیو/صدا) داشته باشد."""
    merged = []
    i, n = 0, len(posts)
    while i < n:
        p = posts[i]
        rep_text = p.text
        group_ids = [p.id]
        photos, videos, audios = list(p.photos), list(p.videos), list(p.audios)
        reply_to = p.reply_to
        j = i + 1
        p_has_media = bool(p.photos or p.videos or p.audios)
        while p_has_media and j < n and posts[j].id == posts[j - 1].id + 1:
            nxt = posts[j]
            has_media = bool(nxt.photos or nxt.videos or nxt.audios)
            if not has_media:
                break
            rep_clean = clean_text(rep_text)
            nxt_clean = clean_text(nxt.text)
            if not (not rep_clean or not nxt_clean or rep_clean == nxt_clean):
                break  # کپشن‌های متفاوت و هر دو غیرخالی؛ یعنی پست جدای دیگری است
            if not rep_clean and nxt_clean:
                rep_text = nxt.text
            group_ids.append(nxt.id)
            photos.extend(nxt.photos)
            videos.extend(nxt.videos)
            audios.extend(nxt.audios)
            reply_to = reply_to or nxt.reply_to
            j += 1
        rep = Post(id=p.id, text=rep_text, links=p.links, photos=photos, videos=videos,
                   audios=audios, reply_to=reply_to)
        merged.append((group_ids, rep))
        i = j
    return merged


def main() -> int:
    token = os.environ.get("BALE_BOT_TOKEN")
    chat_id = os.environ.get("BALE_CHAT_ID")
    if not token or not chat_id:
        print("BALE_BOT_TOKEN and BALE_CHAT_ID must be set", file=sys.stderr)
        return 1

    posts = sorted(fetch_posts(), key=lambda p: p.id)
    if not posts:
        print("no posts found (channel not public, or page layout changed?)")
        return 0

    state = load_state()
    last_id = state.get("last_id")
    if last_id is None:
        ids = [p.id for p in posts]
        n = FIRST_RUN_SEND
        last_id = ids[-n - 1] if 0 < n < len(ids) else (ids[-1] if n == 0 else 0)
        state["last_id"] = last_id
        save_state(state)
        print(f"first run: baseline last_id={last_id}")

    bale = Bale(token, chat_id)
    new_posts = [p for p in posts if p.id > last_id]
    groups = merge_albums(new_posts)
    print(f"{len(new_posts)} new post(s) in {len(groups)} group(s)")

    for group_ids, p in groups:
        text = clean_text(p.text)
        has_media = bool(p.photos or p.videos or p.audios)
        if len(group_ids) > 1:
            print(f"#{group_ids[0]}-{group_ids[-1]}: album of {len(group_ids)} merged")

        reply_to_bale_id = None
        if p.reply_to is not None:
            reply_to_bale_id = state["msg_map"].get(str(p.reply_to))
            if reply_to_bale_id:
                print(f"#{p.id}: reply to tg#{p.reply_to} -> bale#{reply_to_bale_id}")
            else:
                print(f"#{p.id}: reply to tg#{p.reply_to} (not in our history, sending normally)")

        if is_ad(text, p.links):
            print(f"#{p.id}: ad -> skipped")
        elif not text and not has_media:
            print(f"#{p.id}: empty after cleaning -> skipped")
        else:
            try:
                sent_msg_id = send_post(bale, p, text, reply_to_message_id=reply_to_bale_id)
                if sent_msg_id:
                    for gid in group_ids:
                        state["msg_map"][str(gid)] = sent_msg_id
                print(f"#{p.id}: sent")
            except Exception as e:
                print(f"#{p.id}: FAILED ({e}); will retry next run", file=sys.stderr)
                return 1

        state["last_id"] = max(group_ids)
        save_state(state)
        time.sleep(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
