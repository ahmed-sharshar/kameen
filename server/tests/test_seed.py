"""The synthetic demo history: loads once, links into campaigns, and can be removed cleanly."""
from app import canaries, db, seed


def test_seed_values_are_synthetic():
    for campaign in seed.CAMPAIGNS.values():
        for key in ("iban", "iban2"):
            if key in campaign:
                assert canaries.iban_ok(campaign[key]) and campaign[key][4:7] == "999"   # the synthetic bank code
        assert campaign["phone"].startswith("050") and len(campaign["phone"]) == 10      # made-up digits after 050
        assert ".example." in campaign["url"]                                            # a reserved domain
    assert sum(c["count"] for c in seed.CAMPAIGNS.values()) + len(seed.SINGLES) == 25


def test_seed_loads_linked_campaigns_once_and_clears(client, code):
    before = len(client.get("/sessions", headers=code).json()["sessions"])
    drills_before = client.get("/drills/summary", headers=code).json()["total"]

    assert client.portal.call(seed.run) == 25
    assert client.portal.call(seed.run) == 0                     # already loaded: nothing is added twice
    client.portal.call(db.put_value, "seed", {"version": seed.VERSION - 1})
    assert client.portal.call(seed.run) == 25                    # an older set is replaced, not added to

    sessions = client.get("/sessions", headers=code).json()["sessions"]
    assert len(sessions) == before + 25
    graph = client.get("/campaigns", headers=code).json()
    cue_iban = "iban:" + seed.CAMPAIGNS["safe_account"]["iban"]
    assert sum(1 for edge in graph["edges"] if edge["target"] == cue_iban) == 9
    assert graph["campaigns"] >= 3

    summary = client.get("/drills/summary", headers=code).json()
    assert summary["total"] == drills_before + 43
    groups = {g["group"]: g["total"] for g in summary["by_group"]}
    assert groups["Operations"] == 14 and "HR" not in groups     # a group of three is never shown by name

    # A scammer who names the cue-card IBAN in a new session lands in the seeded campaign.
    conv_id = client.post("/sessions", json={"mode": "decoy", "persona_id": "rajesh"}, headers=code).json()["conversation_id"]
    client.post("/chat", json={"conversation_id": conv_id,
                               "text": "Move your balance to " + seed.CUE_CARD["iban"] + " now."}, headers=code)
    for _ in range(40):
        graph = client.get("/campaigns", headers=code).json()
        if {"source": conv_id, "target": cue_iban} in graph["edges"]:
            break
        import time
        time.sleep(0.05)
    assert {"source": conv_id, "target": cue_iban} in graph["edges"]

    assert client.portal.call(seed.clear) == 25
    assert len(client.get("/sessions", headers=code).json()["sessions"]) == before + 1
    assert client.get("/drills/summary", headers=code).json()["total"] == drills_before
