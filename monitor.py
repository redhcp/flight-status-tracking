import os
import json
import requests
from datetime import datetime, timedelta


API_KEY = os.environ["AIRLABS_API_KEY"]
FLIGHTS = os.environ["FLIGHTS"]

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


STATE_FILE = "status.json"


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)


def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, json=payload, timeout=10)


def get_flight(flight, date):

    url = "https://airlabs.co/api/v9/flight"

    params = {
        "api_key": API_KEY,
        "flight_iata": flight,
        "flight_date": date
    }

    r = requests.get(url, params=params, timeout=15)
    data = r.json()

    if not data.get("response"):
        return None

    f = data["response"]

    return {
        "status": f.get("status"),
        "delay": f.get("dep_delay"),
        "arrival_airport": f.get("arr_name")
    }

def now_tz(offset):
    return (datetime.utcnow() + timedelta(hours=offset)).strftime("%H:%M")


def build_message(flight, status, airport):

    return (
        f"✈ {flight}\n"
        f"🛬 Flight {status.upper()}\n\n"
        f"Arrival airport: {airport}\n\n"
        f"Checked: {now_tz(2)} (+2) / {now_tz(-3)} (-3)"
    )


def main():

    state = load_state()

    for entry in FLIGHTS:

        flight, date = entry.split(":")

        key = f"{flight}_{date}"

        current = get_flight(flight, date)

        if not current:
            continue

        last = state.get(key, {})

        last_status = last.get("status")
        last_delay = last.get("delay")

        status = current["status"]
        delay = current["delay"]
        airport = current["arrival_airport"]

        if status == "cancelled" and last_status != "cancelled":
            send(build_message(flight, status, airport))

        if status == "landed" and last_status != "landed":
            send(build_message(flight, status, airport))

        if delay and delay != last_delay:
            send(
                f"✈ {flight}\n"
                f"⚠ Flight DELAYED\n\n"
                f"Delay: {delay} minutes\n"
                f"Arrival airport: {airport}"
            )

        if status != last_status:
            send(build_message(flight, status, airport))

        state[key] = {
            "status": status,
            "delay": delay
        }

    save_state(state)


if __name__ == "__main__":
    main()
