from colorama import Fore

BOT_NAME = "Nexus Playerok Bot"
VERSION = "v1"
DEVELOPER = "@inboxper"

REPO = "NexusDev-maker/Nexus-Playerok-Bot"
ANNOUNCEMENT_BRANCH = "main"
ANNOUNCEMENT_FILE = "announcement.json"

REPO_CONFIGURED = bool(REPO) and "your-github" not in REPO
REPOSITORY = f"https://github.com/{REPO}"
SKIP_UPDATES = False

TELEGRAM_CHANNEL = "https://t.me/NexusPlayerok"
TELEGRAM_CHAT = "https://t.me/inboxper"
TELEGRAM_BOT = "https://t.me/inboxper"

ACCENT_COLOR = Fore.LIGHTCYAN_EX
SECONDARY_COLOR = Fore.CYAN
HIGHLIGHT_COLOR = Fore.LIGHTMAGENTA_EX
SUCCESS_COLOR = Fore.LIGHTBLUE_EX
INFO_COLOR = Fore.LIGHTCYAN_EX
