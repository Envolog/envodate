import os

# Telegram Bot Configuration
TELEGRAM_API_BASE_URL = "https://api.telegram.org/bot"
REPLIT_DOMAIN = os.environ.get("REPLIT_DOMAINS", "").split()[0] if os.environ.get("REPLIT_DOMAINS") else ""
WEBHOOK_URL = f"https://{REPLIT_DOMAIN}/webhook/{os.environ.get('TELEGRAM_BOT_TOKEN', '')}" if REPLIT_DOMAIN else ""

# Bot Settings
BOT_USERNAME = os.environ.get("BOT_USERNAME", "ethiopian_university_dating_bot")
ADMIN_IDS = [int(id) for id in os.environ.get("ADMIN_IDS", "").split(",") if id]
OFFICIAL_CHANNEL_ID = os.environ.get("OFFICIAL_CHANNEL_ID", "")
OFFICIAL_CHANNEL_USERNAME = os.environ.get("OFFICIAL_CHANNEL_USERNAME", "UniMatchEthiopia")
CONFESSION_CHANNEL_ID = os.environ.get("CONFESSION_CHANNEL_ID", "")
CONFESSION_CHANNEL_USERNAME = os.environ.get("CONFESSION_CHANNEL_USERNAME", "UniMatchConfessions")
REQUIRE_CONFESSION_APPROVAL = os.environ.get("REQUIRE_CONFESSION_APPROVAL", "True").lower() == "true"
REQUIRE_CHANNEL_MEMBERSHIP = os.environ.get("REQUIRE_CHANNEL_MEMBERSHIP", "True").lower() == "true"
ENABLE_NOTIFICATIONS = os.environ.get("ENABLE_NOTIFICATIONS", "True").lower() == "true"

# Registration States
REGISTRATION_STATES = {
    "NAME": "reg_name",
    "AGE": "reg_age",
    "GENDER": "reg_gender",
    "INTERESTED_IN": "reg_interested_in",
    "UNIVERSITY": "reg_university",
    "BIO": "reg_bio",
    "PHOTO": "reg_photo",
    "CONFIRM": "reg_confirm",
}

# Other States
STATES = {
    "IDLE": "idle",
    "VIEWING_PROFILE": "viewing_profile",
    "CHATTING": "chatting",
    "CONFESSION": "confession",
    "REPORT": "report",
    "ADMIN": "admin",
}

# Universities list
UNIVERSITIES = [
    "Addis Ababa University",
    "Bahir Dar University",
    "Hawassa University",
    "Jimma University",
    "Mekelle University",
    "Gondar University",
    "Adama Science and Technology University",
    "Haramaya University",
    "Arba Minch University",
    "Dire Dawa University",
    "All Universities"
]

# Offensive words to filter in confessions
DEFAULT_BANNED_WORDS = [
    "offensive1",
    "offensive2",
    "offensive3"
]

# Maximum age allowed for registration
MAX_AGE = 30
MIN_AGE = 18

# Maximum attempts for invalid input
MAX_INVALID_ATTEMPTS = 3

# Maximum bio length
MAX_BIO_LENGTH = 300

# Pagination configuration
PROFILES_PER_PAGE = 1
MESSAGES_PER_PAGE = 5
