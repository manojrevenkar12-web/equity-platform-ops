from epo.guard.plan import analyse
from epo.world.changes import ChangesWorld


def _plan(*rcs, ai=False):
    return {"resource_changes": list(rcs), "commit_trailers": ["Co-Authored-By: Claude <noreply@anthropic.com>"] if ai else []}


def _rc(typ, actions, after, before=None, addr="x.y"):
    return {"address": addr, "type": typ, "change": {"actions": actions, "before": before, "after": after}}


def test_obvious_harm_is_blocked(guard_cfg):
    assert analyse(_plan(_rc("google_project_iam_member", ["create"], {"role": "roles/owner", "member": "allUsers"})), guard_cfg).decision == "block"
    fw = _rc("google_compute_firewall", ["create"], {"source_ranges": ["0.0.0.0/0"], "allow": [{"ports": ["27017"]}]})
    assert analyse(_plan(fw), guard_cfg).decision == "block"
    halves = _rc("google_compute_firewall", ["create"], {"source_ranges": ["0.0.0.0/1", "128.0.0.0/1"], "allow": [{"ports": ["27017"]}]})
    assert analyse(_plan(halves), guard_cfg).decision == "block"
    db = _rc("mongodbatlas_cluster", ["delete", "create"], {"x": 1}, {"x": 0})
    assert analyse(_plan(db), guard_cfg).decision == "block"


def test_the_public_load_balancer_is_not_a_finding(guard_cfg):
    lb = _rc("google_compute_firewall", ["create"], {"source_ranges": ["0.0.0.0/0"], "allow": [{"ports": ["443"]}], "target_tags": ["public-lb"]})
    assert analyse(_plan(lb), guard_cfg).decision == "apply"


def test_ai_written_iam_changes_go_to_a_person(guard_cfg):
    sa = _rc("google_project_iam_member", ["create"], {"role": "roles/storage.objectViewer", "member": "serviceAccount:a@p.iam.gserviceaccount.com"})
    assert analyse(_plan(sa), guard_cfg).decision == "apply"
    assert analyse(_plan(sa, ai=True), guard_cfg).decision == "review"


def test_switching_off_protection_needs_review(guard_cfg):
    rc = _rc("mongodbatlas_cluster", ["update"], {"termination_protection_enabled": False}, {"termination_protection_enabled": True})
    assert analyse(_plan(rc), guard_cfg).decision == "review"


def test_benign_generated_changes_are_never_blocked(cfg, guard_cfg):
    w = ChangesWorld(cfg, 3101)
    benign = [c for wk in range(3) for c in w.week(wk) if not c.harmful]
    assert benign and all(analyse(c.plan, guard_cfg).decision != "block" for c in benign)


def test_an_outside_service_account_slips_past_the_rules_but_not_the_ai_tier(guard_cfg):
    wi = _rc("google_service_account_iam_member", ["create"],
             {"role": "roles/iam.workloadIdentityUser", "member": "serviceAccount:x@other-vendor.iam.gserviceaccount.com"})
    assert analyse(_plan(wi), guard_cfg).decision == "apply"          # a known gap, measured in the evaluation
    assert analyse(_plan(wi, ai=True), guard_cfg).decision == "review"
