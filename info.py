import os

# Koyeb വേരിയബിളുകൾ ഇവിടെ സെറ്റ് ചെയ്യുന്നു
# ഒരു സുരക്ഷയ്ക്ക് വേണ്ടി Koyeb-ൽ വേരിയബിൾ ഇല്ലെങ്കിൽ പകരം ഉപയോഗിക്കാൻ 'None' നൽകിയിരിക്കുന്നു
BOT_TOKEN = os.getenv("BOT_TOKEN", None)
MONGO_URI = os.getenv("MONGO_URI", None)

