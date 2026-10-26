import sqlite3
import datetime
import telebot
from telebot import types

TOKEN = "8980553171:AAElLzmT-HnaZ_zo-LXykahE7e-WLE_-oqQ"
bot = telebot.TeleBot(TOKEN)

def get_top_users_day(page=0, per_page=10):
	conn = sqlite3.connect("bot_stats.db")
	cursor = conn.cursor()
	cursor.execute(
		"""
    	SELECT name, today_count, week_count 
    	FROM users 
    	ORDER BY today_count DESC 
    	LIMIT ? OFFSET ?
	""", 
		(per_page, page * per_page)
	)
	rows = cursor.fetchall()
	conn.close()
	return rows

def get_top_users_week(page=0, per_page=10):
	conn = sqlite3.connect("bot_stats.db")
	cursor = conn.cursor()
	cursor.execute(
			"""
			SELECT name, week_count
			FROM users
			ORDER BY week_count DESC
			LIMIT ? OFFSET ?
	""",
			(per_page, page * per_page),
	)
	rows = cursor.fetchall()
	conn.close()
	return rows
	
def get_pagination_keyboard(page, stat_type):
	keyboard = types.InlineKeyboardMarkup()
	btn_prev = types.InlineKeyboardButton(
		"⬅️ Назад", callback_data=f"stat_{stat_type}_{page - 1}"
	)
	btn_next = types.InlineKeyboardButton(
		"Вперед ➡️", callback_data=f"stat_{stat_type}_{page + 1}"
	)
	
	if page == 0:
		keyboard.add(btn_next)
	else:
	   keyboard.row(btn_prev, btn_next)
	return keyboard

def init_db():
	conn = sqlite3.connect("bot_stats.db")
	cursor = conn.cursor()
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS users (
			user_id INTEGER PRIMARY KEY,
			name TEXT,
			username TEXT,
			today_count INTEGER DEFAULT 0,
			week_count INTEGER DEFAULT 0,
			last_date TEXT,
			week_start_date TEXT
		)
	""")
	conn.commit()
	conn.close()

init_db()

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.reply_to(message, "Привіт абриКОСик!")

@bot.message_handler(commands=['stats_day'])
def show_stats_day(message):
	page = 0
	users = get_top_users_day(page)
	conn = sqlite3.connect("bot_stats.db")
	cursor = conn.cursor()
	
	now = str(datetime.datetime.now().date())
	cursor.execute("SELECT name, username, today_count FROM users WHERE last_date = ? AND today_count > 0 ORDER BY today_count DESC", (now,))
	rows = cursor.fetchall()
	conn.close()
	
	if not rows:
	   bot.reply_to(message, "уу креветки пробивають дно")
	   return
    
	text = "📊 Активність чату (сьогодні):\n\n"
	for i, (name, username, count) in enumerate(rows, 1):
		display_name = name if name else (username if username else "без імені")
		text += f"{i}. {display_name} — {count} повідомлень\n"
    
	bot.send_message(
			message.chat.id,
			text,
			reply_markup=get_pagination_keyboard(page,"day"),
			parse_mode="Markdown",
	)

@bot.message_handler(commands=['stats_week'])
def show_stats_week(message):
	page = 0
	users = get_top_users_week(page)
	conn = sqlite3.connect("bot_stats.db")
	cursor = conn.cursor()
	
	cursor.execute("SELECT name, username, week_count FROM users WHERE week_count > 0 ORDER BY week_count DESC")
	rows = cursor.fetchall()
	conn.close()
	
	if not rows:
	   bot.reply_to(message, "косики вже холодні")
	   return
    
	text = "📈 Активність чату (за тиждень):\n\n"
	for i, (name, username, count) in enumerate(rows, 1):
		display_name = name if name else (username if username else "без імені")
		text += f"{i}. {display_name} — {count} повідомлень\n"
    
	bot.send_message(
			message.chat.id,
			text,
			reply_markup=get_pagination_keyboard(page, "week"),
			parse_mode="Markdown"
	)

@bot.callback_query_handler(func=lambda call: call.data.startswith("stat_"))
def handle_pagination(call):
	parts = call.data.split("_")
	stat_type = parts[1] 
	page = int(parts[2])
	
	if page < 0:
	   page = 0
    
	if stat_type == "day":
		users = get_top_users_day(page)
		title = f"📊 Активність чату (сьогодні) (Сторінка {page + 1}):**\n\n"
	else:
		users = get_top_users_week(page)
		title = f"📈 Активність чату (за тиждень) (Сторінка {page + 1}):**\n\n"
    
	if not users:
		bot.answer_callback_query(call.id, "Більше сторінок немає!")
		return
    
	text = title
	for idx, (name, count) in enumerate(users, start=1):
		real_idx = page * 5 + idx
		text += f"{real_idx}. {name} — {count} повідомлень\n"
    
	bot.edit_message_text(
			text, 
			call.message.chat.id, 
			call.message.message_id, 
			reply_markup=get_pagination_keyboard(page, stat_type), 
			parse_mode="Markdown"
	)
	
@bot.message_handler(func=lambda message: True)
def all_messages(message):
	user_id = message.from_user.id
	name = message.from_user.first_name
	username = message.from_user.username
	today_date = datetime.datetime.now().date()
	today_str = str(today_date)
	
	conn = sqlite3.connect("bot_stats.db")
	cursor = conn.cursor()
	
	cursor.execute("SELECT today_count, week_count, last_date, week_start_date FROM users WHERE user_id = ?", (user_id,))
	row = cursor.fetchone()
	
	if not row:
	       cursor.execute("""
	       	INSERT INTO users (user_id, name, username, today_count, week_count, last_date, week_start_date)
	       	VALUES (?, ?, ?, 1, 1, ?, ?)
	       """, (user_id, name, username, today_str, today_str))
	else:
	   today_count, week_count, last_date, week_start_date = row
	   
	   if last_date != today_str:
	       today_count = 0
	       last_date = today_str
	   
	   if week_start_date:
	       start_date_obj = datetime.datetime.strptime(week_start_date, "%Y-%m-%d").date()
	       if (today_date - start_date_obj).days >= 7:
	           week_count = 0
	           week_start_date = today_str
	       else:
	       	week_start_date = today_str
	       
	       today_count += 1
	       week_count += 1
	       
	       cursor.execute("""
	       	UPDATE users 
	       	SET today_count = ?, week_count = ?, last_date = ?, week_start_date = ?, name = ?, username = ? 
	       	WHERE user_id = ?
	       """, (today_count, week_count, last_date, week_start_date, name, username, user_id))
    
	conn.commit()
	conn.close()

if __name__ == "__main__":
	print("Бот ззапущено!")
	bot.infinity_polling()