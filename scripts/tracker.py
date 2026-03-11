import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────

ORIGIN       = "BOM"
DESTINATION  = "LKO"
TRAVEL_DATE  = "2026-03-17"
MIN_PRICE    = 5500
MAX_PRICE    = 6500
ALERT_EMAIL  = "anaskhn4@gmail.com"

# Set these as environment variables in Render (never hardcode)
AMADEUS_API_KEY    = os.environ["AMADEUS_API_KEY"]
AMADEUS_API_SECRET = os.environ["AMADEUS_API_SECRET"]
GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]

# ─────────────────────────────────────────────────────────────────────────────


def get_amadeus_token():
    resp = requests.post(
        "https://test.api.amadeus.com/v1/security/oauth2/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     AMADEUS_API_KEY,
            "client_secret": AMADEUS_API_SECRET,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_flight_prices(token):
    resp = requests.get(
        "https://test.api.amadeus.com/v2/shopping/flight-offers",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "originLocationCode":      ORIGIN,
            "destinationLocationCode": DESTINATION,
            "departureDate":           TRAVEL_DATE,
            "adults":                  1,
            "currencyCode":            "INR",
            "max":                     10,
        },
    )
    resp.raise_for_status()
    offers = resp.json().get("data", [])
    prices = []
    for offer in offers:
        price    = float(offer["price"]["grandTotal"])
        airline  = offer["validatingAirlineCodes"][0]
        dep_time = offer["itineraries"][0]["segments"][0]["departure"]["at"]
        prices.append({"price": price, "airline": airline, "departure": dep_time})
    return sorted(prices, key=lambda x: x["price"])


def send_email(flights_in_range, cheapest):
    subject = f"✈️ BOM→LKO Price Alert | Cheapest: ₹{cheapest['price']:,.0f}"

    rows = ""
    for f in flights_in_range:
        dep = datetime.fromisoformat(f["departure"]).strftime("%d %b %Y, %I:%M %p")
        rows += f"""
    <tr>
      <td style='padding:8px;border:1px solid #ddd'>{f['airline']}</td>
      <td style='padding:8px;border:1px solid #ddd'>{dep}</td>
      <td style='padding:8px;border:1px solid #ddd;color:green'><b>₹{f['price']:,.0f}</b></td>
    </tr>"""

    body = f"""
<html><body style='font-family:Arial,sans-serif;'>
  <h2 style='color:#1a73e8'>✈️ Flight Price Alert: BOM → LKO</h2>
  <p>Flights found within your budget of <b>₹{MIN_PRICE:,} – ₹{MAX_PRICE:,}</b> on <b>{TRAVEL_DATE}</b>:</p>
  <table style='border-collapse:collapse;width:100%'>
    <tr style='background:#f1f3f4'>
      <th style='padding:8px;border:1px solid #ddd'>Airline</th>
      <th style='padding:8px;border:1px solid #ddd'>Departure</th>
      <th style='padding:8px;border:1px solid #ddd'>Price (INR)</th>
    </tr>
    {rows}
  </table>
  <br>
  <a href='https://www.google.com/flights' style='background:#1a73e8;color:white;padding:10px 20px;text-decoration:none;border-radius:4px'>
    Book on Google Flights
  </a>
  <p style='color:#888;font-size:12px'>This alert was sent at {datetime.now().strftime("%d %b %Y, %I:%M %p")} IST</p>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = ALERT_EMAIL
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, ALERT_EMAIL, msg.as_string())

    print(f"[{datetime.now()}] Alert sent! {len(flights_in_range)} flight(s) in range.")


def main():
    print(f"[{datetime.now()}] Checking prices for {ORIGIN} → {DESTINATION} on {TRAVEL_DATE}…")
    try:
        token   = get_amadeus_token()
        flights = get_flight_prices(token)

        if not flights:
            print("No flights found.")
            return

        cheapest = flights[0]
        print(f"Cheapest found: ₹{cheapest['price']:,.0f} ({cheapest['airline']})")

        in_range = [f for f in flights if MIN_PRICE <= f["price"] <= MAX_PRICE]

        if in_range:
            send_email(in_range, cheapest)
        else:
            print(f"No flights in range ₹{MIN_PRICE:,}–₹{MAX_PRICE:,}. Cheapest is ₹{cheapest['price']:,.0f}.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
