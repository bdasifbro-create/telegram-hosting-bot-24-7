# -*- coding: utf-8 -*-
import os
import subprocess
import telebot
from telebot import types
from flask import Flask
from threading import Thread
import threading
import time
import psutil

# ===== CONFIG =====
TOKEN = os.getenv("8428961340:AAFeK6DiwDb1NV-mHE1R3_W7toblmd_WeIM")
OWNER_ID = 8627605535

bot = telebot.TeleBot(TOKEN)

BASE = "files"
os.makedirs(BASE, exist_ok=True)

running_processes = {}
restart_count = {}

# ===== KEEP ALIVE =====
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Alive 24/7"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# ===== MENU =====
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📤 Upload", "📂 Files")
    kb.add("▶️ Run", "⛔ Stop")
    kb.add("🗑 Delete", "📊 Running")
    kb.add("📈 Stats")
    return kb

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    if msg.from_user.id != OWNER_ID:
        return bot.reply_to(msg, "❌ Not allowed")
    bot.send_message(msg.chat.id, "🚀 PRO Hosting Bot Ready", reply_markup=menu())

# ===== UPLOAD =====
@bot.message_handler(content_types=['document'])
def upload(msg):
    file = bot.get_file(msg.document.file_id)
    data = bot.download_file(file.file_path)

    path = os.path.join(BASE, msg.document.file_name)
    with open(path, "wb") as f:
        f.write(data)

    bot.reply_to(msg, f"✅ Uploaded: {msg.document.file_name}")

# ===== FILE LIST =====
@bot.message_handler(func=lambda m: m.text == "📂 Files")
def files(msg):
    f = os.listdir(BASE)
    bot.send_message(msg.chat.id, "\n".join(f) if f else "❌ No files")

# ===== AUTO RESTART =====
def monitor_process(file, chat_id):
    while file in running_processes:
        proc = running_processes.get(file)

        if proc is None:
            break

        if proc.poll() is not None:
            restart_count[file] = restart_count.get(file, 0) + 1

            if restart_count[file] > 5:
                bot.send_message(chat_id, f"❌ {file} stopped (max restart limit reached)")
                del running_processes[file]
                break

            bot.send_message(chat_id, f"♻️ Restarting {file} ({restart_count[file]}/5)")

            try:
                path = os.path.join(BASE, file)

                new_proc = subprocess.Popen(
                    ["python", path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                running_processes[file] = new_proc

            except Exception as e:
                bot.send_message(chat_id, f"❌ Restart error: {e}")
                break

        time.sleep(3)

# ===== RUN =====
@bot.message_handler(func=lambda m: m.text == "▶️ Run")
def run_menu(msg):
    files = os.listdir(BASE)

    if not files:
        return bot.reply_to(msg, "❌ No file")

    kb = types.InlineKeyboardMarkup()
    for f in files:
        kb.add(types.InlineKeyboardButton(f"▶️ {f}", callback_data=f"run_{f}"))

    bot.send_message(msg.chat.id, "Select file:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("run_"))
def run_file(call):
    file = call.data.replace("run_", "")
    path = os.path.join(BASE, file)

    if file in running_processes:
        return bot.answer_callback_query(call.id, "Already running")

    process = subprocess.Popen(
        ["python", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    running_processes[file] = process
    restart_count[file] = 0

    threading.Thread(target=monitor_process, args=(file, call.message.chat.id), daemon=True).start()

    bot.edit_message_text(f"🟢 Running: {file}",
        call.message.chat.id, call.message.message_id)

# ===== STOP =====
@bot.message_handler(func=lambda m: m.text == "⛔ Stop")
def stop_menu(msg):
    if not running_processes:
        return bot.reply_to(msg, "❌ No running")

    kb = types.InlineKeyboardMarkup()
    for f in running_processes:
        kb.add(types.InlineKeyboardButton(f"⛔ {f}", callback_data=f"stop_{f}"))

    bot.send_message(msg.chat.id, "Stop file:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def stop_file(call):
    file = call.data.replace("stop_", "")

    proc = running_processes.get(file)
    if proc:
        proc.kill()
        del running_processes[file]

    bot.edit_message_text(f"⛔ Stopped: {file}",
        call.message.chat.id, call.message.message_id)

# ===== DELETE =====
@bot.message_handler(func=lambda m: m.text == "🗑 Delete")
def delete_menu(msg):
    files = os.listdir(BASE)

    kb = types.InlineKeyboardMarkup()
    for f in files:
        kb.add(types.InlineKeyboardButton(f"❌ {f}", callback_data=f"del_{f}"))

    bot.send_message(msg.chat.id, "Delete file:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def delete_file(call):
    file = call.data.replace("del_", "")
    path = os.path.join(BASE, file)

    if file in running_processes:
        running_processes[file].kill()
        del running_processes[file]

    if os.path.exists(path):
        os.remove(path)

    bot.edit_message_text(f"🗑 Deleted: {file}",
        call.message.chat.id, call.message.message_id)

# ===== RUNNING =====
@bot.message_handler(func=lambda m: m.text == "📊 Running")
def running(msg):
    if not running_processes:
        return bot.reply_to(msg, "❌ None running")

    text = "🟢 Running:\n"
    for f in running_processes:
        text += f"• {f}\n"

    bot.send_message(msg.chat.id, text)

# ===== STATS =====
@bot.message_handler(func=lambda m: m.text == "📈 Stats")
def stats(msg):
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    bot.send_message(msg.chat.id, f"⚡ CPU: {cpu}%\n💾 RAM: {ram}%")

# ===== RUN BOT =====
if __name__ == "__main__":
    print("🚀 PRO Bot Running 24/7...")
    bot.infinity_polling()
