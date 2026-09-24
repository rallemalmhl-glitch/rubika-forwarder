#!/usr/bin/env python3
"""ربات انتقال گل و خلاصه‌بازی از چند کانال تلگرام به کانال روبیکا.

نسخه‌ی Telethon: به‌جای خواندن صفحه‌ی عمومی تلگرام، با یک اکانت شخصی
(از طریق Session String) مستقیم به پیام‌های کانال‌ها وصل می‌شود. این‌طور
ویدیوی خلاصه‌بازی‌های حجیم هم قابل دریافت است (نه فقط پست‌های کوچک).

فقط پست‌هایی که «گل» یا «خلاصه بازی» تشخیص داده بشن با قالب اختصاصی
به روبیکا فرستاده می‌شن. بقیه‌ی پست‌ها (حاشیه، خبر، تبلیغ) نادیده گرفته
می‌شن. برای هر بازی، فقط اولین کانالی که یک گل/خلاصه رو گزارش کنه
معتبره؛ نسخه‌های تکراری از کانال‌های بعدی رد می‌شن.
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
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

import data

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# ترتیب اولویت کانال‌ها: اولین کانالی که یک گل/خلاصه رو بگه معتبره.
SOURCE_CHANNELS = [
    c.strip().lstrip("@")
    for c in os.getenv(
        "TG_CHANNELS",
        "futtrue,Footballigool,bisbado,ArabicMatch360,LaLiga360",
    ).split(",")
    if c.strip()
]

STATE_FILE = Path(os.getenv("STATE_FILE", "state.json"))
FIRST_RUN_SEND = int(os.getenv("FIRST_RUN_SEND", "0") or 0)
DEDUPE_KEEP_DAYS = int(os.getenv("DEDUPE_KEEP_DAYS", "10") or 10)
FETCH_LIMIT = int(os.getenv("TELETHON_FETCH_LIMIT", "40") or 40)
MAX_MEDIA_BYTES = int(os.getenv("MAX_MEDIA_BYTES", str(80 * 1024 * 1024)))

RUBIKA_TOKEN = os.environ.get("RUBIKA_BOT_TOKEN")
RUBIKA_CHAT_ID = os.environ.get("RUBIKA_CHAT_ID")
RUBIKA_API = "https://botapi.rubika.ir/v3"

TELEGRAM_API_ID = os.environ.get("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH")
TELEGRAM_SESSION = os.environ.get("TELEGRAM_SESSION")

FOOTER = "🎨⚽ @fotballart"

# ---------- normalization helpers ----------

FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
EN_DIGITS = "0123456789"
CIRCLED = {
    "0⃣": "0", "1⃣": "1", "2⃣": "2", "3⃣": "3", "4⃣": "4",
    "5⃣": "5", "6⃣": "6", "7⃣": "7", "8⃣": "8", "9⃣": "9",
    "🔟": "10",
}


def to_ascii_digits(s: str) -> str:
    for fa, en in zip(FA_DIGITS, EN_DIGITS):
        s = s.replace(fa, en)
    for ar, en in zip(AR_DIGITS, EN_DIGITS):
        s = s.replace(ar, en)
    for circ, en in CIRCLED.items():
        s = s.replace(circ, en)
    return s


def squash(s: str) -> str:
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه")
    s = re.sub(r"[\u200c\u200d\u200e\u200f\ufe0f\s\-_.]+", "", s)
    return s.lower()


def to_persian_digits(n) -> str:
    s = str(n)
    return "".join(FA_DIGITS[int(c)] if c.isdigit() else c for c in s)


CIRCLED_FA = {
    "0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣",
    "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣", "10": "🔟",
}


def circled_digit(n) -> str:
    return CIRCLED_FA.get(str(n), str(n))


# ---------- team lookup ----------


class Team:
    __slots__ = ("name", "aliases", "flag", "important")

    def __init__(self, name, aliases, flag, important):
        self.name = name
        self.aliases = aliases
        self.flag = flag
        self.important = important


TEAMS: list[Team] = []
ALIAS_INDEX: dict[str, Team] = {}


def _load_teams():
    for line in data.TEAM_LINES.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        names_part, flag, important = line.split(";")
        names = names_part.split("|")
        t = Team(names[0], names, flag, important == "1")
        TEAMS.append(t)
        for n in names:
            ALIAS_INDEX[squash(n)] = t


_load_teams()
_SORTED_ALIASES = sorted(ALIAS_INDEX.keys(), key=len, reverse=True)


def _letters_only(s: str) -> str:
    return "".join(ch for ch in s if ch.isalpha())


def _teams_in_fused_chunk(chunk: str):
    results = []
    pos = 0
    n = len(chunk)
    while pos < n:
        matched = False
        for alias in _SORTED_ALIASES:
            L = len(alias)
            if L and chunk[pos : pos + L] == alias:
                results.append(ALIAS_INDEX[alias])
                pos += L
                matched = True
                break
        if not matched:
            pos += 1
    return results


def find_all_teams(raw_text: str):
    chunks = [squash(_letters_only(c)) for c in raw_text.split()]
    n = len(chunks)
    found = []
    seen = set()
    i = 0
    while i < n:
        matched_team = None
        matched_span = 0
        for span in (3, 2, 1):
            if i + span <= n:
                combo = "".join(chunks[i : i + span])
                if combo and combo in ALIAS_INDEX:
                    matched_team = ALIAS_INDEX[combo]
                    matched_span = span
                    break
        if matched_team:
            if matched_team.name not in seen:
                seen.add(matched_team.name)
                found.append(matched_team)
            i += matched_span
            continue

        for team in _teams_in_fused_chunk(chunks[i]):
            if team.name not in seen:
                seen.add(team.name)
                found.append(team)
        i += 1

    return found


def detect_flag(raw_text: str, teams: list) -> str:
    for m in re.finditer(r"[\U0001F1E6-\U0001F1FF]{2}", raw_text):
        return m.group(0)
    for pattern, flag in data.FLAG_HINTS:
        if re.search(pattern, raw_text, re.IGNORECASE):
            return flag
    for t in teams:
        if t.flag:
            return t.flag
    return ""


# ---------- ad filter ----------

AD_PATTERNS = [
    r"(?<![\u0600-\u06FF])بت(?![\u0600-\u06FF])",
    r"شرط[\u200c\s]*بند",
    r"بتینگ",
    r"کازینو",
    r"بونوس",
    r"کد[\u200c\s]*پروموشن",
    r"کد[\u200c\s]*معرف",
    r"برداشت[\u200c\s]*آنی",
    r"سایت[\u200c\s]*شرط",
    r"دانلود\s*اپلیکیشن|\bapk\b",
    r"1xbet|bet365|betwinner|melbet|mostbet|1win|pin-?up|parimatch|linebet|22bet|betting|casino",
    r"\bbonus\b|promo[\s_-]?code",
]
AD_RE = re.compile("|".join(AD_PATTERNS), re.IGNORECASE)
AD_HOST_RE = re.compile(r"bet|1win|pinup|casino|gambl|parimatch", re.IGNORECASE)


def is_ad(text: str, links: list) -> bool:
    t = text.replace("ي", "ی").replace("ك", "ک")
    if AD_RE.search(t):
        return True
    for href in links:
        host = urlparse(href).netloc
        if host and host not in ("t.me", "telegram.me") and AD_HOST_RE.search(host):
            return True
    return False


# ---------- translation (best effort, Arabic -> Persian) ----------


def looks_arabic_only(s: str) -> bool:
    if not re.search(r"[\u0600-\u06FF]", s):
        return False
    if re.search(r"[پچژگی]", s):
        return False
    return True


def translate_to_persian(text: str):
    if not text or not looks_arabic_only(text):
        return text
    try:
        from deep_translator import GoogleTranslator

        return GoogleTranslator(source="ar", target="fa").translate(text)
    except Exception as e:
        print(f"  translate failed: {e}")
        return None


# ---------- classification & extraction ----------

GOAL_WORD_RE = re.compile(r"گل[\u200c]?\s")
SUMMARY_HINT_RE = re.compile(r"خلاصه[\u200c\s]*بازی|خلاصه[\u200c\s]*مسابقه|ملخص\s*مباراة")
FULL_MATCH_RE = re.compile(r"بازی[\u200c\s]*کامل|مباراة\s*كاملة|full\s*match")
MINUTE_RE = re.compile(r"دقیق[هة]\s*[:\-]?\s*([0-9]{1,3})")
ORDINAL_RE = re.compile(
    r"گل\s*(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم)"
)
SCORE_PAIR_RE = re.compile(r"([0-9]{1,2})\s*[-–\u2013:]\s*([0-9]{1,2})")
VS_SCORE_RE = re.compile(r"([0-9]{1,2})\s*(?:🆚|vs|-)\s*([0-9]{1,2})")


FOOTER_MARK_RE = re.compile(r"[🔘🆔]")


def main_segment(raw_text: str) -> str:
    """بخش اصلی پست را برمی‌گرداند: قبل از امضای کانال (🔘/🆔)، تا اسم تیم
    به‌اشتباه از هشتگ یا امضا برداشته نشود."""
    m = FOOTER_MARK_RE.search(raw_text)
    return raw_text[: m.start()] if m else raw_text


def classify(raw_text: str) -> str:
    if FULL_MATCH_RE.search(raw_text):
        return "skip"
    if SUMMARY_HINT_RE.search(raw_text):
        return "summary"
    if GOAL_WORD_RE.search(raw_text):
        return "goal"
    ascii_text = to_ascii_digits(raw_text)
    if MINUTE_RE.search(ascii_text) and SCORE_PAIR_RE.search(ascii_text):
        teams = find_all_teams(main_segment(raw_text))
        if len(teams) >= 2:
            return "goal"
    return "other"


def extract_goal(raw_text: str, ascii_text: str):
    seg = main_segment(raw_text)
    teams = find_all_teams(seg)
    if len(teams) < 2:
        return None
    scorer_team, conceding_team = teams[0], teams[1]

    m = MINUTE_RE.search(to_ascii_digits(seg))
    minute = int(m.group(1)) if m else None

    scores = SCORE_PAIR_RE.findall(to_ascii_digits(seg))
    score_a = score_b = None
    if scores:
        score_a, score_b = (int(x) for x in scores[-1])

    om = ORDINAL_RE.search(seg)
    ordinal = data.ORDINALS.get(om.group(1)) if om else None

    scorer = None
    sm = re.search(r"توسط\s+([^\n\r|,،.]+)", seg)
    if sm:
        scorer = sm.group(1).strip(" .!،")
        scorer = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", scorer).strip()

    return {
        "team_a": scorer_team,
        "team_b": conceding_team,
        "minute": minute,
        "score_a": score_a,
        "score_b": score_b,
        "ordinal": ordinal,
        "scorer": scorer,
    }


WEEK_RE = re.compile(r"هفته\s*([۰-۹0-9]+|اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم)[^|\n]*")
FINAL_RE = re.compile(r"فینال[^|\n]*")
REPORT_LANG_RE = re.compile(r"\s*(?:با\s*گزارش(?:ِ)?\s*[\"«].*)$")


def clean_stage(stage: str) -> str:
    stage = REPORT_LANG_RE.sub("", stage)
    return stage.strip(" |")


def extract_summary(raw_text: str, ascii_text: str):
    seg = main_segment(raw_text)
    team_part = seg.split("||")[0] if "||" in seg else seg

    teams = find_all_teams(team_part)
    if len(teams) < 2:
        return None
    team1, team2 = teams[0], teams[1]

    ascii_team_part = to_ascii_digits(team_part)
    scores = VS_SCORE_RE.findall(ascii_team_part) or SCORE_PAIR_RE.findall(ascii_team_part)
    if not scores:
        return None
    score1, score2 = (int(x) for x in scores[0])

    stage = None
    fm = FINAL_RE.search(seg)
    wm = WEEK_RE.search(seg)
    if fm:
        stage = clean_stage(fm.group(0))
    elif wm:
        stage = clean_stage(wm.group(0))

    return {
        "team1": team1, "score1": score1,
        "team2": team2, "score2": score2,
        "stage": stage,
    }


def order_summary_teams(team1, score1, team2, score2, host_is_team1=True):
    if score1 == score2:
        if team1.important and not team2.important:
            return team1, score1, team2, score2
        if team2.important and not team1.important:
            return team2, score2, team1, score1
        return (team1, score1, team2, score2) if host_is_team1 else (team2, score2, team1, score1)
    if score1 > score2:
        return team1, score1, team2, score2
    return team2, score2, team1, score1


# ---------- formatting ----------


def format_goal(g: dict) -> str:
    team_a, team_b = g["team_a"], g["team_b"]
    lines = []
    ordinal_word = None
    if g["ordinal"]:
        rev = {v: k for k, v in data.ORDINALS.items()}
        ordinal_word = rev.get(g["ordinal"])

    head = f"⚽ گل {ordinal_word or ''} {team_a.name} به {team_b.name}".replace("  ", " ").strip()
    lines.append(head)
    if g["scorer"] and g["minute"]:
        lines.append(f"توسط {g['scorer']} در دقیقه {to_persian_digits(g['minute'])}")
    elif g["scorer"]:
        lines.append(f"توسط {g['scorer']}")
    elif g["minute"]:
        lines.append(f"در دقیقه {to_persian_digits(g['minute'])}")
    lines.append("")
    if g["score_a"] is not None and g["score_b"] is not None:
        lines.append(f"{team_a.name} ({to_persian_digits(g['score_a'])})")
        lines.append(f"{team_b.name} ({to_persian_digits(g['score_b'])})")
    lines.append("")
    lines.append(FOOTER)
    return "\n".join(lines)


def format_summary(s: dict) -> str:
    t1, sc1, t2, sc2 = order_summary_teams(s["team1"], s["score1"], s["team2"], s["score2"])
    flag = s.get("flag", "")
    lines = ["🎬 #خلاصه_بازی"]
    if flag:
        lines.append(flag)
    lines.append(f"{t1.name} {circled_digit(sc1)} ـ {circled_digit(sc2)} {t2.name}")
    if s.get("stage"):
        lines.append(s["stage"])
    lines.append("")
    lines.append(FOOTER)
    return "\n".join(lines)


# ---------- fetch (Telethon) ----------


@dataclass
class Post:
    channel: str
    id: int
    text: str = ""
    links: list = field(default_factory=list)
    media_type: str = None  # "video" | "photo" | None
    tg_message: object = None


def fetch_channel_posts(client, channel: str) -> list:
    posts = []
    try:
        for msg in client.iter_messages(channel, limit=FETCH_LIMIT):
            text = msg.message or ""
            media_type = None
            if msg.video:
                media_type = "video"
            elif msg.photo:
                media_type = "photo"
            links = []
            if msg.entities:
                for e in msg.entities:
                    url = getattr(e, "url", None)
                    if url:
                        links.append(url)
            posts.append(
                Post(
                    channel=channel,
                    id=msg.id,
                    text=text,
                    links=links,
                    media_type=media_type,
                    tg_message=msg,
                )
            )
    except Exception as e:
        print(f"  fetch {channel} failed: {e}")
    return posts


# ---------- Rubika send ----------


class Rubika:
    def __init__(self, token: str, chat_id: str):
        self.base = f"{RUBIKA_API}/{token}"
        self.chat_id = chat_id

    def call(self, method: str, payload=None, retries=3):
        payload = dict(payload or {})
        payload["chat_id"] = self.chat_id
        for attempt in range(1, retries + 1):
            try:
                r = requests.post(f"{self.base}/{method}", json=payload, timeout=60)
                j = r.json()
            except Exception as e:
                if attempt == retries:
                    raise RuntimeError(f"{method} network error: {e}")
                time.sleep(2 * attempt)
                continue
            if j.get("status") == "OK" or r.ok:
                return j
            if attempt == retries:
                raise RuntimeError(f"{method} failed: {j}")
            time.sleep(2 * attempt)

    def send_message(self, text: str):
        for i in range(0, len(text), 4000):
            self.call("sendMessage", {"text": text[i : i + 4000]})

    def send_file_bytes(self, file_type: str, content: bytes, filename: str, caption: str = ""):
        if len(content) > MAX_MEDIA_BYTES:
            raise RuntimeError("media too large")
        req = self.call("requestSendFile", {"type": file_type})
        upload_url = req["data"]["upload_url"]
        up = requests.post(upload_url, files={"file": (filename, content)}, timeout=300)
        file_id = up.json()["data"]["file_id"]
        payload = {"file_id": file_id, "type": file_type}
        if caption:
            payload["text"] = caption
        self.call("sendFile", payload)


def send_post(rb: Rubika, client, post: Post, text: str):
    if post.media_type in ("video", "photo"):
        try:
            content = client.download_media(post.tg_message, file=bytes)
            if not content:
                raise RuntimeError("empty media")
            file_type = "Video" if post.media_type == "video" else "Image"
            cap = text if len(text) <= 1000 else ""
            rb.send_file_bytes(file_type, content, "file", cap)
            if len(text) > 1000:
                rb.send_message(text)
            return
        except Exception as e:
            print(f"  media send failed ({e}); sending text only")
    rb.send_message(text)


# ---------- state ----------


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except ValueError:
            pass
    return {"last_id": {}, "fingerprints": {}}


def save_state(state):
    now = time.time()
    cutoff = now - DEDUPE_KEEP_DAYS * 86400
    state["fingerprints"] = {
        k: v for k, v in state["fingerprints"].items() if v > cutoff
    }
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def game_key(team_a, team_b) -> str:
    names = sorted([squash(team_a.name), squash(team_b.name)])
    return "|".join(names)


def goal_fingerprint(g: dict) -> str:
    gk = game_key(g["team_a"], g["team_b"])
    if g["minute"] is not None:
        detail = f"min{g['minute']}"
    elif g["score_a"] is not None and g["score_b"] is not None:
        detail = f"sc{g['score_a']}-{g['score_b']}"
    elif g["ordinal"] is not None:
        detail = f"ord{g['ordinal']}"
    else:
        detail = "unknown"
    return f"goal|{gk}|{detail}"


def summary_fingerprint(s: dict) -> str:
    gk = game_key(s["team1"], s["team2"])
    scores = sorted([s["score1"], s["score2"]])
    return f"summary|{gk}|{scores[0]}-{scores[1]}"


# ---------- main ----------


def main() -> int:
    if not RUBIKA_TOKEN or not RUBIKA_CHAT_ID:
        print("RUBIKA_BOT_TOKEN and RUBIKA_CHAT_ID must be set", file=sys.stderr)
        return 1
    if not (TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_SESSION):
        print("TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_SESSION must be set", file=sys.stderr)
        return 1

    state = load_state()
    rb = Rubika(RUBIKA_TOKEN, RUBIKA_CHAT_ID)
    sent_count = 0

    with TelegramClient(StringSession(TELEGRAM_SESSION), int(TELEGRAM_API_ID), TELEGRAM_API_HASH) as client:
        for channel in SOURCE_CHANNELS:
            posts = sorted(fetch_channel_posts(client, channel), key=lambda p: p.id)
            if not posts:
                continue

            last_id = state["last_id"].get(channel)
            if last_id is None:
                ids = [p.id for p in posts]
                n = FIRST_RUN_SEND
                last_id = ids[-n - 1] if 0 < n < len(ids) else ids[-1]
                state["last_id"][channel] = last_id
                print(f"{channel}: first run, baseline last_id={last_id}")
                if not FIRST_RUN_SEND:
                    continue

            new_posts = [p for p in posts if p.id > last_id]
            print(f"{channel}: {len(new_posts)} new post(s)")

            for p in new_posts:
                state["last_id"][channel] = p.id
                raw = p.text
                if not raw or is_ad(raw, p.links):
                    if raw and is_ad(raw, p.links):
                        print(f"  {channel}#{p.id}: ad -> skipped")
                    save_state(state)
                    continue

                kind = classify(raw)
                if kind not in ("goal", "summary"):
                    save_state(state)
                    continue

                ascii_text = to_ascii_digits(raw)
                try:
                    if kind == "goal":
                        g = extract_goal(raw, ascii_text)
                        if not g:
                            print(f"  {channel}#{p.id}: goal not parsed -> skipped")
                            save_state(state)
                            continue
                        fp = goal_fingerprint(g)
                        if fp in state["fingerprints"]:
                            print(f"  {channel}#{p.id}: duplicate goal -> skipped")
                            save_state(state)
                            continue
                        if g["scorer"]:
                            translated = translate_to_persian(g["scorer"])
                            if translated is None:
                                print(f"  {channel}#{p.id}: translation failed -> skipped")
                                save_state(state)
                                continue
                            g["scorer"] = translated
                        text = format_goal(g)
                    else:
                        s = extract_summary(raw, ascii_text)
                        if not s:
                            print(f"  {channel}#{p.id}: summary not parsed -> skipped")
                            save_state(state)
                            continue
                        fp = summary_fingerprint(s)
                        if fp in state["fingerprints"]:
                            print(f"  {channel}#{p.id}: duplicate summary -> skipped")
                            save_state(state)
                            continue
                        s["flag"] = detect_flag(raw, [s["team1"], s["team2"]])
                        if s.get("stage"):
                            translated = translate_to_persian(s["stage"])
                            if translated is None:
                                print(f"  {channel}#{p.id}: translation failed -> skipped")
                                save_state(state)
                                continue
                            s["stage"] = translated
                        text = format_summary(s)

                    send_post(rb, client, p, text)
                    state["fingerprints"][fp] = time.time()
                    sent_count += 1
                    print(f"  {channel}#{p.id}: sent ({kind})")
                    time.sleep(1)
                except Exception as e:
                    print(f"  {channel}#{p.id}: FAILED ({e})", file=sys.stderr)
                    save_state(state)
                    return 1

                save_state(state)

    save_state(state)
    print(f"done. sent={sent_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
