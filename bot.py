import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Koyeb എൻവയോൺമെന്റ് വേരിയബിളിൽ നിന്ന് ബോട്ട് ടോക്കൺ എടുക്കുന്നു
TOKEN = os.getenv("BOT_TOKEN")

# ഫയലുകൾ താൽക്കാലികമായി സൂക്ഷിക്കാൻ ഒരു ഡിക്ഷണറി (റാം മെമ്മറി)
file_database = {}
file_counter = 1

# ലോഗിൻ വിവരങ്ങൾ റെക്കോർഡ് ചെയ്യാൻ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ബോട്ട് സ്റ്റാർട്ട് ചെയ്യുമ്പോൾ പ്രവർത്തിക്കുന്ന ഫങ്ക്ഷൻ (/start)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ലിങ്ക് വഴിയാണ് ഉപയോക്താവ് വന്നതെങ്കിൽ (ഉദാഹരണത്തിന്: t.me/bot?start=file_1)
    if context.args:
        file_id = context.args[0]
        if file_id in file_database:
            real_file_id = file_database[file_id]['file_id']
            file_type = file_database[file_id]['type']
            
            await update.message.reply_text("താങ്കൾ തിരഞ്ഞ ഫയൽ താഴെ നൽകുന്നു 👇")
            
            # ഫയലിന്റെ തരം അനുസരിച്ച് തിരികെ അയക്കുന്നു
            if file_type == 'document':
                await update.message.reply_document(document=real_file_id)
            elif file_type == 'photo':
                await update.message.reply_photo(photo=real_file_id)
            elif file_type == 'video':
                await update.message.reply_video(video=real_file_id)
            elif file_type == 'audio':
                await update.message.reply_audio(audio=real_file_id)
        else:
            await update.message.reply_text("❌ ക്ഷമിക്കണം, ഈ ഫയൽ കണ്ടെത്താനായില്ല അല്ലെങ്കിൽ ലിങ്ക് കാലാവധി കഴിഞ്ഞു!")
    else:
        # വെറുതെ ബോട്ട് സ്റ്റാർട്ട് ചെയ്യുമ്പോൾ കാണിക്കുന്ന മെസ്സേജ്
        await update.message.reply_text(
            "ഹലോ! ഞാൻ ഒരു ഫയൽ ഷെയറിംഗ് ബോട്ട് ആണ്. 📂\n\n"
            "എനിക്ക് ഏതെങ്കിലും ഫയൽ (Document, Photo, Video, Audio) അയച്ചു തരൂ. "
            "ഞാൻ അതിനൊരു ഷെയറബിൾ ലിങ്ക് (Shareable Link) നിർമ്മിച്ച് നൽകാം."
        )

# ഉപയോക്താവ് അയക്കുന്ന ഫയലുകൾ സ്വീകരിക്കുന്ന ഫങ്ക്ഷൻ
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global file_counter
    
    # ഫയൽ ഏത് തരമാണെന്ന് പരിശോധിക്കുന്നു
    if update.message.document:
        real_file_id = update.message.document.file_id
        file_type = 'document'
    elif update.message.photo:
        real_file_id = update.message.photo[-1].file_id  # ബെസ്റ്റ് ക്വാളിറ്റി ഫോട്ടോ എടുക്കുന്നു
        file_type = 'photo'
    elif update.message.video:
        real_file_id = update.message.video.file_id
        file_type = 'video'
    elif update.message.audio:
        real_file_id = update.message.audio.file_id
        file_type = 'audio'
    else:
        await update.message.reply_text("⚠️ ദയവായി സപ്പോർട്ട് ചെയ്യുന്ന ഒരു ഫയൽ അയക്കുക!")
        return

    # ഓരോ ഫയലിനും തനതായ ഒരു ഐഡി ഉണ്ടാക്കുന്നു (ഉദാ: file_1, file_2)
    share_id = f"file_{file_counter}"
    file_database[share_id] = {'file_id': real_file_id, 'type': file_type}
    file_counter += 1

    # ബോട്ടിന്റെ യൂസർനെയിം ഓട്ടോമാറ്റിക് ആയി എടുക്കുന്നു
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username
    
    # ഡൗൺലോഡ് ലിങ്ക് നിർമ്മിക്കുന്നു
    share_link = f"https://t.me{bot_username}?start={share_id}"

    await update.message.reply_text(
        f"✅ നിങ്ങളുടെ ഫയൽ വിജയകരമായി സേവ് ചെയ്തിരിക്കുന്നു!\n\n"
        f"🔗 ഫയൽ ലിങ്ക്: {share_link}\n\n"
        f"ഈ ലിങ്ക് കോപ്പി ചെയ്ത് ആർക്ക് വേണമെങ്കിലും അയച്ചു കൊടുക്കാം."
    )

def main():
    # ടോക്കൺ ഉണ്ടോ എന്ന് ഉറപ്പുവരുത്തുന്നു
    if not TOKEN:
        print("Error: BOT_TOKEN സെറ്റ് ചെയ്തിട്ടില്ല! Koyeb-ൽ Env Variable നൽകിയിട്ടുണ്ടെന്ന് ഉറപ്പാക്കുക.")
        return

    # ബോട്ട് ആപ്ലിക്കേഷൻ സ്റ്റാർട്ട് ചെയ്യുന്നു
    app = Application.builder().token(TOKEN).build()

    # ഹാൻഡ്‌ലറുകൾ ആഡ് ചെയ്യുന്നു
    app.add_handler(CommandHandler("start", start))
    
    # ഡോക്യുമെന്റ്, ഫോട്ടോ, വീഡിയോ, ഓഡിയോ ഫയലുകളെ ഫിൽട്ടർ ചെയ്യുന്നു
    file_filters = filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO
    app.add_handler(MessageHandler(file_filters, handle_file))

    print("ബോട്ട് വിജയകരമായി റൺ ആകുന്നു...")
    app.run_polling()

if __name__ == '__main__':
    main()
