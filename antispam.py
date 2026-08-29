import re
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, MessageHandler, filters

# ⚠️ നിങ്ങളുടെ ലോഗ് ചാനലിന്റെ ID ഇവിടെ നൽകുക (ID-ക്ക് മുന്നിൽ -100 ഉണ്ടായിരിക്കണം)
LOG_CHANNEL_ID = -1003851866517  

# നിങ്ങൾ നൽകിയ വാക്കുകൾ മാത്രം കണ്ടെത്താനുള്ള പുതിയ പാറ്റേൺ
BAD_WORDS_PATTERN = re.compile(
    r'(xvideos|xnxxn|xnxx|xhamster|xxx videos|തുണ്ട്|porn\s*videos)', 
    re.IGNORECASE
)

# സ്പാമർമാർ ഉപയോഗിക്കുന്ന 18+ ഇമോജികളുടെ ലിസ്റ്റ്
ADULT_EMOJIS = ["🍑", "🍆", "🍌", "💦", "💋", "👙", "🔞", "🥵", "👅"]

async def anti_spam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # സാധാരണ ടെക്സ്റ്റ് മെസ്സേജുകൾ അല്ലെങ്കിലോ മെസ്സേജ് ഇല്ലെങ്കിലോ ഒഴിവാക്കുക
    if not update.message or not update.message.text:
        return

    message_text = update.message.text
    user = update.effective_user
    chat = update.effective_chat

    # ഗ്രൂപ്പ് അഡ്മിൻമാർ അയക്കുന്ന മെസ്സേജ് ആണെങ്കിൽ ബോട്ട് ഒന്നും ചെയ്യില്ല
    try:
        member = await chat.get_member(user.id)
        if member.status in ['creator', 'administrator']:
            return
    except Exception as e:
        print(f"അഡ്മിൻ ചെക്കിങ് പരാജയപ്പെട്ടു: {e}")
        return

    # മെസ്സേജിൽ 18+ ഇമോജികൾ ഉണ്ടോ എന്ന് പരിശോധിക്കുന്നു
    has_adult_emoji = any(emoji in message_text for emoji in ADULT_EMOJIS)

    # വാക്കുകളോ, ലിങ്കുകളോ, അല്ലെങ്കിൽ 18+ ഇമോജികളോ ഉണ്ടോ എന്ന് പരിശോധിക്കുന്നു
    if BAD_WORDS_PATTERN.search(message_text) or "t.me/+" in message_text or "t.me/joinchat" in message_text or has_adult_emoji:
        
        # 1. മെസ്സേജ് അയച്ചയാളെ ഗ്രൂപ്പിൽ Mute ചെയ്യുന്നു 
        try:
            mute_permissions = ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
            await chat.restrict_member(user_id=user.id, permissions=mute_permissions)
        except Exception as e:
            print(f"യൂസറെ മ്യൂട്ട് ചെയ്യാൻ സാധിച്ചില്ല: {e}")

        # 2. യൂസറുടെ പ്രൊഫൈൽ ലിങ്ക് (PM Link) തയ്യാറാക്കുന്നു
        if user.username:
            pm_link = f"https://t.me/{user.username}"
        else:
            pm_link = f"tg://user?id={user.id}"

        # 3. ചാനലിലേക്ക് അയക്കാനുള്ള ലോഗ് റിപ്പോർട്ട് തയ്യാറാക്കുന്നു
        report_text = (
            "🚨 **18+ Spam Mute Report** 🚨\n\n"
            f"👤 **പേര്:** {user.full_name}\n"
            f"🆔 **Telegram ID:** `{user.id}`\n"
            f"🔗 **PM Link:** [ഇവിടെ ക്ലിക്ക് ചെയ്യുക]({pm_link})\n"
            f"💬 **വന്ന ഗ്രൂപ്പ്:** {chat.title}\n\n"
            f"📝 **അയച്ച സ്പാം മെസ്സേജ്:**\n_{message_text}_"
        )

        # 4. ചാനലിലേക്ക് റിപ്പോർട്ട് മെസ്സേജ് അയക്കുന്നു
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID, 
                text=report_text, 
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"ചാനലിലേക്ക് റിപ്പോർട്ട് അയക്കാൻ കഴിഞ്ഞില്ല: {e}")

# ഈ ഫയൽ അപ്ലിക്കേഷനിലേക്ക് എളുപ്പം ലോഡ് ചെയ്യാനുള്ള ഫങ്ക്ഷൻ
def register_antispam(application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam_handler))

