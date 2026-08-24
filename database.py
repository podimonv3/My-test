from pymongo import MongoClient
from info import MONGO_URI

try:
    client = MongoClient(MONGO_URI)
    db = client['telegram_advanced_bot']
    batch_collection = db['batches']
    requests_collection = db['join_requests']
    settings_collection = db['settings']
    users_collection = db['users']  # ബ്രോഡ്കാസ്റ്റിനായി ഉപയോക്താക്കളെ സൂക്ഷിക്കാൻ
    print("✅ MongoDB-യുമായി വിജയകരമായി കണക്ട് ചെയ്തിരിക്കുന്നു!")
except Exception as e:
    print(f"❌ MongoDB കണക്ഷൻ പരാജയപ്പെട്ടു: {e}")

def get_req_channel():
    config = settings_collection.find_one({'_id': 'fsub_config'})
    if config:
        return config.get('channel_id', 0)
    return 0

# പുതിയ ഉപയോക്താക്കളെ ഡാറ്റാബേസിൽ ചേർക്കാൻ
def add_user(user_id):
    users_collection.update_one({'_id': user_id}, {'$set': {'_id': user_id}}, upsert=True)


# 📊 ഡാറ്റാബേസിന്റെ സൈസ് മെഗാബൈറ്റിൽ (MB) കണക്കാക്കുന്ന ഫങ്ക്ഷൻ
def get_db_size():
    try:
        # db.command("dbstats") വഴി ഡാറ്റാബേസ് വിവരങ്ങൾ എടുക്കുന്നു
        stats = db.command("dbstats")
        # bytes-ൽ ലഭിക്കുന്ന സൈസിനെ MB-യിലേക്ക് മാറ്റുന്നു (1024 * 1024)
        data_size_mb = stats.get('dataSize', 0) / (1024 * 1024)
        return round(data_size_mb, 2)
    except Exception as e:
        print(f"Error getting DB stats: {e}")
        return 0.0

