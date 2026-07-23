import telebot
import os
import time
import requests
import yt_dlp
import re
from telebot import types
from threading import Thread
from flask import Flask

# === CONFIGURATION ===
TOKEN = "6408951604:AAEe4eNxFH8m_z4zOrGBMiGRwb3rJvfx0tA"
ADMIN_ID = 5712986255  # Admin ID
BOT_NAME = "@lorifufuMusicBot"
CHANNEL_LINK = "https://t.me/Renji_still_living"
CREDIT_LINK = "https://t.me/Renji_still_living"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# === FLASK WEB SERVER (Render Port Fix) ===
app = Flask(__name__)

@app.route('/')
def hello():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# === DATA PERSISTENCE ===
USERS_FILE = "users.txt"
MAINTENANCE_FILE = "maintenance.txt"

def get_users():
    if not os.path.exists(USERS_FILE): return set()
    with open(USERS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def add_user(user_id):
    users = get_users()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

def is_maintenance():
    if not os.path.exists(MAINTENANCE_FILE): return False
    with open(MAINTENANCE_FILE, "r") as f:
        return f.read().strip() == "on"

def set_maintenance(state):
    with open(MAINTENANCE_FILE, "w") as f:
        f.write("on" if state else "off")

def get_role(user_id):
    return "Sir" if user_id == ADMIN_ID else "User"

# === KEYBOARDS ===
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Search Music", "📊 My Stats")
    markup.add("📜 About", "⚙️ Admin Panel")
    return markup

# === SEARCH LOGIC ===
def search_yt(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Using ytsearch5 to get specific results
            results = ydl.extract_info(f"ytsearch5:{query}", download=False)['entries']
            return results
        except Exception as e:
            print(f"Search Error: {e}")
            return []

# === HANDLERS ===

@bot.message_handler(commands=['start'])
def welcome(message):
    add_user(message.from_user.id)
    role = get_role(message.from_user.id)
    
    if is_maintenance() and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "🛠 *Maintenance Mode*\n\nThe bot is currently under maintenance. Please try again later.")
        return
        
    welcome_text = (
        f"👋 Hello {role} {message.from_user.first_name}!\n\n"
        f"Welcome to *{BOT_NAME}*.\nI can help you find and download your favorite music and videos from YouTube with high quality.\n\n"
        f"💎 Developed by: [lorifufu]({CREDIT_LINK})"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard(), disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == "🎵 Search Music")
def ask_search(message):
    role = get_role(message.from_user.id)
    bot.send_message(message.chat.id, f"🔎 Please enter the song name or artist you want to find, {role}.")

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def user_stats(message):
    bot.reply_to(message, f"👤 *Account Statistics*\n\nYour ID: `{message.from_user.id}`\nStatus: {get_role(message.from_user.id)}\n\nYou have explored many tracks with {BOT_NAME}!")

@bot.message_handler(func=lambda m: m.text == "📜 About")
def about_bot(message):
    bot.reply_to(message, f"🤖 *About {BOT_NAME}*\n\nA professional YouTube downloader bot designed for aesthetic and high-speed performance.\n\nSupport: {CHANNEL_LINK}")

@bot.message_handler(commands=['admin'])
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel")
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Access Denied. This section is restricted to Admin only.")
        return
    m_status = "ON 🔴" if is_maintenance() else "OFF 🟢"
    markup = types.InlineKeyboardMarkup()
    btn_m = types.InlineKeyboardButton(f"Maintenance: {m_status}", callback_data="toggle_m")
    btn_s = types.InlineKeyboardButton("📊 Global Stats", callback_data="bot_stats")
    btn_b = types.InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")
    markup.add(btn_m)
    markup.add(btn_s, btn_b)
    bot.send_message(message.chat.id, "🛠 *Admin Control Panel*\n\nPlease select an action, Sir.", reply_markup=markup)

# === BROADCAST LOGIC ===
def start_broadcast(message):
    users = get_users()
    count = 0
    fail = 0
    status_msg = bot.send_message(ADMIN_ID, "🚀 *Broadcasting started...*")
    
    for user_id in users:
        try:
            bot.copy_message(user_id, ADMIN_ID, message.message_id)
            count += 1
            time.sleep(0.3)
        except:
            fail += 1
    
    bot.edit_message_text(f"✅ *Broadcast Complete*\n\n📬 Success: {count}\n❌ Failed: {fail}", ADMIN_ID, status_msg.message_id)

# === CALLBACK QUERY HANDLER ===
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # Fix Truncated ID: Split carefully
    if call.data.startswith("vid:"):
        vid_id = call.data.replace("vid:", "")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎧 MP3 (Audio)", callback_data=f"aud:{vid_id}"),
                   types.InlineKeyboardButton("🎬 MP4 (Video)", callback_data=f"vdo:{vid_id}"))
        bot.edit_message_text("💾 Choose your preferred format:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("aud:") or call.data.startswith("vdo:"):
        type_dl = "a" if call.data.startswith("aud:") else "v"
        vid_id = call.data.replace("aud:", "").replace("vdo:", "")
        url = f"https://www.youtube.com/watch?v={vid_id}"
        
        status_msg = bot.send_message(call.message.chat.id, "⏳ [▱▱▱▱▱▱▱▱▱▱] 0%\nPreparing your request...")
        
        def download_task():
            last_update_time = 0
            def progress_hook(d):
                nonlocal last_update_time
                if d['status'] == 'downloading':
                    # Extract percentage safely
                    p_str = d.get('_percent_str', '0%')
                    p_clean = re.sub(r'\x1b\[[0-9;]*m', '', p_str).replace('%', '').strip()
                    try:
                        percent = float(p_clean)
                    except:
                        percent = 0
                    
                    # Anti-Jump & Throttling (Every 3 seconds)
                    if time.time() - last_update_time > 3:
                        filled = int(percent / 10)
                        bar = "▰" * filled + "▱" * (10 - filled)
                        try:
                            bot.edit_message_text(f"🚀 Downloading: [{bar}] {int(percent)}%\n\nPlease wait while I process the file.", call.message.chat.id, status_msg.message_id)
                        except: pass
                        last_update_time = time.time()

            try:
                if not os.path.exists("downloads"): os.makedirs("downloads")
                
                ydl_opts = {
                    'format': 'bestaudio/best' if type_dl == 'a' else 'best[ext=mp4]/best',
                    'outtmpl': f'downloads/%(title)s_{vid_id}.%(ext)s',
                    'quiet': True,
                    'no_warnings': True,
                    'progress_hooks': [progress_hook],
                    'socket_timeout': 30,
                    'retries': 10,
                }
                
                # Add cookies if available
                if os.path.exists('cookies.txt'):
                    ydl_opts['cookiefile'] = 'cookies.txt'
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    title = info.get('title', 'Unknown Title')

                bot.edit_message_text("✅ [▰▰▰▰▰▰▰▰▰▰] 100%\nUploading to Telegram...", call.message.chat.id, status_msg.message_id)
                
                with open(filename, 'rb') as f:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📜 Show Lyrics", callback_data=f"lyr:{vid_id}"))
                    caption = f"✅ *Download Complete*\n\n🎵 *Title:* {title}\n🏷 *Source:* {BOT_NAME}\n💎 *Dev:* [lorifufu]({CREDIT_LINK})"
                    
                    if type_dl == 'a':
                        bot.send_audio(call.message.chat.id, f, caption=caption, reply_markup=markup, parse_mode="Markdown")
                    else:
                        bot.send_video(call.message.chat.id, f, caption=caption, reply_markup=markup, parse_mode="Markdown")
                
                bot.delete_message(call.message.chat.id, status_msg.message_id)
                if os.path.exists(filename): os.remove(filename)
            except Exception as e:
                bot.edit_message_text(f"❌ *Connection Error:* {str(e)}\n\nTry searching again or use a different link.", call.message.chat.id, status_msg.message_id)
        
        Thread(target=download_task).start()

    elif call.data.startswith("lyr:"):
        # Aesthetic Lyrics Animation Fix
        lyrics = [
            "✨ Just close your eyes and enjoy the vibe...",
            "🌌 Lost in the melody of this beautiful track.",
            "🎧 Music is the only escape without leaving home.",
            "💫 Every note tells a story of its own.",
            "🌙 Healing the soul with every rhythm.",
            "🌊 Let the music wash away your worries.",
            "⭐ Perfect sound for a perfect moment.",
            "🌿 Simplicity is the ultimate sophistication.",
            "🔥 Feel the energy in every beat.",
            "💎 Developed by @lorifufu with love."
        ]
        
        msg = bot.send_message(call.message.chat.id, "📜 *Fetching Lyrics...*")
        for line in lyrics:
            time.sleep(1.5)
            try:
                bot.edit_message_text(f"📜 *Lyrics*\n\n{line}", call.message.chat.id, msg.message_id)
            except: break
        
        # Final credit with link
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 Join Channel", url=CREDIT_LINK))
        bot.edit_message_text(f"📜 *Lyrics Animation Complete*\n\n💎 Developed by [@lorifufu]({CREDIT_LINK})", call.message.chat.id, msg.message_id, reply_markup=markup, disable_web_page_preview=True)

    elif call.data == "toggle_m":
        new_state = not is_maintenance()
        set_maintenance(new_state)
        status = "ON 🔴" if new_state else "OFF 🟢"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"Maintenance: {status}", callback_data="toggle_m"))
        markup.add(types.InlineKeyboardButton("📊 Global Stats", callback_data="bot_stats"),
                   types.InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"))
        bot.edit_message_text("🛠 *Admin Control Panel*\n\nMaintenance status updated successfully, Sir.", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "bot_stats":
        count = len(get_users())
        bot.answer_callback_query(call.id, f"Total Registered Users: {count}", show_alert=True)
    
    elif call.data == "broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Please send the message you want to broadcast to all users, Sir.")
        bot.register_next_step_handler(msg, start_broadcast)

# === SEARCH HANDLER ===
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    add_user(message.from_user.id)
    role = get_role(message.from_user.id)
    
    if is_maintenance() and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "🛠 *Maintenance Mode is currently active.*")
        return
        
    query = message.text
    if query.startswith("/") or query in ["🎵 Search Music", "📊 My Stats", "📜 About", "⚙️ Admin Panel"]:
        return

    status = bot.reply_to(message, f"🔎 Searching for '{query}'...")
    results = search_yt(query)
    
    if not results:
        bot.edit_message_text("❌ No results found. Please try a different keyword.", message.chat.id, status.message_id)
        return
        
    markup = types.InlineKeyboardMarkup()
    for item in results:
        # Avoid empty IDs
        if not item.get('id'): continue
        title = (item['title'][:45] + '..') if len(item['title']) > 45 else item['title']
        # Shortening callback to prevent truncation
        markup.add(types.InlineKeyboardButton(f"🎥 {title}", callback_data=f"vid:{item['id']}"))
        
    bot.edit_message_text(f"🎼 *Search Results for:* '{query}'\n\nSelect a track to download, {role}:", message.chat.id, status.message_id, reply_markup=markup)

if __name__ == "__main__":
    if not os.path.exists("downloads"): os.makedirs("downloads")
    print("\n--- LORIFUFU MUSIC BOT V3 ULTIMATE PRO ---")
    print("Status: Running...")
    
    # Start Flask web server in a separate thread (for Render port detection)
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    
    # Start bot polling in main thread
    bot.infinity_polling(skip_pending=True, timeout=90, long_polling_timeout=90)
