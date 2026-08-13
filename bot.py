import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import database

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OWNER = os.getenv("OWNER_NAME", "Admin")
REPO = os.getenv("REPO_URL", "https://github.com/repo")
VERSION = "1.0.0"

bot = Bot(token=TOKEN)
dp = Dispatcher()

active_mentions = {}
admin_cache = {}

async def is_admin(chat_id, user_id):
    if chat_id not in admin_cache:
        try:
            admins = await bot.get_chat_administrators(chat_id)
            admin_cache[chat_id] = [admin.user.id for admin in admins]
        except:
            return False
    return user_id in admin_cache[chat_id]

triggers = ('/all', '@all', '#all', '/mentionall', '@mentionall', '#mentionall')

@dp.message(lambda msg: msg.text and any(msg.text.startswith(t) for t in triggers))
async def handle_all_command(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Start Mentioning", callback_data="start_mention", style="primary"),
            InlineKeyboardButton(text="Cancel", callback_data="cancel_mention", style="danger")
        ]
    ])
    await message.reply("Choose an action.", reply_markup=kb)

@dp.callback_query(F.data.in_({"start_mention", "cancel_mention"}))
async def mention_callback(call: CallbackQuery):
    chat_id = call.message.chat.id
    if not await is_admin(chat_id, call.from_user.id):
        await call.answer("Only admins can access this.", show_alert=True)
        return

    if call.data == "cancel_mention":
        active_mentions[chat_id] = False
        await call.answer("Cancelled setup.", show_alert=True)
        await call.message.delete()
        return

    if active_mentions.get(chat_id):
        await call.answer("Process already running.", show_alert=True)
        return

    active_mentions[chat_id] = True
    await call.message.edit_text("Mentioning started.")
    await call.answer()
    
    users = await database.get_recent_users(chat_id)
    
    for i in range(0, len(users), 5):
        if not active_mentions.get(chat_id):
            break
            
        chunk = users[i:i+5]
        mentions = [f"<a href='tg://user?id={u['id']}'>{u['name']}</a>" for u in chunk]
                
        if mentions:
            text = " ".join(mentions)
            await bot.send_message(chat_id, text, parse_mode="HTML")
            
        await asyncio.sleep(2)
        
    active_mentions[chat_id] = False
    try:
        await bot.send_message(chat_id, "Mentioning finished.")
    except:
        pass

@dp.message(Command("cancel"))
async def handle_cancel_cmd(message: Message):
    chat_id = message.chat.id
    if active_mentions.get(chat_id):
        if await is_admin(chat_id, message.from_user.id):
            active_mentions[chat_id] = False
            try:
                await message.delete()
            except:
                pass

@dp.message(Command("start"))
async def handle_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Help", callback_data="help", style="primary"),
            InlineKeyboardButton(text="About Me", callback_data="about", style="primary")
        ]
    ])
    await message.reply("Welcome to Mention Bot.", reply_markup=kb)

@dp.callback_query(F.data.in_({"help", "about", "start"}))
async def start_callbacks(call: CallbackQuery):
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Back", callback_data="start", style="primary")]
    ])
    
    if call.data == "help":
        await call.message.edit_text("I track active users.\nAdmins can use /all to mention them.", reply_markup=back_kb)
    elif call.data == "about":
        count = await database.get_total_users()
        text = f"Owner: {OWNER}\nRepo: {REPO}\nTracked Users: {count}\nVersion: {VERSION}"
        await call.message.edit_text(text, reply_markup=back_kb)
    elif call.data == "start":
        main_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Help", callback_data="help", style="primary"),
                InlineKeyboardButton(text="About Me", callback_data="about", style="primary")
            ]
        ])
        await call.message.edit_text("Welcome to Mention Bot.", reply_markup=main_kb)
    await call.answer()

@dp.message()
async def track_activity(message: Message):
    if message.chat.type in ['group', 'supergroup'] and message.from_user:
        await database.track_user(message.chat.id, message.from_user.id, message.from_user.first_name)

async def main():
    asyncio.create_task(database.sync_db_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
