import logging
import json
import os
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import yt_dlp
import threading
from http.server import SimpleHTTPRequestHandler
import socketserver

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

CACHE_FILE = 'music_cache.json'
SEARCH_CACHE = {} 
CACHE_LOCK = asyncio.Lock()
MAX_SONG_DURATION = 600 

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

async def save_cache_async(cache_data):
    async with CACHE_LOCK:
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Cache save error: {e}")

file_cache = load_cache()

def load_config():
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"business_name": "Music Flow"}

config = load_config()
BOT_NAME = "Music Flow"
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "MusicFlow_Bot"

STRINGS = {
    'kk': {'welcome': "Аудиожазбаны табу үшін ән немесе орындаушының атын жіберіңіз.", 'popular_btn': "🥇 Танымал", 'new_btn': "🎧 Жаңалықтар", 'popular_query': "хиты 2026", 'new_query': "новинки 2026", 'searching': "🔎 Іздеудемін...", 'results': "🎶 Нәтижелер:", 'downloading': "📥 Жүктеудемін...", 'too_large': "❌ Файл тым үлкен.", 'error': "❌ Қате.", 'promo': "🔍 Сүйікті әніңді тап!", 'enjoy': f"Скачано через {BOT_NAME} 🎧"},
    'ru': {'welcome': "Чтобы найти аудиозапись, отправьте название песни или исполнителя.", 'popular_btn': "🥇 Популярное", 'new_btn': "🎧 Новинки", 'popular_query': "хиты 2026", 'new_query': "новинки музыки 2026", 'searching': "🔎 Ищу варианты...", 'results': "🎶 Результаты для:", 'downloading': "📥 Начинаю загрузку...", 'too_large': "❌ Файл слишком большой.", 'error': "❌ Ошибка при скачивании.", 'promo': "🔍 Найти любимую песню!", 'enjoy': f"Скачано через {BOT_NAME} 🎧"},
    'uk': {'welcome': "Щоб знайти аудіозапис, надішліть назву пісні або виконавця.", 'popular_btn': "🥇 Популярне", 'new_btn': "🎧 Новинки", 'promo': "🔍 Знайти улюблену пісню!", 'popular_query': "хіти 2026", 'new_query': "хіти 2026", 'searching': "🔎 Шукаю...", 'results': "🎶 Результати:", 'downloading': "📥 Завантаження...", 'too_large': "❌ Файл завеликий.", 'error': "❌ Помилка.", 'enjoy': f"Завантажено через {BOT_NAME} 🎧"},
    'en': {'welcome': "To find music, send the song or artist name.", 'popular_btn': "🥇 Popular", 'new_btn': "🎧 New Hits", 'promo': "🔍 Find your favorite song!", 'popular_query': "popular music 2026", 'new_query': "best songs 2026", 'searching': "🔎 Searching...", 'results': "🎶 Results for:", 'downloading': "📥 Downloading...", 'too_large': "❌ File too large.", 'error': "❌ Error.", 'enjoy': f"Downloaded via {BOT_NAME} 🎧"},
    'uz': {'welcome': "Audio yozuvni topish uchun qo'shiq yoki artist nomini yuboring.", 'popular_btn': "🥇 Ommabop", 'new_btn': "🎧 Yangi xitlar", 'promo': "🔍 Sevimli qo'shig'ingizni toping!", 'popular_query': "top musiqalar 2026", 'new_query': "yangi qo'shiqlar 2026", 'searching': "🔎 Qidirilmoqda...", 'results': "🎶 Natijalar:", 'downloading': "📥 Yuklanmoqda...", 'too_large': "❌ Fayl juda katta.", 'error': "❌ Xatolik.", 'enjoy': f"{BOT_NAME} orqali yuklab olindi 🎧"},
    'de': {'welcome': "Senden Sie den Namen des Liedes oder Künstlers.", 'popular_btn': "🥇 Beliebt", 'new_btn': "🎧 Neue Hits", 'promo': "🔍 Finde dein Lieblingslied!", 'popular_query': "charts 2026", 'new_query': "neue musik 2026", 'searching': "🔎 Suche...", 'results': "🎶 Ergebnisse:", 'downloading': "📥 Laden...", 'too_large': "❌ Datei zu groß.", 'error': "❌ Fehler.", 'enjoy': f"Über {BOT_NAME} geladen 🎧"},
    'es': {'welcome': "Envía el nombre de la canción или artista.", 'popular_btn': "🥇 Popular", 'new_btn': "🎧 Novedades", 'promo': "🔍 ¡Encuentra tu canción favorita!", 'popular_query': "exitos 2026", 'new_query': "musica nueva 2026", 'searching': "🔎 Buscando...", 'results': "🎶 Resultados:", 'downloading': "📥 Descargando...", 'too_large': "❌ Archivo muy grande.", 'error': "❌ Error.", 'enjoy': f"Descargado vía {BOT_NAME} 🎧"},
    'tr': {'welcome': "Ses kaydı bulmak uchun şarkı veya sanatçı adını gönderin.", 'popular_btn': "🥇 Popüler", 'new_btn': "🎧 Yeni Çыканлар", 'promo': "🔍 En sevdiğiniz şarkıyı bulun!", 'popular_query': "popüler müzк 2026", 'new_query': "yeni şarkılar 2026", 'searching': "🔎 Arıyor...", 'results': "🎶 Sonuçлар:", 'downloading': "📥 Yükленiyor...", 'too_large': "❌ Dosya çok большой.", 'error': "❌ Hata.", 'enjoy': f"{BOT_NAME} aracılığıyla indirildi 🎧"}
}

ITEMS_PER_PAGE = 8

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🇰🇿 Қазақ тілі", callback_data="lang_kk")],
                [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
                [InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk")],
                [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
                [InlineKeyboardButton("🇺🇿 O'zbek tili", callback_data="lang_uz")],
                [InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")],
                [InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es")],
                [InlineKeyboardButton("🇹🇷 Türk", callback_data="lang_tr")]]
    await update.message.reply_text("Please choose your native language.\n\nBy continuing to use this bot, you agree to our terms of service.", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    if not query: return
    lang = context.user_data.get('lang', 'ru')
    s = STRINGS.get(lang, STRINGS['ru'])

    if query == s['popular_btn']: query = s['popular_query']
    elif query == s['new_btn']: query = s['new_query']

    if query in SEARCH_CACHE:
        await update.message.reply_text(f"{s['results']} *{query}*", reply_markup=build_search_keyboard(SEARCH_CACHE[query], 0), parse_mode='Markdown')
        return

    status_msg = await update.message.reply_text(s['searching'])
    ydl_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True, 'check_formats': False, 'ignoreerrors': True}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch80:{query}", download=False))
            
            if not info or 'entries' not in info:
                await status_msg.edit_text("❌ Nothing found.")
                return

            entries = []
            for e in info['entries']:
                if e:
                    d = e.get('duration')
                    if d is not None and d < MAX_SONG_DURATION:
                        entries.append(e)
            
            if not entries:
                await status_msg.edit_text("❌ Nothing found (under 10 mins).")
                return

            SEARCH_CACHE[query] = entries
            context.user_data['search_results'] = entries
            await status_msg.edit_text(f"{s['results']} *{query}*", reply_markup=build_search_keyboard(entries, 0), parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Search error: {e}")
        await status_msg.edit_text(s['error'])

def build_search_keyboard(results, page):
    start_idx = page * ITEMS_PER_PAGE
    current_items = results[start_idx:start_idx + ITEMS_PER_PAGE]
    keyboard = []
    for item in current_items:
        duration_sec = item.get('duration') or 0
        duration = f"{int(duration_sec//60):02d}:{int(duration_sec%60):02d}"
        title = (item.get('title')[:35] + "..") if len(item.get('title', '')) > 38 else item.get('title')
        keyboard.append([InlineKeyboardButton(f"{duration} | {title}", callback_data=f"dl_{item['id']}")])
    total_pages = (len(results) + 7) // 8
    nav = [InlineKeyboardButton("◀️", callback_data=f"p_{page-1}") if page > 0 else InlineKeyboardButton(" ", callback_data="none"),
           InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="none"),
           InlineKeyboardButton("▶️", callback_data=f"p_{page+1}") if page < total_pages - 1 else InlineKeyboardButton(" ", callback_data="none")]
    keyboard.append(nav)
    return InlineKeyboardMarkup(keyboard)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    global BOT_USERNAME
    await query.answer()

    if data.startswith("lang_"):
        lang = data.replace("lang_", ""); context.user_data['lang'] = lang
        s = STRINGS.get(lang, STRINGS['ru'])
        menu = [[KeyboardButton(s['popular_btn']), KeyboardButton(s['new_btn'])]]
        await query.message.reply_text(s['welcome'], reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
        await query.delete_message(); return

    if data.startswith("p_"):
        results = context.user_data.get('search_results')
        if results: await query.edit_message_reply_markup(reply_markup=build_search_keyboard(results, int(data.split("_")[1])))
        return

    if data.startswith("dl_"):
        vid = data.replace("dl_", "")
        lang = context.user_data.get('lang', 'ru')
        s = STRINGS.get(lang, STRINGS['ru'])
        
        # Если BOT_USERNAME еще не подгрузился, используем временную заглушку
        username = BOT_USERNAME if BOT_USERNAME else "bot"
        promo_text = f"[{s['promo']}](https://t.me/{username})"

        if vid in file_cache:
            try:
                await query.edit_message_text("🚀 Мгновенно...")
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=file_cache[vid], caption=promo_text, parse_mode='Markdown')
                return
            except:
                pass # Если файл удален из облака ТГ, пойдем качать заново

        chat_id = query.message.chat_id
        path = f"downloads/{vid}_{chat_id}.m4a"
        await query.edit_message_text(s['downloading'])
        
        ydl_opts = {'format': 'bestaudio[ext=m4a]/bestaudio', 'outtmpl': path, 'quiet': True, 'nopart': True}
        
        try:
            if not os.path.exists('downloads'): os.makedirs('downloads')
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(vid, download=True))
                # Проверка размера
                if os.path.exists(path) and os.path.getsize(path) > 50 * 1024 * 1024:
                    await query.edit_message_text(s['too_large'])
                    try: os.remove(path)
                    except: pass
                    return

                with open(path, 'rb') as f:
                    msg = await context.bot.send_audio(chat_id=chat_id, audio=f, title=info.get('title'), caption=promo_text, parse_mode='Markdown')
                    file_cache[vid] = msg.audio.file_id
                    await save_cache_async(file_cache)
                
                try: os.remove(path)
                except: pass
                await query.delete_message()
        except Exception as e:
            logging.error(f"Download error: {e}")
            await query.edit_message_text(s['error'])

async def post_init(application):
    global BOT_USERNAME
    try:
        bot_info = await application.bot.get_me()
        BOT_USERNAME = bot_info.username
        print(f"Бот запущен: @{BOT_USERNAME}")
    except:
        pass

def run_health_check():
    """Запускает простейший веб-сервер для Render, чтобы он не убивал процесс"""
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        logging.info(f"Health check server started on port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    # Запускаем Health Check в отдельном потоке
    threading.Thread(target=run_health_check, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()
