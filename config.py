from os import getenv

from dotenv import load_dotenv

load_dotenv()


API_ID = int(getenv("26481287"))
API_HASH = getenv("2e7eab515a32ebe882d0dfed7ee78acc")

BOT_TOKEN = getenv("7434690008:AAFr6mC2wd6y0P-Wz785ss9iAniJ4qZ8-WM", None)
DURATION_LIMIT = int(getenv("DURATION_LIMIT", "90"))

OWNER_ID = int(getenv("7934749229"))

PING_IMG = getenv("PING_IMG", "https://te.legra.ph/file/6f99c49bdb4679acad717.jpg")
START_IMG = getenv("START_IMG", "https://te.legra.ph/file/f8ba75bdbb9931cbc8229.jpg")

SESSION = getenv("SESSION", None)

SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/CH_XE")
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/JO7NB")

SUDO_USERS = list(map(int, getenv("SUDO_USERS", "7934749229").split()))


FAILED = "https://te.legra.ph/file/4c896584b592593c00aa8.jpg"
