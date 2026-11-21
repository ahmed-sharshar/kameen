"""Synthetic bait values. Every value here is fake by construction."""
import os
import secrets

DIGITS = "0123456789"


def luhn_ok(number):
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def _numeric(text):
    return "".join(str(ord(c) - 55) if c.isalpha() else c for c in text)


def iban_check_digits(bban, country="AE"):
    """ISO 13616: move the country code and '00' to the end, then 98 - (number mod 97)."""
    return f"{98 - int(_numeric(bban + country + '00')) % 97:02d}"


def iban_ok(iban):
    iban = iban.replace(" ", "")
    return int(_numeric(iban[4:] + iban[:4])) % 97 == 1


def new_card():
    """16 digits that deliberately FAIL the Luhn check, so they cannot be a real card."""
    while True:
        number = "4" + "".join(secrets.choice(DIGITS) for _ in range(15))
        if not luhn_ok(number):
            return number


def one_digit_wrong(card):
    """The version the decoy reads out first. Also fails Luhn."""
    for position in (13, 14, 12, 11):
        for step in (1, 2, 3):
            digit = str((int(card[position]) + step) % 10)
            wrong = card[:position] + digit + card[position + 1:]
            if not luhn_ok(wrong):
                return wrong
    return card


def new_iban():
    """UAE layout: AE, 2 check digits, 3-digit bank code, 16-digit account. Valid checksum."""
    bank = os.environ.get("CANARY_BANK_CODE", "999")      # confirm this code is unassigned
    bban = bank + "".join(secrets.choice(DIGITS) for _ in range(16))
    return "AE" + iban_check_digits(bban) + bban


def new_kit():
    card = new_card()
    return {
        "card": card,
        "card_wrong": one_digit_wrong(card),
        "expiry": "08/29",
        "iban": new_iban(),
        "otp": "".join(secrets.choice(DIGITS) for _ in range(6)),
        "synthetic": True,
    }


def kit_digits(kit):
    """Digit strings the decoy is allowed to say."""
    if not kit:
        return []
    return [kit["card"], kit["card_wrong"], kit["iban"][2:], kit["otp"]]


def is_canary(kit, value):
    digits = "".join(c for c in value if c.isdigit())
    return len(digits) >= 6 and any(digits in allowed or allowed in digits for allowed in kit_digits(kit))
