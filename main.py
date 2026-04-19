import os, subprocess, threading, time
import telebot
from flask import Flask

# ====== ENV ======
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

bot = telebot.TeleBot(TOKEN)

# ====== KEEP ALIVE ======
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Running 24/7 ✅"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# ====== STORAGE ======
BASE = "user_files"
os.makedirs(BASE, exist_ok=True)

running = {}

# ====== START ======
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "✅ Bot Running Successfully!")

# ====== UPLOAD ======
@bot.message_handler(content_types=['document'])
def upload(msg):
    user_id = msg.from_user.id
    file_info = bot.get_file(msg.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    user_dir = f"{BASE}/{user_id}"
    os.makedirs(user_dir, exist_ok=True)

    path = f"{user_dir}/{msg.document.file_name}"
    with open(path, "wb") as f:
        f.write(downloaded)

    bot.reply_to(msg, f"✅ Uploaded: {msg.document.file_name}")

# ====== RUN FILE ======
@bot.message_handler(func=lambda m: m.text and m.text.startswith("run"))
def run_file(msg):
    user_id = msg.from_user.id
    try:
        file_name = msg.text.split(" ")[1]
    except:
        bot.reply_to(msg, "❌ Use: run filename.py")
        return

    path = f"{BASE}/{user_id}/{file_name}"

    if not os.path.exists(path):
        bot.reply_to(msg, "❌ File not found")
        return

    def runner():
        while True:
            try:
                p = subprocess.Popen(["python", path])
                running[path] = p
                p.wait()
                time.sleep(3)  # auto restart
            except:
                time.sleep(5)

    threading.Thread(target=runner).start()

    bot.reply_to(msg, f"▶ Running {file_name} with auto-restart ♻️")

# ====== STOP ======
@bot.message_handler(func=lambda m: m.text and m.text.startswith("stop"))
def stop(msg):
    user_id = msg.from_user.id
    file_name = msg.text.split(" ")[1]
    path = f"{BASE}/{user_id}/{file_name}"

    if path in running:
        running[path].kill()
        del running[path]
        bot.reply_to(msg, "🛑 Stopped")
    else:
        bot.reply_to(msg, "❌ Not running")

# ====== FILE LIST ======
@bot.message_handler(func=lambda m: m.text == "files")
def files(msg):
    user_id = msg.from_user.id
    user_dir = f"{BASE}/{user_id}"

    if not os.path.exists(user_dir):
        bot.reply_to(msg, "❌ No files")
        return

    files = os.listdir(user_dir)
    if not files:
        bot.reply_to(msg, "❌ Empty")
    else:
        bot.reply_to(msg, "\n".join(files))

# ====== DELETE ======
@bot.message_handler(func=lambda m: m.text and m.text.startswith("del"))
def delete(msg):
    user_id = msg.from_user.id
    file_name = msg.text.split(" ")[1]
    path = f"{BASE}/{user_id}/{file_name}"

    if os.path.exists(path):
        os.remove(path)
        bot.reply_to(msg, "🗑 Deleted")
    else:
        bot.reply_to(msg, "❌ Not found")

# ====== RUN ======
print("Bot Started...")
bot.infinity_polling()
