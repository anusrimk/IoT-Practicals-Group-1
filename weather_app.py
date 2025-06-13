import streamlit as st
import requests
import json
from datetime import datetime
import dateparser

LLAMA_API_URL = "http://localhost:11434/api/chat"
WEATHER_API_KEY = "439d1b7ee23c4770b40173704243005"
WEATHER_API_BASE_HISTORY = "http://api.weatherapi.com/v1/history.json"
WEATHER_API_BASE_FORECAST = "http://api.weatherapi.com/v1/forecast.json"

def normalize_date(relative_text):
    parsed = dateparser.parse(relative_text)
    if not parsed:
        raise ValueError(f"Could not parse date from: {relative_text}")
    return parsed.strftime("%Y-%m-%d")

def fetch_weather(location, date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.today().date()
    delta_days = (date_obj - today).days

    if date_obj < today:
        if (today - date_obj).days > 7:
            raise ValueError("Historical weather data is only available for the past 7 days.")
        api_url = WEATHER_API_BASE_HISTORY
    else:
        if delta_days > 14:
            raise ValueError("Forecast is only available up to 14 days into the future.")
        api_url = WEATHER_API_BASE_FORECAST

    params = {"key": WEATHER_API_KEY, "q": location, "dt": date_str}
    response = requests.get(api_url, params=params)
    response.raise_for_status()
    return response.json()

def summarize_with_llama(weather_json, location, date):
    try:
        day = weather_json["forecast"]["forecastday"][0]["day"]
        condition = day["condition"]["text"]
        temp = day["avgtemp_c"]
        rain = day["daily_chance_of_rain"]

        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.today().date()
        tense = "past" if date_obj < today else "future"

        if tense == "past":
            weather_description = (
                f"The weather in {location} on {date} was '{condition}', "
                f"with an average temperature of {temp}°C and a {rain}% chance of rain."
            )
            prompt = (
                f"{weather_description}\n\n"
                "Summarize this in 1-2 natural lines and suggest 3-5 suitable games a person could have played on that day based on the weather. "
                "Include the games as bullet points."
            )
        else:
            weather_description = (
                f"The weather in {location} on {date} is expected to be '{condition}', "
                f"with an average temperature of {temp}°C and a {rain}% chance of rain."
            )
            prompt = (
                f"{weather_description}\n\n"
                "Summarize this in 1-2 natural lines and suggest 3-5 games a person can enjoy based on this upcoming weather. "
                "Include the games as bullet points."
            )

        payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(LLAMA_API_URL, json=payload, stream=True)
        response.raise_for_status()

        content = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    content += data.get("message", {}).get("content", "")
                except Exception:
                    continue

        return content.strip()

    except Exception as e:
        return f"⚠️ Failed to summarize: {e}"

# ---------------- Streamlit UI ----------------

st.title("Game Suggestion")
city_input = st.text_input("what games can we play in delhi right now")

if city_input:
    try:
        location = city_input.strip()
        date_str = normalize_date("today")

        st.success(f"✅ Location: {location}, Date: {date_str}")

        weather_data = fetch_weather(location, date_str)
        summary = summarize_with_llama(weather_data, location, date_str)

        st.markdown("### 📊 Weather Summary + Game Suggestions:")
        st.write(summary)

    except Exception as e:
        st.error(f"❌ Error: {e}")
