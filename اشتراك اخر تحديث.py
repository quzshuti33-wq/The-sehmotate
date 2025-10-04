import logging, sqlite3, re, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ====== CONFIG ======
# IMPORTANT: Replace the placeholders below with your real values BEFORE running.
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"   # <-- استبدل هنا توكن البوت (مثلاً: "123:ABC...")
OWNER_ID = 123456789                    # <-- استبدل هنا رقمك (int)
BOT_CHANNEL = "@YourChannel"            # optional
DEV_CONTACT = "tg://user?id=123456789"  # optional (link to owner)
DB_PATH = "bot_data.db"
# ====================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== DB helpers =====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # global required lists (used for start/check across private usage as earlier)
    c.execute("CREATE TABLE IF NOT EXISTS required_channels (chat TEXT UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS required_groups (chat TEXT UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS required_bots (username TEXT UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS developers (id INTEGER PRIMARY KEY)")
    # per-group channel (one channel per group)
    c.execute(\"\"\"CREATE TABLE IF NOT EXISTS group_channels (
                 group_id INTEGER PRIMARY KEY,
                 channel TEXT
                 )\"\"\")
    conn.commit()
    conn.close()

def add_required(kind, val):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if kind == "channel": c.execute("INSERT OR IGNORE INTO required_channels VALUES (?)", (val,))
    if kind == "group": c.execute("INSERT OR IGNORE INTO required_groups VALUES (?)", (val,))
    if kind == "bot": c.execute("INSERT OR IGNORE INTO required_bots VALUES (?)", (val,))
    conn.commit(); conn.close()

def remove_required(kind, val):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if kind == "channel": c.execute("DELETE FROM required_channels WHERE chat=?", (val,))
    if kind == "group": c.execute("DELETE FROM required_groups WHERE chat=?", (val,))
    if kind == "bot": c.execute("DELETE FROM required_bots WHERE username=?", (val,))
    conn.commit(); conn.close()

def list_required(kind):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if kind == "channel": c.execute("SELECT chat FROM required_channels")
    if kind == "group": c.execute("SELECT chat FROM required_groups")
    if kind == "bot": c.execute("SELECT username FROM required_bots")
    rows = [r[0] for r in c.fetchall()]
    conn.close(); return rows

def add_developer(uid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO developers (id) VALUES (?)", (uid,))
    conn.commit(); conn.close()

def remove_developer(uid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("DELETE FROM developers WHERE id=?", (uid,))
    conn.commit(); conn.close()

def list_devs():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT id FROM developers")
    rows = [r[0] for r in c.fetchall()]; conn.close(); return rows

def set_group_channel(group_id, channel):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("REPLACE INTO group_channels (group_id, channel) VALUES (?,?)", (group_id, channel))
    conn.commit(); conn.close()

def remove_group_channel(group_id):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("DELETE FROM group_channels WHERE group_id=?", (group_id,))
    conn.commit(); conn.close()

def get_group_channel(group_id):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT channel FROM group_channels WHERE group_id=?", (group_id,))
    row = c.fetchone(); conn.close()
    return row[0] if row else None

# ===== utilities =====
def is_admin(uid):
    return uid == OWNER_ID or uid in list_devs()

async def is_member(chat_identifier, user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = await context.bot.get_chat(chat_identifier)
        member = await context.bot.get_chat_member(chat.id, user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False

async def check_subscription_global(user_id, context):
    missing = []
    for ch in list_required("channel"):
        if not await is_member(ch, user_id, context): missing.append(ch)
    for g in list_required("group"):
        if not await is_member(g, user_id, context): missing.append(g)
    for b in list_required("bot"):
        missing.append(b + " (بوت)")
    return missing

_channel_pattern = re.compile(r"(@[A-Za-z0-9_]{5,}|t.me/[A-Za-z0-9_]{5,}|https?://t.me/[A-Za-z0-9_]{5,})")

def parse_channel_from_text(txt: str):
    txt = txt.strip()
    # direct @username or full t.me/... or raw link
    m = _channel_pattern.search(txt)
    if m:
        s = m.group(0)
        # normalize to @username if possible
        if s.startswith("t.me/") or s.startswith("http"):
            s = s.split("/")[-1]
            return "@" + s
        return s if s.startswith("@") else "@" + s
    return None

# ====== Handlers ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("➕ اضفني إلى مجموعتك", url=f"https://t.me/{context.bot.username}?startgroup=new")],
        [InlineKeyboardButton("📢 قناة البوت", url=f"https://t.me/{BOT_CHANNEL.lstrip('@')}"),
         InlineKeyboardButton("👨‍💻 المطور", url=DEV_CONTACT)]
    ]
    await update.message.reply_text("👋 مرحباً! اضفني إلى مجموعتك لتفعيل الاشتراك الإجباري.", reply_markup=InlineKeyboardMarkup(kb))

# admin panel shown by /admin (developer only)
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 ليس لديك صلاحية الوصول للوحة المطور.")
        return
    kb = [
        [InlineKeyboardButton("➕ إضافة قناة (عام)", callback_data="add_channel_global"),
         InlineKeyboardButton("➖ حذف قناة (عام)", callback_data="del_channel_global")],
        [InlineKeyboardButton("➕ إضافة قروب (عام)", callback_data="add_group_global"),
         InlineKeyboardButton("➖ حذف قروب (عام)", callback_data="del_group_global")],
        [InlineKeyboardButton("➕ إضافة بوت (عام)", callback_data="add_bot_global"),
         InlineKeyboardButton("➖ حذف بوت (عام)", callback_data="del_bot_global")],
        [InlineKeyboardButton("➕ رفع مطور", callback_data="promote_dev"),
         InlineKeyboardButton("➖ تنزيل مطور", callback_data="demote_dev")],
        [InlineKeyboardButton("📋 عرض القوائم", callback_data="show_all")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats")]
    ]
    await update.message.reply_text("🔧 لوحة المطور:", reply_markup=InlineKeyboardMarkup(kb))

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    if not is_admin(uid):
        await q.edit_message_text("🚫 للمطورين فقط"); return
    data = q.data

    # global add/remove handlers - set expecting in user_data
    if data.endswith("_global"):
        context.user_data["expecting"] = data
        await q.edit_message_text("✏️ أرسل الآن المعرف (مثل @channel أو رابط t.me/...)")
        return

    if data in ("promote_dev", "demote_dev"):
        context.user_data["expecting"] = data
        await q.edit_message.reply_text("✏️ أرسل الآن معرف المستخدم (user_id) أو @username لترقيته/تنزيله.")
        return

    if data == "stats":
        txt = (
            f"📊 إحصائيات:\n"
            f"القنوات العامة: {len(list_required('channel'))}\n"
            f"القروبات العامة: {len(list_required('group'))}\n"
            f"البوتات العامة: {len(list_required('bot'))}\n"
            f"عدد المطورين: {len(list_devs())}"
        )
        await q.edit_message_text(txt)
        return

    if data == "show_all":
        channels = list_required("channel")
        groups = list_required("group")
        bots = list_required("bot")
        content = f"توقيت الإنشاء: {datetime.datetime.utcnow().isoformat()} UTC\n\n"
        content += "📋 القوائم العامة:\n\n"
        if channels:
            content += "📢 القنوات:\n" + "\n".join(f"- {c} → https://t.me/{c.lstrip('@')}" for c in channels) + "\n\n"
        if groups:
            content += "👥 القروبات:\n" + "\n".join(f"- {g}" for g in groups) + "\n\n"
        if bots:
            content += "🤖 البوتات:\n" + "\n".join(f"- {b} → https://t.me/{b.lstrip('@')}" for b in bots) + "\n\n"
        # also include per-group channels
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT group_id, channel FROM group_channels")
        rows = c.fetchall(); conn.close()
        if rows:
            content += "🔹 قنوات مرتبطة بالقروبات:\n"
            for gid, ch in rows:
                content += f"- group_id={gid} -> {ch} → https://t.me/{ch.lstrip('@')}\n"
        if not (channels or groups or bots or rows):
            content = "⚠️ لا توجد إعدادات حالياً."
        with open("subscriptions.txt", "w", encoding="utf-8") as f:
            f.write(content)
        await q.message.reply_document(InputFile("subscriptions.txt"), caption="📋 القوائم الحالية.")
        return

# When admin/user sends free text expecting an admin action
async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    # first check if we're expecting a global admin action for this user
    expecting = context.user_data.get("expecting")
    if expecting:
        if expecting.endswith("_global"):
            kind = expecting.split("_")[1]  # channel/group/bot
            target = parse_channel_from_text(text) or text
            if kind == "channel":
                add_required("channel", target)
                await update.message.reply_text(f"✅ تم إضافة {target} للقنوات العامة.")
            elif kind == "group":
                add_required("group", target)
                await update.message.reply_text(f"✅ تم إضافة {target} إلى القروبات العامة.")
            elif kind == "bot":
                # normalize bot
                if not target.startswith("@"): target = "@" + target.lstrip("@")
                add_required("bot", target)
                await update.message.reply_text(f"✅ تم إضافة {target} إلى البوتات العامة.")
            context.user_data.pop("expecting", None)
            return
        if expecting in ("promote_dev", "demote_dev"):
            # try to resolve to id
            target_id = None
            try:
                if text.startswith("@"):
                    u = await context.bot.get_chat(text)
                    target_id = u.id
                else:
                    target_id = int(text)
            except Exception as e:
                await update.message.reply_text("❌ تعذر تحديد المستخدم. أرسل @username أو user_id صحيح.")
                context.user_data.pop("expecting", None)
                return
            if expecting == "promote_dev":
                add_developer(target_id); await update.message.reply_text(f"✅ تم رفع {target_id} مطور.")
            else:
                remove_developer(target_id); await update.message.reply_text(f"✅ تم تنزيل {target_id} من المطورين.")
            context.user_data.pop("expecting", None)
            return

    # ===== GROUP-SPECIFIC flows =====
    # If message is in a group and the bot is tracking an 'expecting' for that chat, handle it
    if update.effective_chat.type in ("group", "supergroup"):
        chat_data = context.chat_data
        # if previously someone triggered add/remove for this chat
        if chat_data.get("expecting") == "add_channel":
            channel = parse_channel_from_text(text) or text
            set_group_channel(update.effective_chat.id, channel)
            chat_data.pop("expecting", None)
            await update.message.reply_text(f"✅ تم ربط {channel} كقناة إجباريّة لهذا القروب.")
            return
        if chat_data.get("expecting") == "rem_channel":
            remove_group_channel(update.effective_chat.id)
            chat_data.pop("expecting", None)
            await update.message.reply_text("✅ تم إزالة القناة الإلزاميّة لهذا القروب.")
            return
        # trigger by typing words (without /)
        low = text.lower()
        if low in ("اضف قناة", "اضافة قناة", "اضف القناة"):
            chat_data["expecting"] = "add_channel"
            await update.message.reply_text("📢 يرجى إرسال يوزر القناة (مثل @example) أو رابطها (t.me/...) ليتم تفعيل الاشتراك الإجباري هنا.")
            return
        if low in ("حذف القناة", "ازالة القناة", "احذف القناة"):
            chat_data["expecting"] = "rem_channel"
            await update.message.reply_text("🗑️ سيتم حذف القناة الإلزاميّة لهذا القروب. أرسل أي رسالة للتأكيد.")
            return

    # If we reach here, handle /start or others in private
    if update.effective_chat.type == "private":
        # standard /start handled separately; for free text in private we can reply help text
        await update.message.reply_text("أرسل /start أو /admin (للمطور) لإدارة البوت.")

# When someone posts in any group - enforce per-group channel if set
async def group_message_enforcer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user:
        return
    # ignore the special control phrases above - they are handled in text_input
    # check per-group channel
    gid = update.effective_chat.id
    channel = get_group_channel(gid)
    if not channel:
        return  # nothing to enforce for this group
    # if sender is a bot or the chat itself, skip
    if msg.from_user.is_bot:
        return
    # check membership
    if not await is_member(channel, msg.from_user.id, context):
        try:
            await msg.delete()
        except Exception:
            pass
        mention = msg.from_user.mention_html()
        text = f"{mention} 🚫 لازم تشترك في {channel} عشان تقدر ترسل هنا."
        await update.effective_chat.send_message(text, parse_mode="HTML")
        return

# fallback handler for /start to show same keyboard
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ===== registration and main =====
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("admin", admin_panel))

    # callback queries from admin keyboard
    app.add_handler(CallbackQueryHandler(callback_router))

    # text input (for admin global actions and group add/remove flows)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_input))

    # enforce messages in groups (this runs on every group text message after text_input)
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_message_enforcer))

    logger.info("Bot started")
    app.run_polling()

if __name__ == '__main__':
    main()
