# Kameen (كمين) · ScamShield AI

![Python 3.12](https://img.shields.io/badge/python-3.12-0B5C66) ![FastAPI](https://img.shields.io/badge/server-FastAPI-0B5C66) ![Claude](https://img.shields.io/badge/AI-Claude%20API-0B5C66) ![No build step](https://img.shields.io/badge/website-HTML%20%2B%20JS%2C%20no%20build-0B5C66)

One AI agent against phone and message scams. In **decoy mode** it answers scammers as a believable victim and captures the IBANs, phone numbers and links they give away. In **drill mode**, with a person's consent, it plays the scammer, stops before anything real is shared, and teaches.

| | |
|---|---|
| **Live demo** | https://ahmed-sharshar.github.io/kameen/ |
| **API server** | https://kameen-y4l2.onrender.com (health check: [`/health`](https://kameen-y4l2.onrender.com/health)) |
| **Project guide (PDF)** | [`docs/Kameen-Project-Guide.pdf`](docs/Kameen-Project-Guide.pdf): what Kameen does, the two modes, and every page and dashboard tab with screenshots |

This README is the practical companion to the guide: how to try the demo, how to run and test the code yourself, which tools and services it uses, and how to deploy your own copy.

> **Everything here is a simulation.** The demo is for awareness training. It is not affiliated with, or connected to, Abu Dhabi Police, TAMM, UAE Pass or the Aman service. Only test people who have agreed to be tested.

## Contents

1. [Try the live demo](#1-try-the-live-demo)
2. [Tech stack](#2-tech-stack)
3. [External APIs and services](#3-external-apis-and-services)
4. [Repository layout](#4-repository-layout)
5. [Run it on your computer](#5-run-it-on-your-computer)
6. [Configuration](#6-configuration)
7. [Testing](#7-testing)
8. [Helper scripts](#8-helper-scripts)
9. [HTTP API](#9-http-api)
10. [Deploy your own copy](#10-deploy-your-own-copy)
11. [Scenario cards and approval](#11-scenario-cards-and-approval)
12. [Troubleshooting](#12-troubleshooting)
13. [Responsible use](#13-responsible-use)

---

## 1. Try the live demo

Open **https://ahmed-sharshar.github.io/kameen/**. No account or access code is needed.

- The pill in the top-right corner reads **Waking up Kameen…** while the free-tier server starts. This can take up to a minute after a quiet period; it turns to **Ready** when the server answers.
- The demo uses the real Claude models. Conversations are stored on the demo server and are visible on its dashboard to anyone with the link, so **never type real personal details, card numbers or codes**. Made-up values, like the ones below, are fine.
- It works in any modern browser on desktop or phone. Voice calls need microphone permission.

### Test checklist

Work through these in order; each row says what you should see.

| # | Page | Do this | You should see |
|---|------|---------|----------------|
| 1 | Landing | Open the link | The two mode cards, and the pill turning to **Ready** |
| 2 | Play the scammer | Pick **Rajesh**, choose **WhatsApp**, press **Start text session**. Write as a scammer: `This is your bank. Transfer AED 500 to AE41 9990 4203 1885 6702 214 today.` | Rajesh replies in character; an **IBAN** intel card appears on the right with the quote it came from |
| 3 | Play the scammer | Send a link (`https://pay-check.example.net/a1`) and a call-back number (`050 000 7788`) | A **Link** and a **Phone** card; the **Stage** pill moves on as the conversation progresses |
| 4 | Play the scammer | Ask for his card number, then the code he received | He stalls, then reads out fake values (canaries), often a "wrong" card number first |
| 5 | Play the scammer | Press **End session**, then **Evidence pack** | **Canaries handed out** lists the fake values; the pack is a printable page with the indicators, canaries, a draft report and the transcript |
| 6 | Test yourself | Before enrolling, press **Try to drill someone who is not enrolled** | A refusal from the server: drills need recorded consent |
| 7 | Test yourself | Enrol with a nickname and a group, tick the consent box, pick **Bank security team**, **Text**, **English**, then **Start drill**. Reply as a hesitant person; when asked about the code, type any six digits | The digits show as `[REDACTED]`, the drill ends, and the reveal shows **You started to share a secret**, the lesson and the red flags |
| 8 | Test yourself | Press **Try another scenario** and choose **Arabic** | The whole drill runs in Arabic |
| 9 | Either page | Press **Start call** and allow the microphone (optional) | A spoken conversation; the same panels update |
| 10 | Dashboard → Sessions | Open the dashboard | Your sessions at the top of the list; select one to see its transcript and live events |
| 11 | Dashboard → Cases | Open the Cases tab | Your drill as a case, labelled **Fooled** or **Not fooled** |
| 12 | Dashboard → Campaigns | Open the Campaigns tab | Sessions that share an IBAN, number or link drawn as one linked campaign |

The IBAN above is synthetic: it has a valid checksum under the unassigned bank code `999`, and `example.net` is a reserved domain.

The **Test by email or phone** section of the drill page sends real emails and places real calls. Use it only with your own address or number, or with people who have agreed to be tested. Demo emails come from `scamshiel.ai@gmail.com` and may land in spam.

---

## 2. Tech stack

| Layer | Languages and tools |
|-------|---------------------|
| Server | **Python 3.12**, FastAPI, Uvicorn, SQLAlchemy 2 (async), httpx, python-dotenv |
| Database | **PostgreSQL** in production (psycopg), **SQLite** locally (aiosqlite). Tables are created on start-up |
| Website | **HTML, CSS and plain JavaScript**. No framework and no build step; the files in `docs/` are served as they are |
| Browser voice | ElevenLabs JavaScript client, loaded as an ES module from jsDelivr |
| Content | Scenario and persona cards in **JSON**; model prompts in **Markdown** (`server/app/prompts/`) |
| Tests | **pytest**, with a scripted stand-in model and a throwaway database |
| Hosting | **GitHub Pages** (website), **Render** (server and database), **GitHub Actions** (keep-alive ping), configured in **YAML** |
| Font | Readex Pro from Google Fonts, which covers both Latin and Arabic |

## 3. External APIs and services

Only the access code is required. Each service below switches on when its keys are set; without them, the related button shows a "not set up" note and everything else keeps working.

| Service | What Kameen uses it for | Settings (see [Configuration](#6-configuration)) |
|---------|-------------------------|-----------------------------------------------|
| **Anthropic Claude API** | Live replies (Claude Haiku 5.5), the per-turn director (Claude Sonnet 5.5), the per-session playbook and new scenario drafts (Claude Opus 5.5). Without a key, a scripted stand-in model runs at no cost | `ANTHROPIC_API_KEY`, `LIVE_MODEL`, `DIRECTOR_MODEL`, `PLAYBOOK_MODEL` |
| **ElevenLabs Conversational AI** | Speech in browser calls and outbound phone calls. ElevenLabs sends every spoken turn to Kameen's server as a custom language model | `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_EN`, `ELEVENLABS_AGENT_EN_IN`, `ELEVENLABS_AGENT_AR`, `LLM_SHARED_SECRET` |
| **Twilio** (through ElevenLabs) | The phone number that outbound awareness calls come from | `ELEVENLABS_PHONE_NUMBER_ID` |
| **Telegram Bot API** | Decoy chats, drills on request (`/drill`) and surprise drills | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET` |
| **SendGrid** (or **Resend**, or **SMTP**) | Phishing-awareness emails and case notifications | `SENDGRID_API_KEY` or `RESEND_API_KEY` or `SMTP_USER` + `SMTP_PASSWORD`, plus `MAIL_FROM_ADDRESS` |
| **Render** | Hosts the server and its PostgreSQL database (`render.yaml`) | `DATABASE_URL` is filled in by Render |
| **GitHub Pages** | Hosts the website from the `docs/` folder | `docs/config.js` |

## 4. Repository layout

```
kameen/
├── docs/                         The website (served by GitHub Pages)
│   ├── index.html                Landing page and access gate
│   ├── decoy.html                "Play the scammer": Kameen plays the victim
│   ├── drill.html                "Test yourself": drills, phishing emails, phone calls
│   ├── dashboard.html            Overview, Sessions, Campaigns, Drills, Cases, Evidence
│   ├── app.js                    Shared helpers: API calls, live stream, transcript rendering
│   ├── voice.js                  Browser voice calls through ElevenLabs
│   ├── config.js                 Which server to call, and the default access code
│   ├── style.css                 One stylesheet for every page, light and dark
│   └── Kameen-Project-Guide.pdf  The illustrated project guide
├── server/                       The Python server (Render)
│   ├── app/
│   │   ├── main.py               HTTP routes and the once-a-minute scheduler
│   │   ├── agent.py              One conversation turn: checks, model, reply, reveal
│   │   ├── guards.py             Safety checks on every message in and every reply out
│   │   ├── director.py           Playbook and per-turn stage steering
│   │   ├── extract.py            Intel extraction (patterns + model)
│   │   ├── canaries.py           Synthetic bait: card numbers, IBANs, codes
│   │   ├── campaigns.py          Links sessions that share intel
│   │   ├── cases.py, notify.py   Simulated police handoff and case emails
│   │   ├── phish.py, mail.py     Phishing-awareness emails and the email backends
│   │   ├── voice.py              ElevenLabs browser and outbound calls
│   │   ├── telegram.py           The Telegram bot
│   │   ├── seed.py               Synthetic demo history
│   │   ├── evidence.py           The printable evidence pack
│   │   ├── llm.py, fake.py       Claude client and the scripted stand-in model
│   │   ├── cards/                Persona and scenario cards (JSON)
│   │   ├── prompts/              System prompts for each model role (Markdown)
│   │   └── eval_latest.json      Metrics shown on the dashboard's Evidence tab
│   ├── scripts/                  Command-line helpers (see section 8)
│   ├── tests/                    Unit and end-to-end tests, red-team and self-play harnesses
│   ├── requirements.txt
│   └── .env.example              Every setting, documented
├── reports/                      Raw output of test runs (git-ignored)
├── render.yaml                   Render Blueprint: web service + PostgreSQL
└── .github/workflows/
    └── keepalive.yml             Pings the server every 10 minutes so it stays awake
```

## 5. Run it on your computer

### Prerequisites

- **Python 3.12** (the version the server is tested and deployed with)
- **Git**
- Optional: an Anthropic API key. Without one, Kameen runs with a scripted stand-in model, so you can try every screen and safety check for free.

### Steps (macOS and Linux)

```bash
git clone https://github.com/ahmed-sharshar/kameen.git
```

```bash
cd kameen/server
```

```bash
python3.12 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Optionally open `server/.env` and add your `ANTHROPIC_API_KEY`, or set `SEED_DEMO=1` to start with a synthetic history on the dashboard. Then start the server:

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

In a **second terminal**, from the `kameen` folder, serve the website:

```bash
python3 -m http.server 5500 --directory docs
```

Open **http://localhost:5500**. The page detects that it is running locally and talks to `http://localhost:8000`.

### Windows (PowerShell)

Use the same steps with these commands:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

and, in a second window from the `kameen` folder, `py -m http.server 5500 --directory docs`.

### Good to know

- The local database is `server/kameen.db` (SQLite). Delete it to start from an empty database.
- The website must be served from port **5500** (or another origin listed in `FRONTEND_ORIGIN`), otherwise the browser blocks its requests to the server.
- The default `ACCESS_CODE` matches `DEFAULT_CODE` in `docs/config.js`, so the site opens without asking for a code. If you change one, change the other, or use **Use a different code** on the landing page.
- Voice, Telegram and email need their own keys (see [section 10](#10-deploy-your-own-copy)). Telegram also needs a public address, so it cannot reach a server that only runs on `localhost`.

## 6. Configuration

All settings are environment variables. Locally they live in `server/.env`; on Render they are set in the dashboard. [`server/.env.example`](server/.env.example) lists every one with a comment.

| Group | Variable | Purpose |
|-------|----------|---------|
| Access | `ACCESS_CODE` **(required)** | Code the website sends with every request (`X-Access-Code` header) |
| | `ADMIN_CODE` | Allows uploading new test metrics (`POST /eval`) |
| | `FRONTEND_ORIGIN` | Website origins allowed to call the server, comma-separated |
| | `PUBLIC_URL` | Public address of the server for Telegram and email links (Render sets `RENDER_EXTERNAL_URL` itself) |
| Database | `DATABASE_URL` | PostgreSQL connection string; leave unset for SQLite |
| AI | `ANTHROPIC_API_KEY` | Enables the real models; empty means the scripted stand-in |
| | `LIVE_MODEL`, `DIRECTOR_MODEL`, `PLAYBOOK_MODEL` | Model IDs for each role |
| | `KAMEEN_FAKE_MODEL` | `1` forces the scripted stand-in |
| Voice | `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_EN`, `ELEVENLABS_AGENT_EN_IN`, `ELEVENLABS_AGENT_AR` | ElevenLabs key and the agent ID for each voice |
| | `ELEVENLABS_PHONE_NUMBER_ID` | Imported Twilio number, for outbound calls |
| | `LLM_SHARED_SECRET`, `VOICE_REQUIRE_SECRET` | Secret the voice agents send; `1` makes it mandatory |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET` | Bot token from @BotFather and the webhook secret |
| Email | `SENDGRID_API_KEY`, `RESEND_API_KEY`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_HOST`, `SMTP_PORT` | Email backends, tried in that order |
| | `MAIL_FROM_ADDRESS` | Verified sender address |
| Cases | `NOTIFY_BRAND` | Sender name on notifications (default "ScamShield AI") |
| | `CASE_ALERT_EMAIL`, `AUTO_EMAIL_NUMBER` | A Fooled case from this number is emailed to this address automatically |
| Drills | `DRILL_COOLDOWN_HOURS` | Hours before the same person can be drilled again (`0` for rehearsals) |
| | `DRILL_MIN_GROUP` | Smallest group shown on the dashboard |
| | `CANARY_BANK_CODE` | Bank code used in synthetic bait IBANs |
| Demo | `SEED_DEMO` | `1` loads the synthetic demo history at start-up |

Keys and secrets go in `.env` or the Render dashboard only. `.env` is git-ignored; never commit it.

## 7. Testing

All commands run from `server/`.

### Automated tests (free, about 10 seconds)

```bash
.venv/bin/python -m pytest tests -q
```

The suite (195 tests at the time of writing) runs the real routes against a throwaway SQLite database with the scripted stand-in model, so it makes no paid API calls and sends no real email. It covers the safety checks, consent enforcement, secret masking, the decoy and drill flows, voice and outbound calls, Telegram, phishing emails, the email backends, cases and the demo seed.

### Red-team set

28 hostile messages: prompt injection, "are you a bot?", abuse, and codes spelled out in words or written in Arabic digits. Each reply is checked by rule, not by a model.

```bash
.venv/bin/python tests/redteam.py --dry
```

`--dry` checks the harness with the stand-in model for free. Without `--dry` it calls the real models (a few cents) and adds a "Red-team set" line to the dashboard's Evidence tab. `--only <name>` runs the attacks whose name starts with `<name>`.

### Self-play evaluation (paid)

Simulated scammers against the decoy and simulated trainees (sceptical, hesitant, trusting) against the drill agent. It produces the metrics on the Evidence tab.

```bash
.venv/bin/python tests/selfplay.py --decoy 2 --drill 3
```

That is a small pilot. The full run (`--decoy 40 --drill 45`) costs about US$6. `--rescore ../reports/<file>.json` scores a finished run again without any model calls.

### Manual checks

- Check the server: `curl http://localhost:8000/health` should return `{"ok":true}`.
- Play a scripted conversation against a running server, then watch it appear on the dashboard:

```bash
.venv/bin/python scripts/try_chat.py decoy
```

## 8. Helper scripts

Run from `server/`.

| Command | What it does | Cost |
|---------|--------------|------|
| `.venv/bin/python scripts/seed.py` | Loads the synthetic demo history (does nothing if it is already loaded) | Free |
| `.venv/bin/python scripts/seed.py --clear` | Removes the demo history and nothing else | Free |
| `.venv/bin/python scripts/seed.py --cue` | Prints the IBAN and phone number for the demo cue card | Free |
| `.venv/bin/python scripts/try_chat.py decoy` | Plays a scripted scammer against a running server (`drill [scenario_id]` for a drill) | Free with the stand-in |
| `.venv/bin/python scripts/new_scenario.py <name> "<premise>"` | Drafts a new scenario card in English and Emirati Arabic, saved unapproved | A few cents |
| `.venv/bin/python scripts/arabic_review.py out.html` | Writes every Arabic line Kameen uses into one page for a native reviewer | Free |

`try_chat.py` talks to `http://localhost:8000` by default; set `KAMEEN_URL` to use another server.

## 9. HTTP API

The website is the main client, but every feature is available over HTTP. Send the access code in the `X-Access-Code` header. Interactive documentation is generated at `/docs` on any running server (for example http://localhost:8000/docs).

| Method and path | Purpose |
|-----------------|---------|
| `GET /health` | Liveness check (no code needed) |
| `GET /cards` | Personas and approved scenarios |
| `POST /enrolments` | Record a person's consent to be drilled |
| `POST /sessions` | Start a decoy or drill session |
| `POST /chat` | Send a message in a session and get the agent's reply |
| `GET /events/stream?conversation_id=…` | Live events for a session: messages, stage changes, intel, guardrail events (Server-Sent Events) |
| `GET /sessions`, `GET /sessions/{id}` | List sessions, or one session with transcript, intel and canaries |
| `POST /sessions/{id}/kill`, `POST /sessions/{id}/rating` | End a session; rate how believable the victim was |
| `GET /sessions/{id}/evidence` | Printable evidence pack (HTML) |
| `POST /voice/session`, `GET`/`POST /voice/outbound` | Open a browser voice call; check or place an outbound phone call |
| `POST /v1/chat/completions` | Model endpoint that ElevenLabs calls for every voice turn |
| `GET /campaigns`, `GET /drills/summary` | Campaign graph; drill results by outcome, scenario and group |
| `GET`/`POST /invites` | Surprise-drill invite links for Telegram |
| `GET`/`POST /phish`, `GET /t/{token}` | Phishing-awareness campaigns; the page a recipient's link opens |
| `GET /cases`, `POST /cases/{ref}/email` | Simulated police cases; email one to an address |
| `GET /eval/latest`, `POST /eval` | Test metrics (upload needs `X-Admin-Code`) |
| `POST /telegram/webhook` | Telegram updates (verified with the webhook secret) |

## 10. Deploy your own copy

### Server and database on Render

1. Fork this repository.
2. In Render, choose **New → Blueprint** and select your fork. `render.yaml` creates the web service and a PostgreSQL database.
3. Fill in the values Render asks for (`ACCESS_CODE`, `ANTHROPIC_API_KEY`, and any optional keys). Render generates `ADMIN_CODE`, `LLM_SHARED_SECRET` and `TELEGRAM_WEBHOOK_SECRET` for you.
4. Set `FRONTEND_ORIGIN` to your GitHub Pages origin, for example `https://<your-user>.github.io`.
5. Check `https://<your-service>.onrender.com/health` returns `{"ok":true}`.

> **Schema changes:** the server creates missing tables on start-up but does not migrate existing ones. Render's PostgreSQL keeps its data between deploys, so a new column on an existing table must be added by hand (`ALTER TABLE`) or the database reset.

### Website on GitHub Pages

1. In `docs/config.js`, set `HOSTED_API` to your Render URL and `DEFAULT_CODE` to your `ACCESS_CODE` (or `''` to make visitors type it).
2. In the repository settings, open **Pages** and publish from the `main` branch, folder `/docs`.
3. In `.github/workflows/keepalive.yml`, change the URL to your server's `/health`, so the free-tier server stays awake.

### Voice (ElevenLabs and Twilio)

1. In ElevenLabs, create three agents: English, Indian English and Arabic.
2. For each agent, choose a **Custom LLM** with server URL `https://<your-service>.onrender.com/v1` and use `LLM_SHARED_SECRET` as its API key.
3. Include `kameen_conversation_id={{kameen_conversation_id}}` in the agent's system prompt and set its first message to `{{opening_line}}`. The server fills both in for every call.
4. Put the agent IDs in `ELEVENLABS_AGENT_EN`, `ELEVENLABS_AGENT_EN_IN` and `ELEVENLABS_AGENT_AR`, and your key in `ELEVENLABS_API_KEY`.
5. For outbound calls, buy a Twilio number (on a trial account, verify each number you will call), import it under **Agents → Phone numbers** in ElevenLabs, and set `ELEVENLABS_PHONE_NUMBER_ID`.

The UAE regulates VoIP. Calls from a foreign carrier to UAE mobiles may be filtered or shown as international, so use verified test numbers for demos and a local carrier for any real rollout.

### Telegram

Create a bot with **@BotFather**, set `TELEGRAM_BOT_TOKEN` and restart. On start-up the server points the bot's webhook at itself using `RENDER_EXTERNAL_URL` (or `PUBLIC_URL`). There is no other step.

### Email

Render's free plan blocks outbound SMTP, so use an HTTP provider there:

1. In **SendGrid**, open **Settings → Sender Authentication → Single Sender** and verify the address you will send from. No domain is needed.
2. Create an API key and set `SENDGRID_API_KEY`, with `MAIL_FROM_ADDRESS` set to the verified address.
3. Set `CASE_ALERT_EMAIL` and `AUTO_EMAIL_NUMBER` to your own values.

Mail sent from a free address (such as Gmail) may land in spam. For reliable inbox delivery, authenticate your own domain (SPF, DKIM and DMARC). Resend works too, but its shared sender only reaches the account owner until a domain is verified. SMTP (for example a Gmail App Password) works locally and on hosts that allow it.

## 11. Scenario cards and approval

Drills run only from scenario cards in `server/app/cards/scenarios/`, and only after a named person approves them.

1. Draft a card: `.venv/bin/python scripts/new_scenario.py rental_deposit "A fake landlord wants a deposit before any viewing."` The script checks the card's rules (an opening line for voice and text, a commit question that asks for nothing, no links or account numbers, three red flags, a three-point lesson) and saves it with `"approved_by": null`.
2. Read the card and edit it if needed.
3. Approve it by putting your name and the date in `approved_by`. Each language is approved separately, under `translations`.
4. Run `scripts/arabic_review.py` so a native speaker can review the new Arabic lines.

Personas live in `server/app/cards/personas/`, and the prompts for each model role in `server/app/prompts/`.

## 12. Troubleshooting

| Symptom | Likely cause and fix |
|---------|----------------------|
| The pill stays on **Waking up Kameen…** | The free server is starting; wait up to a minute and reload. Locally, check that uvicorn is running on port 8000 |
| **That code was not accepted** | The page's code differs from the server's `ACCESS_CODE`. Press **Use a different code**, or align `DEFAULT_CODE` in `docs/config.js` |
| The browser console shows a CORS error | Add the site's origin (for example `http://localhost:5500`) to `FRONTEND_ORIGIN` and restart the server |
| A drill is refused | The person has not enrolled, or `DRILL_COOLDOWN_HOURS` has not passed since their last drill |
| **Voice is not configured** or **calls are not set up** | Add the ElevenLabs agent IDs, or for phone calls the API key and `ELEVENLABS_PHONE_NUMBER_ID` |
| Email fails with `403` from Resend | Resend's shared sender only reaches the account owner. Use SendGrid single-sender verification |
| Email fails with `Network is unreachable` on Render | Render blocks SMTP. Use `SENDGRID_API_KEY` |
| A new feature works locally but not on Render | The production database is older than the code; see the schema note in [section 10](#10-deploy-your-own-copy) |
| Port 8000 or 5500 is already in use | Stop the other process, or pick another port (the website's port must be listed in `FRONTEND_ORIGIN`) |

## 13. Responsible use

- Drill, email or call **only people who have agreed** to be tested. The server refuses drills without a consent record, and the email and phone forms ask you to confirm consent.
- Never send anything as the police, a bank or any real organisation. Notifications use `NOTIFY_BRAND`, and phishing emails use generic roles and your own sending address.
- Keep every key in `.env` or your host's settings, and rotate keys that were shared during an event.
- The full list of safeguards built into the code is in section 6 of the [project guide](docs/Kameen-Project-Guide.pdf).

---

Built for the Abu Dhabi Police hackathon, 24–25 November 2026. No open-source licence has been chosen yet; please ask before reusing the code.
