import os

BOT_TOKEN = os.getenv("BOT_TOKEN", None)
MONGO_URI = os.getenv("MONGO_URI", None)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
