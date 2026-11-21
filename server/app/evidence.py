"""The evidence pack: one self-contained HTML page that the browser prints to PDF."""
import time
from html import escape

STYLE = """
body{font:15px/1.5 -apple-system,'Segoe UI',Tahoma,sans-serif;color:#16202b;max-width:820px;margin:32px auto;padding:0 20px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:28px 0 8px;border-bottom:1px solid #c9d1d9;padding-bottom:4px}
.note{background:#fff6dd;border:1px solid #e3c770;padding:10px 14px;border-radius:6px;font-size:14px}
table{border-collapse:collapse;width:100%;font-size:14px} th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #e3e8ee;vertical-align:top}
th{font-weight:600;color:#4a5b6c} code{font-family:ui-monospace,Menlo,monospace;font-size:13px;word-break:break-all}
.them{color:#8a1f1f} .us{color:#1d4f91} .meta{color:#5a6b7c;font-size:13px} pre{white-space:pre-wrap;background:#f4f6f8;padding:12px;border-radius:6px;font-size:13px}
button{font:inherit;padding:6px 14px} @media print{button{display:none} body{margin:0}}
"""


def _when(epoch):
    return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(epoch))


def render(conv, messages, intel, canaries):
    rows = "".join(
        f"<tr><td>{escape(i['type'])}</td><td><code>{escape(i['value'])}</code></td>"
        f"<td>“{escape(i['quote'])}”</td><td>{escape(i['source'])}</td></tr>" for i in intel
    ) or "<tr><td colspan='4'>No indicators were extracted.</td></tr>"
    bait = "".join(f"<tr><td>{escape(c['kind'])}</td><td><code>{escape(c['value'])}</code></td></tr>"
                   for c in canaries) or "<tr><td colspan='2'>None issued.</td></tr>"
    labels = {"agent": ("us", "Decoy" if conv.mode == "decoy" else "Drill agent"),
              "counterpart": ("them", "Other party")}
    transcript = "".join(
        f"<tr><td class='meta'>{_when(m['created_at'])[11:16]}</td>"
        f"<td class='{labels[m['speaker']][0]}'>{labels[m['speaker']][1]}</td><td dir='auto'>{escape(m['text'])}</td></tr>"
        for m in messages if m["speaker"] in labels)
    report = "\n".join(
        ["Report type: suspected fraud attempt (captured by AI decoy)",
         f"Date: {_when(conv.started_at)}", f"Channel: {conv.channel}",
         "Indicators:"] + [f"  - {i['type']}: {i['value']}" for i in intel] +
        ["Summary: the other party approached the decoy and requested payment details or credentials.",
         "Attachments: full transcript below."])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Kameen evidence pack</title>
<style>{STYLE}</style></head><body>
<h1>Kameen evidence pack</h1>
<p class="meta">Session {escape(conv.id)} · {escape(conv.mode)} · {escape(conv.channel)} · started {_when(conv.started_at)}</p>
<p class="note">Produced by an AI decoy. Every card number, IBAN and code the decoy gave out is synthetic bait,
listed below. An officer should verify each indicator against the transcript before acting on it.</p>
<button onclick="window.print()">Save as PDF</button>
<h2>Extracted indicators</h2>
<table><tr><th>Type</th><th>Value</th><th>Supporting quote</th><th>Found by</th></tr>{rows}</table>
<h2>Canaries issued (synthetic)</h2>
<table><tr><th>Kind</th><th>Value</th></tr>{bait}</table>
<h2>Pre-filled report for the Aman service (draft, not sent)</h2>
<pre>{escape(report)}</pre>
<h2>Full transcript</h2>
<table><tr><th>Time</th><th>Speaker</th><th>Text</th></tr>{transcript}</table>
</body></html>"""
