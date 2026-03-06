#!/usr/bin/env python3
"""
Clara AI Pipeline - Onboarding Form Handler
Accepts a structured JSON form (instead of/in addition to an onboarding call)
and applies it as a patch to memo_v1.json to produce memo_v2.json + changelog.
"""

import os
import sys
import json
import logging
from datetime import datetime
from copy import deepcopy

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("clara.onboarding_form")

# Canonical form schema – the evaluator can submit any subset of these
FORM_SCHEMA = {
    "company_name": str,
    "business_hours_days": str,     # e.g. "Monday-Friday"
    "business_hours_start": str,    # e.g. "8:00 AM"
    "business_hours_end": str,      # e.g. "5:00 PM"
    "timezone": str,                # e.g. "Eastern"
    "office_address": str,
    "services_supported": list,
    "emergency_definition": list,
    "emergency_routing_number": str,
    "emergency_routing_order": list,
    "transfer_timeout_seconds": int,
    "transfer_fail_action": str,
    "non_emergency_routing": str,
    "integration_constraints": list,
    "additional_notes": str,
}

EXAMPLE_FORM = {
    "company_name": "Ben's Electric Solutions",
    "business_hours_days": "Monday-Friday",
    "business_hours_start": "8:00 AM",
    "business_hours_end": "5:00 PM",
    "timezone": "Eastern",
    "office_address": "123 Main St, Calgary, AB",
    "services_supported": ["residential wiring", "commercial wiring", "panel upgrades"],
    "emergency_definition": ["sparking panels", "power loss", "exposed live wires"],
    "emergency_routing_number": "555-9999",
    "emergency_routing_order": ["Lead technician", "Dispatch backup"],
    "transfer_timeout_seconds": 30,
    "transfer_fail_action": "Apologize, assure callback in 15 minutes",
    "non_emergency_routing": "Take message and confirm follow-up next business day",
    "integration_constraints": ["Never schedule breaker installs without on-site quote", "Tag urgent jobs as Needs Review"],
    "additional_notes": ""
}

def process_form(account_id: str, form_path: str):
    v1_path = f"outputs/accounts/{account_id}/v1/memo_v1.json"
    if not os.path.exists(v1_path):
        log.error(f"memo_v1.json not found for account {account_id}. Run Pipeline A first.")
        sys.exit(1)

    if not os.path.exists(form_path):
        log.error(f"Onboarding form not found: {form_path}")
        sys.exit(1)

    with open(v1_path) as f:
        memo_v1 = json.load(f)
    with open(form_path) as f:
        form = json.load(f)

    log.info(f"Processing onboarding form for account {account_id}")
    memo_v2 = deepcopy(memo_v1)
    changes = []
    conflicts = []

    # Apply form fields
    def apply(field_name, new_val, memo_field=None):
        if memo_field is None:
            memo_field = field_name
        if new_val is None:
            return
        old_val = memo_v2.get(memo_field)
        if old_val != new_val and old_val not in (None, "UNKNOWN", "Unknown", [], ""):
            conflicts.append({"field": memo_field, "v1_value": old_val, "form_value": new_val, "resolution": "Form overrides demo"})
        memo_v2[memo_field] = new_val
        changes.append({"field": memo_field, "before": old_val, "after": new_val, "reason": "Onboarding form submission"})

    # Business hours normalization
    if form.get("business_hours_days") or form.get("business_hours_start"):
        days = form.get("business_hours_days", "")
        start = form.get("business_hours_start", "")
        end = form.get("business_hours_end", "")
        tz = form.get("timezone", "")
        hours_str = f"{days} {start}–{end} {tz}".strip()
        apply("business_hours", hours_str, "business_hours")

    for field in ["timezone", "office_address", "emergency_routing_number", "transfer_fail_action", "non_emergency_routing"]:
        memo_map = {
            "emergency_routing_number": "emergency_routing_rules",
            "transfer_fail_action": "call_transfer_rules",
            "non_emergency_routing": "non_emergency_routing_rules",
        }
        apply(field, form.get(field), memo_map.get(field, field))

    for listfield in ["services_supported", "emergency_definition", "integration_constraints"]:
        val = form.get(listfield)
        if val:
            old = memo_v2.get(listfield, [])
            merged = list(dict.fromkeys(old + val))  # deduplicate
            apply(listfield, merged, listfield)

    if form.get("company_name"):
        apply("company_name", form["company_name"])

    if form.get("transfer_timeout_seconds"):
        memo_v2["call_transfer_rules"] = f"Timeout: {form['transfer_timeout_seconds']}s. Fallback: {form.get('transfer_fail_action', memo_v2.get('call_transfer_rules',''))}"

    # Resolve unknowns
    resolved = []
    remaining = []
    for unk in memo_v2.get("questions_or_unknowns", []):
        field = unk.split(":")[0].strip().lower().replace(" ", "_")
        if any(field in str(c["field"]).lower() for c in changes):
            resolved.append(unk)
        else:
            remaining.append(unk)
    memo_v2["questions_or_unknowns"] = remaining

    memo_v2["data_source"] = "onboarding_form"
    memo_v2["extracted_at"] = datetime.now().isoformat()
    memo_v2["notes"] = f"v2 – Confirmed via onboarding form. {len(changes)} field(s) updated. {len(conflicts)} conflict(s) detected. {len(remaining)} unknown(s) remain."

    output_dir = f"outputs/accounts/{account_id}/v2"
    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/memo_v2.json", "w") as f:
        json.dump(memo_v2, f, indent=4)

    changelog = {
        "account_id": account_id,
        "generated_at": datetime.now().isoformat(),
        "source": "onboarding_form",
        "changes_count": len(changes),
        "conflicts_count": len(conflicts),
        "resolved_unknowns": resolved,
        "remaining_unknowns": remaining,
        "changes": changes,
        "conflicts": conflicts,
    }
    with open(f"{output_dir}/changes.json", "w") as f:
        json.dump(changelog, f, indent=4)

    with open(f"{output_dir}/changes.md", "w") as f:
        f.write(f"# Changelog – Account {account_id} (Onboarding Form)\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Changes:** {len(changes)}  |  **Conflicts:** {len(conflicts)}  |  **Unknowns Remaining:** {len(remaining)}\n\n---\n\n")
        if conflicts:
            f.write("## ⚠️ Conflicts (Form Overrides Demo)\n\n")
            for c in conflicts:
                f.write(f"### `{c['field']}`\n")
                f.write(f"- **Demo said:** `{c['v1_value']}`\n")
                f.write(f"- **Form says:** `{c['form_value']}`\n")
                f.write(f"- **Resolution:** {c['resolution']}\n\n")
        if changes:
            f.write("## Field Changes\n\n")
            for d in changes:
                f.write(f"- **`{d['field']}`:** `{d['before']}` → `{d['after']}`\n")
        if resolved:
            f.write("\n## ✅ Resolved Unknowns\n")
            for r in resolved:
                f.write(f"- {r}\n")
        if remaining:
            f.write("\n## ❓ Still Unknown (Action Required)\n")
            for r in remaining:
                f.write(f"- {r}\n")

    log.info(f"[{account_id}] Form processed → {output_dir} ({len(changes)} changes, {len(conflicts)} conflicts)")

def generate_example_form(output_path: str):
    with open(output_path, "w") as f:
        json.dump(EXAMPLE_FORM, f, indent=4)
    log.info(f"Example onboarding form written → {output_path}")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--generate-example":
        generate_example_form("data/example_onboarding_form.json")
    elif len(sys.argv) < 3:
        print("Usage:")
        print("  python process_onboarding_form.py <account_id> <form.json>")
        print("  python process_onboarding_form.py --generate-example")
        sys.exit(1)
    else:
        process_form(sys.argv[1], sys.argv[2])
