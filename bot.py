import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient

# info.py ഫയലിൽ നിന്നും വേരിയബിളുകൾ ഇംപോർട്ട് ചെയ്യുന്നു
from info import BOT_TOKEN, MONGO_URI

# ലോഗിൻ വിവരങ്ങൾ റെക്കോർഡ് ചെയ്യാൻ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# MongoDB കണക്ഷൻ സെറ്റപ്പ്
try:
    client = MongoClient(MONGO_URI)
    db = client['telegram_fileshare_bot']
    files_collection = db['files']
    counters_collection = db['counters']
    print("✅ MongoDB ഡാറ്റാബേസുമായി വിജയകരമായി കണക്ട് ചെയ്തിരിക്കുന്നു!")
except Exception as e:
    print(f"❌ MongoDB കണക്ഷൻ പരാജയപ്പെട്ടു: {e}")

# ഫയൽ ഐഡി കൗണ്ടർ നിയന്ത്രിക്കാൻ (file_1, file_2...)
def get_next_sequence_value():
    sequence_document = counters_collection.find_one_and_update(
        {'_id': 'file_id_counter'},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=True
    )
    return sequence_document['sequence_value']

# /start കമാൻഡ് ഹാൻഡ്‌ലർ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        file_id = context.args[0]  # ആദ്യത്തെ ആർഗ്യുമെന്റ് എടുക്കുന്നു
        
        # ഡാറ്റാബേസിൽ ഫയൽ ഉണ്ടോ എന്ന് നോക്കുന്നു
        file_data = files_collection.find_one({'share_id': file_id})
        
        if file_data:
            real_file_id = file_data['file_id']
            file_type = file_data['type']
            
            await update.message.reply_text("താങ്കൾ തിരഞ്ഞ ഫയൽ താഴെ നൽകുന്നു 👇")
            
            if file_type == 'document':
                await update.message.reply_document(document=real_file_id)
            elif file_type == 'photo':
                await update.message.reply_photo(photo=real_file_id)
            elif file_type == 'video':
                await update.message.reply_video(video=real_file_id)
            elif file_type == 'audio':
                await update.message.reply_audio(audio=real_file_id)
        else:
            await update.message.reply_text("❌ ക്ഷമിക്കണം, ഈ ഫയൽ കണ്ടെത്താനായില്ല അല്ലെങ്കിൽ ലിങ്ക് തെറ്റാണ്!")
    else:
        await update.message.reply_text(
            "ഹലോ! ഞാൻ ഒരു ലോങ്-ടേം ഫയൽ ഷെയറിംഗ് ബോട്ട് ആണ്. 📂\n\n"
            "എനിക്ക് ഏതെങ്കിലും ഫയൽ അയച്ചു തരൂ, ഞാൻ അതിനൊരു സ്ഥിരമായ (Permanent) ലിങ്ക് നിർമ്മിച്ച് നൽകാം."
        )

# ഫയലുകൾ സ്വീകരിക്കുന്ന ഫങ്ക്ഷൻ
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        real_file_id = update.message.document.file_id
        file_type = 'document'
    elif update.message.photo:
        real_file_id = update.message.photo[-1].file_id
        file_type = 'photo'
    elif update.message.video:
        real_file_id = update.message.video.file_id
        file_type = 'video'
    elif update.message.audio:
        real_file_id = update.message.audio.file_id
        file_type = 'audio'
    else:
        await update.message.reply_text("⚠️ ദയവായി ഒരു ഫയൽ മാത്രം അയക്കുക!")
        return

    # പുതിയ യുണീക് ഐഡി ഡാറ്റാബേസിൽ നിന്ന് എടുക്കുന്നു
    current_counter = get_next_sequence_value()
    share_id = f"file_{current_counter}"
    
    # ഫയൽ വിവരങ്ങൾ ഡാറ്റാബേസിലേക്ക് സേവ് ചെയ്യുന്നു
    files_collection.insert_one({
        'share_id': share_id,
        'file_id': real_file_id,
        'type': file_type
    })

    bot_info = await context.bot.get_me()
    bot_username = bot_info.username
    share_link = f"https://t.me{bot_username}?start={share_id}"

    await update.message.reply_text(
        f"✅ നിങ്ങളുടെ ഫയൽ ഡാറ്റാബേസിൽ സുരക്ഷിതമായി സേവ് ചെയ്തിരിക്കുന്നു!\n\n"
        f"🔗 സ്ഥിരമായ ലിങ്ക്: {share_link}\n\n"
        f"ഈ ലിങ്ക് ഒരിക്കലും നഷ്ടപ്പെടില്ല."
    )

def main():
    if not BOT_TOKEN or not MONGO_URI:
        print("Error: BOT_TOKEN അല്ലെങ്കിൽ MONGO_URI സെറ്റ് ചെയ്തിട്ടില്ല!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    file_filters = filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO
    app.add_handler(MessageHandler(file_filters, handle_file))

    print("ബോട്ട് റൺ ആകുന്നു...")
    app.run_polling()

if __name__ == '__main__':
    main()
