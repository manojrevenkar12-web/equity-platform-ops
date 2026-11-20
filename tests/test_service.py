from fastapi.testclient import TestClient

from epo.service.api import app

c = TestClient(app)


def test_results_and_gate():
    r = c.get("/api/results").json()
    assert "platform" in r["dev"]["designs"] and isinstance(r["gate"]["dev"], list)


def test_guard_on_every_example_matches_the_cli_rules():
    ex = c.get("/api/guard/examples").json()
    got = {e["name"]: c.post("/api/guard", json={"plan": e["plan"], "commits": e["commits"]}).json()["decision"] for e in ex}
    assert got["db_open"] == "block" and got["replace_database"] == "block" and got["routine"] == "apply"


def test_guard_rejects_something_that_is_not_a_plan():
    assert c.post("/api/guard", json={"plan": {"hello": 1}}).status_code == 422
