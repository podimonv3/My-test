import threading
from flask import Flask

# Koyeb-ന് കാണിച്ചു കൊടുക്കാൻ വേണ്ടിയുള്ള ഒരു ചെറിയ വെബ് പേജ്
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "ബോട്ട് വിജയകരമായി റൺ ആകുന്നു... 🚀"

def run_flask():
    import os
    # Koyeb തനിയെ നൽകുന്ന പോർട്ട് നമ്പർ എടുക്കുന്നു
    port = int(os.getenv("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN സെറ്റ് ചെയ്തിട്ടില്ല!")
        return

    # 💡 ഫ്ലാസ്ക് സെർവർ മറ്റൊരു ത്രെഡിൽ റൺ ചെയ്യിക്കുന്നു (Keep Alive Trick)
    threading.Thread(target=run_flask, daemon=True).start()

    # നിങ്ങളുടെ പഴയ ബോട്ട് സെറ്റപ്പ് താഴെ തുടരുന്നു
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("setchannel", handlers.set_channel_command))
    app.add_handler(CommandHandler("broadcast", handlers.broadcast_command))
    app.add_handler(ChatJoinRequestHandler(handlers.handle_join_request))
    
    forward_filters = filters.FORWARDED & (filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO)
    app.add_handler(MessageHandler(forward_filters, handlers.handle_forwarded_files))

    print("ബോട്ട് വിജയകരമായി റൺ ആകുന്നു...")
    app.run_polling()

if __name__ == '__main__':
    main()
