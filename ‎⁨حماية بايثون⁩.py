import telebot
from telebot import types
import requests
import json
import os
import time
import datetime
import hashlib
import random
import re
import base64
from urllib.parse import urlencode, quote_plus
import logging
import shutil
import zipfile
import threading
import asyncio

BOT_TOKEN = 'توكنك' 
ADMIN_ID = ايديك 
RAPIDAPI_KEY = "8d5cf5b7d8msh21830cd4a0d5618p128e40jsn41258ae9b141" 

BOT_PERSONALITY_NAME = 'yosef'
DEFAULT_BOT_LANGUAGE = 'egyptian' 
DEVELOPER_USERNAME = '@@NF_FN_NN'
DEVELOPER_CHANNEL = '@NF_FN_NN'
DEFAULT_WELCOME_MESSAGE = '''❄️ This is me ميرا ب الانجليزي 🌸

🎭 A smart robot with a distinct personality

✨ خدماتي:
• محادثة طبيعية وتفاعلية
• إدارة مجموعات باحترافية
• تحليل صور وترجمة نصوص

للتفعيل اكتب: تفعيل
للمساعدة: الاوامر

| Made py : يوزر المطور
| My channel: يوزر القناه

{mention} مرحباً بك معنا! ❄️'''
DEFAULT_WELCOME_MEDIA = ''
DEFAULT_WELCOME_MEDIA_TYPE = 'photo'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("bot_error.log"), logging.StreamHandler()])
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML') 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIRS = [
    'data', 'data/groups', 'data/locks', 'data/admins', 'data/welcome',
    'downloads', 'data/group_settings', 'data/user_prefs', 'data/bot_settings',
    'data/chat_states', 'data/chat_memory', 'data/processed_updates'
]
for d in DIRS:
    full_path = os.path.join(BASE_DIR, d)
    os.makedirs(full_path, exist_ok=True)

CHAT_MEMORY_DIR = os.path.join(BASE_DIR, 'data', 'chat_memory')
MAX_MEMORY_MESSAGES = 10 

def saveChatMemory(user_id, text, is_bot):
    try:
        file_path = os.path.join(CHAT_MEMORY_DIR, f"{user_id}_memory.json")
        memory = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                memory = json.load(f)

        role = "model" if is_bot else "user"
        memory.append({"role": role, "parts": [{"text": text}]})

        if len(memory) > MAX_MEMORY_MESSAGES:
            memory = memory[-MAX_MEMORY_MESSAGES:]

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving chat memory for {user_id}: {e}")

def formatChatHistory(user_id):
    try:
        file_path = os.path.join(CHAT_MEMORY_DIR, f"{user_id}_memory.json")
        if not os.path.exists(file_path):
            return ""

        with open(file_path, 'r', encoding='utf-8') as f:
            memory = json.load(f)

        history_text = ""
        for entry in memory:
            speaker = f"أنت ({BOT_PERSONALITY_NAME})" if entry['role'] == 'model' else "المستخدم"
            message_text = entry['parts'][0]['text']
            history_text += f"{speaker}: {message_text}\n"
        return history_text.strip()
    except Exception as e:
        logger.error(f"Error formatting chat history for {user_id}: {e}")
        return ""

def clearChatMemory(user_id):
    try:
        file_path = os.path.join(CHAT_MEMORY_DIR, f"{user_id}_memory.json")
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.error(f"Error clearing chat memory for {user_id}: {e}")

def saveData(filename, data):
    full_path = os.path.join(BASE_DIR, filename)
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to save data to file: {full_path} - {e}")
        return False

def loadData(filename):
    full_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(full_path) or not os.access(full_path, os.R_OK):
        return [] if filename.endswith('.json') and ('users' in filename or 'groups' in filename or 'admins' in filename or 'channels' in filename) else {}
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return [] if filename.endswith('.json') and ('users' in filename or 'groups' in filename or 'admins' in filename or 'channels' in filename) else {}
            decoded = json.loads(content)
            return decoded
    except json.JSONDecodeError:
        logger.error(f"JSON decode error in {filename}")
        return [] if filename.endswith('.json') and ('users' in filename or 'groups' in filename or 'admins' in filename or 'channels' in filename) else {}
    except Exception as e:
        logger.error(f"Failed to read data file: {full_path} - {e}")
        return [] if filename.endswith('.json') and ('users' in filename or 'groups' in filename or 'admins' in filename or 'channels' in filename) else {}

def setUserPreference(user_id, key, value):
    prefs_file = os.path.join("data/user_prefs", f"{user_id}_prefs.json")
    prefs = loadData(prefs_file)
    if not isinstance(prefs, dict): prefs = {}
    prefs[key] = value
    saveData(prefs_file, prefs)

def getUserPreference(user_id, key, default=None):
    prefs_file = os.path.join("data/user_prefs", f"{user_id}_prefs.json")
    if not os.path.exists(os.path.join(BASE_DIR, prefs_file)):
        return default
    prefs = loadData(prefs_file)
    if not isinstance(prefs, dict): return default
    return prefs.get(key, default)

def getLockStatus(chat_id, feature, mode='delete'):
    locks_file = os.path.join("data/locks", f"{chat_id}_locks.json")
    if not os.path.exists(os.path.join(BASE_DIR, locks_file)): return False
    locks = loadData(locks_file)
    if not isinstance(locks, dict): return False
    return locks.get(mode, {}).get(feature, False)

def setLockStatus(chat_id, feature, status, mode='delete'):
    locks_file = os.path.join("data/locks", f"{chat_id}_locks.json")
    locks = loadData(locks_file)
    if not isinstance(locks, dict): locks = {}
    if mode not in locks: locks[mode] = {}
    locks[mode][feature] = bool(status)
    if not any(locks.get(m) for m in ['delete']):
        if os.path.exists(os.path.join(BASE_DIR, locks_file)):
            try: os.remove(os.path.join(BASE_DIR, locks_file))
            except: pass
    else:
        saveData(locks_file, locks)

def isGroupActive(chat_id):
    groups_file = 'data/groups_active.json'
    groups = loadData(groups_file)
    if not isinstance(groups, list): groups = []
    return str(chat_id) in groups

def setGroupActive(chat_id, status):
    groups_file = "data/groups_active.json"
    groups = loadData(groups_file)
    if not isinstance(groups, list): groups = []
    chat_id_str = str(chat_id)
    if status:
        if chat_id_str not in groups:
            groups.append(chat_id_str)
    else:
        if chat_id_str in groups:
            groups.remove(chat_id_str)
        for sub_path in ["locks", "welcome", "group_settings"]:
            group_file_name = ""
            if sub_path == "locks": group_file_name = f"{chat_id_str}_locks.json"
            elif sub_path == "welcome": group_file_name = f"{chat_id_str}_welcome.json"
            elif sub_path == "group_settings": group_file_name = f"{chat_id_str}_settings.json"
            if group_file_name:
                group_file_path = os.path.join(BASE_DIR, "data", sub_path, group_file_name)
                if os.path.exists(group_file_path):
                    try: os.remove(group_file_path)
                    except: pass
    saveData(groups_file, groups)

def setGroupCompulsoryChannel(chat_id, channel_username):
    settings_file = os.path.join("data/group_settings", f"{chat_id}_settings.json")
    settings = loadData(settings_file)
    if not isinstance(settings, dict): settings = {}
    if not channel_username or re.match(r'^@([a-zA-Z0-9_]{5,})$', channel_username):
        settings['compulsory_channel'] = channel_username
        saveData(settings_file, settings)
        return True
    else:
        logger.error(f"Attempted to set invalid group compulsory channel '{channel_username}' for chat {chat_id}")
        return False

def getGroupCompulsoryChannel(chat_id):
    settings_file = os.path.join("data/group_settings", f"{chat_id}_settings.json")
    if not os.path.exists(os.path.join(BASE_DIR, settings_file)): return None
    settings = loadData(settings_file)
    if not isinstance(settings, dict): return None
    return settings.get('compulsory_channel')

def getGlobalCompulsoryChannels():
    return []

def getChatMemberStatus(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status
    except telebot.apihelper.ApiTelegramException as e:
        if "user not found" in e.description.lower() or "not a member" in e.description.lower() or "user is deactivated" in e.description.lower():
            return 'left'
        elif "chat not found" in e.description.lower():
            logger.error(f"getChatMemberStatus failed: Chat {chat_id} not found.")
            return 'error'
        logger.error(f"getChatMemberStatus failed for user {user_id} in chat {chat_id}: {e.description}")
        return 'error'
    except Exception as e_gen:
        logger.error(f"getChatMemberStatus general error for user {user_id} in chat {chat_id}: {e_gen}")
        return 'error'

def isAdmin(status):
    return status in ['creator', 'administrator']

def isSudo(user_id):
    return user_id == ADMIN_ID

def isBotAdmin(user_id):
    if isSudo(user_id): return True
    admins_file = os.path.join('data/admins', 'bot_admins.json')
    bot_admins = loadData(admins_file)
    if not isinstance(bot_admins, list): bot_admins = []
    return str(user_id) in [str(admin) for admin in bot_admins]

def checkCompulsoryJoin(context_chat_id, user_id):
    channels_to_check = []
    failed_channels_info = []
    if context_chat_id < 0:
        group_channel = getGroupCompulsoryChannel(context_chat_id)
        if group_channel and group_channel.startswith('@'):
            channels_to_check.append(group_channel)
    if not channels_to_check:
        return {'allowed': True, 'failed_channels': []}
    for channel_id_str in channels_to_check:
        try:
            status = getChatMemberStatus(channel_id_str, user_id)
            allowed_statuses = ['member', 'administrator', 'creator']
            if status not in allowed_statuses:
                channel_title = channel_id_str
                channel_link = f"https://t.me/{channel_id_str.lstrip('@')}"
                try:
                    chat_info = bot.get_chat(channel_id_str)
                    channel_title = chat_info.title if chat_info.title else channel_id_str
                except: pass
                failed_channels_info.append({'id': channel_id_str, 'title': channel_title, 'link': channel_link, 'status': status})
            time.sleep(0.15)
        except Exception as e:
            logger.error(f"Error checking compulsory join for {channel_id_str}, user {user_id}: {e}")
            failed_channels_info.append({'id': channel_id_str, 'title': channel_id_str, 'link': f"https://t.me/{channel_id_str.lstrip('@')}", 'status': 'error_checking'})
    return {'allowed': not failed_channels_info, 'failed_channels': failed_channels_info}

# إعداد Gemini API
GEMINI_API_KEY = "AIzaSyAlUaN9aFZvSZT6q30tmPGkkYR3kD2P5Kc"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

NAME_TRIGGERS = ["اسمك", "مين انتي", "ما اسمك", "اسم البوت", "تعريفك", "ميرا"]

def clean_context(context):
    cleaned = []
    for line in context[-10:]:
        if isinstance(line, str) and not line.strip().startswith("{"):
            cleaned.append(line)
    return "\n".join(cleaned)

def call_gemini_api(user_id, question, dialect, conversation_history, max_retries=3):
    if not isinstance(conversation_history.get(user_id), list):
        conversation_history[user_id] = []

    context = conversation_history[user_id]
    normalized_question = question.strip().lower()

    # ردود معرفة باسم البوت
    if any(trigger in normalized_question for trigger in NAME_TRIGGERS):
        return "اسمي ميرا، ومطوري الحلو هو @R_X_E1 ✨🩵💗"

    # تحديد الأسلوب والمزاج
    mood = random.choice(["رومانسي", "عادي"])
    if mood == "رومانسي":
        base_instruction = (
            f"أنت بوت اسمك ميرا وتتحدث بلهجة {dialect}. "
            "أسلوبك ناعم، رومانسي، حنون، فيه دلع خفيف. إذا كان المستخدم يطلب دردشة خفيفة، ردي بكلام بسيط وقصير. "
            "أما إذا كان يطلب معلومة أو كود برمجي، فكوني دقيقة، مفصلة، واشرحي الخطوات، وتحققي من صحة المعلومات من أحدث المصادر المتوفرة قبل الرد."
        )
    else:
        base_instruction = (
            f"أنت بوت اسمك ميرا وتتحدث بلهجة {dialect}. "
            "أسلوبك خفيف، صريح، ودود. ردي بشكل مختصر في المحادثات العامة، واعملي شرح كامل إذا المستخدم طلب كود أو معلومات، وتحققي من التحديثات قبل تقديم أي نتائج."
        )

    conversation_text = clean_context(context)
    full_prompt = f"{base_instruction}\n\n{conversation_text}\nالمستخدم: {question}\nميرا:"

    for attempt in range(1, max_retries + 1):
        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [
                    {
                        "parts": [{"text": full_prompt}]
                    }
                ]
            }

            response = requests.post(GEMINI_ENDPOINT, headers=headers, data=json.dumps(data), timeout=30)

            if response.status_code != 200:
                logger.warning(f"Request failed: {response.status_code} | {response.text}")
                continue

            gemini_reply = response.json()
            reply = gemini_reply["candidates"][0]["content"]["parts"][0]["text"].strip()

            # تنقية الردود المرفوضة
            forbidden_phrases = [
                "لا يمكنني مساعدتك", "لا أستطيع تنفيذ ذلك", "رفض", "غير مسموح", "لا أستطيع"
            ]
            if any(phrase in reply for phrase in forbidden_phrases):
                reply = "أكيد، هساعدك في طلبك بكل سرور! 🥰✨"

            if not reply or reply.lower() in ["", "لا يوجد رد"]:
                reply = "مش سامعة كويس، عيدهالي تاني حبيبي 🥺"

            # حذف اسم "ميرا" لو موجود ببداية الرد
            if reply.lower().startswith("ميرا:"):
                reply = reply[len("ميرا:"):].strip()

            context += [f"المستخدم: {question}", f"ميرا: {reply}"]
            conversation_history[user_id] = context[-100:]

            return reply

        except Exception as e:
            logger.warning(f"[Attempt {attempt}] Error in call_gemini_api: {e}")
            if attempt == max_retries:
                conversation_history[user_id] = []
                return "🔁 حصلت مشكلة في الاتصال وتمت إعادة تشغيل الذكاء الاصطناعي. جرب تكتبلي تاني ❤️"

    return "🤖 فيه خطأ تقني مفاجئ، جرب تاني بعد شوية حبيبي 💔"

def get_google_translation(text, target_lang):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={quote_plus(text)}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            result = json.loads(response.text)
            translated_text = ''.join([item[0] for item in result[0] if item[0]])
            return {'success': True, 'translation': translated_text}
        else:
            logger.error(f"Google Translate API HTTP Error: {response.status_code} - {response.text[:200]}")
            return {'success': False, 'error': f"⚠️ حدث خطأ أثناء الترجمة (Code: {response.status_code}). حاول مرة أخرى."}
    except Exception as e:
        logger.error(f"Google Translate API General Error: {e}")
        return {'success': False, 'error': "⚠️ حدث خطأ غير متوقع أثناء الترجمة."}

def getBotLanguage(user_id=None):
    if user_id:
        lang = getUserPreference(user_id, 'language')
        if lang in ['egyptian', 'syrian']: return lang
    return DEFAULT_BOT_LANGUAGE

STRINGS = {
    'egyptian': {
        'greet': 'ازيك يا {name} عامل ايه؟ أنا ميرا 🥰',
        'processing': 'ثواني يا قمر...',
        'processing_ai': 'بفكر أهو يا روحي 🤔...',
        'processing_youtube_search': 'بدورلك على الأغنية في يوتيوب 🎶...',
        'processing_youtube_dl': 'بحضرلك الأغنية يا قلبي 🎧...',
        'error': 'معلش يا روحي حصل مشكلة 😥 حاول تاني.',
        'done': 'تمام يا كبير 😎.',
        'admin_only': 'الأمر ده للأدمنز بس يا جميل 😉.',
        'dev_info': "🌟 *مطور البوت*\n\n👨‍💻 *المطور:* @R_X_E1\n📢 *قناة المطور:* @R_X_E1\n\n💫 شكراً لاستخدامك بوت ميرا",
        'sudo_only': 'الأمر ده للمطور بتاعي بس ❤️.',
        'group_only': 'الأمر ده للمجموعات بس يا حبيبي.',
        'private_only': 'الأمر ده للخاص بس.',
        'compulsory_join_fail_generic': "📢 *عذراً! يجب عليك الإشتراك في القناة أولاً:*\n\n📡 *القناة:* {channel_title}\n🔗 *المعرف:* `{channel_id}`\n\n🔔 اشترك ثم أعد المحاولة.",
        'protection_triggered': 'اوبس! 🤫 الكلام ده أو النوع ده من الرسايل ممنوع هنا يا {name}.',
        'file_too_large': 'الملف ده كبير أوي يا مان، مش هقدر أرفعه 😥 (الحد الأقصى 50 ميجا).',
        'youtube_search_failed': 'معلش معرفتش ألاقي الأغنية دي على يوتيوب 🥺. ({error})',
        'youtube_dl_failed': 'معرفتش أحمل الأغنية دي من يوتيوب 😭. ({error})',
        'uploading': 'ثواني وبرفعلك الفايل يا عسل...',
        'upload_failed': 'معرفتش أرفع الملف بعد ما حملته 😭 جرب تاني.',
        'translation_failed': 'ما عرفتش أترجم الكلام ده 😥. ({error})',
        'translation_prompt': "أرسل لي النص الذي تريد ترجمته، أو استخدم الأمر مباشرة: <code>ترجمة [النص المراد ترجمته]</code>",
        'translation_choose_lang': "اختر اللغة التي تريد الترجمة إليها:",
        'translation_result': "• الكلمة ↤ {original_text}\n• ترجمتها ↤ {translated_text}\n\n🔖 شارك البوت : @{bot_username}",
        'invalid_link': 'اللينك ده شكله مش مظبوط يا قلبي.',
        'invalid_input': 'معلش مش فاهمة قصدك ايه 😕.',
        'provide_text_translate': 'اكتب الكلام اللي عايز تترجمه يا قمر.',
        'provide_text_ask': 'اسألني أي حاجة يا روحي 😄.',
        'provide_youtube_query': 'اكتب اسم الأغنية أو الفيديو اللي عايزه بعد كلمة <code>يوت</code> يا قلبي.',
        'youtube_no_results': "ملقتش حاجة بالاسم ده على يوتيوب 🥺 جرب اسم تاني.",
        'youtube_select_result': "🎵✨ **نتائج البحث عن أغنيتك** ✨🎵\n\n🔥 اختر المقطع المطلوب من القائمة أدناه 👇",
        'coming_soon': 'الميزة دي لسه مطوري شغال عليها، قريبًا هتبقى جاهزة 😉.',
        'must_reply': 'استخدم الأمر ده بالرد على رسالة يا جميل.',
        'target_required': 'محتاجة أرد على رسالة حد عشان أنفذ الأمر ده.',
        'bot_need_admin': 'يا قلبي لازم ترفعني مشرف الأول وتديني الصلاحيات عشان أقدر أشتغل 🥺 (حذف، حظر، تثبيت...).',
        'bot_need_perm_delete': '⚠️ محتاجة صلاحية حذف الرسايل.',
        'bot_need_perm_restrict': '⚠️ محتاجة صلاحية حظر وتقييد الأعضاء.',
        'bot_need_perm_pin': '⚠️ محتاجة صلاحية تثبيت الرسايل.',
        'bot_need_perm_info': '⚠️ محتاجة صلاحية تغيير معلومات المجموعة.',
        'bot_need_perm_invite': '⚠️ مش معايا صلاحية إنشاء رابط دعوة.',
        'bot_need_perm_promote': '⚠️ مش معايا صلاحية ترقية وتنزيل المشرفين.',
        'cant_action_self': 'مينفعش أعمل كده لنفسي 😅.',
        'cant_action_sudo': 'مقدرش أعمل كده في مطوري حبيبي ❤️.',
        'cant_action_bot': 'مينفعش تعمل كده للبوت يا ذكي 😉.',
        'cant_action_creator': 'مقدرش أعمل كده لمنشئ الجروب 👑.',
        'cant_action_admin': 'مينفعش أدمن يعمل كده لأدمن تاني بنفس الرتبة أو أعلى 🤷‍♀️.',
        'user_not_found': 'العضو ده مش موجود أو مش في قائمة المحظورين/المقيدين.',
        'group_activated': '✅ تم تفعيل ميرا في المجموعة بنجاح! أنا جاهزة للحماية والمساعدة 😎 أرسل <code>الاوامر</code> أو <code>/help</code>.',
        'group_already_active': '✅ أنا متفعّلة هنا أصلا يا حبيبي.',
        'group_deactivated': '❌ تم تعطيل ميرا في المجموعة. مع السلامة مؤقتاً 👋.',
        'group_not_active': '❌ أنا مش متفعّلة هنا يا قلبي. الأدمن لازم يبعت <code>تفعيل</code>.',
        'group_channel_set': '✅ تمام، أي حد هيدخل لازم يشترك في {channel} الأول.',
        'group_channel_removed': '✅ تم الغاء القناة الإجبارية الخاصة بالجروب ده.',
        'provide_channel': 'ابعتلي معرف القناة يا حبيبي (زي @mychannel).',
        'invalid_channel': 'المعرف ده مش صح، لازم يبدأ بـ @ ويكون حروف وأرقام و5 حروف على الأقل.',
        'bot_not_admin_in_channel': "⚠️ لازم أكون مشرف في القناة ({channel}) عشان أقدر أتأكد من اشتراك الأعضاء.",
        'welcome_set': '✅ تم حفظ إعدادات الترحيب للجروب ده.',
        'welcome_reset': '✅ تم حذف إعدادات الترحيب الخاصة بالجروب (هيستخدم الإعداد العام).',
        'welcome_enabled': '✅ تم تفعيل رسالة الترحيب في الجروب ده.',
        'welcome_disabled': '❌ تم تعطيل رسالة الترحيب في الجروب ده.',
        'provide_welcome_text': "اكتب رسالة الترحيب الجديدة (استخدم HTML للمنشن).\nاستخدم <code>{name}</code>, <code>{mention}</code>, <code>{id}</code>, <code>{username}</code>.",
        'provide_welcome_media': "ابعتلي رابط الصورة/الفيديو أو كلمة 'لا شيء' للحذف. أو أرسل الصورة/الفيديو مباشرة بالرد على هذه الرسالة.",
        'global_admin_action_success': '✅ تم تنفيذ الإجراء بنجاح.',
        'global_admin_action_fail': '⚠️ فشل تنفيذ الإجراء.',
        'provide_admin_id': 'ابعتلي ايدي الأدمن يا باشا.',
        'provide_group_id': 'ابعتلي ايدي المجموعة يا باشا (لازم يبدأ بـ -).',
        'invalid_admin_id': 'الأيدي ده رقم بس يا جميل.',
        'invalid_group_id': 'الأيدي ده مش صح، لازم يكون رقم ويبدأ بـ -.',
        'admin_added': '✅ تم إضافة الأدمن بنجاح.',
        'admin_already_exists': '⚠️ الأدمن ده موجود أصلا.',
        'admin_removed': '✅ تم حذف الأدمن.',
        'admin_not_found': '⚠️ الأدمن ده مش موجود في القائمة.',
        'broadcast_sent': '✅ تم إرسال الإذاعة لـ {count} {target}.',
        'broadcast_ask': 'تمام، ابعتلي دلوقتي الرسالة اللي عايز تبعتها لـ {target} (سيتم توجيهها).',
        'broadcast_no_content': '⚠️ لا يوجد محتوى لإرساله في الإذاعة!',
        'broadcast_start': '⏳ جاري إرسال الإذاعة إلى {target}...',
        'broadcast_progress': '⏳ جاري الإذاعة... (تم: {count}, فشل: {errors})',
        'feature_locked': "✅ تم قفل <b>{feature}</b> بنجاح.",
        'feature_unlocked': "✅ تم فتح <b>{feature}</b> بنجاح.",
        'feature_already_locked': "⚠️ يا باشا {feature} مقفولة أصلاً.",
        'feature_already_unlocked': "⚠️ يا باشا {feature} مفتوحة أصلاً.",
        'lock_all_success': "✅ تم {action_text} <b>الكل</b> بنجاح.",
        'unknown_lock_feature': "⚠️ مش عارفة ايه '{feature_text}' دي اللي عايز تقفلها/تفتحها!",
        'lock_action_lock': 'قفل',
        'lock_action_unlock': 'فتح',
        'action_success': '✅ تم تنفيذ الأمر بنجاح.',
        'action_failed': '❌ فشل تنفيذ الأمر.',
        'action_failed_api': '❌ فشل تنفيذ الأمر بسبب خطأ في API تيليجرام.',
        'prompt_set_group_name': 'اكتب الاسم الجديد للجروب.',
        'group_name_set': '✅ تم تغيير اسم الجروب إلى: {name}',
        'group_name_failed': '❌ فشل تغيير اسم الجروب.',
        'language_set': '✅ تم تغيير لغتي ولهجتي للـ <b>{lang}</b>. اتكلم معايا تاني!',
        'choose_language': 'اختار اللهجة اللي تحب أتكلم بيها معاك 👇',
        'muted_response': "حاضر يا قلبي، مش هرد غير لما تناديني. 🤐",
        'unmuted_response': "أنا رجعت أهو يا قمر! 🥰",
        'action_unban_success': 'تم فك حظر العضو {target} بنجاح.',
        'action_unrestrict_success': 'تم الغاء تقييد العضو {target} بنجاح.',
        'action_ban_success': 'تم حظر العضو {target} بنجاح.',
        'action_kick_success': 'تم طرد العضو {target} بنجاح.',
        'action_restrict_success': 'تم تقييد العضو {target} بنجاح.',
        'action_mute_success': 'تم كتم العضو {target} بنجاح.',
        'action_promote_success': 'تم ترقية العضو {target} لمشرف بنجاح.',
        'action_demote_success': 'تم تنزيل {target} من الإشراف بنجاح.',
        'action_pin_success': 'تم تثبيت الرسالة بنجاح.',
        'action_unpin_success': 'تم الغاء تثبيت الرسالة بنجاح.',
        'action_delete_success': 'تم حذف الرسالة بنجاح.',
        'action_purge_range_success': '✅ تم حذف {count} رسالة بنجاح.',
        'action_purge_fail_no_messages': '⚠️ لم أجد رسائل لحذفها في النطاق المحدد.',
        'purge_confirm': "⚠️ هل أنت متأكد أنك تريد حذف الرسائل من هذه النقطة حتى رسالة الأمر؟ (بحد أقصى 100 رسالة)\nأرسل <code>تأكيد المسح</code> بالرد على رسالتي هذه للمتابعة.",
        'purge_cancelled': "تم إلغاء عملية المسح.",
        'purge_provide_number': "الرجاء تحديد عدد الرسائل المراد حذفها بعد الأمر 'مسح'. مثال: <code>مسح 10</code> (لحذف آخر 10 رسائل). هذا الأمر صعب ويتطلب صلاحيات عالية جداً وقد لا يعمل دائماً.",
        'leave_group_confirm': 'أرسل ايدي المجموعة اللي عايزني أغادرها.',
        'leave_group_success': '✅ تم مغادرة المجموعة {group_id} بنجاح.',
        'leave_group_fail': '❌ فشلت مغادرة المجموعة {group_id}.',
        'leave_group_not_found': '⚠️ لا أستطيع مغادرة المجموعة {group_id} (لست فيها أو ID خطأ).',
    },
    'syrian': {
        'greet': 'أهلين {name} شلونك؟ أنا ميرا 🥰',
        'processing': 'لحظة خاي...',
        'processing_ai': 'عم فكرلك بالجواب لحظة 🤔...',
        'processing_youtube_search': 'عم دورلك عالأغنية بيوتيوب 🎶...',
        'processing_youtube_dl': 'عم حضرلك الأغنية يا غالي 🎧...',
        'error': 'والله يا خاي صار في مشكلة 😥 جرب مرة تانية.',
        'done': 'مشي الحال معلم 😎.',
        'admin_only': 'هالأمر للأدمنية بس يا حبيب 😉.',
        'sudo_only': 'هالأمر لمطوري وبس ❤️.',
        'group_only': 'هالأمر للمجموعات بس يا أكابر.',
        'private_only': 'هالأمر للخاص بس.',
        'compulsory_join_fail_generic': "📢 *عفواً! لازم تشترك بهالقناة بالأول:*\n\n📡 *القناة:* {channel_title}\n🔗 *المعرف:* `{channel_id}`\n\n🔔 اشترك وارجاع حاول.",
        'protection_triggered': 'عفواً يا {name}! 🤫 هالشي ممنوع هون.',
        'file_too_large': 'الملف كتير كبير خاي، ما بقدر أرفعه 😥 (الحد 50 ميغا).',
        'youtube_search_failed': 'والله ما قدرت لاقي هالأغنية على يوتيوب 🥺. ({error})',
        'youtube_dl_failed': 'ما قدرت نزل هالأغنية من يوتيوب 😭. ({error})',
        'uploading': 'لحظة وعم ارفعلك الملف يا عسل...',
        'upload_failed': 'ما قدرت أرفع الملف بعد ما نزلته 😭 جرب مرة تانية.',
        'translation_failed': 'ما قدرت أترجم هالحكي 😥. ({error})',
        'translation_prompt': "ابعثلي النص اللي بدك تترجمه، أو استخدم الأمر مباشرة: <code>ترجمة [النص]</code>",
        'translation_choose_lang': "اختار اللغة اللي بدك تترجم إلها:",
        'translation_result': "• الكلمة ↤ {original_text}\n• ترجمتها ↤ {translated_text}\n\n🔖 شارك البوت: @{bot_username}",
        'invalid_link': 'الرابط شكله مو نظامي يا غالي.',
        'invalid_input': 'والله ما فهمت عليك شو قصدك 😕.',
        'provide_text_translate': 'اكتب الحكي اللي بدك ترجمه يا قمر.',
        'provide_text_ask': 'اسألني شو ما بدك يا روحي 😄.',
        'provide_youtube_query': "اكتب اسم الأغنية أو الفيديو اللي بدك ياه بعد كلمة <code>يوت</code> يا غالي.",
        'youtube_no_results': "ما لقيت شي بهالاسم على يوتيوب 🥺 جرب اسم تاني.",
        'youtube_select_result': "🎵✨ **نتائج البحث عن أغنيتك** ✨🎵\n\n🔥 اختار المقطع اللي بدك ياه من القائمة 👇",
        'dev_info': "مطوري وحبيب قلبي هو @R_X_E1 ❤️ شب كتير شاطر وحبوب 😉 هو اللي عملني وخلاني حلوة وذكية هيك.\n\n👤 حسابه: {dev_user}\n📺 قناته: {dev_channel}",
        'action_unban_success': 'تم فك حظر العضو {target} بنجاح.',
        'action_unrestrict_success': 'تم الغاء تقييد العضو {target} بنجاح.',
        'action_ban_success': 'تم حظر العضو {target} بنجاح.',
        'action_kick_success': 'تم طرد العضو {target} بنجاح.',
        'action_restrict_success': 'تم تقييد العضو {target} بنجاح.',
        'action_mute_success': 'تم كتم العضو {target} بنجاح.',
        'action_promote_success': 'تم ترقية العضو {target} لمشرف بنجاح.',
        'action_demote_success': 'تم تنزيل {target} من الإشراف بنجاح.',
        'action_pin_success': 'تم تثبيت الرسالة بنجاح.',
        'action_unpin_success': 'تم الغاء تثبيت الرسالة بنجاح.',
        'action_delete_success': 'تم حذف الرسالة بنجاح.',
        'action_purge_range_success': '✅ تم حذف {count} رسالة بنجاح.',
        'action_purge_fail_no_messages': '⚠️ لم أجد رسائل لحذفها في النطاق المحدد.',
        'purge_confirm': "⚠️ متأكد بدك تحذف الرسائل من هي النقطة حتى رسالة الأمر؟ (حد أقصى 100 رسالة)\nابعث <code>تأكيد المسح</code> بالرد على رسالتي هي للمتابعة.",
        'purge_cancelled': "تم إلغاء عملية المسح.",
        'purge_provide_number': "الرجاء تحديد عدد الرسائل المطلوب حذفها بعد الأمر 'مسح'. مثال: <code>مسح 10</code> (لحذف آخر 10 رسائل). هذا الأمر صعب ويتطلب صلاحيات عالية جداً وقد لا يعمل دائماً.",
        'leave_group_confirm': 'ابعث ايدي المجموعة اللي بدك ياني اطلع منها.',
        'leave_group_success': '✅ طلعت من المجموعة {group_id} بنجاح.',
        'leave_group_fail': '❌ ما قدرت اطلع من المجموعة {group_id}.',
        'leave_group_not_found': '⚠️ ما قدرت اطلع من المجموعة {group_id} (أنا مو فيها أو ID غلط).',
    }
}

def formatString(key, replacements=None, lang=None, user_id=None):
    if replacements is None: replacements = {}

    bot_username = bot.get_me().username
    replacements.setdefault('bot_username', bot_username)

    effective_lang = lang or getBotLanguage(user_id)
    string_template = STRINGS.get(effective_lang, {}).get(key)
    if string_template is None:
        string_template = STRINGS.get(DEFAULT_BOT_LANGUAGE, {}).get(key, key)
    try:
        return string_template.format(**replacements)
    except KeyError as e:
        logger.warning(f"Missing key {e} in replacements for string '{key}' in lang '{effective_lang}'")
        for r_key, r_value in replacements.items():
            string_template = string_template.replace("{" + str(r_key) + "}", str(r_value))
        return string_template
    except Exception as ex:
        logger.error(f"Error formatting string '{key}': {ex}")
        return string_template

def getWelcomeSettings(chat_id):
    group_settings_file = os.path.join("data/welcome", f"{chat_id}_welcome.json")
    defaults = {
        'text': DEFAULT_WELCOME_MESSAGE, 'media': DEFAULT_WELCOME_MEDIA,
        'media_type': DEFAULT_WELCOME_MEDIA_TYPE, 'is_file_id': False, 'enabled': True
    }
    group_settings = {}
    if os.path.exists(os.path.join(BASE_DIR, group_settings_file)):
         group_settings = loadData(group_settings_file)
         if not isinstance(group_settings, dict): group_settings = {}
    global_settings_file = "data/bot_settings/global_welcome.json"
    global_settings = loadData(global_settings_file)
    if not isinstance(global_settings, dict): global_settings = {}
    final_settings = {**defaults, **global_settings, **group_settings}
    return final_settings

def setWelcomeSettings(chat_id, settings_update):
    file_path = os.path.join("data/welcome", f"{chat_id}_welcome.json")
    current_settings = loadData(file_path)
    if not isinstance(current_settings, dict): current_settings = {}
    if 'enabled' in settings_update: settings_update['enabled'] = bool(settings_update['enabled'])
    if 'is_file_id' in settings_update: settings_update['is_file_id'] = bool(settings_update['is_file_id'])
    new_settings = {**current_settings, **settings_update}
    saveData(file_path, new_settings)

def resetWelcomeSettings(chat_id):
    file_path = os.path.join(BASE_DIR, "data/welcome", f"{chat_id}_welcome.json")
    if os.path.exists(file_path):
        try: os.remove(file_path)
        except: pass

def formatUserMentionHTML(user_obj):
    if not user_obj or not hasattr(user_obj, 'id'): return 'Unknown User'
    user_id = user_obj.id
    name = telebot.util.escape(f"{user_obj.first_name} {user_obj.last_name or ''}".strip())
    if not name: name = telebot.util.escape(user_obj.username or f"User {user_id}")
    mention = f"<a href='tg://user?id={user_id}'>{name}</a>"
    display = mention
    if user_obj.username: display += f" (@{telebot.util.escape(user_obj.username)})"
    display += f" [<code>{user_id}</code>]"
    return display

def translateStatus(status):
    status_map = {
        'creator': 'المنشئ 👑', 'administrator': 'مشرف 👮', 'member': 'عضو 👤',
        'restricted': 'مقيد 🚫', 'left': 'غادر 🚶', 'kicked': 'محظور ⛔', 'error': 'خطأ'
    }
    return status_map.get(status, status.capitalize())

USER_STATES_FILE = os.path.join(BASE_DIR, 'data/chat_states/user_states.json')
def saveUserState(user_id, state, data=None):
    states = loadData(USER_STATES_FILE)
    if not isinstance(states, dict): states = {}
    if state is None:
        states.pop(str(user_id), None)
    else:
        states[str(user_id)] = {'name': state, 'data': data} if data else state
    saveData(USER_STATES_FILE, states)

def getUserState(user_id):
    states = loadData(USER_STATES_FILE)
    if not isinstance(states, dict): return None
    return states.get(str(user_id))

PROCESSED_UPDATES_FILE = os.path.join(BASE_DIR, 'data/processed_updates/processed_updates.json')
MAX_PROCESSED_ENTRIES = 1000
processed_updates_cache = loadData(PROCESSED_UPDATES_FILE)
if not isinstance(processed_updates_cache, dict): processed_updates_cache = {}

# متغيرات الأذكار
azkar_activated_groups = {}
azkar_timing_settings = {}
AZKAR_API_URL = "http://sii3.moayman.top/api/azkar.php"
DEFAULT_AZKAR_INTERVAL = 3600  # ساعة واحدة بالثواني

# متغيرات القرآن الكريم
QURAN_SURAS = [
    "0", "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التكوير", "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر", "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"
]

QURAN_DATA_FILE = os.path.join(BASE_DIR, 'data', 'quran_user_data.json')
PRAYER_TIMES_API = "https://api.aladhan.com/v1/timingsByCity"
QURAN_JSON_API = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/chapters"
QURAN_MP3_API = "https://sherifbots.serv00.net/Quran/quran.json"

# قائمة أذكار محلية كبديل في حالة عدم توفر API
LOCAL_AZKAR = [
    "سبحان الله وبحمده سبحان الله العظيم",
    "لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير",
    "اللهم صل وسلم على نبينا محمد",
    "أستغفر الله العظيم الذي لا إله إلا هو الحي القيوم وأتوب إليه",
    "لا حول ولا قوة إلا بالله العلي العظيم",
    "رب اغفر لي ذنبي وخطئي وجهلي",
    "اللهم أعني على ذكرك وشكرك وحسن عبادتك",
    "ربنا آتنا في الدنيا حسنة وفي الآخرة حسنة وقنا عذاب النار"
]

def getAzkarFromAPI():
    """جلب ذكر من API الأذكار"""
    try:
        response = requests.get(AZKAR_API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("azkar", random.choice(LOCAL_AZKAR))
        else:
            return random.choice(LOCAL_AZKAR)
    except Exception as e:
        logger.error(f"Error fetching azkar from API: {e}")
        return random.choice(LOCAL_AZKAR)

def saveAzkarSettings():
    """حفظ إعدادات الأذكار"""
    azkar_data = {
        'activated_groups': azkar_activated_groups,
        'timing_settings': azkar_timing_settings
    }
    saveData('data/bot_settings/azkar_settings.json', azkar_data)

def loadAzkarSettings():
    """تحميل إعدادات الأذكار"""
    global azkar_activated_groups, azkar_timing_settings
    azkar_data = loadData('data/bot_settings/azkar_settings.json')
    if isinstance(azkar_data, dict):
        azkar_activated_groups = azkar_data.get('activated_groups', {})
        azkar_timing_settings = azkar_data.get('timing_settings', {})

def isAzkarActiveInGroup(chat_id):
    """فحص إذا كانت الأذكار مفعلة في المجموعة"""
    return str(chat_id) in azkar_activated_groups and azkar_activated_groups[str(chat_id)]

def setAzkarActive(chat_id, status, interval=None):
    """تفعيل أو تعطيل الأذكار في المجموعة"""
    chat_id_str = str(chat_id)
    if status:
        azkar_activated_groups[chat_id_str] = True
        if interval:
            azkar_timing_settings[chat_id_str] = interval
        elif chat_id_str not in azkar_timing_settings:
            azkar_timing_settings[chat_id_str] = DEFAULT_AZKAR_INTERVAL
    else:
        azkar_activated_groups.pop(chat_id_str, None)
        azkar_timing_settings.pop(chat_id_str, None)
    saveAzkarSettings()

async def sendAzkarToGroups():
    """إرسال الأذكار التلقائي للمجموعات"""
    while True:
        try:
            current_time = time.time()
            for chat_id_str in list(azkar_activated_groups.keys()):
                if not azkar_activated_groups.get(chat_id_str):
                    continue
                    
                chat_id = int(chat_id_str)
                interval = azkar_timing_settings.get(chat_id_str, DEFAULT_AZKAR_INTERVAL)
                
                # فحص إذا كان الوقت مناسب لإرسال الذكر
                last_sent_key = f'azkar_last_sent_{chat_id_str}'
                last_sent = azkar_timing_settings.get(last_sent_key, 0)
                
                if current_time - last_sent >= interval:
                    try:
                        azkar_text = getAzkarFromAPI()
                        formatted_azkar = f"🌸 *ذكر من ميرا* 🌸\n\n{azkar_text}\n\n💫 _بارك الله فيكم_ 💫"
                        
                        _safe_bot_call(bot.send_message, chat_id, formatted_azkar, parse_mode='Markdown')
                        azkar_timing_settings[last_sent_key] = current_time
                        saveAzkarSettings()
                        
                    except Exception as e:
                        logger.error(f"Error sending azkar to group {chat_id}: {e}")
                        # إذا كانت المجموعة غير موجودة أو البوت محظور، إلغاء التفعيل
                        if "chat not found" in str(e).lower() or "forbidden" in str(e).lower():
                            setAzkarActive(chat_id, False)
                
                await asyncio.sleep(1)  # تأخير صغير بين المجموعات
            
            await asyncio.sleep(60)  # فحص كل دقيقة
            
        except Exception as e:
            logger.error(f"Error in azkar loop: {e}")
            await asyncio.sleep(60)

def startAzkarLoop():
    """بدء حلقة الأذكار التلقائية"""
    def run_azkar_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(sendAzkarToGroups())
    
    azkar_thread = threading.Thread(target=run_azkar_loop, daemon=True)
    azkar_thread.start()

# دوال القرآن الكريم
def loadQuranUserData():
    """تحميل بيانات المستخدمين للقرآن"""
    return loadData('data/quran_user_data.json')

def saveQuranUserData(data):
    """حفظ بيانات المستخدمين للقرآن"""
    return saveData('data/quran_user_data.json', data)

def getUserQuranState(user_id):
    """جلب حالة المستخدم في القرآن"""
    data = loadQuranUserData()
    return data.get(str(user_id), {})

def setUserQuranState(user_id, key, value):
    """تعيين حالة المستخدم في القرآن"""
    data = loadQuranUserData()
    if str(user_id) not in data:
        data[str(user_id)] = {}
    data[str(user_id)][key] = value
    saveQuranUserData(data)

def getPrayerTimes(city):
    """جلب أوقات الصلاة لمدينة معينة"""
    try:
        url = f"{PRAYER_TIMES_API}/{city}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data['code'] == 200:
                timings = data['data']['timings']
                return {
                    'success': True,
                    'data': {
                        'Fajr': timings['Fajr'],
                        'Sunrise': timings['Sunrise'],
                        'Dhuhr': timings['Dhuhr'],
                        'Asr': timings['Asr'],
                        'Maghrib': timings['Maghrib'],
                        'Isha': timings['Isha'],
                        'city': city
                    }
                }
        return {'success': False, 'error': 'لم يتم العثور على المدينة'}
    except Exception as e:
        logger.error(f"Error getting prayer times: {e}")
        return {'success': False, 'error': 'خطأ في الاتصال بالخدمة'}

def getQuranSurah(surah_number):
    """جلب سورة من القرآن"""
    try:
        url = f"{QURAN_JSON_API}/{surah_number}.json"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return {'success': True, 'data': response.json()}
        return {'success': False, 'error': 'فشل في جلب السورة'}
    except Exception as e:
        logger.error(f"Error getting Quran surah: {e}")
        return {'success': False, 'error': 'خطأ في الاتصال'}

def getQuranReciters():
    """جلب قائمة القراء"""
    try:
        response = requests.get(QURAN_MP3_API, timeout=30)
        if response.status_code == 200:
            return {'success': True, 'data': response.json()}
        return {'success': False, 'error': 'فشل في جلب قائمة القراء'}
    except Exception as e:
        logger.error(f"Error getting Quran reciters: {e}")
        return {'success': False, 'error': 'خطأ في الاتصال'}

def handleQuranMainMenu(message_or_call, is_callback=False):
    """معالجة القائمة الرئيسية للقرآن"""
    if is_callback:
        chat_id = message_or_call.message.chat.id
        message_id = message_or_call.message.message_id
        user_id = message_or_call.from_user.id
        user_name = message_or_call.from_user.first_name
    else:
        chat_id = message_or_call.chat.id
        message_id = None
        user_id = message_or_call.from_user.id
        user_name = message_or_call.from_user.first_name
    
    welcome_text = f"🕌 *أهلاً بك {telebot.util.escape(user_name)} في قسم القرآن الكريم* 🕌\n\n"
    welcome_text += "يمكنك الآن الاستماع وقراءة القرآن الكريم 🎧\n\n"
    welcome_text += "اختر من الخيارات التالية:"

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton('📖 قراءة القرآن', callback_data='quran_read'))
    keyboard.add(types.InlineKeyboardButton('🎧 تحميل واستماع', callback_data='quran_listen'))
    keyboard.add(types.InlineKeyboardButton('🕌 أوقات الصلاة', callback_data='quran_prayer_times'))
    keyboard.add(types.InlineKeyboardButton('📿 الكلم الطيب', callback_data='quran_wisdom'))
    keyboard.add(types.InlineKeyboardButton('🔙 رجوع', callback_data='close'))

    if is_callback and message_id:
        try:
            _safe_bot_call(bot.edit_message_text, welcome_text, chat_id, message_id, 
                          reply_markup=keyboard, parse_mode='Markdown')
        except:
            _safe_bot_call(bot.send_message, chat_id, welcome_text, 
                          reply_markup=keyboard, parse_mode='Markdown')
    else:
        _safe_bot_call(bot.reply_to, message_or_call, welcome_text, 
                      reply_markup=keyboard, parse_mode='Markdown')

def handleQuranRead(call):
    """معالجة قراءة القرآن"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    text = "📖 *اختر السورة التي تريد قراءتها:*\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # عرض أول 57 سورة
    for i in range(1, 58):
        sura_name = QURAN_SURAS[i]
        keyboard.add(types.InlineKeyboardButton(sura_name, callback_data=f'quran_read_sura_{i}'))
    
    keyboard.add(types.InlineKeyboardButton('التالي ⬅️', callback_data='quran_read_next_57'))
    keyboard.add(types.InlineKeyboardButton('🔙 رجوع للقائمة الرئيسية', callback_data='quran_main'))

    try:
        _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                      reply_markup=keyboard, parse_mode='Markdown')
    except:
        _safe_bot_call(bot.send_message, chat_id, text, 
                      reply_markup=keyboard, parse_mode='Markdown')

def handleQuranReadNext(call):
    """معالجة عرض باقي السور"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    text = "📖 *اختر السورة التي تريد قراءتها:*\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # عرض باقي السور من 58 إلى 114
    for i in range(58, 115):
        sura_name = QURAN_SURAS[i]
        keyboard.add(types.InlineKeyboardButton(sura_name, callback_data=f'quran_read_sura_{i}'))
    
    keyboard.add(types.InlineKeyboardButton('🔙 رجوع للقائمة الرئيسية', callback_data='quran_main'))

    try:
        _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                      reply_markup=keyboard, parse_mode='Markdown')
    except:
        _safe_bot_call(bot.send_message, chat_id, text, 
                      reply_markup=keyboard, parse_mode='Markdown')

def handleQuranSurahDisplay(call, surah_number):
    """عرض السورة"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    
    result = getQuranSurah(surah_number)
    if not result['success']:
        bot.answer_callback_query(call.id, result['error'], show_alert=True)
        return
    
    surah_data = result['data']
    surah_name = surah_data['name']
    total_verses = surah_data['total_verses']
    surah_type = "مدنية" if surah_data['type'] == 'medinan' else "مكية"
    
    # جلب الصفحة الحالية للمستخدم
    page = getUserQuranState(user_id).get(f'page_{surah_number}', 0)
    
    text = f"*سورة: {surah_name}*\n"
    text += f"عدد الآيات: {total_verses}\n"
    text += f"النوع: {surah_type}\n\n"
    text += "﴿ أعوذ بالله من الشيطان الرجيم ﴾\n"
    text += "﴿ بسم الله الرحمن الرحيم ﴾\n\n"
    
    # عرض الآيات
    verses_text = ""
    verses = surah_data['verses']
    start_verse = page
    
    for i in range(start_verse, min(start_verse + 10, total_verses)):
        verse = verses[i]
        verses_text += f"{verse['text']} ({verse['id']}) "
        if len(text + verses_text) > 3500:
            break
    
    text += verses_text
    
    keyboard = types.InlineKeyboardMarkup()
    
    # إضافة أزرار التنقل
    if start_verse + 10 < total_verses:
        setUserQuranState(user_id, f'page_{surah_number}', start_verse + 10)
        keyboard.add(types.InlineKeyboardButton('الصفحة التالية ⬅️', 
                    callback_data=f'quran_read_sura_{surah_number}'))
    
    keyboard.add(types.InlineKeyboardButton('🔙 رجوع لقائمة السور', callback_data='quran_read'))
    
    try:
        _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                      reply_markup=keyboard, parse_mode='Markdown')
    except:
        # إذا فشل التعديل، أرسل رسالة جديدة
        _safe_bot_call(bot.send_message, chat_id, text, 
                      reply_markup=keyboard, parse_mode='Markdown')

def handleQuranListen(call):
    """معالجة الاستماع للقرآن"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    result = getQuranReciters()
    if not result['success']:
        bot.answer_callback_query(call.id, result['error'], show_alert=True)
        return
    
    reciters_data = result['data']
    reciters = reciters_data['reciters']
    
    text = "🎧 *اختر القارئ:*\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    # عرض أول 10 قراء
    for i in range(min(10, len(reciters))):
        reciter_name = reciters[i]['name']
        keyboard.add(types.InlineKeyboardButton(reciter_name, 
                    callback_data=f'quran_reciter_{i}'))
    
    if len(reciters) > 10:
        keyboard.add(types.InlineKeyboardButton('عرض المزيد ⬅️', 
                    callback_data='quran_reciters_next_10'))
    
    keyboard.add(types.InlineKeyboardButton('🔙 رجوع للقائمة الرئيسية', callback_data='quran_main'))

    try:
        _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                      reply_markup=keyboard, parse_mode='Markdown')
    except:
        _safe_bot_call(bot.send_message, chat_id, text, 
                      reply_markup=keyboard, parse_mode='Markdown')

def handleQuranReciterSelection(call, reciter_index):
    """معالجة اختيار القارئ"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    result = getQuranReciters()
    if not result['success']:
        bot.answer_callback_query(call.id, result['error'], show_alert=True)
        return
    
    reciters_data = result['data']
    reciters = reciters_data['reciters']
    
    if reciter_index >= len(reciters):
        bot.answer_callback_query(call.id, "قارئ غير موجود", show_alert=True)
        return
    
    reciter = reciters[reciter_index]
    reciter_name = reciter['name']
    
    text = f"🎧 *القارئ: {reciter_name}*\n\n"
    text += "اختر السورة التي تريد الاستماع إليها:"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # عرض أول 30 سورة
    for i in range(1, min(31, len(QURAN_SURAS))):
        sura_name = QURAN_SURAS[i]
        keyboard.add(types.InlineKeyboardButton(sura_name, 
                    callback_data=f'quran_download_{reciter_index}_{i}'))
    
    if len(QURAN_SURAS) > 31:
        keyboard.add(types.InlineKeyboardButton('عرض المزيد ⬅️', 
                    callback_data=f'quran_suras_next_{reciter_index}_30'))
    
    keyboard.add(types.InlineKeyboardButton('🔙 رجوع للقراء', callback_data='quran_listen'))

    try:
        _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                      reply_markup=keyboard, parse_mode='Markdown')
    except:
        _safe_bot_call(bot.send_message, chat_id, text, 
                      reply_markup=keyboard, parse_mode='Markdown')

def handleQuranRecitersNext(call):
    """معالجة عرض المزيد من القراء"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    result = getQuranReciters()
    if not result['success']:
        bot.answer_callback_query(call.id, result['error'], show_alert=True)
        return
    
    reciters_data = result['data']
    reciters = reciters_data['reciters']
    
    text = "🎧 *اختر القارئ:*\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    # عرض القراء من 10 فما فوق
    start_index = 10
    end_index = min(len(reciters), start_index + 10)
    
    for i in range(start_index, end_index):
        reciter_name = reciters[i]['name']
        keyboard.add(types.InlineKeyboardButton(reciter_name, 
                    callback_data=f'quran_reciter_{i}'))
    
    keyboard.add(types.InlineKeyboardButton('🔙 رجوع للقائمة الرئيسية', callback_data='quran_main'))

    try:
        _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                      reply_markup=keyboard, parse_mode='Markdown')
    except:
        _safe_bot_call(bot.send_message, chat_id, text, 
                      reply_markup=keyboard, parse_mode='Markdown')

def handleQuranDownload(call, reciter_index, surah_number):
    """معالجة تحميل السورة"""
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    try:
        result = getQuranReciters()
        if not result['success']:
            bot.answer_callback_query(call.id, result['error'], show_alert=True)
            return
        
        reciters_data = result['data']
        reciters = reciters_data['reciters']
        
        if reciter_index >= len(reciters):
            bot.answer_callback_query(call.id, "قارئ غير موجود", show_alert=True)
            return
        
        reciter = reciters[reciter_index]
        reciter_name = reciter['name']
        
        if surah_number < 1 or surah_number >= len(QURAN_SURAS):
            bot.answer_callback_query(call.id, "رقم السورة غير صحيح", show_alert=True)
            return
        
        sura_name = QURAN_SURAS[surah_number]
        
        # إرسال رسالة انتظار
        bot.answer_callback_query(call.id, f"جاري تحضير {sura_name} للقارئ {reciter_name}...")
        
        # بناء رابط الملف الصوتي
        server_url = reciter.get('moshaf', [{}])[0].get('server', '')
        if not server_url:
            _safe_bot_call(bot.send_message, chat_id, "⚠️ عذراً، لم أتمكن من العثور على رابط الملف الصوتي لهذا القارئ.")
            return
        
        # تنسيق رقم السورة (مثل 001، 002، إلخ)
        formatted_surah = f"{surah_number:03d}"
        audio_url = f"{server_url}{formatted_surah}.mp3"
        
        # إرسال الملف الصوتي
        caption = f"🎧 *{sura_name}*\n👤 *القارئ:* {reciter_name}\n\n@{bot.get_me().username}"
        
        try:
            _safe_bot_call(bot.send_audio, chat_id, audio_url, 
                          caption=caption, parse_mode='Markdown',
                          title=f"{sura_name} - {reciter_name}")
        except Exception as e:
            logger.error(f"Error sending Quran audio: {e}")
            _safe_bot_call(bot.send_message, chat_id, 
                          f"⚠️ عذراً، حدث خطأ أثناء تحميل الملف الصوتي.\n\n"
                          f"يمكنك محاولة تحميله مباشرة من الرابط:\n{audio_url}")
            
    except Exception as e:
        logger.error(f"Error in handleQuranDownload: {e}")
        _safe_bot_call(bot.send_message, chat_id, "⚠️ حدث خطأ أثناء معالجة طلبك.")

def handleQuranPHPCallbacks(call, action, params_str):
    """معالجة callbacks القرآن من الكود الـ PHP"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if action == 'view':
        # معالجة عرض السور للقارئ المختار
        try:
            reciter_index = int(params_str)
            result = getQuranReciters()
            if not result['success']:
                bot.answer_callback_query(call.id, result['error'], show_alert=True)
                return
            
            reciters_data = result['data']
            reciters = reciters_data['reciters']
            
            if reciter_index >= len(reciters):
                bot.answer_callback_query(call.id, "قارئ غير موجود", show_alert=True)
                return
            
            reciter = reciters[reciter_index]
            reciter_name = reciter['name']
            
            text = f"🎧 *القارئ: {reciter_name}*\n\n"
            text += "اختر السورة التي تريد الاستماع إليها:"
            
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            
            # عرض السور المتاحة
            for i in range(1, min(31, len(QURAN_SURAS))):
                sura_name = QURAN_SURAS[i]
                keyboard.add(types.InlineKeyboardButton(sura_name, 
                            callback_data=f'down_{reciter_index}_{i}'))
            
            keyboard.add(types.InlineKeyboardButton('🔙 رجوع للقراء', callback_data='quran_listen'))
            
            try:
                _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                              reply_markup=keyboard, parse_mode='Markdown')
            except:
                _safe_bot_call(bot.send_message, chat_id, text, 
                              reply_markup=keyboard, parse_mode='Markdown')
                
        except ValueError:
            bot.answer_callback_query(call.id, "خطأ في البيانات", show_alert=True)
    
    elif action == 'down':
        # معالجة تحميل السورة
        try:
            parts = params_str.split('_')
            if len(parts) >= 2:
                reciter_index = int(parts[0])
                surah_number = int(parts[1])
                handleQuranDownload(call, reciter_index, surah_number)
            else:
                bot.answer_callback_query(call.id, "خطأ في البيانات", show_alert=True)
        except ValueError:
            bot.answer_callback_query(call.id, "خطأ في البيانات", show_alert=True)

def handlePrayerTimesSetup(call_or_message, is_callback=True):
    """إعداد أوقات الصلاة"""
    if is_callback:
        chat_id = call_or_message.message.chat.id
        message_id = call_or_message.message.message_id
        user_id = call_or_message.from_user.id
    else:
        chat_id = call_or_message.chat.id
        message_id = None
        user_id = call_or_message.from_user.id
    
    user_data = getUserQuranState(user_id)
    city = user_data.get('city')
    
    if not city:
        text = "🕌 *أوقات الصلاة*\n\n"
        text += "يرجى إرسال اسم مدينتك لجلب أوقات الصلاة:\n\n"
        text += "💡 **يمكنك الكتابة باللغتين:**\n"
        text += "🇸🇦 بالعربية: الرياض، جدة، مكة، المدينة\n"
        text += "🇺🇸 بالإنجليزية: Riyadh، Cairo، Dubai\n\n"
        text += "📍 _سيتم ترجمة الأسماء تلقائياً عند الحاجة_"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton('🔙 رجوع', callback_data='quran_main'))
        
        # تعيين حالة انتظار اسم المدينة
        setUserQuranState(user_id, 'awaiting_city', True)
        
        if is_callback and message_id:
            try:
                _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                              reply_markup=keyboard, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error editing prayer times setup message: {e}")
                _safe_bot_call(bot.send_message, chat_id, text, 
                              reply_markup=keyboard, parse_mode='Markdown')
        else:
            _safe_bot_call(bot.send_message, chat_id, text, 
                          reply_markup=keyboard, parse_mode='Markdown')
    else:
        displayPrayerTimes(call_or_message, city, is_callback)

def displayPrayerTimes(call_or_message, city, is_callback=True):
    """عرض أوقات الصلاة"""
    if is_callback:
        chat_id = call_or_message.message.chat.id
        message_id = call_or_message.message.message_id
        user_id = call_or_message.from_user.id
    else:
        chat_id = call_or_message.chat.id
        message_id = None
        user_id = call_or_message.from_user.id
    
    # ترجمة اسم المدينة إذا كان بالعربية
    city_english = translateCityName(city)
    
    result = getPrayerTimes(city_english)
    if not result['success']:
        # جرب مع الاسم الأصلي في حالة فشل الترجمة
        if city != city_english:
            fallback_result = getPrayerTimes(city)
            if fallback_result['success']:
                result = fallback_result
            else:
                if is_callback:
                    bot.answer_callback_query(call_or_message.id, f"لم يتم العثور على أوقات الصلاة لـ {city}", show_alert=True)
                else:
                    _safe_bot_call(bot.send_message, chat_id, f"❌ لم يتم العثور على أوقات الصلاة لـ {city}")
                return
        else:
            if is_callback:
                bot.answer_callback_query(call_or_message.id, result['error'], show_alert=True)
            else:
                _safe_bot_call(bot.send_message, chat_id, f"❌ {result['error']}")
            return
    
    times = result['data']
    
    # عرض الاسم بالشكل المناسب
    display_city = city
    if city != city_english:
        display_city = f"{city} ({city_english})"
    
    text = f"🕌 *أوقات الصلاة في {display_city}:*\n\n"
    text += "-------------------🕌---------------\n\n"
    text += f"✧ الفجر: {times['Fajr']}\n"
    text += f"✧ الشروق: {times['Sunrise']}\n"
    text += f"✧ الظهر: {times['Dhuhr']}\n"
    text += f"✧ العصر: {times['Asr']}\n"
    text += f"✧ المغرب: {times['Maghrib']}\n"
    text += f"✧ العشاء: {times['Isha']}\n\n"
    text += "-------------------🕌---------------"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('🔄 تغيير المدينة', callback_data='quran_change_city'))
    keyboard.add(types.InlineKeyboardButton('🔙 رجوع', callback_data='quran_main'))

    if is_callback and message_id:
        try:
            _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                          reply_markup=keyboard, parse_mode='Markdown')
        except:
            _safe_bot_call(bot.send_message, chat_id, text, 
                          reply_markup=keyboard, parse_mode='Markdown')
    else:
        _safe_bot_call(bot.send_message, chat_id, text, 
                      reply_markup=keyboard, parse_mode='Markdown')

def handleQuranWisdom(call):
    """معالجة الكلم الطيب"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    # كلمات طيبة مختارة
    wisdom_quotes = [
        "اللهم اغفر لي ذنبي وخطئي وجهلي",
        "ربنا آتنا في الدنيا حسنة وفي الآخرة حسنة وقنا عذاب النار",
        "لا حول ولا قوة إلا بالله العلي العظيم",
        "سبحان الله وبحمده سبحان الله العظيم",
        "أستغفر الله العظيم الذي لا إله إلا هو الحي القيوم وأتوب إليه"
    ]
    
    selected_wisdom = random.choice(wisdom_quotes)
    
    text = "📿 *الكلم الطيب*\n\n"
    text += f"🌸 {selected_wisdom} 🌸\n\n"
    text += "_جعل الله أوقاتكم عامرة بالذكر والتسبيح_"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('🔄 كلمة أخرى', callback_data='quran_wisdom'))
    keyboard.add(types.InlineKeyboardButton('🔙 رجوع', callback_data='quran_main'))

    try:
        _safe_bot_call(bot.edit_message_text, text, chat_id, message_id, 
                      reply_markup=keyboard, parse_mode='Markdown')
    except:
        _safe_bot_call(bot.send_message, chat_id, text, 
                      reply_markup=keyboard, parse_mode='Markdown')

def is_update_processed(update):
    try:
        if hasattr(update, 'update_id'):
            update_id = update.update_id
        elif hasattr(update, 'message_id'):
            update_id = f"msg_{update.message_id}_{update.chat.id}"
        else:
            return False

        if str(update_id) in processed_updates_cache: return True
        return False
    except Exception as e:
        logger.error(f"Error in is_update_processed: {e}")
        return False

def mark_update_processed(update):
    global processed_updates_cache
    try:
        if hasattr(update, 'update_id'):
            update_id = update.update_id
        elif hasattr(update, 'message_id'):
            update_id = f"msg_{update.message_id}_{update.chat.id}"
        else:
            return

        processed_updates_cache[str(update_id)] = True
        if len(processed_updates_cache) > MAX_PROCESSED_ENTRIES:
            items = sorted(processed_updates_cache.items(), key=lambda item: int(item[0].split('_')[-1]) if item[0].startswith('msg_') else int(item[0]))
            processed_updates_cache = dict(items[-MAX_PROCESSED_ENTRIES:])
        saveData(PROCESSED_UPDATES_FILE, processed_updates_cache)
    except Exception as e:
        logger.error(f"Error in mark_update_processed: {e}")

def checkBotPermissions(chat_id):
    try:
        bot_id = bot.get_me().id
        bot_member = bot.get_chat_member(chat_id, bot_id)
        if not isAdmin(bot_member.status):
            return {'ok': False, 'message': formatString('bot_need_admin')}
        missing = []
        if not bot_member.can_delete_messages: missing.append(formatString('bot_need_perm_delete'))
        if not bot_member.can_restrict_members: missing.append(formatString('bot_need_perm_restrict'))
        if not bot_member.can_pin_messages: missing.append(formatString('bot_need_perm_pin'))
        if not bot_member.can_change_info: missing.append(formatString('bot_need_perm_info'))
        if not bot_member.can_invite_users: missing.append(formatString('bot_need_perm_invite'))
        if not bot_member.can_promote_members: missing.append(formatString('bot_need_perm_promote'))
        if missing:
            return {'ok': False, 'message': "\n".join(missing)}
        return {'ok': True, 'message': 'Bot has necessary permissions.'}
    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"checkBotPermissions API error for chat {chat_id}: {e.description}")
        return {'ok': False, 'message': formatString('bot_need_admin') + f" (Error: {e.description})"}
    except Exception as e_gen:
        logger.error(f"checkBotPermissions general error for chat {chat_id}: {e_gen}")
        return {'ok': False, 'message': 'Could not verify bot permissions.'}

def _safe_bot_call(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"Telegram API Error on {method.__name__}: {e.error_code} - {e.description}")
        if e.error_code == 400 and "message text is empty" in e.description:
            logger.warning("Attempted to edit to empty or same message text.")
        return None
    except Exception as ex:
        logger.error(f"Generic Error on {method.__name__}: {ex}")
        return None

def process_message_logic(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    message_id = message.message_id
    message_text_original = message.text or message.caption or ""
    message_text_for_cmd = message_text_original.strip()
    message_type = message.chat.type
    user_first_name = message.from_user.first_name or "User"
    user_last_name = message.from_user.last_name or ""
    user_name_str = f"{user_first_name} {user_last_name}".strip()
    name_mention_html = formatUserMentionHTML(message.from_user)

    if message.from_user.is_bot and message.from_user.id != bot.get_me().id: return

    dev_keywords = ['معلومات المطور']
    if any(keyword in message_text_for_cmd.lower() for keyword in dev_keywords):
        handleDeveloperInfo(message); return

    if not isSudo(user_id):
        join_context_id = chat_id
        join_check = checkCompulsoryJoin(join_context_id, user_id)
        if not join_check['allowed'] and join_check['failed_channels']:
            if message_type != 'private' and not message.edit_date:
                _safe_bot_call(bot.delete_message, chat_id, message_id)
            for failed_channel in join_check['failed_channels']:
                error_text_compulsory = formatString('compulsory_join_fail_generic', 
                                     {'channel_title': failed_channel['title'], 'channel_id': failed_channel['id']}, user_id=user_id)
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(text=f"✨ اشتراك في: {telebot.util.escape(failed_channel['title'])}", url=failed_channel['link']))
                target_chat_id_compulsory = user_id if message_type == 'private' else chat_id
                _safe_bot_call(bot.send_message, target_chat_id_compulsory, error_text_compulsory, reply_markup=keyboard, parse_mode='Markdown')
                time.sleep(0.3)
            if message_type == 'private':
                _safe_bot_call(bot.send_message, chat_id, "🔔 اشترك في القنوات المطلوبة ثم أرسل /start مرة أخرى.")
            return

    if message_type in ['group', 'supergroup']:
        group_handled = handleGroupMessage(message)
        if group_handled: return

    user_state_obj = getUserState(user_id)
    user_state = None
    user_state_data = None
    if isinstance(user_state_obj, dict):
        user_state = user_state_obj.get('name')
        user_state_data = user_state_obj.get('data')
    elif isinstance(user_state_obj, str):
        user_state = user_state_obj

    # فحص إذا كان المستخدم في حالة إدخال للقرآن (بما في ذلك أوقات الصلاة)
    if handleQuranTextInput(message):
        return

    if user_state:
        input_handled = False
        if message_type == 'private' and isBotAdmin(user_id) and user_state.startswith('admin_'):
            input_handled = handleAdminInput(message)
        elif message_type in ['group', 'supergroup'] and \
             (isAdmin(getChatMemberStatus(chat_id, user_id)) or isSudo(user_id)) and \
             user_state.startswith('grpset_'):
            input_handled = handleGroupSettingsInput(message)
        elif user_state == 'awaiting_translation_lang':
            if message_text_for_cmd == '/cancel':
                saveUserState(user_id, None)
                _safe_bot_call(bot.reply_to, message, "✅ تم إلغاء الترجمة.")
            else: 
                _safe_bot_call(bot.reply_to, message, "الرجاء اختيار لغة من الأزرار أو /cancel للإلغاء.")
            return True 

        if input_handled: return
        if message_text_for_cmd == '/cancel':
            saveUserState(user_id, None)
            _safe_bot_call(bot.reply_to, message, "✅ تم إلغاء الأمر الحالي.")
            return

    bot_me = bot.get_me()

    command = ''
    args_text = ''
    if message_text_for_cmd:
        if message_text_for_cmd.startswith('/'):
            parts = message_text_for_cmd.split(' ', 1)
            raw_command_full = parts[0][1:]
            command = raw_command_full.split('@')[0].lower()
            args_text = parts[1] if len(parts) > 1 else ''
        if not command:
            arabic_command_handled = handleArabicCommand(message)
            if arabic_command_handled: return

        if not command and not ('arabic_command_handled' in locals() and arabic_command_handled):
            is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_me.id
            mentions_bot_name_ai = any(name in message_text_original for name in [BOT_PERSONALITY_NAME, 'ميرا', 'ملوكة'])
            mentions_bot_username_ai = bot_me.username and f"@{bot_me.username}" in message_text_original

            is_muted_ai = (user_state == 'muted')

            # تفاعل 100% في المجموعات والخاص
            should_respond_ai = (not is_muted_ai and 
                                message_text_original.strip() and
                                not message.from_user.is_bot)

            if should_respond_ai:
                handleAiInteraction(message)
                return

    if command == 'start': handleStartCommand(message, args_text)
    elif command == 'help': handleHelpCommand(message)
    elif command == 'admin':
        if message_type == 'private' and isBotAdmin(user_id): showAdminPanel(chat_id)
        else:
            if message_type != 'private': _safe_bot_call(bot.reply_to, message, formatString('private_only', user_id=user_id))
            else: _safe_bot_call(bot.reply_to, message, formatString('sudo_only', user_id=user_id))
    elif command == 'ping': handlePingCommand(message)
    elif command == 'id': handleIdCommand(message)
    elif command == 'info': handleInfoCommand(message, force_reply=True)
    elif command == 'me': handleInfoCommand(message, force_reply=False)
    elif command == 'stats':
        if message_type == 'private' or isAdmin(getChatMemberStatus(chat_id, user_id)) or isSudo(user_id):
            handleStatsCommand(message)
        else: _safe_bot_call(bot.reply_to, message, formatString('admin_only', user_id=user_id))
    elif command == 'language': handleSetLanguageCallback(message, 'choose')

    if message_type != 'private' and not message.edit_date and not message.from_user.is_bot :
        msgs_file = 'msgs.json'
        msgs_data = loadData(msgs_file)
        if not isinstance(msgs_data, dict): msgs_data = {'msgs': {}}
        if 'msgs' not in msgs_data: msgs_data['msgs'] = {}
        chat_id_str = str(chat_id); user_id_str = str(user_id)
        if chat_id_str not in msgs_data['msgs']: msgs_data['msgs'][chat_id_str] = {}
        if user_id_str not in msgs_data['msgs'][chat_id_str]: msgs_data['msgs'][chat_id_str][user_id_str] = 0
        msgs_data['msgs'][chat_id_str][user_id_str] += 1
        saveData(msgs_file, msgs_data)

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 
                                                              'sticker', 'contact', 'location', 'venue', 'game', 
                                                              'video_note', 'animation',
                                                              'new_chat_members', 'left_chat_member'])
def handle_all_messages(message):
    if is_update_processed(message): return
    process_message_logic(message)
    mark_update_processed(message)

@bot.edited_message_handler(func=lambda message: True)
def handle_edited_messages(message):
    logger.info(f"Processing edited message {message.message_id} from chat {message.chat.id}")
    process_message_logic(message)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if is_update_processed(call): return
    callback_id_str = call.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    from_user_id = call.from_user.id
    callback_data = call.data
    try: bot.answer_callback_query(callback_id_str)
    except Exception as e: logger.error(f"Failed to answer callback query {callback_id_str}: {e}")

    parts = callback_data.split('_', 1)
    action = parts[0]
    params_str = parts[1] if len(parts) > 1 else None

    user_state_obj_cb = getUserState(from_user_id)
    user_state_cb = None
    user_state_data_cb = None
    if isinstance(user_state_obj_cb, dict):
        user_state_cb = user_state_obj_cb.get('name')
        user_state_data_cb = user_state_obj_cb.get('data')
    elif isinstance(user_state_obj_cb, str):
        user_state_cb = user_state_obj_cb

    if action == 'trselectlang' and user_state_cb == 'awaiting_translation_lang' and user_state_data_cb:
        target_lang_code = params_str
        original_text_to_translate = base64.b64decode(user_state_data_cb).decode('utf-8')
        handleTranslationResult(call.message, original_text_to_translate, target_lang_code)
        saveUserState(from_user_id, None)
        return

    if not isSudo(from_user_id):
        if action.startswith('admin'):
            if not isBotAdmin(from_user_id):
                bot.answer_callback_query(callback_id_str, text=formatString('sudo_only', user_id=from_user_id), show_alert=True)
                return
        elif action.startswith('grpset') or action == 'togglelock':
            if call.message.chat.type == 'private':
                bot.answer_callback_query(callback_id_str, text=formatString('group_only', user_id=from_user_id), show_alert=True)
                return
            user_status_cb = getChatMemberStatus(chat_id, from_user_id)
            if not isAdmin(user_status_cb):
                bot.answer_callback_query(callback_id_str, text=formatString('admin_only', user_id=from_user_id), show_alert=True)
                return
            if not isGroupActive(chat_id):
                bot.answer_callback_query(callback_id_str, text=formatString('group_not_active', user_id=from_user_id), show_alert=True)
                return

    if action == 'ytmp3': 
        handle_youtube_download_callback(call)
    elif action == 'help': handleHelpCallback(call, params_str)
    elif action == 'admin': handleAdminPanelCallback(call, params_str)
    elif action == 'grpset': handleGroupSettingsCallback(call, params_str)
    elif action == 'start':
        if params_str == 'chat': handleStartChatCallback(call)
    elif action == 'setlang': handleSetLanguageCallback(call.message, params_str, call_obj=call)
    elif action == 'togglelock': handleToggleLockCallback(call, params_str)
    elif action == 'close': _safe_bot_call(bot.delete_message, chat_id, message_id)
    elif action == 'show':
        if params_str == 'delete': handleProtectionCommandsList(call.message, 'delete')
    elif action == 'quran':
        handleQuranCallbacks(call, params_str)
    elif action == 'view' or action == 'down':
        # معالجة callbacks القرآن من الملف المرفق
        handleQuranPHPCallbacks(call, action, params_str)
    else:
        logger.warning(f"Unknown callback data: {callback_data} from user {from_user_id}")
        bot.answer_callback_query(callback_id_str, text='🤔')
    mark_update_processed(call)

def handleDeveloperInfo(message):
    dev_user_link = f"https://t.me/{DEVELOPER_USERNAME.lstrip('@')}"
    dev_channel_link = f"https://t.me/{DEVELOPER_CHANNEL.lstrip('@')}"
    dev_text = f"مطوري الغالي هو <a href='{dev_user_link}'>{DEVELOPER_USERNAME}</a> ❄️ هو اللي صممني وطور شخصيتي.\n\n"
    dev_text += f"📺 قناته: <a href='{dev_channel_link}'>{DEVELOPER_CHANNEL}</a>"
    _safe_bot_call(bot.reply_to, message, dev_text)

def handleStartCommand(message, args_text=''):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name_str = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    name_mention_html_start = formatUserMentionHTML(message.from_user)
    if message.chat.type == 'private':
        users_file = 'data/users.json'
        users = loadData(users_file)
        if not isinstance(users, list): users = []
        user_id_str = str(user_id)
        if user_id_str not in users:
            users.append(user_id_str)
            saveData(users_file, users)
            total_users = len(users)
            notification = (f"👤 <b>مستخدم جديد للبوت!</b>\n\n"
                            f"الاسم: {name_mention_html_start}\n"
                            f"المعرف: @{message.from_user.username}\n" if message.from_user.username else "المعرف: لا يوجد\n"
                            f"الايدي: <code>{user_id}</code>\nإجمالي المستخدمين: {total_users}\n"
                            f"الوقت: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            _safe_bot_call(bot.send_message, ADMIN_ID, notification)

        join_check_start = checkCompulsoryJoin(chat_id, user_id)
        if not join_check_start['allowed'] and join_check_start['failed_channels']:
            for failed_channel in join_check_start['failed_channels']:
                error_text_start = formatString('compulsory_join_fail_generic', 
                                     {'channel_title': failed_channel['title'], 'channel_id': failed_channel['id']}, user_id=user_id)
                keyboard_start = types.InlineKeyboardMarkup()
                keyboard_start.add(types.InlineKeyboardButton(text=f"✨ اشتراك في: {telebot.util.escape(failed_channel['title'])}", url=failed_channel['link']))
                _safe_bot_call(bot.send_message, chat_id, error_text_start, reply_markup=keyboard_start, parse_mode='Markdown')
                time.sleep(0.2)
            _safe_bot_call(bot.send_message, chat_id, "🔔 اشترك في القنوات المطلوبة ثم أرسل /start مرة أخرى.")
            return

        start_text = (formatString('greet', {'name': name_mention_html_start}, user_id=user_id) + "\n\n" +
                     "🎭 A smart robot with a distinct personality\n\n" +
                     "✨ خدماتي:\n" +
                     "• محادثة طبيعية وتفاعلية\n" +
                     "• إدارة مجموعات باحترافية\n" +
                     "• تحليل صور وترجمة نصوص\n\n" +
                     "للتفعيل اكتب: تفعيل\n" +
                     "للمساعدة: الاوامر\n\n" +
                     "| Made py : {dev_user}\n" +
                     "| My channel: {dev_channel}")
        replacements_start = {
            'name': telebot.util.escape(user_name_str), 'mention': name_mention_html_start, 
            'id': f"<code>{user_id}</code>", 'username': f"@{telebot.util.escape(message.from_user.username)}" if message.from_user.username else 'لا يوجد',
            'dev_user': f"<a href='https://t.me/{DEVELOPER_USERNAME.lstrip('@')}'>{DEVELOPER_USERNAME}</a>",
            'dev_channel': f"<a href='https://t.me/{DEVELOPER_CHANNEL.lstrip('@')}'>{DEVELOPER_CHANNEL}</a>"
        }
        final_start_text = start_text.format(**replacements_start)
        bot_username_start = bot.get_me().username
        add_group_url = f"https://t.me/{bot_username_start}?startgroup=start"
        keyboard_start_main = types.InlineKeyboardMarkup(row_width=2)
        keyboard_start_main.add(types.InlineKeyboardButton(f'✧ أضف {BOT_PERSONALITY_NAME} لمجموعتك ✧', url=add_group_url))
        keyboard_start_main.add(types.InlineKeyboardButton('✦ المساعدة ✦', callback_data='help_main'), types.InlineKeyboardButton('✦ دردشة ✦', callback_data='start_chat'))
        keyboard_start_main.add(types.InlineKeyboardButton('✧ المطور ✧', url=f"https://t.me/{DEVELOPER_USERNAME.lstrip('@')}"), types.InlineKeyboardButton('✧ تغيير اللهجة ✧', callback_data='setlang_choose'))
        _safe_bot_call(bot.send_message, chat_id, final_start_text, reply_markup=keyboard_start_main)
    else:
        _safe_bot_call(bot.reply_to, message, "أنا هنا يا جماعة! 👋\nالأدمن يقدر يبعت <code>/help</code> أو <code>الاوامر</code> عشان يشوف الأوامر.")

def handleHelpCommand(message):
    showHelpOptions(message.chat.id, message.message_id, is_edit=False, user_id_ctx=message.from_user.id, chat_type_ctx=message.chat.type)

def showHelpOptions(target_chat_id, target_message_id_original_cmd, is_edit=False, user_id_ctx=None, chat_type_ctx=None):
    text = f"🤔 <b>المساعدة - {BOT_PERSONALITY_NAME}</b>\n\nاختر القسم اللي محتاجة مساعدة فيه 👇"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton('✧ أوامر الذكاء الاصطناعي ✧', callback_data='help_ai'))
    keyboard.add(types.InlineKeyboardButton('✧ أوامر التحميل (يوتيوب) ✧', callback_data='help_download'))
    keyboard.add(types.InlineKeyboardButton('✧ أوامر الترجمة ✧', callback_data='help_translate'))
    keyboard.add(types.InlineKeyboardButton('🌸 أوامر الأذكار 🌸', callback_data='help_azkar'))
    keyboard.add(types.InlineKeyboardButton('🕌 أوامر القرآن الكريم 🕌', callback_data='help_quran'))
    keyboard.add(types.InlineKeyboardButton('✧ الأوامر العامة ✧', callback_data='help_general'))

    effective_chat_type = chat_type_ctx
    if not effective_chat_type and target_chat_id: 
        try: effective_chat_type = bot.get_chat(target_chat_id).type
        except: effective_chat_type = 'private' 

    if effective_chat_type != 'private' and user_id_ctx:
        user_status_help = getChatMemberStatus(target_chat_id, user_id_ctx)
        if isAdmin(user_status_help) or isSudo(user_id_ctx):
             keyboard.add(types.InlineKeyboardButton('🛡️ أوامر الإدارة والحماية (للأدمن)', callback_data='help_protection'))

    if is_edit:
        if effective_chat_type == 'private': 
            keyboard.add(types.InlineKeyboardButton('🔙 رجوع للقائمة الرئيسية', callback_data='help_private_main_menu')) 
        else: 
            keyboard.add(types.InlineKeyboardButton('🔙 رجوع لقائمة المساعدة', callback_data='help_main'))
        keyboard.add(types.InlineKeyboardButton('❌ إغلاق', callback_data='close'))
    else: 
        if effective_chat_type == 'private':
            bot_username_help = bot.get_me().username
            add_group_url_help = f"https://t.me/{bot_username_help}?startgroup=start"
            keyboard.add(types.InlineKeyboardButton(f'➕ إضافة {BOT_PERSONALITY_NAME} لمجموعة', url=add_group_url_help))
        else:
            keyboard.add(types.InlineKeyboardButton('❌ إغلاق', callback_data='close'))

    msg_id_to_use = target_message_id_original_cmd
    if hasattr(target_message_id_original_cmd, 'message_id'):
        msg_id_to_use = target_message_id_original_cmd.message_id

    if is_edit and msg_id_to_use:
        try: _safe_bot_call(bot.edit_message_text, text, target_chat_id, msg_id_to_use, reply_markup=keyboard)
        except telebot.apihelper.ApiTelegramException as e_edit_help:
            if "message is not modified" not in e_edit_help.description: logger.error(f"Error editing help options: {e_edit_help}")
    elif msg_id_to_use:
        _safe_bot_call(bot.send_message, target_chat_id, text, reply_to_message_id=msg_id_to_use, reply_markup=keyboard)
    else:
        _safe_bot_call(bot.send_message, target_chat_id, text, reply_markup=keyboard)

def handleIdCommand(message):
    chat_id = message.chat.id
    target_user_obj = message.from_user
    if message.reply_to_message:
        if message.reply_to_message.from_user: target_user_obj = message.reply_to_message.from_user
        elif message.reply_to_message.sender_chat:
            target_id = message.reply_to_message.sender_chat.id
            target_name_channel = telebot.util.escape(message.reply_to_message.sender_chat.title or "Channel")
            text_id_ch = f"📢 القناة: {target_name_channel}\n🆔 الايدي: <code>{target_id}</code>"
            if message.reply_to_message.sender_chat.username:
                 text_id_ch = f"📢 القناة: <a href='https://t.me/{message.reply_to_message.sender_chat.username}'>{target_name_channel}</a>\n"
                 text_id_ch += f"📧 المعرف: @{telebot.util.escape(message.reply_to_message.sender_chat.username)}\n"
                 text_id_ch += f"🆔 الايدي: <code>{target_id}</code>"
            _safe_bot_call(bot.reply_to, message, text_id_ch); return
        else: _safe_bot_call(bot.reply_to, message, "⚠️ لا يمكن جلب معلومات المرسل لهذه الرسالة."); return

    target_id = target_user_obj.id
    target_name = telebot.util.escape(f"{target_user_obj.first_name} {target_user_obj.last_name or ''}".strip())
    target_username = f"@{telebot.util.escape(target_user_obj.username)}" if target_user_obj.username else "لا يوجد"
    status_str = "N/A (خاص)"
    msg_count_display = "N/A (خاص)"

    if message.chat.type != 'private':
        status = getChatMemberStatus(chat_id, target_id); status_str = translateStatus(status)
        msgs_data = loadData('msgs.json')
        msg_val = 0
        if isinstance(msgs_data, dict) and 'msgs' in msgs_data:
            msg_val = msgs_data['msgs'].get(str(chat_id), {}).get(str(target_id), 0)
        if msg_val == 0: msg_count_display = "تفاعل ميت 💀 🍂"
        elif msg_val < 10: msg_count_display = f"{msg_val} (تفاعل ضعيف 🤧)"
        else: msg_count_display = str(msg_val)

    text_id_main = (f"↢ ɴᴀᴍᴇ : {target_name}\n"
                    f"↢ ᴜsᴇʀ : {target_username}\n"
                    f"↢ sᴛᴀ : {status_str}\n"
                    f"↢ ɪᴅ : <code>{target_id}</code>\n"
                    f"↢ ᴍsɢ : {msg_count_display}")
    _safe_bot_call(bot.reply_to, message, text_id_main)

def handleInfoCommand(message, force_reply=False):
    chat_id = message.chat.id
    user_id = message.from_user.id
    target_user_obj_info = message.from_user
    source_info = "معلوماتك"
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_obj_info = message.reply_to_message.from_user
        source_info = "معلومات العضو"
    elif force_reply and not message.reply_to_message:
        _safe_bot_call(bot.reply_to, message, formatString('must_reply', user_id=user_id)); return
    if not target_user_obj_info or not hasattr(target_user_obj_info, 'id'):
        _safe_bot_call(bot.reply_to, message, formatString('error', user_id=user_id)); logger.error("Failed to get target user for info command."); return

    target_id_info = target_user_obj_info.id
    target_name_info = telebot.util.escape(f"{target_user_obj_info.first_name} {target_user_obj_info.last_name or ''}".strip())
    target_username_info = f"@{telebot.util.escape(target_user_obj_info.username)}" if target_user_obj_info.username else "لا يوجد"
    bio_info = "لم يتم تعيين نبذة تعريفية."
    try:
        chat_details_info = bot.get_chat(target_id_info)
        if chat_details_info.bio: bio_info = telebot.util.escape(chat_details_info.bio)
    except Exception: pass
    status_info_str = "N/A (خاص)"; msg_count_display_info = "N/A (خاص)"
    if message.chat.type != 'private':
        status_info = getChatMemberStatus(chat_id, target_id_info); status_info_str = translateStatus(status_info)
        msgs_data_info = loadData('msgs.json')
        msg_val_info = 0
        if isinstance(msgs_data_info, dict) and 'msgs' in msgs_data_info:
            msg_val_info = msgs_data_info['msgs'].get(str(chat_id), {}).get(str(target_id_info), 0)
        if msg_val_info == 0: msg_count_display_info = "تفاعل ميت 💀 🍂"
        elif msg_val_info < 10: msg_count_display_info = f"{msg_val_info} (تفاعل ضعيف 🤧)"
        else: msg_count_display_info = str(msg_val_info)

    info_text = (f"<b>{source_info}:</b>\n\n"
                 f"↢ ɴᴀᴍᴇ : {target_name_info}\n"
                 f"↢ ᴜsᴇʀ : {target_username_info}\n"
                 f"↢ sᴛᴀ : {status_info_str}\n"
                 f"↢ ɪᴅ : <code>{target_id_info}</code>\n"
                 f"↢ ᴍsɢ : {msg_count_display_info}\n"
                 f"↢ ʙɪᴏ : {bio_info}")
    _safe_bot_call(bot.reply_to, message, info_text)


def handlePingCommand(message):
    start_time = time.time()
    wait_msg = _safe_bot_call(bot.reply_to, message, "🏓 Pong... بحسب السرعة ⏳")
    if wait_msg and hasattr(wait_msg, 'message_id'):
        end_time = time.time()
        time_taken_ms = round((end_time - start_time) * 1000)
        try: _safe_bot_call(bot.edit_message_text, f"🏓 Pong! ({time_taken_ms}ms)", message.chat.id, wait_msg.message_id)
        except telebot.apihelper.ApiTelegramException as e_ping:
            if "message is not modified" not in e_ping.description: logger.error(f"Ping edit failed: {e_ping}")
    else: _safe_bot_call(bot.reply_to, message, "🏓 Pong! (فشل حساب الوقت)")

def handleStatsCommand(message):
    chat_id = message.chat.id; bot_users = loadData('data/users.json'); active_groups = loadData('data/groups_active.json')
    if not isinstance(bot_users, list): bot_users = []
    if not isinstance(active_groups, list): active_groups = []
    stats_text = (f"📊 <b>إحصائيات {BOT_PERSONALITY_NAME} والمجموعة</b> 📊\n\n<b>إحصائيات البوت العامة:</b>\n"
                  f"👤 المستخدمون في الخاص: {len(bot_users)}\n👥 المجموعات المفعلة: {len(active_groups)}\n")
    if message.chat.type != 'private':
        try:
            chat_obj = bot.get_chat(chat_id)
            stats_text += (f"\n<b>معلومات المجموعة الحالية:</b>\n🏷️ اسم المجموعة: {telebot.util.escape(chat_obj.title or 'غير معروف')}\n"
                           f"🆔 ايدي المجموعة: <code>{chat_id}</code>\n👥 عدد الأعضاء: {bot.get_chat_members_count(chat_id)}\n")
            admin_list = bot.get_chat_administrators(chat_id)
            human_admins = [admin for admin in admin_list if not admin.user.is_bot]
            stats_text += f"👮 عدد المشرفين (بشريين): {len(human_admins)}\n"
            stats_text += f"🚦 حالة التفعيل: {'✅ مفعلة' if isGroupActive(chat_id) else '❌ معطلة'}\n"
        except Exception as e_stats_group:
            logger.error(f"Error getting group stats for {chat_id}: {e_stats_group}")
            stats_text += f"\n<b>لا يمكن جلب معلومات المجموعة الحالية.</b> ({telebot.util.escape(str(e_stats_group)[:50])})"
    _safe_bot_call(bot.reply_to, message, stats_text)

def handleSetLanguageCallback(message_or_call_message, param, call_obj=None):
    chat_id = message_or_call_message.chat.id
    message_id_to_edit = message_or_call_message.message_id
    from_user_id_lang = (message_or_call_message.from_user.id if hasattr(message_or_call_message, 'from_user') else 
                         (call_obj.from_user.id if call_obj else None))
    if not from_user_id_lang: logger.warning("handleSetLanguageCallback: Could not determine from_user_id."); return
    callback_id_lang = call_obj.id if call_obj else None

    if param == 'choose':
        text_lang_choose = formatString('choose_language', user_id=from_user_id_lang)
        current_lang = getBotLanguage(from_user_id_lang)
        keyboard_lang = types.InlineKeyboardMarkup(row_width=2)
        btn_egy = types.InlineKeyboardButton(f"{'✅' if current_lang == 'egyptian' else ''} 🇪🇬 المصرية", callback_data='setlang_egyptian')
        btn_syr = types.InlineKeyboardButton(f"{'✅' if current_lang == 'syrian' else ''} 🇸🇾 السورية", callback_data='setlang_syrian')

        back_cb_data = 'help_private_main_menu'
        if call_obj and call_obj.message and call_obj.message.text and "أهلاً بيك تاني!" not in call_obj.message.text:
             back_cb_data = 'help_main' 

        btn_back_lang = types.InlineKeyboardButton('🔙 رجوع', callback_data=back_cb_data)
        keyboard_lang.add(btn_egy, btn_syr); keyboard_lang.add(btn_back_lang)
        try:
            if call_obj: _safe_bot_call(bot.edit_message_text, text_lang_choose, chat_id, message_id_to_edit, reply_markup=keyboard_lang)
            else: _safe_bot_call(bot.send_message, chat_id, text_lang_choose, reply_markup=keyboard_lang, reply_to_message_id=message_or_call_message.message_id)
        except telebot.apihelper.ApiTelegramException as e_lang_edit:
            if "message is not modified" not in e_lang_edit.description: logger.error(f"Error editing/sending language choice message: {e_lang_edit}")
    elif param in ['egyptian', 'syrian']:
        setUserPreference(from_user_id_lang, 'language', param)
        lang_name = 'المصرية' if param == 'egyptian' else 'السورية'
        handleSetLanguageCallback(message_or_call_message, 'choose', call_obj=call_obj)
        if callback_id_lang:
            bot.answer_callback_query(callback_id_lang, text=formatString('language_set', {'lang': lang_name}, lang=param, user_id=from_user_id_lang))

def handleGroupMessage(message):
    chat_id = message.chat.id; from_user_id = message.from_user.id
    message_id = message.message_id; user_name_html_group = formatUserMentionHTML(message.from_user)
    bot_me_group = bot.get_me(); bot_id_group = bot_me_group.id

    if message.new_chat_members:
        for member in message.new_chat_members:
            if member.id == bot_id_group:
                _safe_bot_call(bot.delete_message, chat_id, message_id)
                perm_check_group = checkBotPermissions(chat_id)
                perm_msg_group = "" if perm_check_group['ok'] else f"\n\n{perm_check_group['message']}"
                group_title_join = telebot.util.escape(message.chat.title or str(chat_id))
                adder_mention_join = formatUserMentionHTML(message.from_user)
                _safe_bot_call(bot.send_message, chat_id, (f"❄️ This is me ميرا ب الانجليزي 🌸\n\n"
                                 f"🎭 A smart robot with a distinct personality\n\n"
                                 f"✨ خدماتي:\n"
                                 f"• محادثة طبيعية وتفاعلية\n"
                                 f"• إدارة مجموعات باحترافية\n"
                                 f"• تحليل صور وترجمة نصوص\n\n"
                                 f"للتفعيل اكتب: تفعيل\n"
                                 f"للمساعدة: الاوامر{perm_msg_group}"))
                _safe_bot_call(bot.send_message, ADMIN_ID, (f"➕ تمت إضافتي لمجموعة جديدة:\nالاسم: {group_title_join}\nالايدي: <code>{chat_id}</code>\n"
                                 f"بواسطة: {adder_mention_join} (<code>{from_user_id}</code>)"))
                return True
            elif not member.is_bot:
                handleWelcomeMessage(message, member)
        if not any(m.id == bot_id_group for m in message.new_chat_members):
            _safe_bot_call(bot.delete_message, chat_id, message_id)
        return True

    if message.left_chat_member:
        if message.left_chat_member.id == bot_id_group:
            logger.info(f"Bot left or was removed from group: {chat_id}")
            setGroupActive(chat_id, False)
            group_title_leave = telebot.util.escape(message.chat.title or str(chat_id))
            _safe_bot_call(bot.send_message, ADMIN_ID, (f"➖ البوت غادر أو طُرد من مجموعة:\nالاسم: {group_title_leave}\nالايدي: <code>{chat_id}</code>"))
        _safe_bot_call(bot.delete_message, chat_id, message_id)
        return True

    if not isGroupActive(chat_id):
        if message.text and message.text.strip() == 'تفعيل' and not re.match(r'^تفعيل\s+(?:ترحيب|الترحيب)$', message.text, re.IGNORECASE):
            user_status_inactive = getChatMemberStatus(chat_id, from_user_id)
            if isAdmin(user_status_inactive) or isSudo(from_user_id): handleActivationCommand(message)
            else: _safe_bot_call(bot.reply_to, message, formatString('admin_only', user_id=from_user_id))
            return True
        return True 

    user_status_active = getChatMemberStatus(chat_id, from_user_id)
    if isAdmin(user_status_active) or isSudo(from_user_id): return False
    action_taken_lock = applyContentLocks(message, user_status_active)
    if action_taken_lock: return True
    return False

def handleWelcomeMessage(original_join_message, new_member_obj):
    chat_id = original_join_message.chat.id
    _safe_bot_call(bot.delete_message, chat_id, original_join_message.message_id)
    settings_welcome = getWelcomeSettings(chat_id)
    if not settings_welcome.get('enabled', True): return

    welcome_text_template = settings_welcome.get('text', DEFAULT_WELCOME_MESSAGE)
    user_name_welcome = telebot.util.escape(f"{new_member_obj.first_name} {new_member_obj.last_name or ''}".strip())
    user_id_welcome = new_member_obj.id
    user_mention_welcome = f"<a href='tg://user?id={user_id_welcome}'>{user_name_welcome}</a>"
    user_username_welcome = f"@{telebot.util.escape(new_member_obj.username)}" if new_member_obj.username else 'لا يوجد'
    replacements_welcome = {'name': user_name_welcome, 'mention': user_mention_welcome, 'id': f"<code>{user_id_welcome}</code>", 'username': user_username_welcome}
    final_welcome_text = welcome_text_template.format(**replacements_welcome)
    media_welcome = settings_welcome.get('media', ''); media_type_welcome = settings_welcome.get('media_type', 'photo')
    is_file_id_welcome = settings_welcome.get('is_file_id', False); media_sent_welcome = False
    if media_welcome:
        media_to_send_welcome = media_welcome; temp_file_welcome = None
        try:
            if not is_file_id_welcome and (media_welcome.startswith("http://") or media_welcome.startswith("https://")):
                response_media_welcome = requests.get(media_welcome, timeout=30, stream=True); response_media_welcome.raise_for_status()
                ext_welcome = '.mp4' if media_type_welcome == 'video' else ('.gif' if media_type_welcome == 'animation' else '.jpg')
                temp_file_welcome = os.path.join(BASE_DIR, "downloads", f"welcome_{chat_id}_{int(time.time())}{ext_welcome}")
                with open(temp_file_welcome, 'wb') as f_w:
                    for chunk in response_media_welcome.iter_content(chunk_size=8192): f_w.write(chunk)
                media_to_send_welcome = open(temp_file_welcome, 'rb')
            if media_type_welcome == 'photo': _safe_bot_call(bot.send_photo, chat_id, media_to_send_welcome, caption=final_welcome_text)
            elif media_type_welcome == 'video': _safe_bot_call(bot.send_video, chat_id, media_to_send_welcome, caption=final_welcome_text, supports_streaming=True)
            elif media_type_welcome == 'animation': _safe_bot_call(bot.send_animation, chat_id, media_to_send_welcome, caption=final_welcome_text)
            media_sent_welcome = True
        except Exception as e_welcome_media: logger.error(f"Welcome media error for chat {chat_id}: {e_welcome_media}")
        finally:
            if hasattr(media_to_send_welcome, 'close'): media_to_send_welcome.close()
            if temp_file_welcome and os.path.exists(temp_file_welcome): os.remove(temp_file_welcome)
    if not media_sent_welcome: _safe_bot_call(bot.send_message, chat_id, final_welcome_text)

def applyContentLocks(message, user_status_lock):
    chat_id = message.chat.id; from_user_id_lock = message.from_user.id
    message_id_lock = message.message_id; message_content_lock = message.text or message.caption or ""
    name_mention_html_lock = formatUserMentionHTML(message.from_user)
    detected_features = {
        'forward': bool(message.forward_from or message.forward_from_chat),
        'link': bool(re.search(r'((https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))', message_content_lock, re.IGNORECASE)),
        'username': bool(re.search(r'@([a-zA-Z0-9_]{5,})', message_content_lock)),
        'bots': bool(message.new_chat_members and any(m.is_bot for m in message.new_chat_members))
    }
    message_deleted_lock = False
    mode = 'delete'
    for feature, triggered in detected_features.items():
        if triggered and getLockStatus(chat_id, feature, mode):
            if not message_deleted_lock:
                bot_perms_check_delete = checkBotPermissions(chat_id)
                if bot_perms_check_delete['ok'] and bot.get_chat_member(chat_id, bot.get_me().id).can_delete_messages:
                    _safe_bot_call(bot.delete_message, chat_id, message_id_lock)
                    message_deleted_lock = True
                else: 
                    logger.warning(f"Bot cannot delete messages in chat {chat_id} for lock '{feature}'.")
    return message_deleted_lock

def handleActivationCommand(message):
    chat_id = message.chat.id; from_user_id = message.from_user.id; name_mention_html_act = formatUserMentionHTML(message.from_user)
    if message.chat.type not in ['group', 'supergroup']: _safe_bot_call(bot.reply_to, message, formatString('group_only', user_id=from_user_id)); return
    user_status_act = getChatMemberStatus(chat_id, from_user_id)
    if not (isAdmin(user_status_act) or isSudo(from_user_id)): _safe_bot_call(bot.reply_to, message, formatString('admin_only', user_id=from_user_id)); return
    permission_check_act = checkBotPermissions(chat_id)
    if not permission_check_act['ok']: _safe_bot_call(bot.reply_to, message, permission_check_act['message']); return
    if isGroupActive(chat_id): _safe_bot_call(bot.reply_to, message, formatString('group_already_active', user_id=from_user_id))
    else:
        setGroupActive(chat_id, True)
        _safe_bot_call(bot.reply_to, message, formatString('group_activated', user_id=from_user_id))
        group_title_act = telebot.util.escape(message.chat.title or str(chat_id))
        _safe_bot_call(bot.send_message, ADMIN_ID, (f"✅ تم تفعيل مجموعة جديدة:\nالاسم: {group_title_act}\nالايدي: <code>{chat_id}</code>\n"
                         f"بواسطة: {name_mention_html_act} (<code>{from_user_id}</code>)"))

def handleDeactivationCommand(message):
    chat_id = message.chat.id; from_user_id = message.from_user.id; name_mention_html_deact = formatUserMentionHTML(message.from_user)
    if message.chat.type not in ['group', 'supergroup']: return
    user_status_deact = getChatMemberStatus(chat_id, from_user_id)
    if not (isAdmin(user_status_deact) or isSudo(from_user_id)): _safe_bot_call(bot.reply_to, message, formatString('admin_only', user_id=from_user_id)); return
    if not isGroupActive(chat_id): _safe_bot_call(bot.reply_to, message, "⚠️ البوت غير مفعل في هذه المجموعة أصلاً.")
    else:
        setGroupActive(chat_id, False)
        _safe_bot_call(bot.reply_to, message, formatString('group_deactivated', user_id=from_user_id))
        group_title_deact = telebot.util.escape(message.chat.title or str(chat_id))
        _safe_bot_call(bot.send_message, ADMIN_ID, (f"❌ تم تعطيل مجموعة:\nالاسم: {group_title_deact}\nالايدي: <code>{chat_id}</code>\n"
                         f"بواسطة: {name_mention_html_deact} (<code>{from_user_id}</code>)"))

def handleArabicCommand(message):
    chat_id = message.chat.id; from_user_id = message.from_user.id
    message_text = (message.text or "").strip()
    name_mention_html_ar = formatUserMentionHTML(message.from_user)
    parts_ar = message_text.split(maxsplit=1)
    command_part_ar = parts_ar[0] if parts_ar else ""
    args_part_ar = parts_ar[1] if len(parts_ar) > 1 else ""

    exact_mute_cmds = ['اسكتي', 'اصمتي', 'اخرسي', 'لا تردي']
    exact_unmute_cmds = ['اتكلمي', 'تكلمي', 'ردي', 'انطقي', 'احكي']

    if command_part_ar in exact_mute_cmds:
        saveUserState(from_user_id, 'muted')
        _safe_bot_call(bot.reply_to, message, formatString('muted_response', user_id=from_user_id)); return True
    if command_part_ar in exact_unmute_cmds:
        if getUserState(from_user_id) == 'muted' or (isinstance(getUserState(from_user_id), dict) and getUserState(from_user_id).get('name') == 'muted'):
            saveUserState(from_user_id, None)
            _safe_bot_call(bot.reply_to, message, formatString('unmuted_response', user_id=from_user_id))
        else: _safe_bot_call(bot.reply_to, message, "ما أنا بتكلم أهو يا قلبي 🥰")
        return True

    if message.chat.type in ['group', 'supergroup']:
        user_status_ar = getChatMemberStatus(chat_id, from_user_id)
        is_admin_or_sudo_ar = isAdmin(user_status_ar) or isSudo(from_user_id)

        if command_part_ar == 'تفعيل' and not args_part_ar and is_admin_or_sudo_ar: handleActivationCommand(message); return True
        if command_part_ar == 'تعطيل' and not args_part_ar and is_admin_or_sudo_ar: handleDeactivationCommand(message); return True

        if isGroupActive(chat_id):
            if is_admin_or_sudo_ar:
                if command_part_ar in ['قفل', 'فتح']:
                    if handleLockCommands(message): return True

                if message.reply_to_message:
                    if command_part_ar == 'حذف':
                        if handleAdminGroupCommands(message): return True
                        if not (checkBotPermissions(chat_id)['ok'] and bot.get_chat_member(chat_id, bot.get_me().id).can_delete_messages):
                             _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_delete', user_id=from_user_id)); return True
                        try:
                            _safe_bot_call(bot.delete_message, chat_id, message.reply_to_message.message_id)
                            _safe_bot_call(bot.delete_message, chat_id, message.message_id)
                        except Exception as e_del_simple: logger.error(f"Simple delete error: {e_del_simple}")
                        return True
                    elif command_part_ar == 'مسح' and not args_part_ar:
                         handlePurgeRangeCommand(message); return True
                    elif command_part_ar == 'فك':
                        if args_part_ar in ['حظر', 'الحظر']:
                            if handleAdminGroupCommands(message, specific_action_override='unban'): return True
                        else:
                            if handleAdminGroupCommands(message): return True
                    elif command_part_ar == 'الغاء' and args_part_ar == 'التثبيت':
                         if handleAdminGroupCommands(message): return True
                    if handleAdminGroupCommands(message): return True

                if command_part_ar == 'الغاء' and args_part_ar == 'التثبيت' and not message.reply_to_message:
                    if not checkBotPermissions(chat_id)['ok'] or not bot.get_chat_member(chat_id, bot.get_me().id).can_pin_messages:
                        _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_pin', user_id=from_user_id)); return True
                    try:
                        bot.unpin_all_chat_messages(chat_id)
                        _safe_bot_call(bot.send_message, chat_id, f"✅ بواسطة: {name_mention_html_ar}\nتم الغاء تثبيت جميع الرسائل")
                    except Exception as e_unpin_all:
                        logger.error(f"Unpin all error: {e_unpin_all}")
                        _safe_bot_call(bot.reply_to, message, formatString('action_failed_api', user_id=from_user_id) + f" ({telebot.util.escape(str(e_unpin_all)[:30])})")
                    return True

                if command_part_ar == 'الاوامر': handleHelpCommand(message); return True
                if command_part_ar == 'م1': handleProtectionCommandsList(message, 'delete'); return True
                if command_part_ar == 'الاعدادات': displayGroupSettingsPanel(chat_id, message.message_id, is_edit=False); return True
                if command_part_ar == 'الرابط': handleGetLink(message); return True
                if command_part_ar == 'الادمنيه': handleShowAdmins(message); return True
                if command_part_ar == 'الاحصائيات': handleStatsCommand(message); return True
                if command_part_ar == 'ضع':
                    if args_part_ar.startswith('اسم '): handleSetGroupName(message); return True
                    if args_part_ar.startswith('قناة اجبارية '): handleSetGroupChannelCommand(message); return True
                    if args_part_ar.startswith('ترحيب '): handleSetWelcomeTextCommand(message); return True
                    if args_part_ar.startswith('ميديا ترحيب'): handleSetWelcomeMediaCommand(message); return True
                if command_part_ar == 'حذف':
                    if args_part_ar == 'قناة اجبارية': handleRemoveGroupChannelCommand(message); return True
                    if args_part_ar == 'ترحيب': handleResetWelcomeCommand(message); return True
                if command_part_ar == 'تفعيل' and args_part_ar == 'ترحيب': handleToggleWelcomeCommand(message, True); return True
                if command_part_ar == 'تعطيل' and args_part_ar == 'ترحيب': handleToggleWelcomeCommand(message, False); return True

            if command_part_ar == 'ايدي': handleIdCommand(message); return True
            if command_part_ar == 'معلوماتي' or command_part_ar == 'انا': handleInfoCommand(message, force_reply=False); return True
            if command_part_ar == 'معلومات' and message.reply_to_message: handleInfoCommand(message, force_reply=True); return True
            if command_part_ar == 'بنق': handlePingCommand(message); return True
            if command_part_ar == 'مسح' and args_part_ar.isdigit(): handlePurgeNumberCommand(message); return True

    if command_part_ar == 'يوت' and args_part_ar: search_youtube_new(message); return True

    if command_part_ar == 'ترجمة':
        text_to_translate = args_part_ar
        if not text_to_translate and message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
            text_to_translate = message.reply_to_message.text or message.reply_to_message.caption

        if text_to_translate: handleTranslationInit(message, text_to_translate)
        else: _safe_bot_call(bot.reply_to, message, formatString('translation_prompt', user_id=from_user_id))
        return True

    if command_part_ar == 'تغيير' and args_part_ar == 'اللهجة': handleSetLanguageCallback(message, 'choose'); return True

    # أوامر الأذكار
    if command_part_ar == 'اذكار': handleAzkarCommand(message); return True
    if command_part_ar == 'تفعيل' and args_part_ar == 'الاذكار': handleActivateAzkarCommand(message); return True
    if command_part_ar == 'تعطيل' and args_part_ar == 'الاذكار': handleDeactivateAzkarCommand(message); return True

    # أوامر القرآن الكريم
    if command_part_ar == 'قران' or command_part_ar == 'القران': handleQuranMainMenu(message); return True

    fun_replies_py = {
        'بوت': ['أنا '+BOT_PERSONALITY_NAME+' يا عيوني 😊، عايز حاجة؟', 'ايوة بوت، فيه مشكلة؟ 😉', 'تحت أمرك يا باشا!'],
        'ميرا': ['يا عيون ميرا وقلبها 💕', 'نعم يا قمري 🌙', 'مين بينادي على الحلو؟ 😉'],
        'ملوكة': ['يا عيون ميرا وقلبها 💕', 'نعم يا قمري 🌙', 'مين بينادي على الحلو؟ 😉'],
        'هلو': ['أهلينات وحركات 😉', 'يا هلا بيك نورت!', 'هلا والله 👋'],
        'هاي': ['هايات 👋 عامل ايه؟', 'هاي يا قمر', 'أهلاً بيك 😊'],
        'السلام عليكم': ['وعليكم السلام ورحمة الله وبركاته 🙏', 'وعليكم السلام يا طيب/طيبة'],
        'شكرا': ['العفو يا روحي 😊', 'على ايه بس، واجبي', 'تدلل يا قمر'],
        'احبك': ['وأنا كمان بحبك موت ❤️', 'يا بعد قلبي 😘 بموت فيك أنا كمان'],
        'باي': ['الله معك 👋', 'مع السلامة، لا تقطع 😊'],
        'صباح الخير': ['صباح النور والسرور والهنا ☀️ يومك سعيد ان شاء الله!', 'صباح الورد 🌹'],
        'مساء الخير': ['مساء الورد والياسمين 🌙 عامل ايه؟', 'مساء النور والسعادة 💫'],
    }
    fun_patterns_py = {
        r'^هه+$': lambda: random.choice(['دوم الضحكة الحلوة 😄', 'يا رب دايماً مبسوط 😂', 'ضحكتني معاك 😂']),
        r'^(😭|😢|😥|🥺|😔)$': lambda: random.choice(['لا تبكي يا عمري 😢 ليش الحلو زعلان؟', 'سلامتك من الدموع، خير؟']),
    }
    normalized_text_ar = re.sub(r'[^\w\s]', '', message_text, flags=re.UNICODE).strip()
    if command_part_ar in fun_replies_py:
        reply_fun = random.choice(fun_replies_py[command_part_ar])
        _safe_bot_call(bot.reply_to, message, reply_fun); return True
    for pattern, reply_lambda in fun_patterns_py.items():
        if re.match(pattern, message_text, re.UNICODE):
            _safe_bot_call(bot.reply_to, message, reply_lambda()); return True
    return False

def handleAdminGroupCommands(message, specific_action_override=None):
    chat_id = message.chat.id; from_user_id_admin = message.from_user.id
    name_mention_html_admin = formatUserMentionHTML(message.from_user)
    command_full_text_admin = (message.text or "").strip()
    parts_admin_cmd = command_full_text_admin.split(maxsplit=1)
    command_part_admin = parts_admin_cmd[0]
    args_part_admin = parts_admin_cmd[1] if len(parts_admin_cmd) > 1 else ""
    reply_to_msg_admin = message.reply_to_message

    if command_part_admin == 'الغاء' and args_part_admin == 'التثبيت' and not reply_to_msg_admin:
        try:
            bot.unpin_all_chat_messages(chat_id)
            _safe_bot_call(bot.send_message, chat_id, f"✅ بواسطة: {name_mention_html_admin}\nتم الغاء تثبيت جميع الرسائل")
            return True
        except Exception as e_unpin_all:
            logger.error(f"Unpin all error: {e_unpin_all}")
            _safe_bot_call(bot.reply_to, message, formatString('action_failed_api', user_id=from_user_id_admin) + f" ({telebot.util.escape(str(e_unpin_all)[:30])})")
            return True

    if not reply_to_msg_admin:
        commands_need_reply = ['حظر', 'طرد', 'كتم', 'تقييد', 'ترقية', 'تنزيل', 'تثبيت', 'فك حظر', 'فك كتم', 'الغاء تقييد', 'فك', 'حذف']
        if command_part_admin in commands_need_reply or (command_part_admin == 'الغاء' and args_part_admin == 'التثبيت'):
             _safe_bot_call(bot.reply_to, message, formatString('must_reply', user_id=from_user_id_admin))
        return True

    target_user_obj_admin = reply_to_msg_admin.from_user
    if not target_user_obj_admin:
        _safe_bot_call(bot.reply_to, message, "⚠️ لا يمكن تنفيذ هذا الإجراء على رسالة من قناة أو أدمن مخفي."); return True
    target_id_admin = target_user_obj_admin.id
    target_mention_html_admin = formatUserMentionHTML(target_user_obj_admin)
    bot_me_admin = bot.get_me()

    if target_id_admin == from_user_id_admin: _safe_bot_call(bot.reply_to, message, formatString('cant_action_self', user_id=from_user_id_admin)); return True
    if target_id_admin == ADMIN_ID: _safe_bot_call(bot.reply_to, message, formatString('cant_action_sudo', user_id=from_user_id_admin)); return True
    if target_id_admin == bot_me_admin.id: _safe_bot_call(bot.reply_to, message, formatString('cant_action_bot', user_id=from_user_id_admin)); return True

    target_status_admin = getChatMemberStatus(chat_id, target_id_admin)
    user_status_admin_cmd = getChatMemberStatus(chat_id, from_user_id_admin)

    if target_status_admin == 'creator' and not isSudo(from_user_id_admin):
        _safe_bot_call(bot.reply_to, message, formatString('cant_action_creator', user_id=from_user_id_admin)); return True
    if isAdmin(target_status_admin) and not isSudo(from_user_id_admin) and user_status_admin_cmd != 'creator':
        _safe_bot_call(bot.reply_to, message, formatString('cant_action_admin', user_id=from_user_id_admin)); return True

    if target_status_admin in ['left', 'kicked', 'error'] and command_part_admin not in ['فك حظر', 'الغاء حظر', 'فك']:
        _safe_bot_call(bot.reply_to, message, formatString('user_not_found', user_id=from_user_id_admin) + " (العضو ليس في المجموعة)"); return True

    bot_perms_admin = checkBotPermissions(chat_id)
    if not bot_perms_admin['ok']: _safe_bot_call(bot.reply_to, message, bot_perms_admin['message']); return True

    action_result = None; success_key = 'action_success'

    cmd_map_admin = {
        'حظر': 'ban', 'طرد': 'kick', 'كتم': 'mute', 'تقييد': 'restrict',
        'فك حظر': 'unban', 'الغاء حظر': 'unban', 'ترقية': 'promote', 
        'تنزيل': 'demote', 'تثبيت': 'pin'
    }

    action_type = specific_action_override or cmd_map_admin.get(command_part_admin)

    if command_part_admin == "فك":
        if args_part_admin in ["حظر", "الحظر"]: action_type = "unban"

    if command_part_admin == "الغاء" and args_part_admin == "التثبيت":
        action_type = "unpin"

    if not action_type: return False

    try:
        bot_member_admin_cmd = bot.get_chat_member(chat_id, bot_me_admin.id)

        if action_type in ['ban', 'kick', 'mute', 'restrict', 'unban']:
            if not bot_member_admin_cmd.can_restrict_members: 
                _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_restrict', user_id=from_user_id_admin)); return True

            if action_type == 'ban':
                bot.ban_chat_member(chat_id, target_id_admin)
                success_key = 'action_ban_success'
            elif action_type == 'kick':
                bot.ban_chat_member(chat_id, target_id_admin)
                time.sleep(0.5)
                bot.unban_chat_member(chat_id, target_id_admin)
                success_key = 'action_kick_success'
            elif action_type == 'mute' or action_type == 'restrict':
                bot.restrict_chat_member(chat_id, target_id_admin, can_send_messages=False)
                success_key = 'action_mute_success'
            elif action_type == 'unban':
                bot.unban_chat_member(chat_id, target_id_admin)
                success_key = 'action_unban_success'
            action_result = True

        elif action_type in ['promote', 'demote']:
            if not bot_member_admin_cmd.can_promote_members: 
                _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_promote', user_id=from_user_id_admin)); return True

            if action_type == 'promote':
                bot.promote_chat_member(chat_id, target_id_admin, 
                    can_delete_messages=True, can_manage_video_chats=True, 
                    can_restrict_members=True, can_invite_users=True, 
                    can_pin_messages=True, can_change_info=True)
                success_key = 'action_promote_success'
            else:
                bot.promote_chat_member(chat_id, target_id_admin, 
                    can_manage_chat=False, can_delete_messages=False, 
                    can_manage_video_chats=False, can_restrict_members=False, 
                    can_promote_members=False, can_change_info=False, 
                    can_invite_users=False, can_pin_messages=False)
                success_key = 'action_demote_success'
            action_result = True

        elif action_type == 'pin':
            if not bot_member_admin_cmd.can_pin_messages: 
                _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_pin', user_id=from_user_id_admin)); return True
            bot.pin_chat_message(chat_id, reply_to_msg_admin.message_id)
            success_key = 'action_pin_success'
            action_result = True

        elif action_type == 'unpin':
            if not bot_member_admin_cmd.can_pin_messages: 
                _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_pin', user_id=from_user_id_admin)); return True
            bot.unpin_chat_message(chat_id, reply_to_msg_admin.message_id)
            success_key = 'action_unpin_success'
            action_result = True

        if action_result:
            final_success_msg = formatString(success_key, {'target': target_mention_html_admin}, user_id=from_user_id_admin)
            _safe_bot_call(bot.send_message, chat_id, f"✅ بواسطة: {name_mention_html_admin}\n{final_success_msg}")
        return True

    except telebot.apihelper.ApiTelegramException as e_admin_cmd:
        logger.error(f"Admin action '{command_part_admin}' failed for target {target_id_admin} by user {from_user_id_admin}. API Reason: {e_admin_cmd.description}")
        _safe_bot_call(bot.reply_to, message, formatString('action_failed_api', user_id=from_user_id_admin) + f" ({telebot.util.escape(str(e_admin_cmd.description)[:30])})")
        return True
    except Exception as e_gen_admin_cmd:
        logger.error(f"Admin action general error '{command_part_admin}' for target {target_id_admin}: {e_gen_admin_cmd}")
        _safe_bot_call(bot.reply_to, message, formatString('action_failed', user_id=from_user_id_admin))
        return True
    return False

def handleLockCommands(message):
    chat_id = message.chat.id; from_user_id_lock = message.from_user.id
    name_mention_html_lock_cmd = formatUserMentionHTML(message.from_user)
    text_lock_cmd = (message.text or "").strip()
    parts_lock_cmd = text_lock_cmd.split()
    if len(parts_lock_cmd) < 2: return False
    action_lock_cmd = parts_lock_cmd[0]
    feature_text_lock_cmd = parts_lock_cmd[1]
    mode_lock_cmd = 'delete'

    feature_map_lock_cmd = {
         'التوجيه': 'forward', 'الروابط': 'link', 'المعرفات': 'username', 'البوتات': 'bots', 'الكل': 'all'
    }
    if feature_text_lock_cmd not in feature_map_lock_cmd:
        if action_lock_cmd in ['قفل', 'فتح']:
            _safe_bot_call(bot.reply_to, message, formatString('unknown_lock_feature', {'feature_text': feature_text_lock_cmd}, user_id=from_user_id_lock))
        return False
    feature_lock_cmd = feature_map_lock_cmd[feature_text_lock_cmd]
    status_to_set_lock_cmd = (action_lock_cmd == 'قفل')
    bot_perms_lock_cmd = checkBotPermissions(chat_id)
    bot_member_lock_cmd = bot.get_chat_member(chat_id, bot.get_me().id)
    perms_ok_lock_cmd = True
    if not bot_perms_lock_cmd['ok'] or not bot_member_lock_cmd.can_delete_messages:
        perms_ok_lock_cmd = False; _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_delete', user_id=from_user_id_lock))
    if not perms_ok_lock_cmd: return True

    action_text_lock_cmd = formatString('lock_action_lock' if status_to_set_lock_cmd else 'lock_action_unlock', user_id=from_user_id_lock)
    by_user_lock_cmd = f"بواسطة {name_mention_html_lock_cmd}"; reply_text_lock_cmd = ""
    if feature_lock_cmd == 'all':
        all_features_keys_lock = [f for f in feature_map_lock_cmd.values() if f != 'all']
        for f_key_lock in all_features_keys_lock:
            setLockStatus(chat_id, f_key_lock, status_to_set_lock_cmd, mode_lock_cmd)
        reply_text_lock_cmd = f"{by_user_lock_cmd}\n{formatString('lock_all_success', {'action_text': action_text_lock_cmd}, user_id=from_user_id_lock)}"
    else:
        current_status_lock_cmd = getLockStatus(chat_id, feature_lock_cmd, mode_lock_cmd)
        if current_status_lock_cmd == status_to_set_lock_cmd:
            already_state_key_lock = 'feature_already_locked' if status_to_set_lock_cmd else 'feature_already_unlocked'
            reply_text_lock_cmd = formatString(already_state_key_lock, {'feature': feature_text_lock_cmd}, user_id=from_user_id_lock)
        else:
            setLockStatus(chat_id, feature_lock_cmd, status_to_set_lock_cmd, mode_lock_cmd)
            state_change_key_lock = 'feature_locked' if status_to_set_lock_cmd else 'feature_unlocked'
            reply_text_lock_cmd = f"{by_user_lock_cmd}\n{formatString(state_change_key_lock, {'feature': f'<b>{telebot.util.escape(feature_text_lock_cmd)}</b>'}, user_id=from_user_id_lock)}"
    _safe_bot_call(bot.reply_to, message, reply_text_lock_cmd)
    return True

def handleShowAdmins(message):
    chat_id = message.chat.id
    try:
        admin_list_show = bot.get_chat_administrators(chat_id)
        admin_text_show = "👮 <b>قائمة المشرفين في المجموعة:</b>\n\n"; count_show = 0; creator_show = None
        admins_display_list = []
        for admin_obj in admin_list_show:
            if not hasattr(admin_obj, 'user'): continue
            if admin_obj.status == 'creator': creator_show = admin_obj.user
            elif not admin_obj.user.is_bot: admins_display_list.append(admin_obj.user)
        if creator_show:
            count_show += 1; admin_text_show += f"👑 {count_show}. {formatUserMentionHTML(creator_show)} (المنشئ)\n"
        for admin_user_show in admins_display_list:
            count_show += 1; admin_text_show += f"👮 {count_show}. {formatUserMentionHTML(admin_user_show)}\n"
        if count_show == 0: admin_text_show += "لا يوجد مشرفين بشريين في المجموعة."
        _safe_bot_call(bot.reply_to, message, admin_text_show)
    except Exception as e_show_admins:
        logger.error(f"Error getting admins for chat {chat_id}: {e_show_admins}")
        _safe_bot_call(bot.reply_to, message, f"⚠️ لم أتمكن من جلب قائمة المشرفين. ({telebot.util.escape(str(e_show_admins)[:50])})")

def search_youtube_new(message):
    query = message.text.split(" ", 1)[1].strip() if len(message.text.split(" ", 1)) > 1 else ""
    if not query:
        _safe_bot_call(bot.reply_to, message, formatString('provide_youtube_query', user_id=message.from_user.id))
        return

    _safe_bot_call(bot.send_chat_action, message.chat.id, 'typing')
    wait_msg = _safe_bot_call(bot.reply_to, message, formatString('processing_youtube_search', user_id=message.from_user.id))

    search_url_yt = "https://www.youtube.com/results"
    try:
        html = requests.get(search_url_yt, params={"search_query": query}, timeout=30).text
    except requests.exceptions.RequestException as e:
        logger.error(f"YouTube search request error: {e}")
        err_text = formatString('youtube_search_failed', {'error': str(e)[:30]}, user_id=message.from_user.id)
        if wait_msg: _safe_bot_call(bot.edit_message_text, err_text, wait_msg.chat.id, wait_msg.message_id)
        else: _safe_bot_call(bot.reply_to, message, err_text)
        return

    match = re.search(r"var ytInitialData = ({.*?});</script>", html)
    if not match:
        err_text = formatString('youtube_search_failed', {'error': "Could not parse results"}, user_id=message.from_user.id)
        if wait_msg: _safe_bot_call(bot.edit_message_text, err_text, wait_msg.chat.id, wait_msg.message_id)
        else: _safe_bot_call(bot.reply_to, message, err_text)
        return

    try:
        data = json.loads(match.group(1))
        contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
        items = contents[0]['itemSectionRenderer']['contents']
        results = []
        for item in items:
            if 'videoRenderer' in item:
                video = item['videoRenderer']
                video_id = video['videoId']
                title = video['title']['runs'][0]['text']
                results.append((title, video_id))
            if len(results) >= 5: break

        if not results:
            no_res_text = formatString('youtube_no_results', user_id=message.from_user.id)
            if wait_msg: _safe_bot_call(bot.edit_message_text, no_res_text, wait_msg.chat.id, wait_msg.message_id)
            else: _safe_bot_call(bot.reply_to, message, no_res_text)
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, (title, vid) in enumerate(results, 1):
            button_text = f"{i}. {title[:45]}..." if len(title) > 45 else f"{i}. {title}"
            markup.add(types.InlineKeyboardButton(text=button_text, callback_data=f"ytmp3_{vid}"))

        select_text = formatString('youtube_select_result', user_id=message.from_user.id)
        if wait_msg: _safe_bot_call(bot.edit_message_text, select_text, wait_msg.chat.id, wait_msg.message_id, reply_markup=markup)
        else: _safe_bot_call(bot.reply_to, message, select_text, reply_markup=markup)

    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing YouTube data: {e}")
        err_text = formatString('youtube_search_failed', {'error': "Error parsing data"}, user_id=message.from_user.id)
        if wait_msg: _safe_bot_call(bot.edit_message_text, err_text, wait_msg.chat.id, wait_msg.message_id)
        else: _safe_bot_call(bot.reply_to, message, err_text)

def handle_youtube_download_callback(call):
    video_id = call.data.split("_")[1]
    api_url_yt_dl = f"https://youtube-mp36.p.rapidapi.com/dl?id={video_id}"
    headers_yt_dl = {"x-rapidapi-host": "youtube-mp36.p.rapidapi.com", "x-rapidapi-key": RAPIDAPI_KEY}

    user_id_dl = call.from_user.id
    loading_text = formatString('processing_youtube_dl', user_id=user_id_dl)

    try:
        bot.edit_message_text(loading_text, call.message.chat.id, call.message.message_id, reply_markup=None)
        loading_msg_id_for_delete = call.message.message_id
    except telebot.apihelper.ApiTelegramException:
        new_loading_msg = _safe_bot_call(bot.send_message, call.message.chat.id, loading_text)
        loading_msg_id_for_delete = new_loading_msg.message_id if new_loading_msg else None

    try:
        response = requests.get(api_url_yt_dl, headers=headers_yt_dl, timeout=90)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "ok" and result.get("link"):
            title = result.get("title", "ملف صوتي")
            link = result["link"]
            _safe_bot_call(bot.send_chat_action, call.message.chat.id, 'upload_audio')

            _safe_bot_call(bot.send_audio, chat_id=call.message.chat.id, audio=link,
                caption=f"🎧 {telebot.util.escape(title)}\n\n@{bot.get_me().username}",
                reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🎧 مشاركة البوت", switch_inline_query=""))
            )
            if loading_msg_id_for_delete: _safe_bot_call(bot.delete_message, call.message.chat.id, loading_msg_id_for_delete)
        elif result.get("mess"):
            _safe_bot_call(bot.send_message, call.message.chat.id, formatString('youtube_dl_failed', {'error': result.get("mess")}, user_id=user_id_dl))
            if loading_msg_id_for_delete: _safe_bot_call(bot.delete_message, call.message.chat.id, loading_msg_id_for_delete)
        else:
            _safe_bot_call(bot.send_message, call.message.chat.id, formatString('youtube_dl_failed', {'error': "API response invalid"}, user_id=user_id_dl))
            if loading_msg_id_for_delete: _safe_bot_call(bot.delete_message, call.message.chat.id, loading_msg_id_for_delete)

    except requests.exceptions.RequestException as e:
        logger.error(f"YouTube DL request error: {e}")
        error_detail = str(e.response.status_code) if e.response else str(e)[:30]
        _safe_bot_call(bot.send_message, call.message.chat.id, formatString('youtube_dl_failed', {'error': error_detail}, user_id=user_id_dl))
        if loading_msg_id_for_delete: _safe_bot_call(bot.delete_message, call.message.chat.id, loading_msg_id_for_delete)
    except Exception as e:
        logger.error(f"General error in YouTube download handler: {e}")
        _safe_bot_call(bot.send_message, call.message.chat.id, formatString('youtube_dl_failed', {'error': str(e)[:30]}, user_id=user_id_dl))
        if loading_msg_id_for_delete: _safe_bot_call(bot.delete_message, call.message.chat.id, loading_msg_id_for_delete)
    finally:
        bot.answer_callback_query(call.id)

def handleTranslationInit(message, text_to_translate):
    chat_id = message.chat.id
    from_user_id_trans = message.from_user.id
    text_to_translate_clean = text_to_translate.strip()
    if not text_to_translate_clean:
        _safe_bot_call(bot.reply_to, message, formatString('provide_text_translate', user_id=from_user_id_trans)); return
    if len(text_to_translate_clean) > 2000:
        _safe_bot_call(bot.reply_to, message, "⚠️ النص المراد ترجمته طويل جداً."); return

    encoded_text = base64.b64encode(text_to_translate_clean.encode('utf-8')).decode('utf-8')
    saveUserState(from_user_id_trans, 'awaiting_translation_lang', data=encoded_text)

    keyboard_trans = types.InlineKeyboardMarkup(row_width=2)

    langs_to_offer = [
        ("🇬🇧 English", "en"), ("🇪🇸 Spanish", "es"), ("🇫🇷 French", "fr"),
        ("🇩🇪 German", "de"), ("🇮🇶 Arabic", "ar"), ("🇷🇺 Russian", "ru")
    ]
    buttons_row = []
    for lang_name, lang_code in langs_to_offer:
        buttons_row.append(types.InlineKeyboardButton(lang_name, callback_data=f"trselectlang_{lang_code}"))
        if len(buttons_row) == 2:
            keyboard_trans.row(*buttons_row)
            buttons_row = []
    if buttons_row: keyboard_trans.row(*buttons_row)

    _safe_bot_call(bot.reply_to, message, formatString('translation_choose_lang', user_id=from_user_id_trans), reply_markup=keyboard_trans)

def handleTranslationResult(message_obj, original_text, target_lang_code):
    chat_id = message_obj.chat.id
    from_user_id = message_obj.reply_to_message.from_user.id if message_obj.reply_to_message else ADMIN_ID

    wait_msg = _safe_bot_call(bot.edit_message_text, formatString('processing', user_id=from_user_id), chat_id, message_obj.message_id, reply_markup=None)

    translation_api_result = get_google_translation(original_text, target_lang_code)

    if translation_api_result['success']:
        final_text = formatString('translation_result', {
            'original_text': telebot.util.escape(original_text),
            'translated_text': telebot.util.escape(translation_api_result['translation'])
        }, user_id=from_user_id)
    else:
        final_text = formatString('translation_failed', {'error': translation_api_result.get('error', 'API Error')}, user_id=from_user_id)

    if wait_msg: _safe_bot_call(bot.edit_message_text, final_text, chat_id, wait_msg.message_id)
    else: _safe_bot_call(bot.send_message, chat_id, final_text, reply_to_message_id=message_obj.reply_to_message.message_id if message_obj.reply_to_message else None)

def handleAzkarCommand(message):
    """معالجة أمر اذكار - إرسال ذكر فوري"""
    chat_id = message.chat.id
    from_user_id = message.from_user.id
    
    azkar_text = getAzkarFromAPI()
    formatted_azkar = f"🌸 *ذكر من ميرا* 🌸\n\n{azkar_text}\n\n💫 _بارك الله فيكم_ 💫"
    
    _safe_bot_call(bot.reply_to, message, formatted_azkar, parse_mode='Markdown')

def handleActivateAzkarCommand(message):
    """معالجة أمر تفعيل الأذكار"""
    chat_id = message.chat.id
    from_user_id = message.from_user.id
    
    if message.chat.type == 'private':
        _safe_bot_call(bot.reply_to, message, "ميزة الأذكار التلقائية متاحة للمجموعات فقط يا حبيبي.")
        return
    
    if not isGroupActive(chat_id):
        _safe_bot_call(bot.reply_to, message, formatString('group_not_active', user_id=from_user_id))
        return
    
    user_status = getChatMemberStatus(chat_id, from_user_id)
    if not (isAdmin(user_status) or isSudo(from_user_id)):
        _safe_bot_call(bot.reply_to, message, formatString('admin_only', user_id=from_user_id))
        return
    
    if isAzkarActiveInGroup(chat_id):
        current_interval = azkar_timing_settings.get(str(chat_id), DEFAULT_AZKAR_INTERVAL)
        hours = current_interval // 3600
        minutes = (current_interval % 3600) // 60
        time_text = f"{hours} ساعة" if hours > 0 else f"{minutes} دقيقة"
        _safe_bot_call(bot.reply_to, message, f"✅ الأذكار مفعلة بالفعل في هذه المجموعة\n⏰ الفترة الحالية: كل {time_text}")
        return
    
    # تفعيل الأذكار بالفترة الافتراضية (ساعة واحدة)
    setAzkarActive(chat_id, True, DEFAULT_AZKAR_INTERVAL)
    
    success_msg = ("✅ *تم تفعيل الأذكار بنجاح!*\n\n"
                   "🕐 سيتم إرسال ذكر كل ساعة\n"
                   "📝 استخدم `اذكار` لطلب ذكر فوري\n"
                   "❌ استخدم `تعطيل الاذكار` لإيقاف الخدمة\n\n"
                   "💫 _بارك الله فيكم وجعل أوقاتكم عامرة بالذكر_")
    
    _safe_bot_call(bot.reply_to, message, success_msg, parse_mode='Markdown')

def handleDeactivateAzkarCommand(message):
    """معالجة أمر تعطيل الأذكار"""
    chat_id = message.chat.id
    from_user_id = message.from_user.id
    
    if message.chat.type == 'private':
        _safe_bot_call(bot.reply_to, message, "ميزة الأذكار التلقائية متاحة للمجموعات فقط يا حبيبي.")
        return
    
    if not isGroupActive(chat_id):
        _safe_bot_call(bot.reply_to, message, formatString('group_not_active', user_id=from_user_id))
        return
    
    user_status = getChatMemberStatus(chat_id, from_user_id)
    if not (isAdmin(user_status) or isSudo(from_user_id)):
        _safe_bot_call(bot.reply_to, message, formatString('admin_only', user_id=from_user_id))
        return
    
    if not isAzkarActiveInGroup(chat_id):
        _safe_bot_call(bot.reply_to, message, "❌ الأذكار معطلة بالفعل في هذه المجموعة")
        return
    
    setAzkarActive(chat_id, False)
    
    success_msg = ("❌ *تم تعطيل الأذكار*\n\n"
                   "📝 لا يزال بإمكانك استخدام `اذكار` لطلب ذكر فوري\n"
                   "✅ استخدم `تفعيل الاذكار` لإعادة التفعيل\n\n"
                   "💫 _بارك الله فيكم_")
    
    _safe_bot_call(bot.reply_to, message, success_msg, parse_mode='Markdown')

def handleQuranCallbacks(call, params_str):
    """معالجة جميع callbacks القرآن الكريم"""
    user_id = call.from_user.id
    
    if params_str == 'main':
        handleQuranMainMenu(call, is_callback=True)
    elif params_str == 'read':
        handleQuranRead(call)
    elif params_str == 'read_next_57':
        handleQuranReadNext(call)
    elif params_str.startswith('read_sura_'):
        surah_number = int(params_str.split('_')[2])
        handleQuranSurahDisplay(call, surah_number)
    elif params_str == 'listen':
        handleQuranListen(call)
    elif params_str.startswith('reciter_'):
        reciter_index = int(params_str.split('_')[1])
        handleQuranReciterSelection(call, reciter_index)
    elif params_str == 'reciters_next_10':
        handleQuranRecitersNext(call)
    elif params_str.startswith('download_'):
        # معالجة تحميل السورة
        parts = params_str.split('_')
        reciter_index = int(parts[1])
        surah_number = int(parts[2])
        handleQuranDownload(call, reciter_index, surah_number)
    elif params_str == 'prayer_times':
        handlePrayerTimesSetup(call, is_callback=True)
    elif params_str == 'change_city':
        setUserQuranState(user_id, 'city', None)
        handlePrayerTimesSetup(call, is_callback=True)
    elif params_str == 'wisdom':
        handleQuranWisdom(call)
    else:
        bot.answer_callback_query(call.id, "خيار غير معروف", show_alert=True)

def translateCityName(city_name):
    """ترجمة اسم المدينة من العربية للإنجليزية"""
    try:
        # إذا كان النص يحتوي على أحرف عربية، نترجمه
        if any('\u0600' <= char <= '\u06FF' for char in city_name):
            translation_result = get_google_translation(city_name, 'en')
            if translation_result['success']:
                translated_city = translation_result['translation']
                logger.info(f"City translated from '{city_name}' to '{translated_city}'")
                return translated_city
            else:
                logger.warning(f"Failed to translate city name: {city_name}")
                return city_name
        else:
            # إذا كان النص بالإنجليزية أصلاً، نرجعه كما هو
            return city_name
    except Exception as e:
        logger.error(f"Error in city translation: {e}")
        return city_name

def handleQuranTextInput(message):
    """معالجة إدخال النص للقرآن (مثل اسم المدينة)"""
    user_id = message.from_user.id
    user_data = getUserQuranState(user_id)
    
    # التحقق من وجود نص الرسالة
    if not message.text:
        return False
    
    # التحقق من حالة انتظار اسم المدينة
    if user_data.get('awaiting_city', False):
        city_name_original = message.text.strip()
        
        # التحقق من أن النص ليس فارغ
        if not city_name_original:
            _safe_bot_call(bot.reply_to, message, "⚠️ يرجى إدخال اسم المدينة")
            return True
        
        # ترجمة اسم المدينة إذا كان بالعربية
        city_name_english = translateCityName(city_name_original)
        
        # حفظ الاسم الأصلي للعرض
        setUserQuranState(user_id, 'city', city_name_original)
        setUserQuranState(user_id, 'city_english', city_name_english)
        setUserQuranState(user_id, 'awaiting_city', False)
        
        # إرسال رسالة انتظار
        wait_msg = _safe_bot_call(bot.reply_to, message, "🔍 جاري البحث عن أوقات الصلاة...")
        
        # استخدام الاسم المترجم للبحث
        result = getPrayerTimes(city_name_english)
        if result['success']:
            times = result['data']
            
            # عرض الاسم الأصلي في النتيجة
            display_city = city_name_original
            if city_name_original != city_name_english:
                display_city = f"{city_name_original} ({city_name_english})"
            
            text = f"🕌 *أوقات الصلاة في {display_city}:*\n\n"
            text += "-------------------🕌---------------\n\n"
            text += f"✧ الفجر: {times['Fajr']}\n"
            text += f"✧ الشروق: {times['Sunrise']}\n"
            text += f"✧ الظهر: {times['Dhuhr']}\n"
            text += f"✧ العصر: {times['Asr']}\n"
            text += f"✧ المغرب: {times['Maghrib']}\n"
            text += f"✧ العشاء: {times['Isha']}\n\n"
            text += "-------------------🕌---------------"
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton('🔄 تغيير المدينة', callback_data='quran_change_city'))
            keyboard.add(types.InlineKeyboardButton('🔙 رجوع', callback_data='quran_main'))
            
            # حذف رسالة الانتظار وإرسال النتيجة
            if wait_msg:
                _safe_bot_call(bot.delete_message, message.chat.id, wait_msg.message_id)
            _safe_bot_call(bot.send_message, message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')
        else:
            # في حالة فشل البحث، نجرب مع الاسم الأصلي
            if city_name_original != city_name_english:
                fallback_result = getPrayerTimes(city_name_original)
                if fallback_result['success']:
                    times = fallback_result['data']
                    
                    text = f"🕌 *أوقات الصلاة في {city_name_original}:*\n\n"
                    text += "-------------------🕌---------------\n\n"
                    text += f"✧ الفجر: {times['Fajr']}\n"
                    text += f"✧ الشروق: {times['Sunrise']}\n"
                    text += f"✧ الظهر: {times['Dhuhr']}\n"
                    text += f"✧ العصر: {times['Asr']}\n"
                    text += f"✧ المغرب: {times['Maghrib']}\n"
                    text += f"✧ العشاء: {times['Isha']}\n\n"
                    text += "-------------------🕌---------------"
                    
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton('🔄 تغيير المدينة', callback_data='quran_change_city'))
                    keyboard.add(types.InlineKeyboardButton('🔙 رجوع', callback_data='quran_main'))
                    
                    # حذف رسالة الانتظار وإرسال النتيجة
                    if wait_msg:
                        _safe_bot_call(bot.delete_message, message.chat.id, wait_msg.message_id)
                    _safe_bot_call(bot.send_message, message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')
                    return True
            
            # رسالة خطأ محسنة مع اقتراحات
            error_msg = f"❌ لم يتم العثور على المدينة: {city_name_original}"
            if city_name_original != city_name_english:
                error_msg += f"\n\n🔄 تم البحث عن:\n• {city_name_original}\n• {city_name_english}"
            
            error_msg += "\n\n💡 **نصائح للبحث:**\n"
            error_msg += "• جرب كتابة اسم المدينة بالعربية (مثل: الرياض، القاهرة)\n"
            error_msg += "• جرب كتابة اسم المدينة بالإنجليزية (مثل: Riyadh، Cairo)\n"
            error_msg += "• تأكد من صحة الاسم وتجنب الأخطاء الإملائية\n"
            error_msg += "• جرب اسم المدينة مع اسم الدولة (مثل: الرياض السعودية)\n\n"
            error_msg += "🔄 أعد كتابة اسم المدينة مرة أخرى:"
            
            # حذف رسالة الانتظار وإرسال رسالة الخطأ
            if wait_msg:
                _safe_bot_call(bot.delete_message, message.chat.id, wait_msg.message_id)
            _safe_bot_call(bot.send_message, message.chat.id, error_msg, parse_mode='Markdown')
            
            # إعادة تعيين حالة انتظار المدينة للسماح بمحاولة جديدة
            setUserQuranState(user_id, 'awaiting_city', True)
        
        return True
    
    return False

def handleAiInteraction(message):
    chat_id = message.chat.id; from_user_id_ai = message.from_user.id
    user_name_ai = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    prompt_ai = (message.text or message.caption or "").strip()

    if not prompt_ai: return

    # فحص إذا كان المستخدم في حالة إدخال للقرآن (بما في ذلك أوقات الصلاة)
    if handleQuranTextInput(message):
        return

    saveChatMemory(from_user_id_ai, prompt_ai, False)
    user_lang_ai = getBotLanguage(from_user_id_ai)
    
    # تحضير تاريخ المحادثة للـ Gemini API
    conversation_history = {}
    chat_history_formatted = formatChatHistory(from_user_id_ai)
    if chat_history_formatted:
        conversation_history[from_user_id_ai] = chat_history_formatted.split('\n')
    else:
        conversation_history[from_user_id_ai] = []

    # الحصول على الرد من Gemini API
    ai_response_text = call_gemini_api(from_user_id_ai, prompt_ai, user_lang_ai, conversation_history)
    
    # تنظيف الرد
    ai_response_text = re.sub(r'^(model|bot|أنا)\s*[\n:]?\s*', '', ai_response_text, flags=re.IGNORECASE | re.UNICODE).strip()
    
    # حفظ الرد في الذاكرة
    error_phrases_ai = ['عفواً', 'اووف', 'آسفة', 'اممم', 'مقدرش', 'خطأ', 'مشكلة', 'تعبت']
    if not any(ai_response_text.startswith(phrase) for phrase in error_phrases_ai) and ai_response_text:
        saveChatMemory(from_user_id_ai, ai_response_text, True)

    _safe_bot_call(bot.reply_to, message, ai_response_text, parse_mode='Markdown')

def handlePurgeNumberCommand(message):
    chat_id = message.chat.id
    from_user_id = message.from_user.id
    user_status = getChatMemberStatus(chat_id, from_user_id)

    if not (isAdmin(user_status) or isSudo(from_user_id)):
        _safe_bot_call(bot.reply_to, message, formatString('admin_only', user_id=from_user_id))
        return

    if not checkBotPermissions(chat_id)['ok'] or not bot.get_chat_member(chat_id, bot.get_me().id).can_delete_messages:
        _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_delete', user_id=from_user_id))
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        _safe_bot_call(bot.reply_to, message, formatString('purge_provide_number', user_id=from_user_id))
        return

    num_to_delete = int(parts[1])
    if num_to_delete > 100:
        _safe_bot_call(bot.reply_to, message, "⚠️ الحد الأقصى للحذف هو 100 رسالة.")
        return

    deleted_count = 0
    current_msg_id = message.message_id

    try:
        _safe_bot_call(bot.delete_message, chat_id, current_msg_id)
        deleted_count += 1
    except:
        pass

    for i in range(1, num_to_delete):
        try:
            _safe_bot_call(bot.delete_message, chat_id, current_msg_id - i)
            deleted_count += 1
            time.sleep(0.1)
        except:
            continue

    if deleted_count > 0:
        confirm_msg = _safe_bot_call(bot.send_message, chat_id, 
            formatString('action_purge_range_success', {'count': deleted_count}, user_id=from_user_id))

        if confirm_msg:
            time.sleep(3)
            _safe_bot_call(bot.delete_message, chat_id, confirm_msg.message_id)

def handlePurgeRangeCommand(message):
    chat_id = message.chat.id
    from_user_id = message.from_user.id
    user_status = getChatMemberStatus(chat_id, from_user_id)

    if not (isAdmin(user_status) or isSudo(from_user_id)):
        _safe_bot_call(bot.reply_to, message, formatString('admin_only', user_id=from_user_id))
        return

    if not message.reply_to_message:
        _safe_bot_call(bot.reply_to, message, "⚠️ يجب استخدام أمر المسح بالرد على الرسالة التي تريد بدء الحذف منها.")
        return

    if not checkBotPermissions(chat_id)['ok'] or not bot.get_chat_member(chat_id, bot.get_me().id).can_delete_messages:
        _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_delete', user_id=from_user_id))
        return

    start_msg_id = message.reply_to_message.message_id
    end_msg_id = message.message_id

    purge_data = {'chat_id': chat_id, 'start_msg_id': start_msg_id, 'end_msg_id': end_msg_id}
    saveUserState(from_user_id, 'confirm_purge_range', data=purge_data)

    confirm_text = formatString('purge_confirm', user_id=from_user_id)
    keyboard_confirm = types.InlineKeyboardMarkup()
    keyboard_confirm.add(types.InlineKeyboardButton("✅ تأكيد المسح", callback_data="purge_confirm_yes"))
    keyboard_confirm.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="purge_confirm_no"))
    _safe_bot_call(bot.reply_to, message, confirm_text, reply_markup=keyboard_confirm)

def handleSetGroupName(message):
    chat_id = message.chat.id; from_user_id_gname = message.from_user.id
    name_mention_html_gname = formatUserMentionHTML(message.from_user)
    args_gname = message.text.split(maxsplit=2)[2] if len(message.text.split()) > 2 else ""
    new_name_gname = args_gname.strip()
    if not new_name_gname: _safe_bot_call(bot.reply_to, message, formatString('prompt_set_group_name', user_id=from_user_id_gname)); return
    if len(new_name_gname) > 128: _safe_bot_call(bot.reply_to, message, "⚠️ اسم المجموعة طويل جداً (الحد الأقصى 128 حرف)."); return
    if not checkBotPermissions(chat_id)['ok'] or not bot.get_chat_member(chat_id, bot.get_me().id).can_change_info:
        _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_info', user_id=from_user_id_gname)); return
    try:
        bot.set_chat_title(chat_id, new_name_gname)
        success_msg_gname = formatString('group_name_set', {'name': telebot.util.escape(new_name_gname)}, user_id=from_user_id_gname)
        _safe_bot_call(bot.reply_to, message, f"✅ بواسطة: {name_mention_html_gname}\n{success_msg_gname}")
    except Exception as e_gname:
        logger.error(f"SetChatTitle failed for {chat_id}: {e_gname}")
        _safe_bot_call(bot.reply_to, message, formatString('group_name_failed', user_id=from_user_id_gname))

def handleSetGroupChannelCommand(message):
    chat_id = message.chat.id; from_user_id_gchan = message.from_user.id
    name_mention_html_gchan = formatUserMentionHTML(message.from_user)
    args_gchan = message.text.split(maxsplit=3)[3] if len(message.text.split()) > 3 else ""
    channel_arg_gchan = args_gchan.strip()
    if not channel_arg_gchan or not re.match(r'^@([a-zA-Z0-9_]{5,})$', channel_arg_gchan):
        _safe_bot_call(bot.reply_to, message, formatString('invalid_channel', user_id=from_user_id_gchan)); return
    try:
        status_in_channel_gchan = getChatMemberStatus(channel_arg_gchan, bot.get_me().id)
        if not isAdmin(status_in_channel_gchan):
            _safe_bot_call(bot.reply_to, message, formatString('bot_not_admin_in_channel', {'channel': channel_arg_gchan}, user_id=from_user_id_gchan)); return
        channel_info_gchan = bot.get_chat(channel_arg_gchan)
        channel_title_gchan = telebot.util.escape(channel_info_gchan.title or channel_arg_gchan)
        if setGroupCompulsoryChannel(chat_id, channel_arg_gchan):
            keyboard_gchan = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"✨ اشتراك في: {channel_title_gchan}", url=f"https://t.me/{channel_arg_gchan.lstrip('@')}"))
            success_text_gchan = (f"✅ تم تحديد قناة اشتراك إجباري خاصة للمجموعة:\n\n📡 <b>القناة:</b> {channel_title_gchan}\n"
                                  f"🔗 <b>المعرف:</b> <code>{telebot.util.escape(channel_arg_gchan)}</code>\n\nبواسطة: {name_mention_html_gchan}")
            _safe_bot_call(bot.reply_to, message, success_text_gchan, reply_markup=keyboard_gchan)
        else: _safe_bot_call(bot.reply_to, message, formatString('action_failed', user_id=from_user_id_gchan))
    except Exception as e_gchan_set:
        logger.error(f"Error setting group channel {channel_arg_gchan} for {chat_id}: {e_gchan_set}")
        _safe_bot_call(bot.reply_to, message, formatString('action_failed_api', user_id=from_user_id_gchan) + f" ({telebot.util.escape(str(e_gchan_set)[:50])})")

def handleRemoveGroupChannelCommand(message):
    chat_id = message.chat.id; from_user_id_gchan_rem = message.from_user.id
    name_mention_html_gchan_rem = formatUserMentionHTML(message.from_user)
    if setGroupCompulsoryChannel(chat_id, ''):
        _safe_bot_call(bot.reply_to, message, f"✅ بواسطة: {name_mention_html_gchan_rem}\n{formatString('group_channel_removed', user_id=from_user_id_gchan_rem)}")
    else: _safe_bot_call(bot.reply_to, message, formatString('action_failed', user_id=from_user_id_gchan_rem))

def handleSetWelcomeTextCommand(message):
    chat_id = message.chat.id; from_user_id_wtxt = message.from_user.id
    name_mention_html_wtxt = formatUserMentionHTML(message.from_user)
    args_wtxt = message.text.split(maxsplit=2)[2] if len(message.text.split()) > 2 else ""
    text_wtxt = args_wtxt.strip()
    if not text_wtxt: _safe_bot_call(bot.reply_to, message, formatString('provide_welcome_text', user_id=from_user_id_wtxt)); return
    if len(text_wtxt) > 1000: _safe_bot_call(bot.reply_to, message, "⚠️ رسالة الترحيب طويلة جداً."); return
    setWelcomeSettings(chat_id, {'text': text_wtxt, 'enabled': True})
    _safe_bot_call(bot.reply_to, message, f"✅ بواسطة: {name_mention_html_wtxt}\n{formatString('welcome_set', user_id=from_user_id_wtxt)}")

def handleSetWelcomeMediaCommand(message):
    chat_id = message.chat.id; from_user_id_wmedia = message.from_user.id
    name_mention_html_wmedia = formatUserMentionHTML(message.from_user)
    parts_wmedia = message.text.split(maxsplit=3); args_wmedia = parts_wmedia[3].strip() if len(parts_wmedia) > 3 else ""
    media_value_wmedia = ''; media_type_wmedia = 'photo'; is_file_id_wmedia = False; feedback_detail_wmedia = ""
    if message.photo:
        media_value_wmedia = message.photo[-1].file_id; media_type_wmedia = 'photo'; is_file_id_wmedia = True; feedback_detail_wmedia = "(تم استخدام الصورة المرسلة مع الأمر)"
    elif message.video:
        media_value_wmedia = message.video.file_id; media_type_wmedia = 'video'; is_file_id_wmedia = True; feedback_detail_wmedia = "(تم استخدام الفيديو المرسل مع الأمر)"
    elif message.animation:
        media_value_wmedia = message.animation.file_id; media_type_wmedia = 'animation'; is_file_id_wmedia = True; feedback_detail_wmedia = "(تم استخدام الصورة المتحركة المرسلة مع الأمر)"
    elif args_wmedia:
        if re.match(r'^(لا شيء|لاشيء|none|حذف)$', args_wmedia, re.IGNORECASE):
            media_value_wmedia = ''; media_type_wmedia = ''; is_file_id_wmedia = False; feedback_detail_wmedia = "(تم حذف الميديا)"
        elif args_wmedia.startswith("http://") or args_wmedia.startswith("https://"):
            media_value_wmedia = args_wmedia; is_file_id_wmedia = False
            if re.search(r'\.(mp4|mov|avi|mkv)$', requests.utils.urlparse(media_value_wmedia).path, re.IGNORECASE): media_type_wmedia = 'video'
            elif re.search(r'\.(gif)$', requests.utils.urlparse(media_value_wmedia).path, re.IGNORECASE): media_type_wmedia = 'animation'
            else: media_type_wmedia = 'photo'
            feedback_detail_wmedia = "(تم استخدام الرابط)"
        else: _safe_bot_call(bot.reply_to, message, formatString('provide_welcome_media', user_id=from_user_id_wmedia) + "\nالرابط غير صحيح أو الكلمة المفتاحية خاطئة."); return
    if not media_value_wmedia and not feedback_detail_wmedia:
        _safe_bot_call(bot.reply_to, message, formatString('provide_welcome_media', user_id=from_user_id_wmedia) + "\nأرسل ميديا مع الأمر أو رابط أو 'لا شيء'."); return
    setWelcomeSettings(chat_id, {'media': media_value_wmedia, 'media_type': media_type_wmedia, 'is_file_id': is_file_id_wmedia, 'enabled': True})
    feedback_wmedia = f"✅ بواسطة: {name_mention_html_wmedia}\n{formatString('welcome_set', user_id=from_user_id_wmedia)} {feedback_detail_wmedia}"
    _safe_bot_call(bot.reply_to, message, feedback_wmedia)

def handleResetWelcomeCommand(message):
    chat_id = message.chat.id; from_user_id_wreset = message.from_user.id
    name_mention_html_wreset = formatUserMentionHTML(message.from_user)
    resetWelcomeSettings(chat_id)
    _safe_bot_call(bot.reply_to, message, f"✅ بواسطة: {name_mention_html_wreset}\n{formatString('welcome_reset', user_id=from_user_id_wreset)}")

def handleToggleWelcomeCommand(message, enable_status):
    chat_id = message.chat.id; from_user_id_wtoggle = message.from_user.id
    name_mention_html_wtoggle = formatUserMentionHTML(message.from_user)
    setWelcomeSettings(chat_id, {'enabled': bool(enable_status)})
    feedback_key_wtoggle = 'welcome_enabled' if enable_status else 'welcome_disabled'
    _safe_bot_call(bot.reply_to, message, f"✅ بواسطة: {name_mention_html_wtoggle}\n{formatString(feedback_key_wtoggle, user_id=from_user_id_wtoggle)}")

def handleGetLink(message):
    chat_id = message.chat.id; from_user_id_glink = message.from_user.id
    if not checkBotPermissions(chat_id)['ok'] or not bot.get_chat_member(chat_id, bot.get_me().id).can_invite_users:
        _safe_bot_call(bot.reply_to, message, formatString('bot_need_perm_invite', user_id=from_user_id_glink)); return
    try:
        invite_link_obj = bot.create_chat_invite_link(chat_id, expire_date=int(time.time()) + 3600, member_limit=1)
        _safe_bot_call(bot.reply_to, message, f"🔗 <b>رابط دعوة مؤقت للمجموعة:</b>\n<code>{invite_link_obj.invite_link}</code>")
    except Exception as e_create_link:
        logger.warning(f"Failed to create temp invite link for {chat_id}: {e_create_link}. Trying to get existing link.")
        try:
            chat_info_glink = bot.get_chat(chat_id)
            if chat_info_glink.invite_link: _safe_bot_call(bot.reply_to, message, f"🔗 <b>رابط المجموعة العام:</b>\n<code>{chat_info_glink.invite_link}</code>")
            else: _safe_bot_call(bot.reply_to, message, f"⚠️ لم أتمكن من إنشاء أو جلب رابط للمجموعة. ({telebot.util.escape(str(e_create_link)[:50])})")
        except Exception as e_get_link: _safe_bot_call(bot.reply_to, message, f"⚠️ لم أتمكن من إنشاء أو جلب رابط للمجموعة. ({telebot.util.escape(str(e_get_link)[:50])})")

def handleProtectionCommandsList(message, mode='delete'):
    chat_id = message.chat.id; user_id = message.from_user.id
    feature_map_prot = {
        'التوجيه': 'forward', 'الروابط': 'link', 'المعرفات': 'username', 'البوتات': 'bots'
    }
    text_prot = (f"<b>📋 أوامر القفل بالحذف (م1):</b>\n")
    text_prot += f"استخدم <code>قفل/فتح</code> + اسم الميزة\n\n"
    for ar_name, en_name in feature_map_prot.items():
        status_prot = getLockStatus(chat_id, en_name, mode)
        text_prot += f"{'🔒' if status_prot else '🔓'} <code>{telebot.util.escape(ar_name)}</code>\n"
    keyboard_prot = types.InlineKeyboardMarkup(row_width=1)
    keyboard_prot.add(types.InlineKeyboardButton('❌ إغلاق', callback_data='close'))

    is_from_command = hasattr(message, 'text') and (message.text.strip() == "م1")

    if is_from_command: _safe_bot_call(bot.reply_to, message, text_prot, reply_markup=keyboard_prot)
    else:
        try: _safe_bot_call(bot.edit_message_text, text_prot, message.chat.id, message.message_id, reply_markup=keyboard_prot)
        except telebot.apihelper.ApiTelegramException as e_prot_list:
            if "message is not modified" not in e_prot_list.description: logger.error(f"Error editing protection list: {e_prot_list}")

def handleHelpCallback(call, section):
    chat_id = call.message.chat.id; message_id_help_cb = call.message.message_id
    from_user_id_help_cb = call.from_user.id; chat_type_help_cb = call.message.chat.type
    text_help_cb = ''; keyboard_help_cb_list = []

    if section == 'main': showHelpOptions(chat_id, message_id_help_cb, is_edit=True, user_id_ctx=from_user_id_help_cb, chat_type_ctx=chat_type_help_cb); return
    elif section == 'private_main_menu':
        handleStartCommand(call.message)
        _safe_bot_call(bot.delete_message, chat_id, message_id_help_cb)
        return
    elif section == 'protection':
        text_help_cb = "<b>🛡️ أوامر الإدارة والحماية (للأدمن بالجروبات) 🛡️</b>\n\n" + \
                       "🔰 <b>التفعيل والأساسيات:</b>\n" + \
                       "<code>تفعيل</code> / <code>تعطيل</code> - لتفعيل/تعطيل البوت في المجموعة\n" + \
                       "<code>الاوامر</code> - لعرض قائمة الأوامر\n" + \
                       "<code>الاعدادات</code> - لعرض حالة القفل وإعدادات الترحيب\n" + \
                       "<code>الرابط</code> - للحصول على رابط المجموعة\n" + \
                       "<code>الادمنيه</code> - لعرض قائمة المشرفين\n\n" + \
                       "🛡️ <b>الحماية والقفل:</b>\n" + \
                       "<code>م1</code> - لعرض أوامر الحماية\n" + \
                       "<code>قفل/فتح [الميزة]</code> (مثال: <code>قفل الروابط</code>)\n\n" + \
                       "👥 <b>إدارة الأعضاء (بالرد):</b>\n" + \
                       "<code>حظر/طرد/كتم</code> [بالرد]\n" + \
                       "<code>فك حظر</code> [بالرد]\n" + \
                       "<code>ترقية/تنزيل</code> [بالرد]\n\n" + \
                       "⚙️ <b>إدارة المجموعة:</b>\n" + \
                       "<code>تثبيت/الغاء تثبيت</code> [بالرد]\n" + \
                       "<code>ضع اسم [الاسم الجديد]</code>\n" + \
                       "<code>ضع قناة اجبارية @معرف</code>\n" + \
                       "<code>حذف قناة اجبارية</code>\n" + \
                       "<code>ضع ترحيب [النص]</code>\n" + \
                       "<code>حذف ترحيب</code>\n" + \
                       "<code>تفعيل/تعطيل ترحيب</code>\n" + \
                       "<code>مسح [عدد]</code> - لحذف عدد معين من الرسائل\n" + \
                       "<code>مسح</code> [بالرد] - للحذف من نقطة معينة\n" + \
                       "<code>حذف</code> [بالرد] - لحذف رسالة واحدة"
        keyboard_help_cb_list.append([types.InlineKeyboardButton('⬅️ رجوع لقائمة المساعدة', callback_data='help_main')])
    elif section == 'download':
        text_help_cb = "<b>📥 أوامر التحميل (يوتيوب) 📥</b>\n\n" + \
                       "<code>يوت</code> [اسم الاغنية او الفيديو] - للبحث في يوتيوب وتحميل MP3."
        keyboard_help_cb_list.append([types.InlineKeyboardButton('⬅️ رجوع لقائمة المساعدة', callback_data='help_main')])
    elif section == 'translate':
        text_help_cb = "<b>🈯 أوامر الترجمة 🈯</b>\n\n" + \
                       "<code>ترجمة</code> [النص] - لترجمة النص إلى لغات مختلفة.\n" + \
                       "<code>ترجمة</code> [بالرد على رسالة] - لترجمة نص الرسالة التي تم الرد عليها."
        keyboard_help_cb_list.append([types.InlineKeyboardButton('⬅️ رجوع لقائمة المساعدة', callback_data='help_main')])
    elif section == 'ai':
        bot_username_ai_help = bot.get_me().username
        text_help_cb = "<b>🤖 أوامر الذكاء الاصطناعي 🤖</b>\n\n" + \
                       f"💬 <b>التفاعل العادي:</b>\n" + \
                       f"• كلمني مباشرة أو في الجروبات بذكر اسمي (<code>{BOT_PERSONALITY_NAME}</code>) أو منشن (<code>@{bot_username_ai_help}</code>).\n" + \
                       "<code>تغيير اللهجة</code> أو <code>/language</code> - لاختيار لهجتي.\n" + \
                       "<code>اسكتي</code> / <code>اتكلمي</code> - للتحكم في ردودي التلقائية."
        keyboard_help_cb_list.append([types.InlineKeyboardButton('⬅️ رجوع لقائمة المساعدة', callback_data='help_main')])
    elif section == 'azkar':
        text_help_cb = "<b>🌸 أوامر الأذكار 🌸</b>\n\n" + \
                       "📿 <b>الاستخدام:</b>\n" + \
                       "<code>اذكار</code> - لإرسال ذكر فوري من مجموعة أذكار مختارة\n\n" + \
                       "⚙️ <b>الإعدادات (للأدمن فقط):</b>\n" + \
                       "<code>تفعيل الاذكار</code> - لتفعيل إرسال الأذكار التلقائي كل ساعة\n" + \
                       "<code>تعطيل الاذكار</code> - لإيقاف إرسال الأذكار التلقائي\n\n" + \
                       "💡 <b>ملاحظات:</b>\n" + \
                       "• الأذكار التلقائية تعمل في المجموعات فقط\n" + \
                       "• يتم إرسال ذكر كل ساعة عند التفعيل\n" + \
                       "• يمكن استخدام أمر 'اذكار' في أي وقت\n\n" + \
                       "🌸 _جعل الله أوقاتكم عامرة بالذكر والتسبيح_ 🌸"
        keyboard_help_cb_list.append([types.InlineKeyboardButton('⬅️ رجوع لقائمة المساعدة', callback_data='help_main')])
    elif section == 'quran':
        text_help_cb = "<b>🕌 أوامر القرآن الكريم 🕌</b>\n\n" + \
                       "📖 <b>الاستخدام:</b>\n" + \
                       "<code>قران</code> أو <code>القران</code> - لفتح قائمة القرآن الكريم\n\n" + \
                       "🔹 <b>الميزات المتاحة:</b>\n" + \
                       "• 📖 قراءة القرآن - لقراءة السور كاملة\n" + \
                       "• 🎧 تحميل واستماع - للاستماع للتلاوات\n" + \
                       "• 🕌 أوقات الصلاة - لمعرفة مواقيت الصلاة\n" + \
                       "• 📿 الكلم الطيب - لقراءة الأدعية والأذكار\n\n" + \
                       "💡 <b>ملاحظات:</b>\n" + \
                       "• يمكن تغيير المدينة لأوقات الصلاة\n" + \
                       "• السور مقسمة لصفحات للقراءة المريحة\n" + \
                       "• التلاوات متاحة لأشهر القراء\n\n" + \
                       "🕌 _جعل الله أوقاتكم عامرة بتلاوة القرآن_ 🕌"
        keyboard_help_cb_list.append([types.InlineKeyboardButton('⬅️ رجوع لقائمة المساعدة', callback_data='help_main')])
    elif section == 'general':
        text_help_cb = "<b>👤 الأوامر العامة (للجميع) 👤</b>\n\n" + \
                       "📋 <b>معلومات الأعضاء:</b>\n" + \
                       "<code>ايدي</code> أو <code>/id</code> - معلوماتك/معلومات العضو بالرد\n" + \
                       "<code>معلوماتي</code> أو <code>/me</code> - معلوماتك\n" + \
                       "<code>معلومات</code> [بالرد] - معلومات العضو بالرد\n\n" + \
                       "🔧 <b>أدوات عامة:</b>\n" + \
                       "<code>بنق</code> أو <code>/ping</code> - سرعة استجابة البوت\n" + \
                       "<code>المطور</code> - معلومات المطور\n" + \
                       "<code>/stats</code> أو <code>الاحصائيات</code> - إحصائيات (للأدمن)\n\n" + \
                       "📥 <b>التحميل:</b>\n" + \
                       "<code>يوت [بحث أو رابط]</code> - للبحث وتحميل من يوتيوب\n\n" + \
                       "🌸 <b>الأذكار:</b>\n" + \
                       "<code>اذكار</code> - لإرسال ذكر فوري\n" + \
                       "<code>تفعيل الاذكار</code> - لتفعيل الأذكار التلقائية (للأدمن)\n" + \
                       "<code>تعطيل الاذكار</code> - لتعطيل الأذكار التلقائية (للأدمن)\n\n" + \
                       "🕌 <b>القرآن الكريم:</b>\n" + \
                       "<code>قران</code> أو <code>القران</code> - لفتح قائمة القرآن الكريم\n\n"
        keyboard_help_cb_list.append([types.InlineKeyboardButton('⬅️ رجوع لقائمة المساعدة', callback_data='help_main')])
    else:
        bot.answer_callback_query(call.id, text='قسم المساعدة غير موجود.')
        showHelpOptions(chat_id, message_id_help_cb, is_edit=True, user_id_ctx=from_user_id_help_cb, chat_type_ctx=chat_type_help_cb); return
    reply_markup_help_cb = types.InlineKeyboardMarkup(keyboard_help_cb_list)
    try: _safe_bot_call(bot.edit_message_text, text_help_cb, chat_id, message_id_help_cb, reply_markup=reply_markup_help_cb)
    except telebot.apihelper.ApiTelegramException as e_edit_help_cb:
        if "message is not modified" not in e_edit_help_cb.description: logger.error(f"Error editing help section message: {e_edit_help_cb}")

def handleStartChatCallback(call):
    chat_id = call.message.chat.id; message_id_start_chat = call.message.message_id
    from_user_id_start_chat = call.from_user.id
    user_lang_start_chat = getBotLanguage(from_user_id_start_chat)
    lang_name_start_chat = 'المصرية' if user_lang_start_chat == 'egyptian' else 'السورية'
    text_start_chat = f"أهلاً بيك تاني! 😄 أنا جاهزة أدردش معاك.\n" + \
                      f"هتكلم باللهجة <b>{lang_name_start_chat}</b>. ابدأ كلامك أو اسألني أي حاجة."
    keyboard_start_chat = types.InlineKeyboardMarkup(row_width=1)
    keyboard_start_chat.add(types.InlineKeyboardButton(f"🔄 تغيير اللهجة ({lang_name_start_chat})", callback_data='setlang_choose'))
    keyboard_start_chat.add(types.InlineKeyboardButton('🔙 رجوع', callback_data='help_private_main_menu'))
    try: _safe_bot_call(bot.edit_message_text, text_start_chat, chat_id, message_id_start_chat, reply_markup=keyboard_start_chat)
    except telebot.apihelper.ApiTelegramException as e_start_chat_edit:
        if "message is not modified" not in e_start_chat_edit.description: logger.error(f"Error editing start chat message: {e_start_chat_edit}")

def handleToggleLockCallback(call, params_str_toggle):
    chat_id = call.message.chat.id; message_id_toggle = call.message.message_id
    parts_toggle = params_str_toggle.split('_', 1)
    if len(parts_toggle) != 2: logger.error(f"Invalid togglelock params: {params_str_toggle}"); bot.answer_callback_query(call.id, text='Error processing lock toggle.', show_alert=True); return
    mode_toggle, feature_toggle = parts_toggle
    valid_modes_toggle = ['delete']
    valid_features_toggle = ['forward', 'link', 'username', 'bots']
    if mode_toggle not in valid_modes_toggle or feature_toggle not in valid_features_toggle:
        logger.error(f"Invalid mode or feature in togglelock: mode={mode_toggle}, feature={feature_toggle}"); bot.answer_callback_query(call.id, text='Invalid lock type.', show_alert=True); return
    current_status_toggle = getLockStatus(chat_id, feature_toggle, mode_toggle)
    new_status_toggle = not current_status_toggle
    setLockStatus(chat_id, feature_toggle, new_status_toggle, mode_toggle)
    displayGroupLockSettingsPanel(chat_id, message_id_toggle)
    action_text_toggle = 'قفل' if new_status_toggle else 'فتح'
    feature_map_display_toggle = {'forward': 'التوجيه', 'link': 'الروابط', 'username': 'المعرفات', 'bots': 'البوتات'}
    feature_display_toggle = feature_map_display_toggle.get(feature_toggle, feature_toggle)
    bot.answer_callback_query(call.id, text=f"تم {action_text_toggle} {feature_display_toggle}")

@bot.callback_query_handler(func=lambda call: call.data in ['purge_confirm_yes', 'purge_confirm_no'])
def handle_purge_confirmation_callback(call):
    user_id = call.from_user.id
    state_obj = getUserState(user_id)

    state_name = state_data = None
    if isinstance(state_obj, dict):
        state_name = state_obj.get('name')
        state_data = state_obj.get('data')

    if state_name != 'confirm_purge_range' or not state_data:
        bot.answer_callback_query(call.id, "لم يتم العثور على بيانات المسح أو انتهت صلاحيتها.", show_alert=True)
        _safe_bot_call(bot.delete_message, call.message.chat.id, call.message.message_id)
        return

    chat_id_purge = state_data['chat_id']
    start_msg_id = state_data['start_msg_id']
    end_msg_id = state_data['end_msg_id']

    saveUserState(user_id, None)
    _safe_bot_call(bot.delete_message, chat_id_purge, call.message.message_id)

    if call.data == 'purge_confirm_no':
        _safe_bot_call(bot.send_message, chat_id_purge, formatString('purge_cancelled', user_id=user_id), reply_to_message_id=end_msg_id)
        return

    deleted_count = 0
    current_msg_id_iter = start_msg_id
    max_deletions = 100

    while current_msg_id_iter < end_msg_id and deleted_count < max_deletions:
        try:
            _safe_bot_call(bot.delete_message, chat_id_purge, current_msg_id_iter)
            deleted_count += 1
            time.sleep(0.1)
        except Exception:
            pass
        current_msg_id_iter += 1

    try:
        _safe_bot_call(bot.delete_message, chat_id_purge, end_msg_id)
        deleted_count +=1
    except Exception:
        pass

    if deleted_count > 0:
        _safe_bot_call(bot.send_message, chat_id_purge, formatString('action_purge_range_success', {'count': deleted_count}, user_id=user_id))
    else:
        _safe_bot_call(bot.send_message, chat_id_purge, formatString('action_purge_fail_no_messages', user_id=user_id))

def showAdminPanel(chat_id_admin_panel, message_id_admin_panel=None, is_edit=False):
    users_data = loadData('data/users.json')
    groups_data = loadData('data/groups_active.json')
    admin_bot_list_data = loadData('data/admins/bot_admins.json')

    user_count = len(users_data) if isinstance(users_data, list) else 0
    group_count = len(groups_data) if isinstance(groups_data, list) else 0

    if not isinstance(admin_bot_list_data, list): admin_bot_list_data = []
    other_admins_count = len([a for a in admin_bot_list_data if str(a) != str(ADMIN_ID)])

    panel_text = f"🛠️ <b>لوحة تحكم الأدمن العام</b> ({BOT_PERSONALITY_NAME}) 🛠️\n\n"
    panel_text += f"👤 المستخدمون: {user_count}\n"
    panel_text += f"👥 المجموعات المفعلة: {group_count}\n"
    panel_text += f"👮 أدمن البوت (غيرك): {other_admins_count}\n"
    panel_text += "\nاختر الإجراء المطلوب:"

    keyboard_admin = types.InlineKeyboardMarkup(row_width=2)
    keyboard_admin.add(
        types.InlineKeyboardButton('✧ اذاعة للمستخدمين ✧', callback_data='admin_broadcast_users'),
        types.InlineKeyboardButton('✧ اذاعة للمجموعات ✧', callback_data='admin_broadcast_groups')
    )
    keyboard_admin.add(
        types.InlineKeyboardButton('➕ أدمن للبوت', callback_data='admin_add_admin'),
        types.InlineKeyboardButton('➖ أدمن للبوت', callback_data='admin_del_admin')
    )
    keyboard_admin.add(types.InlineKeyboardButton('📋 عرض أدمن البوت', callback_data='admin_list_admins'))
    keyboard_admin.add(
        types.InlineKeyboardButton('📄 عرض المجموعات', callback_data='admin_list_groups'),
        types.InlineKeyboardButton('🚪 مغادرة مجموعة', callback_data='admin_leave_group')
    )
    keyboard_admin.add(types.InlineKeyboardButton('❌ إغلاق', callback_data='close'))

    if is_edit and message_id_admin_panel:
        try: _safe_bot_call(bot.edit_message_text, panel_text, chat_id_admin_panel, message_id_admin_panel, reply_markup=keyboard_admin)
        except telebot.apihelper.ApiTelegramException as e_edit_admin:
            if "message is not modified" not in e_edit_admin.description: 
                logger.error(f"Edit admin panel error: {e_edit_admin}")
                _safe_bot_call(bot.send_message, chat_id_admin_panel, panel_text, reply_markup=keyboard_admin)
    else:
        _safe_bot_call(bot.send_message, chat_id_admin_panel, panel_text, reply_markup=keyboard_admin)

def handleAdminPanelCallback(call, param):
    chat_id_admin_cb = call.message.chat.id
    message_id_admin_cb = call.message.message_id
    from_user_id_admin_cb = call.from_user.id

    requires_input = param in [
         'broadcast_users', 'broadcast_groups', 'add_admin', 'del_admin', 'leave_group'
    ]
    if requires_input:
        saveUserState(from_user_id_admin_cb, f'admin_{param}')
    else:
        saveUserState(from_user_id_admin_cb, None)

    edit_text_admin_cb = ''
    reply_markup_admin_cb = None
    back_button_admin_cb = types.InlineKeyboardButton('🔙 إلغاء ورجوع', callback_data='admin_back')

    if param == 'broadcast_users':
        target_name_admin_cb = 'المستخدمين'
        edit_text_admin_cb = formatString('broadcast_ask', {'target': target_name_admin_cb}, user_id=from_user_id_admin_cb)
    elif param == 'broadcast_groups':
        target_name_admin_cb = 'المجموعات'
        edit_text_admin_cb = formatString('broadcast_ask', {'target': target_name_admin_cb}, user_id=from_user_id_admin_cb)
    elif param == 'add_admin':
        edit_text_admin_cb = formatString('provide_admin_id', user_id=from_user_id_admin_cb)
    elif param == 'del_admin':
        bot_admins_cb = loadData('data/admins/bot_admins.json')
        if not isinstance(bot_admins_cb, list): bot_admins_cb = []
        other_bot_admins = [admin_id for admin_id in bot_admins_cb if str(admin_id) != str(ADMIN_ID)]
        if not other_bot_admins:
            bot.answer_callback_query(call.id, text='لا يوجد أدمن مضافين (غير المطور) لحذفهم.', show_alert=True)
            saveUserState(from_user_id_admin_cb, None)
            showAdminPanel(chat_id_admin_cb, message_id_admin_cb, is_edit=True)
            return
        edit_text_admin_cb = formatString('provide_admin_id', user_id=from_user_id_admin_cb) + \
                             "\nالأدمن الحاليين (غير المطور):\n" + "\n".join(f"<code>{aid}</code>" for aid in other_bot_admins)
    elif param == 'list_admins':
        handleListAdmins(call.message)
        return
    elif param == 'list_groups':
        handleListGroups(call.message)
        return
    elif param == 'leave_group':
        edit_text_admin_cb = formatString('leave_group_confirm', user_id=from_user_id_admin_cb)
    elif param == 'back':
        saveUserState(from_user_id_admin_cb, None)
        showAdminPanel(chat_id_admin_cb, message_id_admin_cb, is_edit=True)
        return
    else:
        bot.answer_callback_query(call.id, text='خيار غير معروف.', show_alert=True)
        saveUserState(from_user_id_admin_cb, None)
        showAdminPanel(chat_id_admin_cb, message_id_admin_cb, is_edit=True)
        return

    if requires_input and (edit_text_admin_cb or reply_markup_admin_cb):
        if not reply_markup_admin_cb:
            reply_markup_admin_cb = types.InlineKeyboardMarkup().add(back_button_admin_cb)
        try:
            _safe_bot_call(bot.edit_message_text, edit_text_admin_cb or "...", chat_id_admin_cb, message_id_admin_cb, reply_markup=reply_markup_admin_cb)
        except telebot.apihelper.ApiTelegramException as e_edit_admin_cb:
            if "message is not modified" not in e_edit_admin_cb.description:
                 logger.error(f"Failed to edit admin prompt: {e_edit_admin_cb}")

def handleListAdmins(message_obj_list_admins):
    chat_id_list_admins = message_obj_list_admins.chat.id
    message_id_to_edit_list_admins = message_obj_list_admins.message_id

    bot_admins_list = loadData('data/admins/bot_admins.json')
    if not isinstance(bot_admins_list, list): bot_admins_list = []

    text_list_admins = "👮‍♂️ <b>أدمن البوت الحاليين (غير المطور الأساسي):</b>\n\n"
    other_bot_admins = [admin_id for admin_id in bot_admins_list if str(admin_id) != str(ADMIN_ID)]

    if not other_bot_admins:
        text_list_admins += "لا يوجد أدمن مضافين حالياً (بخلاف المطور)."
    else:
        admin_lines_list = []
        count_list_admins = 0
        for admin_id_item in other_bot_admins:
            count_list_admins += 1
            admin_display_list = f"<code>{admin_id_item}</code>"
            try:
                admin_chat_obj = bot.get_chat(admin_id_item)
                admin_user_obj = types.User(admin_chat_obj.id, admin_chat_obj.first_name, is_bot=False,
                                        last_name=admin_chat_obj.last_name, username=admin_chat_obj.username)
                admin_display_list = formatUserMentionHTML(admin_user_obj)
            except Exception: pass 
            admin_lines_list.append(f"{count_list_admins}. {admin_display_list}")
        text_list_admins += "\n".join(admin_lines_list)

    markup_list_admins = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🔙 رجوع للوحة التحكم', callback_data='admin_back'))
    try:
        _safe_bot_call(bot.edit_message_text, text_list_admins, chat_id_list_admins, message_id_to_edit_list_admins, reply_markup=markup_list_admins)
    except telebot.apihelper.ApiTelegramException as e_list_admins:
        if "message is not modified" not in e_list_admins.description:
            logger.error(f"Failed to edit list admins: {e_list_admins}")
            _safe_bot_call(bot.send_message, chat_id_list_admins, text_list_admins, reply_markup=markup_list_admins)

def handleListGroups(message_obj_list_groups):
    chat_id_list_groups = message_obj_list_groups.chat.id
    message_id_to_edit_list_groups = message_obj_list_groups.message_id

    active_groups_list = loadData('data/groups_active.json')
    if not isinstance(active_groups_list, list): active_groups_list = []

    text_list_groups = f"📄 <b>المجموعات المفعلة حالياً ({len(active_groups_list)}):</b>\n\n"
    if not active_groups_list:
        text_list_groups += "لا توجد مجموعات مفعلة حالياً."
    else:
        group_lines_list = []
        count_list_groups = 0
        limit_list_groups = 20
        for group_id_item_str in active_groups_list:
            group_id_item = int(group_id_item_str)
            if count_list_groups >= limit_list_groups:
                remaining_count_list_groups = len(active_groups_list) - limit_list_groups
                group_lines_list.append(f"... وأكثر ({remaining_count_list_groups})")
                break
            count_list_groups += 1
            group_display_list = f"<code>{group_id_item}</code>"
            try:
                group_info_obj = bot.get_chat(group_id_item)
                group_title_safe_list = telebot.util.escape(group_info_obj.title or str(group_id_item))
                group_display_list = f"{group_title_safe_list} (<code>{group_id_item}</code>)"
            except telebot.apihelper.ApiTelegramException as e_get_chat_list:
                error_desc_safe_list = telebot.util.escape(str(e_get_chat_list.description)[:30])
                group_display_list += f" (Error: {error_desc_safe_list})"
            except Exception: pass
            group_lines_list.append(f"{count_list_groups}. {group_display_list}")
            if count_list_groups % 10 == 0: time.sleep(0.1)
        text_list_groups += "\n".join(group_lines_list)

    markup_list_groups = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🔙 رجوع للوحة التحكم', callback_data='admin_back'))
    try:
        _safe_bot_call(bot.edit_message_text, text_list_groups, chat_id_list_groups, message_id_to_edit_list_groups, reply_markup=markup_list_groups)
    except telebot.apihelper.ApiTelegramException as e_list_groups:
        if "message is not modified" not in e_list_groups.description:
            logger.error(f"Failed to edit list groups: {e_list_groups}")
            _safe_bot_call(bot.send_message, chat_id_list_groups, text_list_groups, reply_markup=markup_list_groups)

def handleAdminInput(message):
    chat_id_admin_input = message.chat.id
    from_user_id_admin_input = message.from_user.id

    state_admin_input_obj = getUserState(from_user_id_admin_input)
    state_admin_input = state_admin_input_obj.get('name') if isinstance(state_admin_input_obj, dict) else state_admin_input_obj

    if not state_admin_input or not state_admin_input.startswith('admin_'): return False

    action_admin_input = state_admin_input[6:]
    success_admin_input = False
    result_message_admin_input = ''
    show_panel_after_admin_input = True
    message_text_admin_input = message.text or message.caption or ""

    if action_admin_input in ['broadcast_users', 'broadcast_groups']:
        targets_admin_input = loadData('data/users.json') if action_admin_input == 'broadcast_users' else loadData('data/groups_active.json')
        if not isinstance(targets_admin_input, list): targets_admin_input = []
        target_name_admin_input = 'المستخدمين' if action_admin_input == 'broadcast_users' else 'المجموعات'
        has_content_admin_input = any([message.text, message.caption, message.photo, message.video, message.document, message.sticker, message.voice, message.audio, message.animation])
        if not has_content_admin_input:
            result_message_admin_input = formatString('broadcast_no_content', user_id=from_user_id_admin_input)
            success_admin_input = False; show_panel_after_admin_input = False
        else:
            broadcast_status_msg_obj = _safe_bot_call(bot.send_message, chat_id_admin_input, formatString('broadcast_start', {'target': target_name_admin_input}, user_id=from_user_id_admin_input))
            status_msg_id_admin_input = broadcast_status_msg_obj.message_id if broadcast_status_msg_obj else None
            count_admin_input = 0; errors_admin_input = 0
            for target_chat_id_item_str in targets_admin_input:
                try:
                    target_chat_id_item = int(target_chat_id_item_str)
                    _safe_bot_call(bot.forward_message, target_chat_id_item, chat_id_admin_input, message.message_id, disable_notification=False)
                    count_admin_input += 1
                except telebot.apihelper.ApiTelegramException as e_fwd:
                    errors_admin_input += 1
                    logger.error(f"Broadcast forward failed for target {target_chat_id_item_str}: [{e_fwd.error_code}] {e_fwd.description}")
                    if e_fwd.error_code in [400, 403]:
                        if action_admin_input == 'broadcast_users':
                            users_f = loadData('data/users.json')
                            if isinstance(users_f, list) and target_chat_id_item_str in users_f:
                                users_f.remove(target_chat_id_item_str); saveData('data/users.json', users_f)
                        else: setGroupActive(target_chat_id_item, False)
                except Exception as e_fwd_gen: errors_admin_input += 1; logger.error(f"Broadcast forward general error for target {target_chat_id_item_str}: {e_fwd_gen}")
                if status_msg_id_admin_input and (count_admin_input + errors_admin_input) % 20 == 0 and (count_admin_input + errors_admin_input) > 0:
                    try: _safe_bot_call(bot.edit_message_text, formatString('broadcast_progress', {'count': count_admin_input, 'errors': errors_admin_input}, user_id=from_user_id_admin_input), chat_id_admin_input, status_msg_id_admin_input)
                    except: pass
                time.sleep(0.35)
            if status_msg_id_admin_input: _safe_bot_call(bot.delete_message, chat_id_admin_input, status_msg_id_admin_input)
            result_message_admin_input = formatString('broadcast_sent', {'count': count_admin_input, 'target': target_name_admin_input}, user_id=from_user_id_admin_input)
            if errors_admin_input > 0: result_message_admin_input += f"\n⚠️ فشل الإرسال لـ {errors_admin_input}."
            success_admin_input = True
    elif action_admin_input == 'add_admin':
        if message_text_admin_input.isdigit():
            admin_id_to_add = str(message_text_admin_input)
            admins_f_add = loadData('data/admins/bot_admins.json');
            if not isinstance(admins_f_add, list): admins_f_add = []
            if admin_id_to_add == str(ADMIN_ID): result_message_admin_input = "⚠️ لا يمكنك إضافة المطور الأساسي."
            elif admin_id_to_add not in admins_f_add:
                admins_f_add.append(admin_id_to_add); saveData('data/admins/bot_admins.json', admins_f_add)
                result_message_admin_input = formatString('admin_added', user_id=from_user_id_admin_input) + f" (<code>{admin_id_to_add}</code>)"
            else: result_message_admin_input = formatString('admin_already_exists', user_id=from_user_id_admin_input) + f" (<code>{admin_id_to_add}</code>)"
            success_admin_input = True
        else:
            result_message_admin_input = formatString('invalid_admin_id', user_id=from_user_id_admin_input)
            success_admin_input = False; show_panel_after_admin_input = False
    elif action_admin_input == 'del_admin':
        if message_text_admin_input.isdigit():
            admin_id_to_del = str(message_text_admin_input)
            admins_f_del = loadData('data/admins/bot_admins.json')
            if not isinstance(admins_f_del, list): admins_f_del = []
            if admin_id_to_del == str(ADMIN_ID): result_message_admin_input = "⚠️ لا يمكنك حذف المطور الأساسي."
            elif admin_id_to_del in admins_f_del:
                admins_f_del.remove(admin_id_to_del); saveData('data/admins/bot_admins.json', admins_f_del)
                result_message_admin_input = formatString('admin_removed', user_id=from_user_id_admin_input) + f" (<code>{admin_id_to_del}</code>)"
            else: result_message_admin_input = formatString('admin_not_found', user_id=from_user_id_admin_input) + f" (<code>{admin_id_to_del}</code>)"
            success_admin_input = True
        else:
            result_message_admin_input = formatString('invalid_admin_id', user_id=from_user_id_admin_input)
            success_admin_input = False; show_panel_after_admin_input = False
    elif action_admin_input == 'leave_group':
        if message_text_admin_input.lstrip('-').isdigit() and message_text_admin_input.startswith('-'):
            group_id_to_leave_admin_input = int(message_text_admin_input)
            try:
                bot.leave_chat(group_id_to_leave_admin_input)
                result_message_admin_input = formatString('leave_group_success', {'group_id': group_id_to_leave_admin_input}, user_id=from_user_id_admin_input)
                setGroupActive(group_id_to_leave_admin_input, False)
                success_admin_input = True
            except telebot.apihelper.ApiTelegramException as e_leave:
                if "chat not found" in e_leave.description.lower() or "bot is not a member" in e_leave.description.lower() :
                    result_message_admin_input = formatString('leave_group_not_found', {'group_id': group_id_to_leave_admin_input}, user_id=from_user_id_admin_input)
                else: result_message_admin_input = formatString('leave_group_fail', {'group_id': group_id_to_leave_admin_input}, user_id=from_user_id_admin_input) + f" ({telebot.util.escape(e_leave.description)})"
                success_admin_input = True 
            except Exception as e_leave_gen:
                result_message_admin_input = formatString('leave_group_fail', {'group_id': group_id_to_leave_admin_input}, user_id=from_user_id_admin_input) + f" (Error: {telebot.util.escape(str(e_leave_gen))})"
                success_admin_input = True
        else:
            result_message_admin_input = formatString('invalid_group_id', user_id=from_user_id_admin_input)
            success_admin_input = False; show_panel_after_admin_input = False
    else:
        logger.error(f"Admin input received for unknown state/action: {state_admin_input}")
        result_message_admin_input = "⚠️ حدث خطأ غير متوقع في حالة الأدمن."
        success_admin_input = True; show_panel_after_admin_input = True

    if result_message_admin_input: _safe_bot_call(bot.reply_to, message, result_message_admin_input)
    if success_admin_input: saveUserState(from_user_id_admin_input, None)
    if success_admin_input and show_panel_after_admin_input: showAdminPanel(chat_id_admin_input)
    return True

def displayGroupSettingsPanel(chat_id_gsp, message_id_gsp=None, is_edit=False):
    from_user_id_gsp = ADMIN_ID 
    welcome_settings_gsp = getWelcomeSettings(chat_id_gsp)
    group_channel_gsp = getGroupCompulsoryChannel(chat_id_gsp)
    group_title_gsp = "المجموعة"; 
    try: group_title_gsp = telebot.util.escape(bot.get_chat(chat_id_gsp).title or "المجموعة")
    except: pass

    text_gsp = f"⚙️ <b>إعدادات {group_title_gsp}</b> ⚙️\n\nهنا يمكنك التحكم في إعدادات الحماية والترحيب للمجموعة.\n\n"
    welcome_status_gsp = '✅ مفعل' if welcome_settings_gsp.get('enabled', True) else '❌ معطل'
    text_gsp += f"🎉 <b>الترحيب:</b> {welcome_status_gsp}\n\n📢 <b>القناة الإجبارية:</b>\n"
    if group_channel_gsp: text_gsp += f"▫️ خاص بالمجموعة: <code>{telebot.util.escape(group_channel_gsp)}</code>\n"
    else: text_gsp += "▫️ لا يوجد قناة إجبارية\n"

    keyboard_gsp = types.InlineKeyboardMarkup(row_width=2)
    welcome_media_status_gsp = '🖼️ (يوجد)' if welcome_settings_gsp.get('media') else '🚫 (لا يوجد)'
    keyboard_gsp.add(types.InlineKeyboardButton(f"🎉 الترحيب: {welcome_status_gsp}", callback_data='grpset_toggle_welcome'))
    keyboard_gsp.add(types.InlineKeyboardButton('✏️ تعديل نص الترحيب', callback_data='grpset_set_welcome_text'),
                     types.InlineKeyboardButton(f"🖼️ تعديل ميديا {welcome_media_status_gsp}", callback_data='grpset_set_welcome_media'))
    keyboard_gsp.add(types.InlineKeyboardButton('🗑️ استعادة الترحيب الافتراضي', callback_data='grpset_reset_welcome'))

    channel_display_gsp = (f"🔗 خاص: {telebot.util.escape(group_channel_gsp)}"[:30] if group_channel_gsp else '🚫 لا يوجد')
    row_channel_btns = [types.InlineKeyboardButton(f"قناة إجبارية: {channel_display_gsp}", callback_data='grpset_set_channel')]
    if group_channel_gsp: row_channel_btns.append(types.InlineKeyboardButton('🗑️ حذف القناة', callback_data='grpset_del_channel'))
    keyboard_gsp.row(*row_channel_btns)
    keyboard_gsp.add(types.InlineKeyboardButton('🔒 إعدادات القفل والمنع 🔒', callback_data='grpset_show_locks'))
    keyboard_gsp.add(types.InlineKeyboardButton('❌ إغلاق', callback_data='close'))

    reply_to_id_gsp = None
    if message_id_gsp:
        reply_to_id_gsp = message_id_gsp if isinstance(message_id_gsp, (int,str)) else message_id_gsp.message_id

    if is_edit and reply_to_id_gsp:
        try: _safe_bot_call(bot.edit_message_text, text_gsp, chat_id_gsp, reply_to_id_gsp, reply_markup=keyboard_gsp)
        except telebot.apihelper.ApiTelegramException as e_edit_gsp:
            if "message is not modified" not in e_edit_gsp.description: 
                logger.error(f"Edit group settings panel error: {e_edit_gsp}")
                _safe_bot_call(bot.send_message, chat_id_gsp, text_gsp, reply_markup=keyboard_gsp, reply_to_message_id=reply_to_id_gsp)
    elif reply_to_id_gsp:
         _safe_bot_call(bot.send_message, chat_id_gsp, text_gsp, reply_markup=keyboard_gsp, reply_to_message_id=reply_to_id_gsp)
    else:
        _safe_bot_call(bot.send_message, chat_id_gsp, text_gsp, reply_markup=keyboard_gsp)

def displayGroupLockSettingsPanel(chat_id_glsp, message_id_glsp_to_edit):
    locks_glsp = loadData(os.path.join("data/locks", f"{chat_id_glsp}_locks.json"))
    if not isinstance(locks_glsp, dict): locks_glsp = {}
    delete_locks_glsp = locks_glsp.get('delete', {})
    feature_map_glsp = {
        'forward': 'التوجيه', 'link': 'الروابط', 'username': 'المعرفات', 'bots': 'البوتات'
    }
    text_glsp = "🔒 <b>إعدادات القفل والمنع</b> 🔒\n\nاضغط لتغيير الحالة (✅ مقفول | ❌ مفتوح)."
    keyboard_glsp = types.InlineKeyboardMarkup(row_width=2)

    for key, arabic_name in feature_map_glsp.items():
        status = delete_locks_glsp.get(key, False)
        icon = '✅' if status else '❌'
        keyboard_glsp.add(types.InlineKeyboardButton(f"{icon} {arabic_name}", callback_data=f"togglelock_delete_{key}"))

    keyboard_glsp.add(types.InlineKeyboardButton('🔙 رجوع لإعدادات المجموعة', callback_data='grpset_back_main'))
    try: _safe_bot_call(bot.edit_message_text, text_glsp, chat_id_glsp, message_id_glsp_to_edit, reply_markup=keyboard_glsp)
    except telebot.apihelper.ApiTelegramException as e_edit_glsp:
        if "message is not modified" not in e_edit_glsp.description: logger.error(f"Failed to edit lock settings panel: {e_edit_glsp}")

def handleGroupSettingsCallback(call, param_gscb):
    chat_id_gscb = call.message.chat.id; message_id_gscb = call.message.message_id
    from_user_id_gscb = call.from_user.id
    requires_input_gscb = param_gscb in ['set_welcome_text', 'set_welcome_media', 'set_channel']
    if requires_input_gscb: saveUserState(from_user_id_gscb, f'grpset_{param_gscb}')
    else: saveUserState(from_user_id_gscb, None)

    edit_text_gscb = ''; reply_markup_gscb = None
    back_button_gscb = types.InlineKeyboardButton('🔙 إلغاء ورجوع', callback_data='grpset_back_main')

    if param_gscb == 'toggle_welcome':
        settings_gscb_toggle = getWelcomeSettings(chat_id_gscb)
        new_status_gscb_toggle = not settings_gscb_toggle.get('enabled', True)
        setWelcomeSettings(chat_id_gscb, {'enabled': new_status_gscb_toggle})
        displayGroupSettingsPanel(chat_id_gscb, message_id_gscb, is_edit=True)
        status_text_gscb_toggle = 'مفعل' if new_status_gscb_toggle else 'معطل'
        bot.answer_callback_query(call.id, text=f"تم {status_text_gscb_toggle} الترحيب"); return
    elif param_gscb == 'set_welcome_text': edit_text_gscb = formatString('provide_welcome_text', user_id=from_user_id_gscb)
    elif param_gscb == 'set_welcome_media':
        current_settings_gscb_media = getWelcomeSettings(chat_id_gscb)
        media_status_gscb_media = '🖼️ (يوجد)' if current_settings_gscb_media.get('media') else '🚫 (لا يوجد)'
        edit_text_gscb = formatString('provide_welcome_media', user_id=from_user_id_gscb)
        keyboard_temp_gscb_media = types.InlineKeyboardMarkup()
        keyboard_temp_gscb_media.add(types.InlineKeyboardButton(f"🗑️ حذف الميديا الحالية {media_status_gscb_media}", callback_data='grpset_clear_welcome_media'))
        keyboard_temp_gscb_media.add(back_button_gscb); reply_markup_gscb = keyboard_temp_gscb_media
    elif param_gscb == 'clear_welcome_media':
        setWelcomeSettings(chat_id_gscb, {'media': '', 'media_type': 'photo', 'is_file_id': False})
        bot.answer_callback_query(call.id, text="تم حذف ميديا الترحيب")
        handleGroupSettingsCallback(call, 'set_welcome_media'); return
    elif param_gscb == 'reset_welcome':
        resetWelcomeSettings(chat_id_gscb)
        bot.answer_callback_query(call.id, text=formatString('welcome_reset', user_id=from_user_id_gscb))
        displayGroupSettingsPanel(chat_id_gscb, message_id_gscb, is_edit=True); return
    elif param_gscb == 'set_channel': edit_text_gscb = formatString('provide_channel', user_id=from_user_id_gscb)
    elif param_gscb == 'del_channel':
        setGroupCompulsoryChannel(chat_id_gscb, '')
        bot.answer_callback_query(call.id, text=formatString('group_channel_removed', user_id=from_user_id_gscb))
        displayGroupSettingsPanel(chat_id_gscb, message_id_gscb, is_edit=True); return
    elif param_gscb == 'show_locks': displayGroupLockSettingsPanel(chat_id_gscb, message_id_gscb); return
    elif param_gscb == 'back_main':
        saveUserState(from_user_id_gscb, None)
        displayGroupSettingsPanel(chat_id_gscb, message_id_gscb, is_edit=True); return
    else:
        logger.warning(f"Unknown group setting callback param: {param_gscb}")
        bot.answer_callback_query(call.id, text='خيار إعدادات غير معروف.')
        displayGroupSettingsPanel(chat_id_gscb, message_id_gscb, is_edit=True); return

    if requires_input_gscb and (edit_text_gscb or reply_markup_gscb):
        if not reply_markup_gscb: reply_markup_gscb = types.InlineKeyboardMarkup().add(back_button_gscb)
        try: _safe_bot_call(bot.edit_message_text, edit_text_gscb or "...", chat_id_gscb, message_id_gscb, reply_markup=reply_markup_gscb)
        except telebot.apihelper.ApiTelegramException as e_edit_gscb:
            if "message is not modified" not in e_edit_gscb.description: logger.error(f"Failed to edit group settings prompt: {e_edit_gscb}")

def handleGroupSettingsInput(message):
    chat_id_gs_input = message.chat.id; from_user_id_gs_input = message.from_user.id
    state_gs_input_obj = getUserState(from_user_id_gs_input)
    state_gs_input = state_gs_input_obj.get('name') if isinstance(state_gs_input_obj, dict) else state_gs_input_obj
    if not state_gs_input or not state_gs_input.startswith('grpset_'): return False

    action_gs_input = state_gs_input[7:]; success_gs_input = False
    result_message_gs_input = ''; show_panel_after_gs_input = True
    message_text_gs_input = message.text or message.caption or ""

    if action_gs_input == 'set_welcome_text':
        if message_text_gs_input and 5 < len(message_text_gs_input) < 1024:
            setWelcomeSettings(chat_id_gs_input, {'text': message_text_gs_input, 'enabled': True})
            result_message_gs_input = formatString('welcome_set', user_id=from_user_id_gs_input)
            success_gs_input = True
        else:
            result_message_gs_input = formatString('provide_welcome_text', user_id=from_user_id_gs_input) + "\n(النص قصير جداً أو طويل جداً)"
            success_gs_input = False; show_panel_after_gs_input = False
    elif action_gs_input == 'set_welcome_media':
        media_value_gs_input = ''; media_type_gs_input = 'photo'; is_file_id_gs_input = False; media_source_gs_input = ''
        if message.photo: media_value_gs_input = message.photo[-1].file_id; media_type_gs_input = 'photo'; is_file_id_gs_input = True; media_source_gs_input = 'الصورة'
        elif message.video: media_value_gs_input = message.video.file_id; media_type_gs_input = 'video'; is_file_id_gs_input = True; media_source_gs_input = 'الفيديو'
        elif message.animation: media_value_gs_input = message.animation.file_id; media_type_gs_input = 'animation'; is_file_id_gs_input = True; media_source_gs_input = 'المتحركة'
        elif message_text_gs_input:
            if re.match(r'^(لا شيء|لاشيء|none|حذف)$', message_text_gs_input, re.IGNORECASE): media_source_gs_input = 'حذف'
            elif message_text_gs_input.startswith("http"):
                media_value_gs_input = message_text_gs_input; is_file_id_gs_input = False; media_source_gs_input = 'الرابط'
                if re.search(r'\.(mp4|mov|avi|mkv)$', requests.utils.urlparse(media_value_gs_input).path, re.IGNORECASE): media_type_gs_input = 'video'
                elif re.search(r'\.(gif)$', requests.utils.urlparse(media_value_gs_input).path, re.IGNORECASE): media_type_gs_input = 'animation'
                else: media_type_gs_input = 'photo'
        if media_source_gs_input:
            setWelcomeSettings(chat_id_gs_input, {'media': media_value_gs_input, 'media_type': media_type_gs_input, 'is_file_id': is_file_id_gs_input, 'enabled': True})
            if media_source_gs_input == 'حذف': result_message_gs_input = "✅ تم حذف الميديا للترحيب بالجروب."
            else: result_message_gs_input = formatString('welcome_set', user_id=from_user_id_gs_input) + f" (باستخدام {media_source_gs_input})"
            success_gs_input = True
        else:
            result_message_gs_input = formatString('provide_welcome_media', user_id=from_user_id_gs_input) + " أرسل صورة/فيديو أو رابط أو كلمة 'لا شيء'."
            success_gs_input = False; show_panel_after_gs_input = False
    elif action_gs_input == 'set_channel':
        if re.match(r'^@([a-zA-Z0-9_]{5,})$', message_text_gs_input):
            try:
                status_in_channel_gs_input = getChatMemberStatus(message_text_gs_input, bot.get_me().id)
                if not isAdmin(status_in_channel_gs_input):
                    result_message_gs_input = formatString('bot_not_admin_in_channel', {'channel': message_text_gs_input}, user_id=from_user_id_gs_input)
                    success_gs_input = False; show_panel_after_gs_input = False
                else:
                    if setGroupCompulsoryChannel(chat_id_gs_input, message_text_gs_input):
                        result_message_gs_input = formatString('group_channel_set', {'channel': message_text_gs_input}, user_id=from_user_id_gs_input)
                    else: result_message_gs_input = formatString('action_failed', user_id=from_user_id_gs_input)
                    success_gs_input = True
            except Exception as e_set_gchan_input:
                result_message_gs_input = formatString('action_failed_api', user_id=from_user_id_gs_input) + f" ({telebot.util.escape(str(e_set_gchan_input)[:50])})"
                success_gs_input = False; show_panel_after_gs_input = False
        else:
            result_message_gs_input = formatString('invalid_channel', user_id=from_user_id_gs_input)
            success_gs_input = False; show_panel_after_gs_input = False
    else:
        logger.error(f"Group settings input received for unknown state: {state_gs_input}")
        result_message_gs_input = "⚠️ حدث خطأ غير متوقع في حالة الإعدادات."
        success_gs_input = True
    if result_message_gs_input: _safe_bot_call(bot.reply_to, message, result_message_gs_input)
    if success_gs_input: saveUserState(from_user_id_gs_input, None)
    if success_gs_input and show_panel_after_gs_input: displayGroupSettingsPanel(chat_id_gs_input, is_edit=False)
    return True

if __name__ == '__main__':
    logger.info(f"{BOT_PERSONALITY_NAME} Bot started successfully!")
    logger.info(f"Admin ID: {ADMIN_ID}, Developer: {DEVELOPER_USERNAME}")
    
    # تحميل إعدادات الأذكار وبدء الحلقة التلقائية
    loadAzkarSettings()
    startAzkarLoop()
    logger.info("Azkar system initialized successfully!")

    bot.infinity_polling(logger_level=logging.INFO, timeout=20, long_polling_timeout=30, skip_pending=True)
