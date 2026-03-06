#!/usr/bin/env python3
"""
Clara AI - Onboarding Update Engine
-----------------------------------
This engine processes refined operational requirements from onboarding calls.
It computes the delta between preliminary assumptions (v1) and confirmed
specifications (v2), generating both structured and human-readable changelogs.

Author: Clara AI Pipeline Team
"""

import os
import sys
import json
import re
import logging
from datetime import datetime
from copy import deepcopy

# Professional logging configuration
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("clara.update_v2")

def clean(line: str) -> str:
    return re.sub(r"^[A-Za-z\s]+:\s*", "", line).strip()

def get_client_lines(text):
    """Extract all lines spoken by a client/guest speaker."""
    results = []
    for line in text.split("\n"):
        if re.search(r"^(client|ben|sarah|john|jim|tom|bp|caller|guest)\s*:", line, re.I):
            cleaned = clean(line)
            if cleaned:
                results.append(cleaned)
    return results

def extract_hours_update(text):
    patterns = [
        r"(?:actually|correction|update|change|revised?)[\s,]+(?:our\s+)?hours?\s+(?:are|to)\s+(.+?)(?:\.|$)",
        r"hours?\s+(?:are|changed to|updated to|now)\s+(.+?)(?:\.|$)",
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*(?:to|-)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)[^.\n]{0,60})",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).strip()
    return None

def extract_routing_update(text):
    patterns = [
        r"(?:route|send|transfer|forward|call)\s+(?:emergencies?|emergency calls?)\s+(?:to|directly to)\s+([^.\n]+)",
        r"(?:emergency\s+(?:number|routing|contact)\s+is|cell\s+(?:is|number is))\s+([^.\n]+)",
        r"(?:reach us|call us|contact)\s+at\s+([\d\s\-().+]{7,20})",
        r"\b(555[-.\s]?\d{4}|1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\(\d{3}\)\s*\d{3}[-.\s]?\d{4})\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).strip()
    return None

def extract_fallback_update(text):
    patterns = [
        r"(?:if transfer fails?|if (?:no answer|it fails?|we miss))[^.\n]{0,20}[:,]?\s*([^.\n]+)",
        r"(?:fallback|backup plan|if unreachable)[^.\n]{0,20}[:,]?\s*([^.\n]+)",
        r"(?:apologize|assure|tell them)[^.\n]{0,20}(?:and|that)\s+([^.\n]+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).strip()
    return None

def extract_constraints(text):
    constraints = []
    patterns = [
        r"(?:never|don'?t|do not|must not)\s+([^.\n]{5,120})",
        r"(?:always|make sure|tag all|do NOT)\s+([^.\n]{5,120})",
        r"(?:constraint|note|important)\s*:?\s*([^.\n]{5,120})",
    ]
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            c = m.group(0).strip()
            if c not in constraints:
                constraints.append(c)
    return constraints[:5]

def extract_non_emergency_update(text):
    patterns = [
        r"non[\s-]emergency[^.\n]{0,30}[:,]?\s*([^.\n]+)",
        r"(?:not an emergency|for regular calls?)[^.\n]{0,30}[:,]?\s*([^.\n]+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).strip()
    return None

def compute_diff(v1: dict, v2: dict) -> list:
    changes = []
    for key in v2:
        if key in ("extracted_at", "data_source", "notes"):
            continue
        old_val = v1.get(key)
        new_val = v2.get(key)
        if old_val != new_val:
            changes.append({
                "field": key,
                "before": old_val,
                "after": new_val,
                "reason": "Updated from onboarding call"
            })
    return changes

def update_memo_v2(account_id: str, onboarding_path: str):
    v1_path = f"outputs/accounts/{account_id}/v1/memo_v1.json"
    if not os.path.exists(v1_path):
        log.error(f"memo_v1.json not found for account {account_id}. Run Pipeline A first.")
        sys.exit(1)
    if not os.path.exists(onboarding_path):
        log.error(f"Onboarding transcript not found: {onboarding_path}")
        sys.exit(1)

    with open(v1_path, "r") as f:
        memo_v1 = json.load(f)
    with open(onboarding_path, "r", encoding="utf-8") as f:
        text = f.read()

    log.info(f"Processing onboarding for account {account_id}")
    memo_v2 = deepcopy(memo_v1)

    # Apply updates – only update if a real value is found
    hours_update = extract_hours_update(text)
    if hours_update:
        memo_v2["business_hours"] = hours_update

    routing_update = extract_routing_update(text)
    if routing_update:
        memo_v2["emergency_routing_rules"] = routing_update

    fallback_update = extract_fallback_update(text)
    if fallback_update:
        memo_v2["call_transfer_rules"] = f"Fallback: {fallback_update}"

    non_emerg_update = extract_non_emergency_update(text)
    if non_emerg_update:
        memo_v2["non_emergency_routing_rules"] = non_emerg_update

    new_constraints = extract_constraints(text)
    # Append only genuinely new constraints
    existing = [c.lower() for c in memo_v2.get("integration_constraints", [])]
    for c in new_constraints:
        if c.lower() not in existing:
            memo_v2["integration_constraints"].append(c)
            existing.append(c.lower())

    # Compute diff
    diffs = compute_diff(memo_v1, memo_v2)

    # Resolve unknowns that were answered
    resolved = []
    remaining = []
    for unk in memo_v2.get("questions_or_unknowns", []):
        field = unk.split(":")[0].strip().lower()
        matched = any(d["field"].lower() == field for d in diffs)
        if matched:
            resolved.append(unk)
        else:
            remaining.append(unk)
    memo_v2["questions_or_unknowns"] = remaining

    memo_v2["data_source"] = "onboarding_call"
    memo_v2["extracted_at"] = datetime.now().isoformat()
    memo_v2["notes"] = f"v2 – Confirmed onboarding. {len(diffs)} field(s) updated. {len(remaining)} unknown(s) remain."

    # Save v2 memo
    output_dir = f"outputs/accounts/{account_id}/v2"
    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/memo_v2.json", "w") as f:
        json.dump(memo_v2, f, indent=4)

    # Save structured changelog JSON
    changelog_data = {
        "account_id": account_id,
        "generated_at": datetime.now().isoformat(),
        "changes_count": len(diffs),
        "resolved_unknowns": resolved,
        "remaining_unknowns": remaining,
        "changes": diffs,
    }
    with open(f"{output_dir}/changes.json", "w") as f:
        json.dump(changelog_data, f, indent=4)

    # Save human-readable markdown changelog
    with open(f"{output_dir}/changes.md", "w") as f:
        f.write(f"# Changelog – Account {account_id}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Changes Applied:** {len(diffs)}\n")
        f.write(f"**Unknowns Resolved:** {len(resolved)}\n")
        f.write(f"**Unknowns Remaining:** {len(remaining)}\n\n---\n\n")
        if diffs:
            f.write("## Field Changes\n\n")
            for d in diffs:
                f.write(f"### `{d['field']}`\n")
                f.write(f"- **Before (v1):** `{d['before']}`\n")
                f.write(f"- **After (v2):** `{d['after']}`\n")
                f.write(f"- **Reason:** {d['reason']}\n\n")
        if resolved:
            f.write("## Resolved Unknowns\n")
            for r in resolved:
                f.write(f"- ✅ {r}\n")
            f.write("\n")
        if remaining:
            f.write("## Still Unknown (Action Required)\n")
            for r in remaining:
                f.write(f"- ❓ {r}\n")

    log.info(f"[{account_id}] memo_v2.json + changes.md + changes.json written → {output_dir}  ({len(diffs)} changes)")
    return memo_v2

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python update_memo_v2.py <account_id> <onboarding_transcript_path>")
        sys.exit(1)
    update_memo_v2(sys.argv[1], sys.argv[2])
