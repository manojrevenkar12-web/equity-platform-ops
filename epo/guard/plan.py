"""A guard on Terraform plans before they are applied, stricter for changes written with an AI assistant.

It reads `terraform show -json` output and finds what a reviewer would worry about:

- **Block:** public principals in IAM; `roles/owner` to a person or group; the internet on database, SSH or
  workflow-admin ports; deleting or replacing stateful resources (databases, keys, buckets, clusters);
  `cluster-admin` for the default service account.
- **Review:** broad roles (`editor`, `iam.*`) to people or groups; switching off termination or deletion
  protection; IAM changes in an AI-written change.
- **Info:** everything else, with a risk score from what the plan touches.

The decision: block on any block finding; ask a person on any review finding, or when an AI-written change scores
above the AI threshold; otherwise apply after CI. Rules and thresholds come from `config/guard.yaml`.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field

STATEFUL = {"mongodbatlas_cluster", "google_sql_database_instance", "google_kms_crypto_key", "google_storage_bucket",
            "google_container_cluster", "google_compute_disk"}
IAM = {"google_project_iam_member", "google_project_iam_binding", "google_storage_bucket_iam_member",
       "google_service_account_iam_member"}
PUBLIC = {"allUsers", "allAuthenticatedUsers"}
BROAD_ROLES = ("roles/editor", "roles/iam.")
PROTECTION = ("termination_protection_enabled", "deletion_protection")


@dataclass
class Finding:
    level: str          # block | review | info
    address: str
    rule: str
    detail: str


@dataclass
class Verdict:
    decision: str       # block | review | apply
    risk: float
    ai: bool
    findings: list[Finding] = field(default_factory=list)


def _ports(spec: str) -> range:
    a, _, b = spec.partition("-")
    return range(int(a), int(b or a) + 1)


def _is_internet(ranges: list[str]) -> bool:
    """Open to the internet: 0.0.0.0/0, or ranges that together cover half of the IPv4 space or more
    (0.0.0.0/1 plus 128.0.0.0/1 is the whole internet written in two lines)."""
    covered = 0
    for r in ranges or []:
        try:
            net = ipaddress.ip_network(r, strict=False)
        except ValueError:
            continue
        if net.prefixlen == 0:
            return True
        if net.version == 4:
            covered += net.num_addresses
    return covered >= 2**31


def analyse(plan: dict, cfg: dict) -> Verdict:
    sensitive = set(cfg["sensitive_ports"])
    public_ok = set(cfg["public_ports"])
    ai = any("Co-Authored-By" in t and any(k in t for k in cfg["ai_trailer_names"]) for t in plan.get("commit_trailers", []))
    out: list[Finding] = []
    risk = 0.0
    for rc in plan.get("resource_changes", []):
        addr, typ = rc["address"], rc["type"]
        actions = rc["change"]["actions"]
        before, after = rc["change"].get("before") or {}, rc["change"].get("after") or {}
        if "delete" in actions:
            risk += cfg["risk"]["delete"]
            if typ in STATEFUL:
                verb = "replaces" if "create" in actions else "deletes"
                out.append(Finding("block", addr, "stateful_delete", f"{verb} a stateful {typ}"))
        if typ in IAM and after:
            risk += cfg["risk"]["iam"]
            member, role = after.get("member", ""), after.get("role", "")
            if member in PUBLIC:
                out.append(Finding("block", addr, "public_principal", f"{role} to {member}"))
            elif role == "roles/owner" and not member.startswith("serviceAccount:"):
                out.append(Finding("block", addr, "owner_to_people", f"{role} to {member}"))
            elif role.startswith(BROAD_ROLES) and not member.startswith("serviceAccount:"):
                out.append(Finding("review", addr, "broad_role", f"{role} to {member}"))
            elif ai:
                out.append(Finding("review", addr, "ai_iam_change", f"{role} to {member} in an AI-written change"))
        if typ == "google_compute_firewall" and after:
            risk += cfg["risk"]["network"]
            if _is_internet(after.get("source_ranges", [])):
                ports = set()
                for a in after.get("allow", []):
                    for p in a.get("ports", []) or ["0-65535"]:
                        ports |= set(_ports(p))
                hit = sorted(ports & sensitive)
                if hit:
                    out.append(Finding("block", addr, "internet_to_sensitive_port", f"0.0.0.0/0 to {hit[:5]}"))
                elif not ports <= public_ok or "public-lb" not in after.get("target_tags", []):
                    out.append(Finding("review", addr, "internet_ingress", f"0.0.0.0/0 to {len(ports)} ports"))
        if typ == "kubernetes_cluster_role_binding" and after:
            risk += cfg["risk"]["iam"]
            role = (after.get("role_ref") or [{}])[0].get("name")
            subj = after.get("subject") or []
            if role == "cluster-admin" and any(s.get("name") in ("default", "system:authenticated") for s in subj):
                out.append(Finding("block", addr, "cluster_admin_default", "cluster-admin for the default account"))
        for key in PROTECTION:
            if before.get(key) is True and after.get(key) is False:
                out.append(Finding("review", addr, "protection_off", f"{key} switched off"))
                risk += cfg["risk"]["delete"]
    if any(f.level == "block" for f in out):
        decision = "block"
    elif any(f.level == "review" for f in out) or (ai and risk >= cfg["ai_review_risk"]) or risk >= cfg["review_risk"]:
        decision = "review"
    else:
        decision = "apply"
    return Verdict(decision, risk, ai, out)
