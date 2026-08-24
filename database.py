from pymongo import MongoClient
from info import MONGO_URI

try:
    client = MongoClient(MONGO_URI)
    db = client['telegram_modular_bot']
    batch_collection = db['batches']
    requests_collection = db['join_requests']
    settings_collection = db['settings']
    print("✅ MongoDB-യുമായി വിജയകരമായി കണക്ട് ചെയ്തിരിക്കുന്നു!")
except Exception as e:
    print(f"❌ MongoDB കണക്ഷൻ പരാജയപ്പെട്ടു: {e}")

def get_req_channel():
    config = settings_collection.find_one({'_id': 'fsub_config'})
    if config:
        return config.get('channel_id', 0)
    return 0

