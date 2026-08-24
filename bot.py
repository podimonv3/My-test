import logging
import base64
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient

from info import BOT_TOKEN, MONGO_URI, OWNER_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# MongoDB സെറ്റപ്പ്
try:
    client = MongoClient(MONGO_URI)
    db = client['telegram_forward_batch_bot']
    batch_collection = db['batches']
    print("✅ MongoDB-യുമായി വിജയകരമായി കണക്ട് ചെയ്തിരിക്കുന്നു!")
except Exception as e:
    print(f"❌ MongoDB കണക്ഷൻ പരാജയപ്പെട്ടു: {e}")

# ഓരോ യൂസറുടെയും ആദ്യത്തെ ഫയൽ താൽക്കാലികമായി ഓർത്തു വെക്കാൻ
user_data_store = {}

# /start കമാൻഡ്
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        batch_id = context.args
        batch_data = batch_collection.find_one({'batch_id': batch_id})
        
        if batch_data:
            from_chat = batch_data['from_chat']
            start_id = batch_data['start_id']
            end_id = batch_data['end_id']
            
            await update.message.reply_text("📦 താങ്കൾ തിരഞ്ഞ ഫയലുകൾ താഴെ നൽകുന്നു...")
            
            success_count = 0
            for msg_id in range(start_id, end_id + 1):
                try:
                    await context.bot.copy_message(
                        chat_id=update.message.chat_id,
                        from_chat_id=from_chat,
                        message_id=msg_id
                    )
                    success_count += 1
                except:
                    continue
            
            if success_count == 0:
                await update.message.reply_text("❌ ക്ഷമിക്കണം, ഫയലുകൾ ഒന്നും കണ്ടെത്താനായില്ല!")
        else:
            await update.message.reply_text("❌ തെറ്റായ ലിങ്ക് അല്ലെങ്കിൽ ഈ ബാച്ച് നിലവിലില്ല!")
    else:
        await update.message.reply_text(
            "ഹലോ! ഞാൻ ഒരു Batch File Share Bot ആണ്. 📂\n\n"
            "**ഉപയോഗിക്കേണ്ട രീതി (For Owner):**\n"
            "ചാനലിൽ നിന്നും ആദ്യത്തെ ഫയലും, തുടർന്ന് അവസാനത്തെ ഫയലും ഇങ്ങോട്ട് **Forward** ചെയ്യുക. ഞാൻ ബാച്ച് ലിങ്ക് നൽകാം."
        )

# ഫയലുകൾ ഫോർവേഡ് ചെയ്യുമ്പോൾ കൈകാര്യം ചെയ്യുന്ന ഫങ്ക്ഷൻ
async def handle_forwarded_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # ബോട്ട് ഓണർക്കാണോ എന്ന് പരിശോധിക്കുന്നു
    if user_id != OWNER_ID:
        await update.message.reply_text("🔒 ക്ഷമിക്കണം, ഈ ബോട്ട് ഉപയോഗിക്കാൻ നിങ്ങൾക്ക് അനുവാദമില്ല!")
        return

    # ഫയൽ ചാനലിൽ നിന്ന് ഫോർവേഡ് ചെയ്തതാണോ എന്ന് നോക്കുന്നു
    if not update.message.forward_origin:
        await update.message.reply_text("⚠️ ദയവായി ഒരു ചാനലിൽ നിന്നും ഫയൽ **Forward** ചെയ്ത് അയക്കുക!")
        return
        
    origin = update.message.forward_origin
    
    # ചാനൽ ഐഡിയും മെസ്സേജ് ഐഡിയും എടുക്കുന്നു
    if hasattr(origin, 'chat') and origin.chat:
        chat_id = origin.chat.id
        msg_id = origin.message_id
    else:
        await update.message.reply_text("❌ ഈ ചാനലിൽ നിന്നുള്ള ഫയൽ ഐഡി എടുക്കാൻ കഴിഞ്ഞില്ല. ചാനൽ പ്രൈവസി സെറ്റിങ്സ് പരിശോധിക്കുക!")
        return

    # ഈ യൂസർ ഇതിനു മുൻപ് ആദ്യത്തെ ഫയൽ അയച്ചിട്ടില്ലെങ്കിൽ, ഇത് ആദ്യ ഫയലായി സേവ് ചെയ്യുന്നു
    if user_id not in user_data_store:
        user_data_store[user_id] = {
            'chat_id': chat_id,
            'start_msg_id': msg_id
        }
        await update.message.reply_text(
            "📥 **ആദ്യത്തെ ഫയൽ സ്വീകരിച്ചിരിക്കുന്നു!**\n\n"
            "ഇനി ബാച്ചിന്റെ **അവസാനത്തെ ഫയൽ** കൂടി ഇതേ ചാനലിൽ നിന്നും ഫോർവേഡ് ചെയ്ത് അയക്കൂ..."
        )
    else:
        # രണ്ടാമത്തെ ഫയൽ വരുമ്പോൾ ബാച്ച് ലിങ്ക് ഉണ്ടാക്കുന്നു
        first_file_data = user_data_store[user_id]
        
        # രണ്ട് ഫയലും ഒരേ ചാനലിൽ നിന്നാണോ എന്ന് ഉറപ്പ് വരുത്തുന്നു
        if first_file_data['chat_id'] != chat_id:
            await update.message.reply_text("❌ എറർ! രണ്ട് ഫയലുകളും ഒരേ ചാനലിൽ നിന്നും തന്നെ ഫോർവേഡ് ചെയ്യണം. വീണ്ടും ശ്രമിക്കുക!")
            del user_data_store[user_id] # താൽക്കാലിക ഡാറ്റ ക്ലിയർ ചെയ്യുന്നു
            return
            
        start_id = min(first_file_data['start_msg_id'], msg_id)
        end_id = max(first_file_data['start_msg_id'], msg_id)
        
        # യുണീക് ബാച്ച് ഐഡി നിർമ്മിക്കുന്നു
        unique_str = f"{chat_id}_{start_id}_{end_id}"
        batch_id = base64.urlsafe_b64encode(unique_str.encode()).decode().replace("=", "")
        
        # ഡാറ്റാബേസിലേക്ക് മാറ്റുന്നു
        batch_collection.update_one(
            {'batch_id': batch_id},
            {'$set': {
                'batch_id': batch_id,
                'from_chat': chat_id,
                'start_id': start_id,
                'end_id': end_id
            }},
            upsert=True
        )
        
        bot_info = await context.bot.get_me()
        batch_link = f"https://t.me{bot_info.username}?start={batch_id}"
        
        await update.message.reply_text(
            f"✅ **Batch വിജയകരമായി നിർമ്മിച്ചിരിക്കുന്നു!**\n\n"
            f"📊 ആകെ ഫയലുകൾ: {end_id - start_id + 1} എണ്ണം\n"
            f"🔗 **നിങ്ങളുടെ Batch ലിങ്ക്:** {batch_link}\n\n"
            f"_(അടുത്ത ബാച്ച് ഉണ്ടാക്കാൻ വീണ്ടും ആദ്യത്തെ ഫയൽ ഫോർവേഡ് ചെയ്യാം)_",
            parse_mode="Markdown"
        )
        
        # ബാച്ച് കഴിഞ്ഞതു കൊണ്ട് ഈ യൂസറുടെ താൽക്കാലിക മെമ്മറി ക്ലിയർ ചെയ്യുന്നു
        del user_data_store[user_id]

def main():
    if not BOT_TOKEN or not MONGO_URI:
        print("Error: BOT_TOKEN അല്ലെങ്കിൽ MONGO_URI സെറ്റ് ചെയ്തിട്ടില്ല!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    # ഫോർവേഡ് ചെയ്ത് വരുന്ന ഫയലുകളെ പിടിച്ചെടുക്കാൻ (ഫോട്ടോ, വീഡിയോ, ഡോക്യുമെന്റ്, ഓഡിയോ)
    forward_filters = filters.FORWARDED & (filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO)
    app.add_handler(MessageHandler(forward_filters, handle_forwarded_files))

    print("ബോട്ട് റൺ ആകുന്നു...")
    app.run_polling()

if __name__ == '__main__':
    main()
