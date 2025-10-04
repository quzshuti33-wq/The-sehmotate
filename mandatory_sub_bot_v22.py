import logging, sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ==== CONFIG ====
BOT_TOKEN = "8455080896:AAFodUYuWKL18itWn1vLs8cefV-P-hE9_2A"
OWNER_ID = 7934749229
BOT_CHANNEL = "@JO7NB"
DEV_CONTACT = "tg://user?id=7934749229"
DB_PATH = "bot_data.db"
# ================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== DB ====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS required_channels (chat TEXT UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS required_groups (chat TEXT UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS required_bots (username TEXT UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS developers (id INTEGER PRIMARY KEY)")
    conn.commit(); conn.close()

def add_required(kind,val):
    conn=sqlite3.connect(DB_PATH);c=conn.cursor()
    if kind=="channel": c.execute("INSERT OR IGNORE INTO required_channels VALUES (?)",(val,))
    if kind=="group": c.execute("INSERT OR IGNORE INTO required_groups VALUES (?)",(val,))
    if kind=="bot": c.execute("INSERT OR IGNORE INTO required_bots VALUES (?)",(val,))
    conn.commit();conn.close()

def remove_required(kind,val):
    conn=sqlite3.connect(DB_PATH);c=conn.cursor()
    if kind=="channel": c.execute("DELETE FROM required_channels WHERE chat=?",(val,))
    if kind=="group": c.execute("DELETE FROM required_groups WHERE chat=?",(val,))
    if kind=="bot": c.execute("DELETE FROM required_bots WHERE username=?",(val,))
    conn.commit();conn.close()

def list_required(kind):
    conn=sqlite3.connect(DB_PATH);c=conn.cursor()
    if kind=="channel": c.execute("SELECT chat FROM required_channels")
    if kind=="group": c.execute("SELECT chat FROM required_groups")
    if kind=="bot": c.execute("SELECT username FROM required_bots")
    rows=[r[0] for r in c.fetchall()]
    conn.close(); return rows

def list_devs():
    conn=sqlite3.connect(DB_PATH);c=conn.cursor();c.execute("SELECT id FROM developers")
    rows=[r[0] for r in c.fetchall()];conn.close();return rows

def is_admin(uid): return uid==OWNER_ID or uid in list_devs()

# ==== UTIL ====
async def is_member(chat,user,context):
    try:
        member = await context.bot.get_chat_member(chat,user)
        return member.status not in ("left","kicked")
    except: return False

async def check_subscription(user_id,context):
    missing=[]
    for ch in list_required("channel"):
        if not await is_member(ch,user_id,context): missing.append(ch)
    for g in list_required("group"):
        if not await is_member(g,user_id,context): missing.append(g)
    for b in list_required("bot"):
        missing.append(b+" (بوت)")  
    return missing

# ==== HANDLERS ====
async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    kb=[
        [InlineKeyboardButton("➕ اضفني إلى مجموعتك", url=f"https://t.me/{context.bot.username}?startgroup=new")],
        [InlineKeyboardButton("📢 قناة البوت",url=f"https://t.me/{BOT_CHANNEL.lstrip('@JO7NB')}"),
         InlineKeyboardButton("👨‍💻 المطور",url=DEV_CONTACT)]
    ]
    await update.message.reply_text("👋 مرحباً! اضفني إلى مجموعتك لتفعيل الاشتراك الإجباري.", 
                                    reply_markup=InlineKeyboardMarkup(kb))

async def group_message(update:Update, context:ContextTypes.DEFAULT_TYPE):
    msg=update.message
    user=msg.from_user
    missing=await check_subscription(user.id,context)
    if missing:
        try: await msg.delete()
        except: pass
        mention=user.mention_html()
        text=f"{mention} 🚫 لازم تشترك أولاً:\n"+"\n".join(missing)
        await msg.chat.send_message(text,parse_mode="HTML")

async def admin_panel(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    kb=[
        [InlineKeyboardButton("➕ إضافة قناة",callback_data="add_channel"),
         InlineKeyboardButton("➖ حذف قناة",callback_data="del_channel")],
        [InlineKeyboardButton("➕ إضافة قروب",callback_data="add_group"),
         InlineKeyboardButton("➖ حذف قروب",callback_data="del_group")],
        [InlineKeyboardButton("➕ إضافة بوت",callback_data="add_bot"),
         InlineKeyboardButton("➖ حذف بوت",callback_data="del_bot")],
        [InlineKeyboardButton("📋 عرض القوائم",callback_data="show_all")],
        [InlineKeyboardButton("📊 إحصائيات",callback_data="stats")]
    ]
    await update.message.reply_text("🔧 لوحة المطور:",reply_markup=InlineKeyboardMarkup(kb))

async def callback(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;await q.answer()
    user=q.from_user
    if not is_admin(user.id):
        await q.edit_message_text("🚫 للمطورين فقط");return

    data=q.data
    if data in ["add_channel","add_group","add_bot","del_channel","del_group","del_bot"]:
        context.user_data["expecting"]=data
        await q.edit_message_text("✏️ ارسل الآن المعرف (مثل @channel أو @bot أو -100...)")
        return

    if data=="stats":
        txt=(f"📊 إحصائيات:\n"
             f"قنوات: {len(list_required('channel'))}\n"
             f"قروبات: {len(list_required('group'))}\n"
             f"بوتات: {len(list_required('bot'))}\n"
             f"مطورين: {len(list_devs())}")
        await q.edit_message_text(txt)

    if data=="show_all":
        channels=list_required("channel")
        groups=list_required("group")
        bots=list_required("bot")
        content="📋 قائمة الاشتراكات المطلوبة:\n\n"

        if channels:
            content+="📢 القنوات:\n"
            for c in channels:
                content+=f"- {c} → https://t.me/{c.lstrip('@')}\n"
        if groups:
            content+="\n👥 القروبات:\n"
            for g in groups:
                if str(g).startswith("-100"):
                    content+=f"- {g} (قروب معرف)\n"
                else:
                    content+=f"- {g} → https://t.me/{g.lstrip('@')}\n"
        if bots:
            content+="\n🤖 البوتات:\n"
            for b in bots:
                content+=f"- {b} → https://t.me/{b.lstrip('@')}\n"

        if not (channels or groups or bots):
            content="⚠️ لا توجد اشتراكات مضافة حالياً."

        with open("subscriptions.txt","w",encoding="utf-8") as f:
            f.write(content)
        await q.message.reply_document(InputFile("subscriptions.txt"),caption="📋 القوائم الحالية.")

async def text_input(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    expecting=context.user_data.get("expecting")
    if not expecting: return
    txt=update.message.text.strip()
    if expecting.startswith("add_"):
        kind=expecting.split("_")[1]
        add_required(kind,txt)
        await update.message.reply_text(f"✅ تمت إضافة {txt} إلى {kind}")
    if expecting.startswith("del_"):
        kind=expecting.split("_")[1]
        remove_required(kind,txt)
        await update.message.reply_text(f"❌ تم حذف {txt} من {kind}")
    context.user_data["expecting"]=None

# ==== MAIN ====
def main():
    init_db()
    app=ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("admin",admin_panel))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_input))
    app.run_polling()

if __name__=="__main__": main()
