import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ChatJoinRequestHandler

# മറ്റ് ഫയലുകളിൽ നിന്നും ആവശ്യമായവ ഇംപോർട്ട് ചെയ്യുന്നു
from info import BOT_TOKEN
import handlers

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN സെറ്റ് ചെയ്തിട്ടില്ല!")
        return

    # ബോട്ട് ആപ്ലിക്കേഷൻ സ്റ്റാർട്ട് ചെയ്യുന്നു
    app = Application.builder().token(BOT_TOKEN).build()

    # ഹാൻഡ്‌ലറുകൾ കണക്ട് ചെയ്യുന്നു
    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("setchannel", handlers.set_channel_command))
    app.add_handler(ChatJoinRequestHandler(handlers.handle_join_request))
    
    forward_filters = filters.FORWARDED & (filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO)
    app.add_handler(MessageHandler(forward_filters, handlers.handle_forwarded_files))

    print("ബോട്ട് വിജയകരമായി റൺ ആകുന്നു...")
    app.run_polling()

if __name__ == '__main__':
    main()
