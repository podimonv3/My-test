import base64
import asyncio
import os
import psutil  # 👈 റാം വിവരങ്ങൾ എടുക്കാൻ ആവശ്യമായ ലൈബ്രറി ചേർത്തു
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from info import OWNER_ID
from database import (
    batch_collection, 
    requests_collection, 
    settings_collection, 
    users_collection, 
    get_req_channel, 
    add_user,
    get_db_size
)

user_data_store = {}


# 1. യൂസർ ചാനലിലേക്ക് റിക്വസ്റ്റ് അയക്കുമ്പോൾ തൽക്ഷണം ഫയൽ നൽകുന്ന ഫങ്ക്ഷൻ 🚀
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user_id = request.from_user.id
    chat_id = request.chat.id
    
    current_channel = get_req_channel()
    if chat_id == current_channel:
        # ഡാറ്റാബേസിൽ റിക്വസ്റ്റ് വന്നിട്ടുണ്ടെന്ന് മാർക്ക് ചെയ്യുന്നു
        requests_collection.update_one(
            {'user_id': user_id, 'channel_id': chat_id},
            {'$set': {'user_id': user_id, 'channel_id': chat_id, 'status': 'requested'}},
            upsert=True
        )
        
        # യൂസർക്ക് ലഭിക്കേണ്ട ബാച്ച് ഫയലുകൾ ഉണ്ടോ എന്ന് നോക്കുന്നു
        user_pending = requests_collection.find_one({'user_id': user_id, 'channel_id': chat_id})
        if user_pending and 'batch_id' in user_pending:
            batch_id = user_pending['batch_id']
            batch_data = batch_collection.find_one({'batch_id': batch_id})
            
            if batch_data:
                from_chat = batch_data['from_chat']
                start_id = batch_data['start_id']
                end_id = batch_data['end_id']
                
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="✨ **നിങ്ങളുടെ ജോയിൻ റിക്വസ്റ്റ് ലഭിച്ചിരിക്കുന്നു! നിങ്ങൾ തിരഞ്ഞ ഫയലുകൾ താഴെ നൽകുന്നു:** 👇"
                    )
                    for msg_id in range(start_id, end_id + 1):
                        await context.bot.copy_message(
                            chat_id=user_id,
                            from_chat_id=from_chat,
                            message_id=msg_id,
                            protect_content=True
                        )
                    # ഫയലുകൾ അയച്ചതിന് ശേഷം താൽക്കാലിക ബാച്ച് ഐഡി ഡാറ്റ ക്ലിയർ ചെയ്യുന്നു
                    requests_collection.update_one(
                        {'user_id': user_id, 'channel_id': chat_id},
                        {'$unset': {'batch_id': ""}}
                    )
                except:
                    pass

# /start കമാൻഡ് - ഒരു വട്ടം റിക്വസ്റ്റ് അയച്ചാൽ പിന്നീട് ചോദിക്കില്ല 🛡️
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)
    current_channel = get_req_channel()
    
    if context.args:
        # ലിസ്റ്റിലെ ആദ്യത്തെ സ്ട്രിങ് എലമെന്റ് വേർതിരിച്ചെടുക്കുന്നു
        batch_id = context.args[0] if isinstance(context.args, list) and len(context.args) > 0 else context.args
        
        # 1. യൂസർ ഇതിനകം ചാനലിൽ മെമ്പർ ആണോ എന്ന് നോക്കുന്നു
        is_joined = False
        try:
            member = await context.bot.get_chat_member(chat_id=current_channel, user_id=user_id)
            if member.status in ['member', 'administrator', 'creator']:
                is_joined = True
        except:
            pass
            
        # 2. 🔥 യൂസർ നേരത്തെ ഈ ചാനലിലേക്ക് റിക്വസ്റ്റ് അയച്ചിട്ടുണ്ടോ എന്ന് ഡാറ്റാബേസിൽ നോക്കുന്നു
        has_requested = False
        if not is_joined and current_channel:
            db_check = requests_collection.find_one({
                'user_id': user_id, 
                'channel_id': current_channel, 
                'status': 'requested'
            })
            if db_check:
                has_requested = True

        # യൂസർ മെമ്പറും അല്ല, ഇതുവരെ റിക്വസ്റ്റും അയച്ചിട്ടില്ലെങ്കിൽ മാത്രം റിക്വസ്റ്റ് ചോദിക്കുക 👇
        if not is_joined and not has_requested:
            # യൂസർക്ക് ഏത് ബാച്ച് ഫയൽ ആണോ വേണ്ടത്, അത് ഡാറ്റാബേസിൽ താൽക്കാലികമായി കുറിച്ചു വെക്കുന്നു
            requests_collection.update_one(
                {'user_id': user_id, 'channel_id': current_channel},
                {'$set': {'batch_id': batch_id, 'status': 'pending'}},
                upsert=True
            )
            
            try:
                # ബോട്ട് സ്വന്തമായി ഒരു Join Request ഇൻവൈറ്റ് ലിങ്ക് നിർമ്മിക്കുന്നു 🔗
                chat_info = await context.bot.create_chat_invite_link(
                    chat_id=current_channel,
                    creates_join_request=True
                )
                invite_link = chat_info.invite_link
            except:
                invite_link = "https://t.me"

            keyboard = [[InlineKeyboardButton("📩 Request to Join Channel", url=invite_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "⚠️ **ഫയലുകൾ ലഭിക്കുന്നതിനായി താഴെ കാണുന്ന ചാനലിലേക്ക് Join Request അയക്കുക!**\n\n"
                "👇 *താഴെയുള്ള ബട്ടൺ അമർത്തി റിക്വസ്റ്റ് കൊടുക്കുന്ന നിമിഷം ബോട്ട് ഫയലുകൾ അയച്ചു തരും.*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

        # മെമ്പർ ആണെങ്കിലോ, അല്ലെങ്കിൽ നേരത്തെ റിക്വസ്റ്റ് അയച്ചിട്ടുണ്ടെങ്കിലോ നേരിട്ട് ഫയലുകൾ നൽകുന്നു 🚀
        batch_data = batch_collection.find_one({'batch_id': batch_id})
        if batch_data:
            from_chat = batch_data['from_chat']
            start_id = batch_data['start_id']
            end_id = batch_data['end_id']
            
            await update.message.reply_text("✨ **താങ്കൾ തിരഞ്ഞ ഫയലുകൾ താഴെ നൽകുന്നു!** 👇")
            for msg_id in range(start_id, end_id + 1):
                try:
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
        await update.message.reply_text("ഹലോ! ഞാൻ ഒരു അഡ്വാന്‍സ്ഡ് ജോയിൻ റിക്വസ്റ്റ് ഫീച്ചറുള്ള ഫയൽ ഷെയറിങ് ബോട്ട് ആണ്. 📂")



# /setchannel കമാൻഡ് (തിരുത്തിയ ഭാഗം 🛠️)
async def set_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text("⚠️ **രീതി:** `/setchannel [ചാനൽ_ഐഡി]`", parse_mode="Markdown")
        return

    try:
        # ലിസ്റ്റിലെ ആദ്യത്തെ വാല്യൂ [0] എടുത്ത് അതിനെ int ആക്കി മാറ്റുന്നു 👇
        new_channel_id = int(context.args[0])
        try:
            await context.bot.get_chat(new_channel_id)
        except TelegramError:
            await update.message.reply_text("❌ ബോട്ടിന് ഈ ചാനലിൽ പ്രവേശനമില്ല! ആദ്യം ബോട്ടിനെ ആ ചാനലിൽ **Admin** ആക്കുക.")
            return

        settings_collection.update_one({'_id': 'fsub_config'}, {'$set': {'channel_id': new_channel_id}}, upsert=True)
        requests_collection.delete_many({}) 
        
        await update.message.reply_text(
            f"✅ **റിക്വസ്റ്റ് ചാനൽ മാറ്റിയിരിക്കുന്നു!**\n🆔 ID: `{new_channel_id}`\n\n"
            f"🧹 _ഡാറ്റാബേസിലെ പഴയ ജോയിൻ റിക്വസ്റ്റുകൾ എല്ലാം വിജയകരമായി ക്ലിയർ ചെയ്തിട്ടുണ്ട്._", 
            parse_mode="Markdown"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("❌ തെറ്റായ ഐഡി ഫോർമാറ്റ്!")


# /broadcast കമാൻഡ്
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

    if not update.message.forward_date:
        await update.message.reply_text("⚠️ ദയവായി ഒരു ചാനലിൽ നിന്നും ഫയൽ **Forward** ചെയ്ത് അയക്കുക!")
        return
        
    chat_id = update.message.forward_from_chat.id if update.message.forward_from_chat else None
    msg_id = update.message.forward_from_message_id if update.message.forward_from_message_id else None
    
    if not chat_id or not msg_id:
        await update.message.reply_text("❌ ഈ ഫയലിൽ നിന്നും ചാനൽ ഡാറ്റ എടുക്കാൻ കഴിഞ്ഞില്ല. ചാനൽ പബ്ലിക് ആണെന്ന് ഉറപ്പാക്കുക.")
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
        batch_link = f"https://t.me/{bot_info.username}?start={batch_id}"
        
        await update.message.reply_text(f"✅ **Batch നിർമ്മിച്ചിരിക്കുന്നു!**\n🔗 **Batch ലിങ്ക്:** {batch_link}", parse_mode="HTML")
        del user_data_store[user_id]



# 📊 സ്റ്റാറ്റിസ്റ്റിക്സ് വിവരങ്ങൾ ശേഖരിക്കുന്ന ഫങ്ക്ഷൻ (ക്രാഷ് പ്രൊട്ടക്ഷൻ ഉൾപ്പെടുത്തിയത് 🛡️)
async def generate_stats_text() -> str:
    total_users = users_collection.count_documents({})
    total_batches = batch_collection.count_documents({})
    total_requests = requests_collection.count_documents({})
    current_channel = get_req_channel()

    try:
        used_db_space = get_db_size()
        if used_db_space is None:
            used_db_space = 0.0
    except:
        used_db_space = 0.0

    total_db_limit = 512.00
    remaining_db_space = max(0.0, total_db_limit - used_db_space)
    db_used_percentage = round((used_db_space / total_db_limit) * 100, 2)

    koyeb_ram_limit = int(os.getenv("KOYEB_INSTANCE_MEMORY_MB", 512))
    koyeb_instance_type = os.getenv("KOYEB_INSTANCE_TYPE", "nano")
    
    try:
        process = psutil.Process(os.getpid())
        bot_ram_used_bytes = process.memory_info().rss
        bot_ram_used_mb = round(bot_ram_used_bytes / (1024 * 1024), 2)
    except:
        bot_ram_used_mb = 0.0
    
    koyeb_remaining_ram = max(0.0, koyeb_ram_limit - bot_ram_used_mb)
    koyeb_used_percentage = round((bot_ram_used_mb / koyeb_ram_limit) * 100, 2)

    channel_text = f"`{current_channel}`" if current_channel else "സെറ്റ് ചെയ്തിട്ടില്ല ❌"

    text = (
        f"📊 **ബോട്ട് സ്റ്റാറ്റിസ്റ്റിക്സ് (Bot Stats)**\n\n"
        f"👤 **ആകെ ഉപയോക്താക്കൾ:** {total_users}\n"
        f"📦 **ആകെ ബാച്ച് ലിങ്കുകൾ:** {total_batches}\n"
        f"📩 **നിലവിലുള്ള ജോയിൻ റിക്വസ്റ്റുകൾ:** {total_requests}\n\n"
        
        f"💾 **ഡാറ്റാബേസ് വിവരങ്ങൾ (MongoDB):**\n"
        f" └ 📉 ഉപയോഗിച്ചത്: `{used_db_space} MB` ({db_used_percentage}%)\n"
        f" └ 📈 ബാക്കിയുള്ളത്: `{remaining_db_space} MB` / `512 MB`\n\n"
        
        f"🚀 **ഹോസ്റ്റിംഗ് വിവരങ്ങൾ (Koyeb):**\n"
        f" └ 🆔 ഇൻസ്റ്റൻസ് തരം: `{koyeb_instance_type.upper()}`\n"
        f" └ 📉 ബോട്ട് ഉപയോഗിക്കുന്ന റാം: `{bot_ram_used_mb} MB` ({koyeb_used_percentage}%)\n"
        f" └ 📈 ഹോസ്റ്റിംഗിൽ ബാക്കിയുള്ള റാം: `{koyeb_remaining_ram} MB` / `{koyeb_ram_limit} MB`\n\n"
        
        f"📢 **നിലവിലെ റിക്വസ്റ്റ് ചാനൽ ഐഡി:** {channel_text}"
    )
    return text

# /stats കമാൻഡ് വഴി ആദ്യം മെസ്സേജ് അയക്കുന്നു
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        return

    keyboard = [[InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    stats_text = await generate_stats_text()
    await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode="Markdown")

# ബട്ടൻ അമർത്തുമ്പോൾ മെസ്സേജ് എഡിറ്റ് ചെയ്യുന്ന ഫങ്ക്ഷൻ
async def stats_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != OWNER_ID:
        await query.answer("🔒 ക്ഷമിക്കണം, നിങ്ങൾക്ക് ഇതിന് അനുവാദമില്ല!", show_alert=True)
        return

    await query.answer("🔄 വിവരങ്ങൾ പുതുക്കുന്നു...")
    updated_text = await generate_stats_text()
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(text=updated_text, reply_markup=reply_markup, parse_mode="Markdown")
    except TelegramError:
        pass

