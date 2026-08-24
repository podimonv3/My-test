import base64
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from info import OWNER_ID
from database import batch_collection, requests_collection, settings_collection, users_collection, get_req_channel, add_user

user_data_store = {}

# Join Request വരുന്നത് ട്രാക്ക് ചെയ്യാൻ
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user_id = request.from_user.id
    chat_id = request.chat.id
    
    current_channel = get_req_channel()
    if chat_id == current_channel:
        requests_collection.update_one(
            {'user_id': user_id, 'channel_id': chat_id},
            {'$set': {'user_id': user_id, 'channel_id': chat_id, 'status': 'requested'}},
            upsert=True
        )

# ചാനലിൽ ഉണ്ടോ എന്ന് നോക്കാൻ
async def has_requested_or_joined(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    current_channel = get_req_channel()
    if not current_channel:
        return True
        
    try:
        member = await context.bot.get_chat_member(chat_id=current_channel, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except TelegramError:
        pass

    db_check = requests_collection.find_one({'user_id': user_id, 'channel_id': current_channel, 'status': 'requested'})
    return bool(db_check)

# /start കമാൻഡ്
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)
    current_channel = get_req_channel()
    
    if context.args:
        batch_id = context.args
        
        allowed = await has_requested_or_joined(context, user_id)
        if not allowed:
            try:
                chat_info = await context.bot.get_chat(current_channel)
                invite_link = chat_info.invite_link if chat_info.invite_link else f"https://t.me{chat_info.username}"
            except:
                invite_link = "https://t.me"

            keyboard = [
                [InlineKeyboardButton("📩 Request to Join", url=invite_link)],
                [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me{(await context.bot.get_me()).username}?start={batch_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "⚠️ **ഫയലുകൾ ലഭിക്കുന്നതിനായി താഴെ കാണുന്ന ചാനലിലേക്ക് Join Request അയക്കുക!**\n\n"
                "റിക്വസ്റ്റ് അയച്ചതിന് ശേഷം മാത്രം താഴെയുള്ള **Try Again** ബട്ടൺ അമർത്തുക.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

        batch_data = batch_collection.find_one({'batch_id': batch_id})
        if batch_data:
            from_chat = batch_data['from_chat']
            start_id = batch_data['start_id']
            end_id = batch_data['end_id']
            
            # Welcome Message / Ads 
            await update.message.reply_text(
                "✨ **താങ്കൾ തിരഞ്ഞ ഫയലുകൾ താഴെ നൽകുന്നു!**\n\n"
                "📢 കൂടുതൽ ഫയലുകൾക്കായി ഞങ്ങളോടൊപ്പം തുടരുക! 👇"
            )
            
            for msg_id in range(start_id, end_id + 1):
                try:
                    # 🔥 ഇവിടുത്തെ മാറ്റം ശ്രദ്ധിക്കുക:
                    # 1. copy_message ഉപയോഗിച്ചതിനാൽ ചാനൽ പേര് (Forward Tag) കാണില്ല.
                    # 2. protect_content=True നൽകിയതിനാൽ ഫയൽ ഫോർവേഡ് ചെയ്യാനോ സേവ് ചെയ്യാനോ സാധിക്കില്ല.
                    await context.bot.copy_message(
                        chat_id=update.message.chat_id,
                        from_chat_id=from_chat,
                        message_id=msg_id,
                        protect_content=True
                    )
                except:
                    continue
        else:
            await update.message.reply_text("❌ തെറ്റായ ലിങ്ക് അല്ലെങ്കിൽ ഈ ബാച്ച് നിലവിലില്ല!")
    else:
        await update.message.reply_text("ഹലോ! ഞാൻ ഒരു അഡ്വാൻസ്ഡ് Force Join ഫീച്ചറുള്ള Batch File Share Bot ആണ്. 📂")

# /setchannel കമാൻഡ് (പഴയ റിക്വസ്റ്റുകൾ ക്ലിയർ ചെയ്യുന്ന പുതുക്കിയ രീതി)
async def set_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text("⚠️ **രീതി:** `/setchannel [ചാനൽ_ഐഡി]`", parse_mode="Markdown")
        return

    try:
        new_channel_id = int(context.args)
        try:
            await context.bot.get_chat(new_channel_id)
        except TelegramError:
            await update.message.reply_text("❌ ബോട്ടിന് ഈ ചാനലിൽ പ്രവേശനമില്ല! ആദ്യം ബോട്ടിനെ ആ ചാനലിൽ **Admin** ആക്കുക.")
            return

        # 1. പുതിയ ചാനൽ ഐഡി ഡാറ്റാബേസിൽ അപ്‌ഡേറ്റ് ചെയ്യുന്നു
        settings_collection.update_one({'_id': 'fsub_config'}, {'$set': {'channel_id': new_channel_id}}, upsert=True)
        
        # 2. 🔥 പുതിയ മാറ്റം: പഴയ റിക്വസ്റ്റുകൾ എല്ലാം ഡാറ്റാബേസിൽ നിന്ന് തനിയെ ഡിലീറ്റ് ചെയ്യുന്നു
        requests_collection.delete_many({}) 
        
        await update.message.reply_text(
            f"✅ **റിക്വസ്റ്റ് ചാനൽ മാറ്റിയിരിക്കുന്നു!**\n🆔 ID: `{new_channel_id}`\n\n"
            f"🧹 _ഡാറ്റാബേസിലെ പഴയ ജോയിൻ റിക്വസ്റ്റുകൾ എല്ലാം വിജയകരമായി ക്ലിയർ ചെയ്തിട്ടുണ്ട്._", 
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ തെറ്റായ ഐഡി ഫോർമാറ്റ്!")


# Broadcasting കമാൻഡ് (Owner Only)
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ **ഉപയോഗിക്കേണ്ട രീതി:** ഏതെങ്കിലും ഒരു മെസ്സേജിന് മറുപടിയായി (Reply) `/broadcast` എന്ന് ടൈപ്പ് ചെയ്യുക.")
        return

    broadcast_msg = update.message.reply_to_message
    all_users = users_collection.find()
    
    await update.message.reply_text("📢 ബ്രോഡ്കാസ്റ്റിംഗ് ആരംഭിച്ചിരിക്കുന്നു...")
    
    success = 0
    failed = 0
    
    for user in all_users:
        try:
            await context.bot.copy_message(
                chat_id=user['_id'],
                from_chat_id=update.message.chat_id,
                message_id=broadcast_msg.message_id
            )
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
            continue

    await update.message.reply_text(
        f"✅ **ബ്രോഡ്കാസ്റ്റിംഗ് പൂർത്തിയായി!**\n\n👤 വിജയം: {success}\n❌ പരാജയം (Blocked Users): {failed}"
    )

# ഫയലുകൾ ഫോർവേഡ് ചെയ്യുന്നത് നിയന്ത്രിക്കാൻ
async def handle_forwarded_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        return

    if not update.message.forward_origin:
        await update.message.reply_text("⚠️ ദയവായി ഒരു ചാനലിൽ നിന്നും ഫയൽ **Forward** ചെയ്ത് അയക്കുക!")
        return
        
    origin = update.message.forward_origin
    if hasattr(origin, 'chat') and origin.chat:
        chat_id = origin.chat.id
        msg_id = origin.message_id
    else:
        await update.message.reply_text("❌ ഫയൽ ഐഡി എടുക്കാൻ കഴിഞ്ഞില്ല.")
        return

    if user_id not in user_data_store:
        user_data_store[user_id] = {'chat_id': chat_id, 'start_msg_id': msg_id}
        await update.message.reply_text("📥 **ആദ്യത്തെ ഫയൽ സ്വീകരിച്ചിരിക്കുന്നു!**\n\nഇനി അവസാന ഫയൽ ഫോർവേഡ് ചെയ്യൂ...")
    else:
        first_file_data = user_data_store[user_id]
        if first_file_data['chat_id'] != chat_id:
            await update.message.reply_text("❌ രണ്ട് ഫയലുകളും ഒരേ ചാനലിൽ നിന്നായിരിക്കണം!")
            del user_data_store[user_id]
            return
            
        start_id = min(first_file_data['start_msg_id'], msg_id)
        end_id = max(first_file_data['start_msg_id'], msg_id)
        
        unique_str = f"{chat_id}_{start_id}_{end_id}"
        batch_id = base64.urlsafe_b64encode(unique_str.encode()).decode().replace("=", "")
        
        batch_collection.update_one(
            {'batch_id': batch_id},
            {'$set': {'batch_id': batch_id, 'from_chat': chat_id, 'start_id': start_id, 'end_id': end_id}},
            upsert=True
        )
        
        bot_info = await context.bot.get_me()
        batch_link = f"https://t.me{bot_info.username}?start={batch_id}"
        
        await update.message.reply_text(f"✅ **Batch നിർമ്മിച്ചിരിക്കുന്നു!**\n🔗 **Batch ലിങ്ക്:** {batch_link}", parse_mode="Markdown")
        del user_data_store[user_id]

