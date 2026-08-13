import os
import time
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client["telegram_bot"]
users_collection = db["users"]

active_cache = {}

async def track_user(chat_id, user_id, name):
    if chat_id not in active_cache:
        active_cache[chat_id] = {}
    active_cache[chat_id][user_id] = {"time": time.time(), "name": name}

async def sync_db_loop():
    while True:
        await asyncio.sleep(60)
        for chat_id, users in list(active_cache.items()):
            if not users:
                continue
            
            for user_id, data in list(users.items()):
                await users_collection.update_one(
                    {"chat_id": chat_id, "user_id": user_id},
                    {"$set": {"last_active": data["time"], "name": data["name"]}},
                    upsert=True
                )
            users.clear()

async def get_recent_users(chat_id):
    cursor = users_collection.find({"chat_id": chat_id}).sort("last_active", -1)
    documents = await cursor.to_list(length=None)
    return [{"id": doc["user_id"], "name": doc.get("name", "User")} for doc in documents]

async def get_total_users():
    return await users_collection.count_documents({})
