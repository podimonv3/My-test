import logging
import threading
from flask import Flask
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ChatJoinRequestHandler, CallbackQueryHandler 
# info.py ഫയലിൽ നിന്നും BOT_TOKEN കൃത്യമായി ഇമ്പോർട്ട് ചെയ്യുന്നു
from info import BOT_TOKEN
import handlers

# 🚨 പുതിയ ആന്റി-സ്പാം ഫയൽ ഇവിടെ ഇമ്പോർട്ട് ചെയ്യുന്നു
from antispam import register_antispam

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Koyeb-ന് കാണിച്ചു കൊടുക്കാൻ വേണ്ടിയുള്ള ഒരു ചെറിയ വെബ് പേജ് (Keep Alive)
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "ബോട്ട് വിജയകരമായി റൺ ആകുന്നു... 🚀"

def run_flask():
    import os
    port = int(os.getenv("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN സെറ്റ് ചെയ്തിട്ടില്ല!")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    # കമാൻഡുകൾ
    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("setchannel", handlers.set_channel_command))
    app.add_handler(CommandHandler("broadcast", handlers.broadcast_command))
    app.add_handler(CommandHandler("stats", handlers.stats_command))
    
    # 🔄 പുതിയ റിഫ്രഷ് ബട്ടൺ പ്രവർത്തിക്കാൻ ഈ വരി താഴെ ആഡ് ചെയ്യുക
    app.add_handler(CallbackQueryHandler(handlers.stats_callback_handler, pattern="^refresh_stats$"))
    
    app.add_handler(ChatJoinRequestHandler(handlers.handle_join_request))
    
    # 📝 സ്റ്റിക്കറുകളും ടെക്സ്റ്റുകളും കൂടി ഫോർവേഡ് ഫിൽട്ടറിലേക്ക് ഇവിടെ ആഡ് ചെയ്തിരിക്കുന്നു
    forward_filters = filters.FORWARDED & (
        filters.Document.ALL | 
        filters.PHOTO | 
        filters.VIDEO | 
        filters.AUDIO | 
        filters.Sticker.ALL |          # സ്റ്റിക്കറുകൾക്കായി
        (filters.TEXT & ~filters.COMMAND) # കമാൻഡുകൾ അല്ലാത്ത സാധാരണ ടെക്സ്റ്റുകൾക്കായി
    )
    app.add_handler(MessageHandler(forward_filters, handlers.handle_forwarded_files))

    # 🛡️ ആന്റി-സ്പാം ഫೀച്ചർ ബോട്ടിലേക്ക് ഇവിടെ കണക്ട് ചെയ്യുന്നു
    # ശ്രദ്ധിക്കുക: മറ്റ് ഫയൽ ഫോർവേഡുകൾ തടസ്സപ്പെടാതിരിക്കാൻ ഇത് കമാൻഡുകൾക്ക് താഴെയാണ് നൽകിയിരിക്കുന്നത്
    register_antispam(app)

    print("ബോട്ട് വിജയകരമായി റൺ ആകുന്നു...")
    app.run_polling()

if __name__ == '__main__':
    main()

