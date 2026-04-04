# ============================================================
# alerts.py — compare old vs new prices, fire alerts on drops
# Stage 7: scorer integrated — each drop now carries a score + grade
# ============================================================

import smtplib
from email.mime.text import MIMEText

from app.config import (
    EMAIL_SENDER, EMAIL_PASSWORD,
    SMTP_HOST, SMTP_PORT,
    ALERT_THRESHOLD_PERCENT, EMAIL_ENABLED,
)
from app.scoring import score_drop, grade as get_grade


def _send_email(subject: str, body: str, receiver: str) -> None:
    msg             = MIMEText(body)
    msg["Subject"]  = subject
    msg["From"]     = EMAIL_SENDER
    msg["To"]       = receiver
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver, msg.as_string())
        print(f"[alerts] Email sent to {receiver}: {subject}")
    except Exception as e:
        print(f"[alerts] Email failed: {e}")


def _console_alert(name: str, old: float, new: float, link: str, drop_pct: float, score: float, grade: str) -> None:
    print(f"\n{'='*60}")
    print(f"  PRICE DROP  |  Score: {score}/100  |  Grade: {grade}")
    print(f"  {name}")
    print(f"  ${old:.2f}  →  ${new:.2f}  ({drop_pct:.1f}% drop)")
    print(f"  {link}")
    print(f"{'='*60}\n")


def check_for_drops(
    previous:      dict,
    current:       list[dict],
    settings=None,
    user_email:    str = "",
    price_history: dict = None,     # {gpu_name: [price, price, ...]} oldest first
) -> list[dict]:
    """Compare current scrape against previous prices and alert on drops.

    Args:
        previous:      {name: {price, link}} from last scrape
        current:       [{name, price, link, query, retailer}] from scraper
        settings:      UserSettings ORM object — overrides global thresholds
        user_email:    To: address for email alerts
        price_history: {name: [float]} — all historical prices per GPU,
                       used by scorer for rarity calculation. If None,
                       scorer uses neutral rarity score (50).

    Returns:
        List of drop dicts, each with score and grade attached.
    """
    threshold     = settings.alert_threshold if settings else ALERT_THRESHOLD_PERCENT
    email_enabled = settings.email_enabled   if settings else EMAIL_ENABLED
    receiver      = user_email               if user_email else ""
    history       = price_history or {}

    drops = []

    for item in current:
        name = item["name"]

        if name not in previous:
            continue

        old_price = previous[name]["price"]
        new_price = item["price"]

        if old_price == 0:
            continue

        drop_pct = ((old_price - new_price) / old_price) * 100

        if drop_pct >= threshold:
            # ── Score this drop ───────────────────────────────────────────
            deal_score = score_drop(
                drop_pct      = drop_pct,
                price_history = history.get(name, []),
                current_price = new_price,
                all_current   = current,
                gpu_name      = name,
            )
            deal_grade = get_grade(deal_score)

            _console_alert(name, old_price, new_price, item["link"], drop_pct, deal_score, deal_grade)

            if email_enabled and receiver:
                subject = f"[{deal_grade}] GPU Deal: {name} dropped {drop_pct:.1f}%"
                body    = (
                    f"Deal score: {deal_score}/100  (Grade {deal_grade})\n\n"
                    f"Product : {name}\n"
                    f"Old     : ${old_price:.2f}\n"
                    f"New     : ${new_price:.2f}\n"
                    f"Drop    : {drop_pct:.1f}%\n"
                    f"Link    : {item['link']}"
                )
                _send_email(subject, body, receiver)

            drops.append({
                "name":      name,
                "old_price": old_price,
                "new_price": new_price,
                "drop_pct":  round(drop_pct, 2),
                "score":     deal_score,
                "grade":     deal_grade,
                "link":      item["link"],
            })

    return drops
