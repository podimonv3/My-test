import os

BOT_TOKEN = os.getenv("BOT_TOKEN", None)
MONGO_URI = os.getenv("MONGO_URI", None)

# നിങ്ങളുടെ ടെലിഗ്രാം അക്കൗണ്ട് ഐഡി (Owner ID) ഇവിടെ Koyeb വഴി നൽകണം
# ഇത് ബോട്ട് ദുരുപയോഗം ചെയ്യാതിരിക്കാൻ സഹായിക്കും
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
