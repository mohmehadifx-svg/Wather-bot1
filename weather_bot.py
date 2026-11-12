import os
import threading
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes

# আপনার টেলিগ্রাম বটের টোকেন এখানে বসান
TELEGRAM_BOT_TOKEN = "8839063447:AAGSXQm2XGXMaAMlcnivAnXtFzH5TZm-mqU"

# Render-এর ফ্রি Web Service চালু রাখার জন্য ছোট ওয়েব সার্ভার
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Weather Bot is Running Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# মালদ্বীপের সমস্ত অ্যাটলের ডাটাবেজ
MALDIVES_ATOLLS = {
    "haa alifu": (6.9500, 73.1167),
    "haa dhaalu": (6.5833, 73.1167),
    "shaviyani": (6.2167, 73.4167),
    "noonu": (5.8000, 73.4167),
    "raa": (5.6000, 73.0000),
    "baa": (5.1500, 73.1167),
    "lhaviyani": (5.3500, 73.5500),
    "kaafu": (4.3167, 73.5500),
    "male": (4.1755, 73.5093),
    "alif alif": (3.9167, 72.9167),
    "alif dhaalu": (3.5200, 72.9000),
    "vaavu": (3.3333, 73.5500),
    "meemu": (2.9167, 73.5333),
    "faafu": (3.0833, 73.0000),
    "dhaalu": (2.8333, 72.9167),
    "thaa": (2.2500, 73.3333),
    "laamu": (1.9167, 73.5333),
    "gaafu alifu": (0.5281, 73.4131),
    "gaafu dhaalu": (0.3156, 73.4344),
    "gnaviyani": (-0.2833, 73.4167),
    "addu": (-0.6000, 73.1500),
    "seenu": (-0.6000, 73.1500)
}

user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📍 Location", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome to the Global Weather & Marine Bot! 🌍\nClick the button below to select a region:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "main_menu":
        user_states.pop(user_id, None)
        keyboard = [
            [InlineKeyboardButton("🇧🇩 Bangladesh", callback_data="country_bd")],
            [InlineKeyboardButton("🇲🇻 Maldives", callback_data="country_mv")]
        ]
        await query.edit_message_text("Please choose a country:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "country_bd":
        user_states[user_id] = "waiting_bd_district"
        keyboard = [[InlineKeyboardButton("🔙 Back to Countries", callback_data="main_menu")]]
        await query.edit_message_text(
            "🇧🇩 **Bangladesh Selected**\n\n"
            "You can search for **any of the 64 districts** in Bangladesh.\n"
            "Please type the name of the district you want to check (e.g., *Dhaka, Cox's Bazar, Sylhet, Chattogram*):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "country_mv":
        user_states[user_id] = "waiting_mv_atoll"
        atolls_string = ", ".join([atoll.title() for atoll in MALDIVES_ATOLLS.keys()])
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Countries", callback_data="main_menu")]]
        await query.edit_message_text(
            "🇲🇻 **Maldives Selected**\n\n"
            "All administrative atolls are supported.\n"
            "Please type the name of the Atoll you want to check (e.g., *Male, Kaafu, Addu, Baa*):\n\n"
            f"📋 **Available Atolls:** {atolls_string}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip().lower()
    
    if user_id not in user_states:
        await update.message.reply_text("Please click /start to begin.")
        return

    state = user_states[user_id]
    
    if state == "waiting_bd_district":
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={text}&count=5"
        try:
            res = requests.get(geo_url).json()
            if "results" not in res:
                await update.message.reply_text("⚠️ District not found. Please check the spelling and type a valid Bangladesh district name.")
                return
            
            loc = None
            for item in res["results"]:
                if item.get("country", "").lower() == "bangladesh":
                    loc = item
                    break
            
            if not loc:
                loc = res["results"][0]
                
            lat, lon = loc["latitude"], loc["longitude"]
            place_name = f"{loc['name']}, {loc.get('country', 'Bangladesh')}"
            
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,wind_speed_10m"
            w_res = requests.get(weather_url).json().get("current", {})
            
            temp = w_res.get("temperature_2m", "N/A")
            feels_like = w_res.get("apparent_temperature", "N/A")
            humidity = w_res.get("relative_humidity_2m", "N/A")
            rain = w_res.get("precipitation", 0)
            wind = w_res.get("wind_speed_10m", "N/A")
            
            weather_note = "Normal weather conditions."
            if isinstance(temp, (int, float)):
                if temp < 18:
                    weather_note = "❄️ Weather is cold/chilly. Warm clothing recommended."
                elif temp > 30:
                    weather_note = "☀️ Weather is warm/hot."

            report = (
                f"📍 **Location:** {place_name}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🌡️ **Temperature:** {temp}°C\n"
                f"🧥 **Feels Like:** {feels_like}°C\n"
                f"💧 **Humidity:** {humidity}%\n"
                f"🌧️ **Precipitation/Rain:** {rain} mm\n"
                f"💨 **Wind Speed:** {wind} km/h\n"
                f"📌 **Condition Note:** {weather_note}\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔍 Search Another District", callback_data="country_bd")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            await update.message.reply_text(report, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            
        except Exception as e:
            await update.message.reply_text("⚠️ An error occurred while fetching data. Please try again.")

    elif state == "waiting_mv_atoll":
        if text not in MALDIVES_ATOLLS:
            await update.message.reply_text("⚠️ Atoll not found. Please type a valid Maldives Atoll name from the list.")
            return
        
        lat, lon = MALDIVES_ATOLLS[text]
        place_name = f"{text.title()} Atoll, Maldives"
        
        marine_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&marine=sea_level_height_including_tides"
        m_res = requests.get(marine_url).json()
        current = m_res.get("current", {})
        
        temp = current.get("temperature_2m", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        rain = current.get("precipitation", 0)
        wind = current.get("wind_speed_10m", "N/A")
        sea_level = current.get("sea_level_height_including_tides", "Normal")
        
        report = (
            f"🇲🇻 **Maldives Marine & Weather Report**\n"
            f"📍 **Atoll:** {place_name}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🌡️ **Temperature:** {temp}°C\n"
            f"💧 **Humidity:** {humidity}%\n"
            f"🌧️ **Rainfall:** {rain} mm\n"
            f"💨 **Wind Speed:** {wind} km/h\n"
            f"🌊 **Sea Water Level:** {sea_level} meters\n"
            f"⏰ **Tide & Ocean Status:** Active tidal fluctuations, current flow, and oceanic sea-level tracking are operational.\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔍 Search Another Atoll", callback_data="country_mv")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        await update.message.reply_text(report, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

if __name__ == "__main__":
    # ব্যাকগ্রাউন্ডে ওয়েব সার্ভার চালু করা
    threading.Thread(target=run_web, daemon=True).start()
    
    # টেলিগ্রাম বট চালু করা
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_input))

    app.run_polling()