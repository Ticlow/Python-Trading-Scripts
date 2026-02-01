---

## How It Works

### Floor Price Monitoring
- Fetches the current floor price from the Magic Eden Ordinals API
- Converts the floor price from BTC to USD using a live BTC/USD rate
- Compares the current floor price to the last alerted floor price
- Sends an alert if the percentage change exceeds the configured threshold

### Listing Delta Detection
- Fetches active listings from the BestInSlot API
- Sorts listings by price (ascending)
- Compares the cheapest listing to the 5th cheapest listing
- Triggers an alert if the price delta exceeds the configured threshold
- Ensures each listing is only alerted once

### BTC → USD Conversion
- Retrieves the live BTC/USD price from CoinGecko
- USD values are included in logs and alerts for readability
- USD prices are informational only and do not affect alert logic

---

## Configuration (Required)

Sensitive data and configuration values are stored in a separate file.

You must create a `config.json` file containing API keys, thresholds, and email credentials.

### `config.json` (example)

```json
{
  "ME_API_KEY": "YOUR_MAGIC_EDEN_API_KEY",
  "BIS_API_KEY": "YOUR_BESTINSLOT_API_KEY",

  "FLOOR_CHANGE_THRESHOLD": 10,
  "LISTING_DELTA_THRESHOLD": 15,
  "CHECK_INTERVAL": 300,

  "BIS_MAX_REQUESTS_PER_MIN": 100,
  "BIS_MAX_REQUESTS_PER_DAY": 10000,

  "SMTP_SERVER": "smtp.example.com",
  "SMTP_PORT": 587,
  "SENDER_EMAIL": "alerts@example.com",
  "SENDER_PASSWORD": "EMAIL_PASSWORD",
  "RECEIVER_EMAIL": "receiver@example.com"
}
