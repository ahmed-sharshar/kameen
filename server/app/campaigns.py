"""Campaign linking: conversations that share an indicator belong to one operation."""
from . import db

LINKING_TYPES = {"iban", "phone", "url", "payment_link", "wallet", "account"}


async def graph():
    """Nodes and edges for the dashboard graph, and the number of linked campaigns."""
    by_value, conversations = {}, set()
    for row in await db.list_intel():
        if row["type"] not in LINKING_TYPES:
            continue
        key = (row["type"], row["normalised_value"])
        by_value.setdefault(key, {"label": row["value"], "conversations": set()})
        by_value[key]["conversations"].add(row["conversation_id"])
        conversations.add(row["conversation_id"])

    parent = {c: c for c in conversations}

    def root(c):
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    nodes = [{"id": c, "label": c[:8], "kind": "conversation"} for c in sorted(conversations)]
    edges = []
    for (kind, value), entry in by_value.items():
        node_id = f"{kind}:{value}"
        nodes.append({"id": node_id, "label": entry["label"], "kind": "intel", "type": kind})
        members = sorted(entry["conversations"])
        for conv_id in members:
            edges.append({"source": conv_id, "target": node_id})
            parent[root(conv_id)] = root(members[0])

    sizes = {}
    for c in conversations:
        sizes[root(c)] = sizes.get(root(c), 0) + 1
    return {"nodes": nodes, "edges": edges, "campaigns": sum(1 for n in sizes.values() if n >= 2)}
