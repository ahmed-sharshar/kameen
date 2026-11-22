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

## Sessions that go quiet

Once a minute the server closes sessions nobody is in any more: a drill after 15 minutes without a message, a decoy session after two hours. A drill closed this way still gets the reveal and the lesson on its record, with the outcome `stopped`. Leaving the drill page does the same at once.

## Deploying

See the build plan for the Render, GitHub Pages and ElevenLabs steps. Keys go in `server/.env` locally and in Render's environment variables. They are never committed.
