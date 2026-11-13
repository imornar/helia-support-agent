#!/usr/bin/env python3
"""Consistency checks for the Helia design repo. Run: python3 scripts/validate.py

Exit code 0 when every check passes, 1 otherwise. Requires: pyyaml, jsonschema.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
STANDARDS = ROOT / "standards"
MANIFEST_DIR = STANDARDS / "manifests"
POLICY_FILE = STANDARDS / "approval-policy.example.yaml"
POLICY_TESTS_FILE = STANDARDS / "policy-tests.yaml"
SCHEMA_FILE = STANDARDS / "schema" / "tool-manifest.schema.json"
DESIGN_FILE = ROOT / "docs" / "design.md"
STANDARD_FILE = ROOT / "docs" / "team-standard.md"
GREPTILE_RULES = ROOT / ".greptile" / "rules.md"

SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv"}
TEXT_SUFFIXES = {".md", ".mdc", ".yaml", ".yml", ".json", ".py", ".sh", ""}
DERIVED_ONLY_INPUTS = re.compile(r"^(customer_id|currency|amount\w*|\w*_minor)$")
SAFE_BUILTINS = {"any": any, "all": all, "len": len, "min": min, "max": max}

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def repo_files() -> list[Path]:
    return [
        p for p in ROOT.rglob("*")
        if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
    ]


# ---------------------------------------------------------------- parsing

def check_parse(files: list[Path]) -> None:
    for p in files:
        try:
            if p.suffix in {".yaml", ".yml"}:
                yaml.safe_load(p.read_text())
            elif p.suffix == ".json":
                json.loads(p.read_text())
        except Exception as exc:  # noqa: BLE001
            fail(f"{rel(p)}: does not parse: {exc}")


# -------------------------------------------------------------- manifests

def load_manifests() -> dict[str, dict]:
    schema = json.loads(SCHEMA_FILE.read_text())
    validator = Draft202012Validator(schema)
    template = yaml.safe_load((STANDARDS / "tool-manifest.template.yaml").read_text())
    for err in validator.iter_errors(template):
        fail(f"tool-manifest.template.yaml: schema: {err.json_path}: {err.message}")

    manifests: dict[str, dict] = {}
    for p in sorted(MANIFEST_DIR.glob("*.manifest.yaml")):
        m = yaml.safe_load(p.read_text())
        for err in validator.iter_errors(m):
            fail(f"{rel(p)}: schema: {err.json_path}: {err.message}")
        if not isinstance(m, dict) or "name" not in m:
            continue
        name = m["name"]
        if p.name != f"{name}.manifest.yaml":
            fail(f"{rel(p)}: file name must be {name}.manifest.yaml")
        check_manifest_semantics(rel(p), m)
        manifests[name] = m
    if not manifests:
        fail("standards/manifests: no manifests found")
    return manifests


def check_manifest_semantics(where: str, m: dict) -> None:
    write = m.get("side_effect") == "write"
    undo = m.get("undo", {})
    if write and undo.get("kind") == "none" and m.get("risk_tier") != "R3":
        fail(f"{where}: a write with undo.kind none must be risk_tier R3")
    if undo.get("kind") == "before_image" and undo.get("before_image_store") != "compensation_store":
        fail(f"{where}: before_image undo must use compensation_store, never the audit log")
    if m.get("kill_switch_flag") != f"agent.tool.{m.get('name')}.enabled":
        fail(f"{where}: kill_switch_flag must be agent.tool.{m.get('name')}.enabled")

    for field, spec in (m.get("inputs") or {}).items():
        source = spec.get("source")
        if DERIVED_ONLY_INPUTS.match(field) and source == "model":
            fail(f"{where}: input '{field}' must never be source: model")
        if field == "customer_id" and source != "case":
            fail(f"{where}: customer_id must be source: case")
        if source == "model":
            bounded = any(k in spec for k in ("values", "candidates", "max", "max_length"))
            if not bounded:
                fail(f"{where}: model input '{field}' needs values, candidates, max or max_length")

    if write:
        for key in ("idempotency", "verify"):
            if key not in m:
                fail(f"{where}: write tools need '{key}'")
        if m.get("retries", {}).get("unknown_outcome") != "read_back_before_retry":
            fail(f"{where}: write tools must read back before retrying an unknown outcome")
        states = m.get("verify", {}).get("states", {})
        if states.get("pending") == "done":
            fail(f"{where}: a pending state must never count as done")


# ----------------------------------------------------------------- policy

def load_policy(manifests: dict[str, dict]) -> dict:
    policy = yaml.safe_load(POLICY_FILE.read_text())
    where = rel(POLICY_FILE)
    rules = policy.get("rules", [])

    if policy.get("default_decision") != "human":
        fail(f"{where}: default_decision must be human")

    ids = [r.get("id") for r in rules]
    for dup in {i for i in ids if ids.count(i) > 1}:
        fail(f"{where}: duplicate rule id {dup}")

    tools_in_policy = {r.get("tool") for r in rules}
    for r in rules:
        if r.get("tool") not in manifests:
            fail(f"{where}: rule {r.get('id')} targets unknown tool {r.get('tool')}")
        if r.get("decision") not in {"auto", "human", "deny"}:
            fail(f"{where}: rule {r.get('id')} has invalid decision")
    for name in manifests:
        if name not in tools_in_policy:
            fail(f"{where}: tool {name} has a manifest but no policy rule")

    for name, m in manifests.items():
        tool_rules = [r for r in rules if r.get("tool") == name]
        autos = [r for r in tool_rules if r.get("decision") == "auto"]
        floors = [r for r in tool_rules if r.get("decision") in {"human", "deny"}]
        tier = m.get("risk_tier")
        for r in autos:
            if tier != "R0":
                if r.get("enabled", True):
                    fail(f"{where}: auto rule {r['id']} on {tier} tool must start enabled: false")
                if not r.get("cap"):
                    fail(f"{where}: auto rule {r['id']} must declare a cap")
            if tier == "R3" and not r.get("standing_approval", {}).get("approved_by_role"):
                fail(f"{where}: auto rule {r['id']} on an R3 tool needs standing_approval.approved_by_role")
        if autos and floors:
            if min(f["priority"] for f in floors) <= max(a["priority"] for a in autos):
                fail(f"{where}: every floor for {name} must outrank every auto rule")

    token = policy.get("approvals", {}).get("token", {})
    if token.get("consume") != "atomic":
        fail(f"{where}: approvals.token.consume must be atomic")
    if token.get("stale_policy") != "reject":
        fail(f"{where}: approvals.token.stale_policy must be reject")
    if "policy_version" not in token.get("bind", []):
        fail(f"{where}: approval tokens must bind policy_version")
    if policy.get("approvals", {}).get("audit_fail_mode") != "closed":
        fail(f"{where}: approvals.audit_fail_mode must be closed")
    return policy


def to_ns(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{k: to_ns(v) for k, v in value.items()})
    if isinstance(value, list):
        return [to_ns(v) for v in value]
    return value


def evaluate(policy: dict, tool: str, ctx: dict, enable: set[str], extra: list[dict]):
    """Reference evaluator. Rule expressions are trusted repo content, not user input."""
    rules = [dict(r) for r in policy["rules"]] + [dict(r) for r in extra]
    active = [
        r for r in rules
        if r.get("tool") == tool and (r.get("enabled", True) or r.get("id") in enable)
    ]
    active.sort(key=lambda r: r["priority"], reverse=True)
    names = {k: to_ns(v) for k, v in ctx.items()}
    for r in active:
        expr = r.get("when")
        if expr is None or eval(expr, {"__builtins__": SAFE_BUILTINS}, names):  # noqa: S307
            return r["decision"], r.get("id")
    return policy["default_decision"], None


def run_policy_tests(policy: dict) -> int:
    data = yaml.safe_load(POLICY_TESTS_FILE.read_text())
    defaults = data.get("defaults", {})
    rule_ids = {r["id"] for r in policy["rules"]}
    count = 0
    for case in data.get("cases", []):
        count += 1
        name = case.get("name", "?")
        enable = set(case.get("enable", []))
        for rid in enable - rule_ids:
            fail(f"policy-tests: '{name}' enables unknown rule {rid}")
        ctx = {k: v for k, v in defaults.items()}
        for k in defaults:
            if k in case:
                ctx[k] = case[k]
        ctx.update(case.get("params", {}))
        try:
            decision, rid = evaluate(policy, case["tool"], ctx, enable, case.get("extra_rules", []))
        except Exception as exc:  # noqa: BLE001
            fail(f"policy-tests: '{name}' raised {exc!r}")
            continue
        expect = case["expect"]
        if decision != expect["decision"] or ("rule" in expect and rid != expect["rule"]):
            fail(f"policy-tests: '{name}' expected {expect}, got decision={decision} rule={rid}")
    return count


# ------------------------------------------------------- cross-file sync

def check_design_table(manifests: dict[str, dict], policy: dict) -> None:
    text = DESIGN_FILE.read_text()
    section = text.split("## 3.", 1)[-1].split("\n## ", 1)[0]
    tools = set(re.findall(r"^\|\s*`([a-z_]+)`", section, flags=re.M))
    if not tools:
        fail("docs/design.md: could not find the human-in-the-loop table in section 3")
    policy_tools = {r["tool"] for r in policy["rules"]}
    for t in tools:
        if t not in manifests:
            fail(f"docs/design.md: tool {t} in section 3 has no manifest")
        if t not in policy_tools:
            fail(f"docs/design.md: tool {t} in section 3 has no policy rule")
    for t in manifests:
        if t not in tools:
            fail(f"docs/design.md: manifest {t} is missing from the section 3 table")


def audit_fields(path: Path, marker: str) -> set[str]:
    for line in path.read_text().splitlines():
        if marker in line:
            return set(re.findall(r"`([a-z_]+)`", line))
    fail(f"{rel(path)}: could not find the audit field list ('{marker}')")
    return set()


def check_audit_field_sync() -> None:
    standard = audit_fields(STANDARD_FILE, "append-only audit event per step")
    greptile = audit_fields(GREPTILE_RULES, "**Audit events** must include")
    if standard and greptile and standard != greptile:
        fail(
            "audit fields differ between docs/team-standard.md and .greptile/rules.md: "
            f"only in standard {sorted(standard - greptile)}, only in greptile {sorted(greptile - standard)}"
        )


LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def check_links(files: list[Path]) -> None:
    for p in files:
        if p.suffix not in {".md", ".mdc"}:
            continue
        for target in LINK.findall(p.read_text()):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            if path and not (p.parent / path).exists():
                fail(f"{rel(p)}: broken link {target}")


def check_em_dash(files: list[Path]) -> None:
    for p in files:
        if p.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if "\u2014" in line:
                fail(f"{rel(p)}:{n}: em dash character")


# ------------------------------------------------------------------- main

def main() -> int:
    files = repo_files()
    check_parse(files)
    manifests = load_manifests()
    policy = load_policy(manifests)
    n_tests = run_policy_tests(policy)
    check_design_table(manifests, policy)
    check_audit_field_sync()
    check_links(files)
    check_em_dash(files)

    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {len(manifests)} manifests, {len(policy['rules'])} policy rules, {n_tests} policy tests, links and text checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
