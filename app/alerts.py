# ============================================================
# alerts.py — compare old vs new prices, fire alerts on drops
# ============================================================

import smtplib
from email.mime.text import MIMEText
from config import ALERT_THRESHOLD_PERCENT, EMAIL_ENABLED, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER, SMTP_HOST, SMTP_PORT


def _send_email(subject: str, body: str) -> None:
    """Send a plain-text email via Gmail SMTP."""
    msg             = MIMEText(body)
    msg["Subject"]  = subject
    msg["From"]     = EMAIL_SENDER
    msg["To"]       = EMAIL_RECEIVER

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()                               # encrypt the connection
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print(f"[alerts] Email sent: {subject}")
    except Exception as e:
        print(f"[alerts] Email failed: {e}")


def _console_alert(name: str, old: float, new: float, link: str) -> None:
    """Print a formatted price drop alert to the terminal."""
    drop_pct = ((old - new) / old) * 100
    print(f"\n{'='*60}")
    print(f"  💸 PRICE DROP DETECTED")
    print(f"  {name}")
    print(f"  ${old:.2f}  →  ${new:.2f}  ({drop_pct:.1f}% drop)")
    print(f"  {link}")
    print(f"{'='*60}\n")


def check_for_drops(previous: dict, current: list[dict]) -> None:
    """Compare current scrape against previous prices and alert on significant drops.

    Args:
        previous: output of storage.load_latest_prices() → {name: {price, link}}
        current:  output of scraper.scrape_all()         → list of {name, price, link, query}
    """
    for item in current:
        name = item["name"]

        if name not in previous:                            # new product, no baseline to compare
            continue

        old_price = previous[name]["price"]
        new_price = item["price"]

        if old_price == 0:                                  # guard against division by zero
            continue

        drop_pct = ((old_price - new_price) / old_price) * 100

        if drop_pct >= ALERT_THRESHOLD_PERCENT:             # only alert if drop is big enough
            _console_alert(name, old_price, new_price, item["link"])

            if EMAIL_ENABLED:
                subject = f"GPU Price Drop: {name}"
                body    = (
                    f"Price dropped by {drop_pct:.1f}%!\n\n"
                    f"Product : {name}\n"
                    f"Old     : ${old_price:.2f}\n"
                    f"New     : ${new_price:.2f}\n"
                    f"Link    : {item['link']}"
                )
                _send_email(subject, body)
