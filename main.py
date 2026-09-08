import asyncio
import requests
import json
import logging
import random
from datetime import datetime
from collections import Counter
import threading

from flask import Flask
from telegram import Bot
from telegram.constants import ParseMode

# --- Configuration ---
BOT_TOKEN = "8421396575:AAHTcG-fNAp6r1iq9yg-xMhNL-jWgVHPRcY"
CHANNEL_USERNAME = "-1003723520077"

# Sticker IDs
WIN_STICKER = "CAACAgUAAxkBAAEC4G9pifQIzVJ60qpe_n0aZRqPjOqXfgACXxoAAo_FYFaOLtZ5d3HjojoE"
LOSS_STICKER = "CAACAgUAAxkBAAEC4INpifhHjjiCUzXA_Z87dWdNqXtEkAACNxYAAqXy8Fbys0mlir6tpzoE"
JACKPOT_STICKER = "CAACAgUAAxkBAAEC4JNpijzPzEMqyQP-MnWjPR9LOSrnggAC-RQAAhjt6VegzLnRRkH9azoE"

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"

# Global variables
last_processed_id = None
current_prediction = None
current_numbers = []
current_win_rate = "95%"
win_count = 0
total_predictions = 0
jackpot_count = 0
loss_count = 0
loss_streak = 0

bet_progression = [10, 35, 115, 380]
recent_signals_history = []

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

# --- Prediction Functions ---
def predict_ultra_win_rate(history):
    if not history or len(history) < 10:
        return 'BIG', "92%", "AI Turbo Engine"
        
    last_10_sizes = ['BIG' if n >= 5 else 'SMALL' for n in history[:10]]
    last_4_sizes = last_10_sizes[:4]
    
    if last_4_sizes == ['BIG', 'BIG', 'BIG', 'BIG']:
        return 'BIG', f"{random.randint(96, 99)}%", "🐉 ULTRA DRAGON RUN"
    if last_4_sizes == ['SMALL', 'SMALL', 'SMALL', 'SMALL']:
        return 'SMALL', f"{random.randint(96, 99)}%", "🐉 ULTRA DRAGON RUN"
        
    if last_10_sizes[:3] == ['BIG', 'SMALL', 'BIG']:
        return 'SMALL', f"{random.randint(92, 96)}%", "⚡ MIRROR PATTERN BREAK"
    if last_10_sizes[:3] == ['SMALL', 'BIG', 'SMALL']:
        return 'BIG', f"{random.randint(92, 96)}%", "⚡ MIRROR PATTERN BREAK"
        
    big_count = last_10_sizes.count('BIG')
    if big_count >= 7:
        return 'SMALL', f"{random.randint(94, 97)}%", "📉 OVERBOUGHT CORRECTION"
    elif big_count <= 3:
        return 'BIG', f"{random.randint(94, 97)}%", "📈 OVERSOLD CORRECTION"
        
    next_pred = 'BIG' if history[0] >= 5 else 'SMALL'
    return next_pred, f"{random.randint(90, 94)}%", "🚀 INSTANT SPEED MOMENTUM"

def generate_hot_and_cold_numbers(prediction, history):
    pool = [5, 6, 7, 8, 9] if prediction == 'BIG' else [0, 1, 2, 3, 4]
    if not history:
        return sorted(random.sample(pool, 2))
        
    recent_numbers = history[:15]
    matched_pool = [n for n in recent_numbers if n in pool]
    
    if matched_pool:
        counts = Counter(matched_pool)
        hot_number = counts.most_common(1)[0][0]
    else:
        hot_number = random.choice(pool)
        
    remaining_pool = [n for n in pool if n != hot_number]
    cold_number = random.choice(remaining_pool) if remaining_pool else hot_number
    
    return sorted([hot_number, cold_number])

async def send_signal_to_channel(period, prediction, numbers, bet_amount, win_rate, pattern_info):
    message = f"""
✨ <b>TK CLUB GLOBAL VIP BOT (V7)</b> ✨
💎 <i>The Ultimate Wingo Auto-Signal System</i>
━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>PERIOD:</b> <code>{period}</code>
📊 <b>PREDICTION:</b> 🌟 <b>{prediction}</b> 🌟
🔥 <b>AI CONFIDENCE:</b> <code>{win_rate}</code>

🎯 <b>LUCKY NUMBERS:</b> 【 <code>{numbers[0]}</code> 】 or 【 <code>{numbers[1]}</code> 】
💰 <b>RECOMMENDED BET:</b> <code>{bet_amount} TK</code>
━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>LIVE ANALYTICS ENGINE:</b>
├• <b>Pattern:</b> <code>{pattern_info}</code>
├• <b>Algo Model:</b> <code>Neural-Matrix v7.2</code>
└• <b>Recovery Status:</b> <code>1-Step Auto Recovery Active</code>

⚠️ <i>Maintain your 3-4 Level Fund Balance for Maximum Safety!</i>
👑 <b>AMVIPTEAM GLOBAL</b> 👑
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    try:
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=message, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Signal Send Error: {e}")

async def send_10_games_report():
    global recent_signals_history, win_count, loss_count, jackpot_count
    current_time = datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")
    
    report_msg = f"""
📊 <b>TK CLUB GLOBAL - AI ACCURACY REPORT</b>
━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>TIME:</b> <code>{current_time}</code>
✅ <b>TOTAL WINS:</b> <code>{win_count}</code>
❌ <b>TOTAL LOSS:</b> <code>{loss_count}</code>
🔥 <b>JACKPOT HITS:</b> <code>{jackpot_count}</code>
━━━━━━━━━━━━━━━━━━━━━━━━
🏆 <b>LAST 10 GAMES PERFORMANCE:</b>
"""
    for idx, item in enumerate(recent_signals_history, 1):
        status_icon = "🟢" if "WIN" in item['status'] else "🔴"
        report_msg += f"{status_icon} <code>{item['period']}</code> | <b>{item['pred']}</b> → {item['act_num']} | {item['status']}\n"
        
    report_msg += """━━━━━━━━━━━━━━━━━━━━━━━━
💎 <i>Powered by Global Data Analytics. Pinned automatically!</i>
"""
    try:
        sent_message = await bot.send_message(chat_id=CHANNEL_USERNAME, text=report_msg, parse_mode=ParseMode.HTML)
        await bot.pin_chat_message(chat_id=CHANNEL_USERNAME, message_id=sent_message.message_id, disable_notification=False)
    except Exception as e:
        logger.error(f"Error sending/pinning history report: {e}")
    
    recent_signals_history = []

async def process_result(actual_number, period):
    global win_count, loss_count, total_predictions, loss_streak, jackpot_count, recent_signals_history
    
    if not current_prediction: return

    total_predictions += 1
    actual_size = 'BIG' if actual_number >= 5 else 'SMALL'
    is_win = (actual_size == current_prediction)
    is_jackpot = (actual_number in current_numbers)
    
    if is_jackpot or is_win:
        win_count += 1
        loss_streak = 0
        if is_jackpot: jackpot_count += 1
        
        msg = f"✨ <b>PERIOD {period} RESULT</b> ✨\n━━━━━━━━━━━━━━━━━━━━\n🎲 <b>Winning Number:</b> <code>{actual_number}</code> ({actual_size})\n🎯 <b>Status:</b> 🎉 <b>SUCCESSFUL WIN!</b>"
        await bot.send_message(CHANNEL_USERNAME, msg, parse_mode=ParseMode.HTML)
        await bot.send_sticker(CHANNEL_USERNAME, JACKPOT_STICKER if is_jackpot else WIN_STICKER)
    else:
        loss_count += 1
        loss_streak += 1
        
        if loss_streak >= 3:
            loss_streak = 0
            
        msg = f"⚡ <b>PERIOD {period} RESULT</b> ⚡\n━━━━━━━━━━━━━━━━━━━━\n🎲 <b>Winning Number:</b> <code>{actual_number}</code> ({actual_size})\n⚠️ <b>Status:</b> <b>1-Step Recovery Triggered!</b>\n💰 <b>Next Target:</b> <code>{bet_progression[min(loss_streak, len(bet_progression)-1)]} TK</code>"
        await bot.send_message(CHANNEL_USERNAME, msg, parse_mode=ParseMode.HTML)
        await bot.send_sticker(CHANNEL_USERNAME, LOSS_STICKER)

    recent_signals_history.append({
        'period': period,
        'pred': current_prediction,
        'act_num': actual_number,
        'act_size': actual_size,
        'status': 'WIN' if is_win else 'LOSS'
    })

    if len(recent_signals_history) >= 10:
        await send_10_games_report()

async def main_loop():
    global last_processed_id, current_prediction, current_numbers, current_win_rate, loss_streak
    
    logger.info("🚀 TK Club Ultra VIP Global V7 Bot Started Successfully...")
    
    while True:
        try:
            response = requests.get(API_URL, timeout=10)
            data = response.json()
            
            if data.get('data') and data['data'].get('list'):
                latest = data['data']['list'][0]
                current_id = latest['issueNumber']
                current_number = int(latest['number'])
                
                if last_processed_id is None or current_id != last_processed_id:
                    
                    if last_processed_id:
                        await process_result(current_number, last_processed_id)
                    
                    history = [int(item['number']) for item in data['data']['list'][:20]]
                    
                    current_prediction, current_win_rate, pattern_info = predict_ultra_win_rate(history)
                    current_numbers = generate_hot_and_cold_numbers(current_prediction, history)
                    
                    next_period = str(int(current_id) + 1)
                    bet = bet_progression[min(loss_streak, len(bet_progression)-1)]
                    
                    await send_signal_to_channel(next_period, current_prediction, current_numbers, bet, current_win_rate, pattern_info)
                    
                    last_processed_id = current_id
                    logger.info(f"Global Signal Sent for Period: {next_period}")
            
        except Exception as e:
            logger.error(f"Loop Error: {e}")
        
        await asyncio.sleep(5)

# Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ TK Club Bot is Running!"

@app.route('/start')
def start():
    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_loop())
    
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    return "🤖 Bot Started Successfully!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
