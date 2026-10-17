# -*- coding: utf-8 -*-
"""
🤖 ربات تبلیغ‌گر J4J — نسخه‌ی Telethon (نهایی و بدون باگ)
==================================================
✅ استفاده از SESSION_STRING2 (اکانت تبلیغ‌گر جدا)
✅ عضویت خودکار در گروه‌ها
✅ ارسال نوبتی دو متن
✅ فاصله ۶۰ ثانیه بین هر گروه
✅ گزارش به Saved Messages
"""

import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import sys
import json
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    try:
        from telethon import TelegramClient, StringSession
    except ImportError:
        print("=" * 60)
        print("❌ telethon نصب نیست!")
        print("  py -m pip install telethon")
        print("=" * 60)
        sys.exit(1)

from telethon.errors import (
    FloodWaitError,
    ChannelPrivateError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    InviteHashInvalidError,
    InviteHashExpiredError,
    UsernameNotOccupiedError,
    UserAlreadyParticipantError,
    RPCError,
)

BASE_DIR = Path(__file__).parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# ============================================================
# CONFIGURATION
# ============================================================

API_ID = int(os.getenv("API_ID", "0") or "0")
API_HASH = os.getenv("API_HASH", "").strip()
SESSION_STRING = (
    os.getenv("SESSION_STRING2")
    or os.getenv("AD_SESSION_STRING")
    or os.getenv("SESSION_STRING", "")
).strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "8581608010") or "8581608010")

TARGET_GROUPS: List[str] = [
    "@jfjbq",
    "@jfjax",
    "@jfjab",
    "@jfjat",
    "@jfjac",
    "https://t.me/michaybq",
]

BETWEEN_GROUPS_DELAY = int(os.getenv("BETWEEN_GROUPS_DELAY", "60"))
JITTER = int(os.getenv("JITTER", "5"))

STATE_FILE = BASE_DIR / "state.json"
ADS_FILE = BASE_DIR / "ads.txt"
LOG_FILE = BASE_DIR / "j4j_bot.log"

DEFAULT_ADS = """جفج؟

https://t.me/+UZV1z08twtM2MDVk

عضو شدی با 5 تا اک عضو میشم❤️

---

نت ملی شد🚫

ولی ما همچنان وصلیم

الکی پول به کانفیگ الکی نده بیا اینجا رایگان وصل شو

https://t.me/+UZV1z08twtM2MDVk"""

DEFAULT_STATE: Dict[str, Any] = {
    "groups": {},
    "stats": {
        "total_sent": 0, "today_sent": 0, "today_date": "",
        "errors": 0, "bans": 0, "joined": 0,
    },
    "last_run": "",
    "log": [],
}


def _deep_merge(default: dict, override: dict) -> dict:
    merged = default.copy()
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return _deep_merge(DEFAULT_STATE, saved)
        except Exception as e:
            print(f"⚠️ خطا در خواندن state.json: {e} — استفاده از پیش‌فرض")
    return json.loads(json.dumps(DEFAULT_STATE))


def save_state() -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"save_state error: {e}")


state: Dict[str, Any] = load_state()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("j4j_bot")


def add_log_entry(msg: str, level: str = "info") -> None:
    state["log"].insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "msg": msg, "level": level,
    })
    state["log"] = state["log"][:30]
    save_state()
    getattr(log, level, log.info)(msg)


def load_ads() -> List[str]:
    if not ADS_FILE.exists():
        with open(ADS_FILE, "w", encoding="utf-8") as f:
            f.write(DEFAULT_ADS)
        add_log_entry("📝 فایل ads.txt ساخته شد با ۲ متن پیش‌فرض")
    try:
        with open(ADS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        add_log_entry(f"❌ خطا در خواندن ads.txt: {e}", "error")
        return []
    ads = [a.strip() for a in content.split("\n---\n") if a.strip()]
    return ads


# === CLIENT ===
if not SESSION_STRING:
    print("=" * 60)
    print("❌ SESSION_STRING تنظیم نشده!")
    print("برای ساخت: python get_session.py")
    print("بعد در .env یا GitHub Secrets بذارش:")
    print("  SESSION_STRING2=...")
    print("=" * 60)
    sys.exit(1)

if not API_ID or not API_HASH:
    print("❌ API_ID و API_HASH تنظیم نشده!")
    print("از https://my.telegram.org بگیر.")
    sys.exit(1)

ad_app = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH,
)


# === HELPERS ===
async def send_test_message() -> None:
    try:
        await ad_app.send_message(
            "me",
            "🧪 <b>تست اتصال</b>\n\n"
            "✅ ربات J4J با موفقیت اجرا شد!\n\n"
            f"📋 گروه‌های هدف: {len(TARGET_GROUPS)} عدد\n"
            f"📝 متن‌های آماده: از ads.txt\n"
            f"⏱ فاصله بین گروه‌ها: {BETWEEN_GROUPS_DELAY}s\n"
            f"🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="html",
        )
        add_log_entry("🧪 پیام تستی به Saved Messages ارسال شد")
    except Exception as e:
        add_log_entry(f"❌ خطا در ارسال پیام تستی: {e}", "error")


async def join_group_if_needed(target: str) -> bool:
    """اگه هنوز عضو گروه نباشیم، عضو می‌شیم."""
    target_clean = target.strip()

    group_state = state["groups"].get(target_clean, {})
    if group_state.get("status") == "active":
        return True

    try:
        if target_clean.startswith("@"):
            try:
                await ad_app.get_entity(target_clean)
                add_log_entry(f"✅ از قبل عضو هستیم: {target_clean}")
                return True
            except Exception:
                add_log_entry(f"➕ عضو نیستیم، تلاش برای عضویت در: {target_clean}")
                try:
                    await ad_app.join_chat(target_clean)
                    add_log_entry(f"✅ عضو شدیم: {target_clean}")
                    state["stats"]["joined"] += 1
                    save_state()
                    await asyncio.sleep(random.uniform(2, 5))
                    return True
                except UserAlreadyParticipantError:
                    add_log_entry(f"✅ از قبل عضو بودیم: {target_clean}")
                    return True
                except (InviteHashInvalidError, InviteHashExpiredError):
                    add_log_entry(f"❌ لینک دعوت نامعتبر: {target_clean}", "error")
                    return False
                except Exception as e:
                    add_log_entry(f"❌ خطا در عضویت {target_clean}: {e}", "error")
                    return False

        elif "t.me/+" in target_clean or "joinchat" in target_clean:
            add_log_entry(f"➕ تلاش برای عضویت با لینک: {target_clean}")
            try:
                await ad_app.join_chat(target_clean)
                add_log_entry(f"✅ عضو شدیم: {target_clean}")
                state["stats"]["joined"] += 1
                save_state()
                await asyncio.sleep(random.uniform(2, 5))
                return True
            except UserAlreadyParticipantError:
                add_log_entry(f"✅ از قبل عضو بودیم: {target_clean}")
                return True
            except (InviteHashInvalidError, InviteHashExpiredError):
                add_log_entry(f"❌ لینک دعوت نامعتبر: {target_clean}", "error")
                return False
            except Exception as e:
                add_log_entry(f"❌ خطا در عضویت {target_clean}: {e}", "error")
                return False

        elif "t.me/" in target_clean and "joinchat" not in target_clean and "+" not in target_clean:
            username = target_clean.split("t.me/")[-1].split("?")[0]
            full_username = f"@{username}"
            try:
                await ad_app.get_entity(full_username)
                add_log_entry(f"✅ از قبل عضو هستیم: {full_username}")
                return True
            except Exception:
                add_log_entry(f"➕ تلاش برای عضویت: {full_username}")
                try:
                    await ad_app.join_chat(full_username)
                    add_log_entry(f"✅ عضو شدیم: {full_username}")
                    state["stats"]["joined"] += 1
                    save_state()
                    await asyncio.sleep(random.uniform(2, 5))
                    return True
                except UserAlreadyParticipantError:
                    add_log_entry(f"✅ از قبل عضو بودیم: {full_username}")
                    return True
                except Exception as e:
                    add_log_entry(f"❌ خطا در عضویت {full_username}: {e}", "error")
                    return False

        else:
            add_log_entry(f"⚠️ فرمت ناشناخته: {target_clean}", "warning")
            return False

    except Exception as e:
        add_log_entry(f"❌ خطا در join_group_if_needed {target_clean}: {e}", "error")
        return False


async def send_ad_to_group(target: str, ad_text: str) -> bool:
    target_clean = target.strip()
    group_state = state["groups"].get(target_clean, {
        "last_post_at": 0, "post_count": 0, "status": "unknown",
    })
    try:
        try:
            async with ad_app.action(target_clean, "typing"):
                await asyncio.sleep(random.uniform(1.0, 2.0))
        except Exception:
            pass

        await ad_app.send_message(target_clean, ad_text, parse_mode="html")

        state["groups"][target_clean] = {
            "last_post_at": time.time(),
            "post_count": group_state.get("post_count", 0) + 1,
            "status": "active", "last_error": "",
        }
        state["stats"]["total_sent"] += 1
        state["stats"]["today_sent"] += 1
        save_state()
        add_log_entry(
            f"📤 ارسال شد به {target_clean} "
            f"(مجموع: {state['groups'][target_clean]['post_count']})"
        )
        return True

    except FloodWaitError as e:
        add_log_entry(f"⏳ FloodWait {e.seconds}s برای {target_clean}", "warning")
        await asyncio.sleep(min(e.seconds + 5, 300))
        try:
            await ad_app.send_message(target_clean, ad_text, parse_mode="html")
            state["groups"][target_clean] = {
                "last_post_at": time.time(),
                "post_count": group_state.get("post_count", 0) + 1,
                "status": "active",
            }
            state["stats"]["total_sent"] += 1
            state["stats"]["today_sent"] += 1
            save_state()
            add_log_entry(f"📤 ارسال شد به {target_clean} (بعد از FloodWait)")
            return True
        except Exception as e2:
            add_log_entry(f"❌ خطا بعد از FloodWait برای {target_clean}: {e2}", "error")
            state["stats"]["errors"] += 1
            save_state()
            return False

    except (ChannelPrivateError, ChatWriteForbiddenError, UserBannedInChannelError) as e:
        add_log_entry(
            f"🚫 بن/محروم در {target_clean}: {type(e).__name__}",
            "error",
        )
        state["groups"][target_clean] = {
            **group_state, "status": "banned", "last_error": type(e).__name__,
        }
        state["stats"]["bans"] += 1
        state["stats"]["errors"] += 1
        save_state()
        return False

    except RPCError as e:
        add_log_entry(f"❌ RPC خطا در {target_clean}: {e}", "error")
        state["stats"]["errors"] += 1
        save_state()
        return False

    except Exception as e:
        add_log_entry(f"❌ خطا در ارسال به {target_clean}: {e}", "error")
        state["stats"]["errors"] += 1
        save_state()
        return False


# === MAIN ===
async def main() -> None:
    log.info("=" * 60)
    log.info("🚀 شروع اجرای J4J Bot (Telethon)")
    log.info(f"🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"📋 گروه‌های هدف: {len(TARGET_GROUPS)}")
    log.info(f"⏱ فاصله بین گروه‌ها: {BETWEEN_GROUPS_DELAY}s (±{JITTER}s jitter)")
    log.info("=" * 60)

    await ad_app.start()
    log.info("✅ اکانت متصل شد")

    today = datetime.now().strftime("%Y-%m-%d")
    if state["stats"]["today_date"] != today:
        state["stats"]["today_date"] = today
        state["stats"]["today_sent"] = 0
        save_state()
        log.info(f"📅 روز جدید: {today} — شمارنده ریست شد")

    if state["stats"]["total_sent"] == 0:
        log.info("🧪 اولین اجرا — ارسال پیام تستی...")
        await send_test_message()

    ads = load_ads()
    if not ads:
        log.error("❌ هیچ متنی برای ارسال وجود نداره!")
        await ad_app.disconnect()
        return

    log.info(f"📝 {len(ads)} متن بارگذاری شد")

    posted = 0
    errors = 0

    for i, target in enumerate(TARGET_GROUPS):
        target_clean = target.strip()
        log.info("")
        log.info(f"--- [{i+1}/{len(TARGET_GROUPS)}] {target_clean} ---")

        joined = await join_group_if_needed(target_clean)
        if not joined:
            log.warning(f"⚠️ عضویت ناموفق بود — رد شد")
            errors += 1
            continue

        ad_index = i % len(ads)
        ad_text = ads[ad_index]
        ad_label = "متن۱ (جفج؟)" if ad_index == 0 else f"متن{ad_index+1} (نت ملی)"
        log.info(f"📝 ارسال {ad_label} به {target_clean}")

        success = await send_ad_to_group(target_clean, ad_text)
        if success:
            posted += 1
        else:
            errors += 1

        if i < len(TARGET_GROUPS) - 1:
            delay = BETWEEN_GROUPS_DELAY + random.randint(-JITTER, JITTER)
            delay = max(45, delay)
            log.info(f"⏳ صبر {delay}s قبل از گروه بعدی...")
            await asyncio.sleep(delay)

    state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_state()

    summary = (
        f"✅ <b>اجرای J4J کامل شد</b>\n\n"
        f"🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"📤 ارسال شده: <b>{posted}</b>\n"
        f"❌ خطا: <b>{errors}</b>\n\n"
        f"📊 کل ارسال: {state['stats']['total_sent']}\n"
        f"📅 امروز: {state['stats']['today_sent']}\n"
        f"🚫 بن‌ها: {state['stats']['bans']}\n"
        f"➕ عضو شده‌ها: {state['stats']['joined']}\n"
    )

    log.info("")
    log.info("=" * 60)
    log.info(f"✅ خلاصه: ارسال={posted}, خطا={errors}")
    log.info(f"📊 کل: {state['stats']['total_sent']} | امروز: {state['stats']['today_sent']}")
    log.info("=" * 60)

    try:
        await ad_app.send_message("me", summary, parse_mode="html")
        log.info("📨 خلاصه به Saved Messages ارسال شد")
    except Exception as e:
        log.error(f"خطا در ارسال خلاصه: {e}")

    await ad_app.disconnect()
    log.info("👋 اجرا تموم شد")

    print(f"\n{'='*60}")
    print(f"✅ Run complete: {posted} posted, {errors} errors")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 متوقف شد.")
    except Exception as e:
        print(f"\n💥 خطای مهلک: {e}")
        sys.exit(1)