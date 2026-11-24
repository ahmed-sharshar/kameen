# Kameen (كمين)

One AI agent, two modes, for the fight against phone and message scams.

- **Decoy mode.** The agent plays a believable victim. It keeps a scammer talking, extracts their IBANs, phone numbers and links, and hands out tracked fake card and bank details.
- **Drill mode.** The agent plays a scammer against a person who consented. It stops before any secret is given, reveals the drill and teaches a short lesson.

Everything here is a simulation. The scammer is a teammate, a judge or a test simulator, and every card number, IBAN and code the decoy gives out is synthetic.

## Layout

```
docs/      the website (GitHub Pages)
server/    the Python server (Render)
  app/     routes, agent turn, safety checks, prompts, cards
  tests/   unit tests and end-to-end flows
reports/   test metrics
```

## Run it locally

```bash
cd server
python3.12 -m venv .venv            # or: uv venv --python 3.12 .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                # then edit .env
.venv/bin/uvicorn app.main:app --reload
```

In a second terminal, serve the website:

```bash
python3 -m http.server 5500 --directory docs
```

Open http://localhost:5500 and enter the access code from `.env`.

Without `ANTHROPIC_API_KEY` the server uses a short scripted stand-in for the model, so every screen and safety check can be tried with no API calls. Add the key to `.env` to talk to Claude.

## Tests

```bash
cd server
.venv/bin/python -m pytest tests -q
```

The tests run the real routes against a throwaway SQLite file and the scripted model.

Two more scripts call the real models and cost money, so they are run by hand:

- `tests/selfplay.py` plays simulated scammers against the decoy and simulated trainees against the drill agent (about $6 for the full run). `--rescore` scores a finished run again for free.
- `tests/redteam.py` sends 28 hostile messages (prompt injection, "are you a bot", abuse, codes given in words or Arabic digits) and checks each reply by rule (under $0.10). `--dry` checks the script itself for free.

Both write the numbers shown on the dashboard's Evidence tab.

`scripts/arabic_review.py` writes every Arabic line Kameen uses into one page for a native reviewer.

## Safety rules that live in code

- A drill starts only for a person with a consent record. There is no override.
- In a drill, digits and number words that look like a secret are masked before they are stored or sent to any model, and the drill ends on the same turn.
- The drill agent may only ask the scenario card's commit question. A reply that asks for a code or card number is replaced.
- The decoy may only say numbers from its synthetic kit or numbers the scammer said first.
- Scenario cards run only after a person sets `approved_by` on the card.

## Demo history

`server/scripts/seed.py` loads 25 synthetic past conversations in three linked campaigns, plus 43 drill results, so the dashboard has something to show. Everything in it is invented: IBANs use the synthetic bank code, phone numbers are made-up digits after the 050 prefix, and links sit under the reserved example domains. Run it with `--clear` to remove it, or `--cue` to print the IBAN and phone for the demo cue card. On the server, `SEED_DEMO=1` loads it once at start-up.

## Approving a scenario card

A drill runs only from a card whose `approved_by` field names the person who read and approved it. The three cards in `server/app/cards/scenarios/` are approved in English and in Arabic; each language is approved on its own, under `translations`. A new card, or a new translation, starts with `"approved_by": null` and is refused until someone puts their name there.

## Adding a scenario

```bash
cd server
.venv/bin/python scripts/new_scenario.py rental_deposit "A fake landlord wants a deposit before any viewing."
```

The script asks the strongest model for a card in English and Emirati Arabic, checks it against the card rules (a voice and a text opening line, a commit question that asks for nothing, no links or account numbers, three red flags, a three-point lesson) and saves it unapproved. It costs a few cents. Read the card, edit it if needed, then approve it. `scripts/arabic_review.py` adds its Arabic lines to the reviewer's page.

In every drill the agent may not give an account number, IBAN, wallet, link, email address or phone number: a made-up one could belong to someone real. A reply that contains one is replaced by the card's commit question.

## Telegram

Set `TELEGRAM_BOT_TOKEN` (from @BotFather) and restart. At start-up the server asks Telegram for the bot's name and points its webhook at itself, using `RENDER_EXTERNAL_URL` or `PUBLIC_URL` and `TELEGRAM_WEBHOOK_SECRET`. There is no other step.

- **Decoy.** Anyone who writes to the bot is treated as a scammer and gets the persona. The conversation shows on the dashboard like any other.
- **Drill on request.** `/drill` (or `/drill ar` for Arabic) makes the bot play a scammer against the person who asked, straight away. The first time, they are shown what will happen and must reply AGREE. The cooldown does not apply to a drill a person asks for themselves.
- **Switching roles.** A person who agreed to drills reaches the decoy by sending `/start`, and goes back to being the target with `/drill`.
- **Surprise drills.** On the dashboard's Drills tab an organiser creates an invite link for a group, with a scenario, a language and a window. A person who opens the link is shown what will happen and must reply AGREE; nothing is recorded otherwise, and no name is kept. One unmarked scam message then arrives at a random moment inside the window. The drill runs like any other and ends with the reveal and the lesson. `/leave` withdraws at once. A message nobody answers for twelve hours is revealed too, with the outcome `ignored`. The dashboard shows counts per invite, never who.

The server sends due drills once a minute, so it has to be running at that moment. On a host that sleeps when idle, a drill that came due during sleep is sent as soon as the server next wakes.

## Phishing-awareness emails

Set `RESEND_API_KEY` (from [resend.com](https://resend.com)) and restart. On the **Test yourself** page an organiser enters a group, a scenario, a language and a list of recipients, and attests that those people agreed to be tested. Kameen sends each one a simulated scam email built from an approved scenario card.

What the feature never does, by design:

- The email asks for nothing and the landing page has **no form**. The only thing recorded is whether the person clicked the link.
- It never imitates a real bank, company, government body or person. The sender name is a generic role from the card ("Refunds Office"), the sending address is yours, and the link is plainly on Kameen's own domain — the giveaway a careful reader is meant to catch.
- Clicking the link (`/t/<token>`) records the click once and immediately shows the person that it was a drill and what to watch for.

The dashboard lists, per campaign, who was emailed and who clicked. `MAIL_FROM_ADDRESS` sets the sending address (default `onboarding@resend.dev`, which Resend only delivers to the account owner until you verify a domain). The link host comes from `PUBLIC_URL` or `RENDER_EXTERNAL_URL`. Note that some email security scanners open links automatically, which can register as a click.

## Awareness calls by phone

Kameen can call a real number and run a drill by voice. It uses ElevenLabs' Twilio integration, so:

1. In Twilio, buy a number and verify the recipient's number (trial) or run a paid account.
2. Import the Twilio number into ElevenLabs (Agents → Phone numbers).
3. On the server set `ELEVENLABS_API_KEY` and `ELEVENLABS_PHONE_NUMBER_ID` (the imported number's ElevenLabs ID), then restart.

On the **Test yourself** page, an organiser enters a number, a scenario and a voice, and attests they are authorised. Kameen starts a drill conversation, opens the voice window, and asks ElevenLabs to dial out as the drill's agent. Each turn comes back to the server's `/v1/chat/completions` endpoint keyed by the conversation ID, exactly like a browser voice call, and the drill ends with the spoken reveal. It only calls numbers an organiser enters and attests to; the call is refused unless the key and number ID are set.

Note: the UAE regulates VoIP. Calls from a foreign carrier to UAE mobiles may be filtered or shown as international, and a local caller ID cannot be set. For a real rollout, use the local carriers; for a demo, call verified test numbers.

## Sessions that go quiet

Once a minute the server closes sessions nobody is in any more: a drill after 15 minutes without a message, a decoy session after two hours. A drill closed this way still gets the reveal and the lesson on its record, with the outcome `stopped`. Leaving the drill page does the same at once.

## Deploying

See the build plan for the Render, GitHub Pages and ElevenLabs steps. Keys go in `server/.env` locally and in Render's environment variables. They are never committed.
