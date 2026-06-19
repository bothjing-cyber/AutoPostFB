"""
Poster Bot — Route 1 starter
=============================
Drop content (text + photo or video) into this bot privately.
It replies with a menu. You tap a destination, and it posts:

  [1] Telegram channel (with contact buttons) + Facebook Page
  [2] TikTok  -> phase 2, stubbed for now

Built to run 24/7 on Railway, same as your scraper bot.

------------------------------------------------------------
WHAT YOU NEED TO FILL IN (the CONFIG block below):
  BOT_TOKEN          - from @BotFather on Telegram
  OWNER_ID           - your own Telegram user ID (so only YOU can post)
  TELEGRAM_CHANNEL   - your channel, e.g. "@myshopchannel" or the numeric -100... id
  FB_PAGE_ID         - your Facebook Page ID
  FB_PAGE_TOKEN      - a long-lived Page access token
  CONTACT_USERNAME   - your telegram username for the "Message us" button
  CONTACT_PHONE      - phone number for the "Call" button
  MORE_LINK          - any link for the "More" button (FB page, website...)
------------------------------------------------------------

INSTALL (locally or in Railway):
  pip install python-telegram-bot==21.6 requests

RUN:
  python poster_bot.py
"""

import os
import logging
import tempfile

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ============================================================
# CONFIG  — fill these in. On Railway, set them as Variables
# and they'll be read from the environment automatically.
# ============================================================
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "8647737480:AAEwiw0S18qTJ33OVwHZoYnxtEHD2wR_URE")
OWNER_ID         = int(os.environ.get("6737634349", "0"))          # your telegram user id
TELEGRAM_CHANNEL = os.environ.get("https://t.me/toyota_Sokharatith", "@yourchannel")
FB_PAGE_ID       = os.environ.get("FB_PAGE_ID", "1339318928160765")
FB_PAGE_TOKEN    = os.environ.get("FB_PAGE_TOKEN", "EAATCGnz0NZC0BR2409YP3ps7mof2uidVXcZA6squhMNOfOzI6IvZBek7zyPUfAW0EsZBeAcK3WxZAUZAFafrq4VhQyFVM5KYDGq3XFFR0wZBRwt387RVXZBZCQ5evekd6oeYtxNWljTZCKDwpXGVuAomu6coFM5JJlw385pcmw3aFBt6AZAih9Xp6260ZCGQJV5WXiVJaJaKxQ1ZACfw2D8pIWNjZBtsTA79GsPXbq6U9n7KjkFNyZCqDfZB1h0hZBPKChV0XNxoycotKFHBH1WVjnc4Rf5MBexSHPnwEIyTPiGMZD")

CONTACT_USERNAME = os.environ.get("CONTACT_USERNAME", "bosokhara.tith")  # no @
CONTACT_PHONE    = os.environ.get("CONTACT_PHONE", "+85517333762")
MORE_LINK        = os.environ.get("MORE_LINK", "https://web.facebook.com/toyotacambodiabosokhara")

# ============================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("poster_bot")

# Holds the most recent drop per user, in memory.
# { user_id: {"kind": "photo"/"video", "file_id": "...", "caption": "..."} }
pending = {}


# ------------------------------------------------------------
# Buttons that sit UNDER each Telegram channel post
# ------------------------------------------------------------
def channel_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💬 Message us", url=f"https://t.me/{CONTACT_USERNAME}"),
            InlineKeyboardButton("📞 Call", url=f"tel:{CONTACT_PHONE}"),
        ],
        [InlineKeyboardButton("🔗 More", url=MORE_LINK)],
    ])


# ------------------------------------------------------------
# The destination menu the bot shows you after you drop content
# ------------------------------------------------------------
def destination_menu(kind: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("1️⃣ Telegram + Facebook", callback_data="route1")]]
    # TikTok only makes sense for video, and it's phase 2 anyway.
    if kind == "video":
        rows.append([InlineKeyboardButton("2️⃣ TikTok (coming soon)", callback_data="route2")])
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


# ------------------------------------------------------------
# Step 1: you drop content (photo or video, with optional caption)
# ------------------------------------------------------------
async def on_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Only you can use this bot.
    if OWNER_ID and user_id != OWNER_ID:
        await update.message.reply_text("Sorry, this bot is private.")
        return

    msg = update.message
    caption = msg.caption or ""

    if msg.photo:
        # photo[-1] is the highest-resolution version
        pending[user_id] = {"kind": "photo", "file_id": msg.photo[-1].file_id, "caption": caption}
        kind = "photo"
    elif msg.video:
        pending[user_id] = {"kind": "video", "file_id": msg.video.file_id, "caption": caption}
        kind = "video"
    else:
        await msg.reply_text("Send me a photo or a video (you can add a caption with it).")
        return

    await msg.reply_text(
        f"Got your {kind}. Where should it go?",
        reply_markup=destination_menu(kind),
    )


# ------------------------------------------------------------
# Step 2: you tap a destination
# ------------------------------------------------------------
async def on_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if OWNER_ID and user_id != OWNER_ID:
        return

    choice = query.data
    item = pending.get(user_id)

    if choice == "cancel":
        pending.pop(user_id, None)
        await query.edit_message_text("Cancelled.")
        return

    if not item:
        await query.edit_message_text("Nothing to post — drop content again.")
        return

    if choice == "route2":
        await query.edit_message_text("TikTok isn't wired up yet — that's phase 2.")
        return

    # ---- Route 1: Telegram channel + Facebook ----
    await query.edit_message_text("Posting… give me a sec.")

    # Download the file from Telegram to a temp path (Facebook needs the actual file)
    tg_file = await context.bot.get_file(item["file_id"])
    suffix = ".jpg" if item["kind"] == "photo" else ".mp4"
    tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=suffix).name
    await tg_file.download_to_drive(tmp_path)

    results = []

    # 1) Post to the Telegram channel WITH the contact buttons
    try:
        if item["kind"] == "photo":
            await context.bot.send_photo(
                chat_id=TELEGRAM_CHANNEL,
                photo=item["file_id"],
                caption=item["caption"],
                reply_markup=channel_buttons(),
            )
        else:
            await context.bot.send_video(
                chat_id=TELEGRAM_CHANNEL,
                video=item["file_id"],
                caption=item["caption"],
                reply_markup=channel_buttons(),
            )
        results.append("✅ Telegram channel")
    except Exception as e:
        log.exception("Telegram post failed")
        results.append(f"❌ Telegram: {e}")

    # 2) Post to the Facebook Page
    try:
        post_to_facebook(item["kind"], tmp_path, item["caption"])
        results.append("✅ Facebook page")
    except Exception as e:
        log.exception("Facebook post failed")
        results.append(f"❌ Facebook: {e}")

    # Clean up the temp file
    try:
        os.remove(tmp_path)
    except OSError:
        pass

    pending.pop(user_id, None)
    await query.edit_message_text("Done.\n" + "\n".join(results))


# ------------------------------------------------------------
# Facebook posting via the Graph API
# ------------------------------------------------------------
def post_to_facebook(kind: str, file_path: str, caption: str):
    if kind == "photo":
        url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
        with open(file_path, "rb") as f:
            r = requests.post(
                url,
                data={"caption": caption, "access_token": FB_PAGE_TOKEN},
                files={"source": f},
                timeout=120,
            )
    else:  # video
        url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/videos"
        with open(file_path, "rb") as f:
            r = requests.post(
                url,
                data={"description": caption, "access_token": FB_PAGE_TOKEN},
                files={"source": f},
                timeout=300,
            )

    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text}")
    return r.json()


# ------------------------------------------------------------
# Wire it all up
# ------------------------------------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Any photo or video you send privately -> on_content
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, on_content))
    # Button taps -> on_choice
    app.add_handler(CallbackQueryHandler(on_choice))

    log.info("Poster bot running. Waiting for content…")
    app.run_polling()


if __name__ == "__main__":
    main()
