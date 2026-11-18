import os
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from downloader import get_info, download_video, download_audio, clean_file
from database import init_db, add_user, stats

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
MAX_MB = int(os.getenv("MAX_FILE_MB", "2000"))
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
WORK_DIR = DATA_DIR / "downloads"
WORK_DIR.mkdir(parents=True, exist_ok=True)

# Optional self-hosted Telegram Bot API server. Without it, Telegram cloud upload limit is 50 MB.
api_base = os.getenv("TELEGRAM_API_BASE_URL")
file_base = os.getenv("TELEGRAM_FILE_BASE_URL")
builder = Application.builder().token(TOKEN)
if api_base and file_base:
    builder = (builder.base_url(api_base).base_file_url(file_base)
               .local_mode(True).connect_timeout(30).read_timeout(120)
               .write_timeout(3600).media_write_timeout(3600))
app = builder.build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    await update.message.reply_text(
        "👋 YouTube Downloader ready!\n\nYouTube link bhejo. Main available qualities aur audio options dikhaunga.\n\n"
        "Commands: /start /help /cancel" +
        ("\n/adminstats" if update.effective_user.id in ADMIN_IDS else "")
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Supported: public videos you own or have permission to download.\n"
        "Send a YouTube URL, choose video quality or MP3/M4A, then wait for delivery.\n"
        "Large uploads (>50 MB) require a self-hosted Telegram Bot API server."
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proc = context.user_data.get("process")
    if proc and proc.returncode is None:
        proc.terminate()
        await update.message.reply_text("⛔ Download cancel kar diya.")
    else:
        await update.message.reply_text("Abhi koi active download nahi hai.")

async def adminstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    users, jobs = stats()
    await update.message.reply_text(f"👥 Users: {users}\n📥 Completed jobs: {jobs}")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    url = update.message.text.strip()
    if not ("youtube.com/" in url or "youtu.be/" in url):
        await update.message.reply_text("Please valid YouTube URL bhejo.")
        return
    msg = await update.message.reply_text("🔎 Video information check ho rahi hai...")
    try:
        info = await get_info(url)
        context.user_data["video_url"] = url
        context.user_data["video_title"] = info.get("title", "YouTube video")[:150]
        buttons = []
        seen = set()
        for f in info.get("formats", []):
            h = f.get("height")
            if h and f.get("vcodec") != "none" and h <= 2160 and h not in seen:
                seen.add(h)
        for h in sorted(seen, reverse=True):
            buttons.append([InlineKeyboardButton(f"🎬 {h}p", callback_data=f"v:{h}")])
        buttons.append([
            InlineKeyboardButton("🎵 MP3 192", callback_data="a:mp3"),
            InlineKeyboardButton("🎵 M4A", callback_data="a:m4a")
        ])
        duration = info.get("duration_string", "Unknown")
        await msg.edit_text(
            f"**{context.user_data['video_title']}**\n⏱ Duration: {duration}\n\nQuality select karo:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Video info nahi mil payi: {str(e)[:500]}")

async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    url = context.user_data.get("video_url")
    if not url:
        await q.edit_message_text("Link expire ho gaya. Dobara URL bhejo.")
        return
    mode, value = q.data.split(":", 1)
    status = await q.edit_message_text("⏬ Download start ho raha hai...")
    try:
        if mode == "v":
            path = await download_video(url, int(value), WORK_DIR, context)
        else:
            path = await download_audio(url, value, WORK_DIR, context)
        size = Path(path).stat().st_size
        if size > MAX_MB * 1024 * 1024:
            clean_file(path)
            await status.edit_text(f"❌ File {size/1024/1024:.1f} MB hai. Limit {MAX_MB} MB hai.")
            return
        # Standard Telegram Bot API: 50 MB. Local Bot API server supports up to 2000 MB.
        if not (api_base and file_base) and size > 50 * 1024 * 1024:
            clean_file(path)
            await status.edit_text(
                f"⚠️ File {size/1024/1024:.1f} MB hai. Normal Telegram Bot API ki limit 50 MB hai.\n"
                "2 GB delivery ke liye self-hosted Telegram Bot API server configure karo."
            )
            return
        await status.edit_text("📤 Telegram par upload ho raha hai...")
        caption = f"✅ {context.user_data.get('video_title','Download')}"
        if api_base and file_base:
            # Local Bot API server + PTB local_mode: pass the local path directly.
            await q.message.reply_document(document=path, filename=Path(path).name, caption=caption)
        else:
            with open(path, "rb") as f:
                await q.message.reply_document(document=f, filename=Path(path).name, caption=caption)
        clean_file(path)
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Download/upload failed: {str(e)[:700]}")
    finally:
        context.user_data.pop("process", None)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(CommandHandler("adminstats", adminstats))
app.add_handler(CallbackQueryHandler(choose, pattern=r"^[va]:"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

if __name__ == "__main__":
    init_db()
    print("Bot is starting...")
    app.run_polling(drop_pending_updates=True)
