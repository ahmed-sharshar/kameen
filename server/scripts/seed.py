"""Loads or removes the synthetic demo history.

Usage (from server/):  .venv/bin/python scripts/seed.py          load it (does nothing if already loaded)
                       .venv/bin/python scripts/seed.py --clear  remove it, and nothing else
                       .venv/bin/python scripts/seed.py --cue    print the IBAN and phone for the demo cue card
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, seed          # noqa: E402  (the path line above must run first)


async def main():
    if "--cue" in sys.argv:
        print("IBAN :", seed.CUE_CARD["iban"])
        print("Phone:", seed.CUE_CARD["phone"])
        return
    await db.init()
    if "--clear" in sys.argv:
        print("removed", await seed.clear(), "seeded conversations")
    else:
        print("added", await seed.run(), "seeded conversations")


if __name__ == "__main__":
    asyncio.run(main())
