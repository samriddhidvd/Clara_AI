#!/usr/bin/env python3
"""
Clara AI - Demo Extraction Engine
---------------------------------
This script parses preliminary business data from initial demo call transcripts.
It focuses on capturing the 'directional' intent of the client while explicitly
flagging missing operational details for confirmation during onboarding.

Author: Clara AI Pipeline Team
"""

import os
import sys
import json
import re
import logging
from datetime import datetime

# Configure clean logging for production visibility
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("clara.extract")

# ── helpers ──────────────────────────────────────────────────────────────────
def clean(line: str) -> str:
    """Strip speaker labels like 'Client:', 'Agent:', 'Ben:', etc."""
    return re.sub(r"^[A-Za-z\s]+:\s*", "", line).strip()

def first_match(patterns, text, group=1):
    """Utility to return the first regex match from a list of candidates."""
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                return m.group(group).strip()
            except IndexError:
                return m.group(0).strip()
    return None

def all_matches(patterns, text):
    results = []
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            try:
                results.append(m.group(1).strip())
            except IndexError:
                results.append(m.group(0).strip())
    return list(dict.fromkeys(results))  # deduplicate, preserve order

# ── extractors ───────────────────────────────────────────────────────────────
def extract_company(text):
    patterns = [
        r"(?:I'?m|this is|calling from|name is)\s+([A-Z][A-Za-z0-9\s'&,.-]{2,40}?)(?:\.|,|$|\n)",
        r"(?:from|with|at)\s+([A-Z][A-Za-z0-9\s'&]+(?:Electric|Plumbing|Fire|HVAC|Sprinkler|Alarm|Facility|Pressure|Solutions?|Services?|Pros?|Protection|Contractor|Systems?))",
        r"([A-Z][A-Za-z0-9\s'&]+(?:Electric|Plumbing|Fire|HVAC|Sprinkler|Alarm|Facility|Solutions?|Services?|Protection))",
    ]
    result = first_match(patterns, text)
    if result:
        return result.rstrip(".,")
    return None

def extract_business_hours(text):
    patterns = [
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*(?:to|-)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)[^.\n]{0,50})",
        r"((?:monday|mon)\s*(?:through|to|-)\s*(?:friday|fri|saturday|sat|sunday|sun)[^.\n]{0,60})",
        r"(open\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)[^.\n]{0,50})",
        r"(24\s*/\s*7|twenty[\s-]four[^.\n]{0,20})",
    ]
    return first_match(patterns, text)

def extract_timezone(text):
    patterns = [
        r"\b(Eastern|Central|Mountain|Pacific|ET|CT|MT|PT|EST|CST|MST|PST|EDT|CDT|MDT|PDT)\b",
    ]
    return first_match(patterns, text)

def extract_address(text):
    patterns = [
        r"\d{1,5}\s+[A-Za-z0-9\s]+(?:Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Road|Rd\.?|Drive|Dr\.?|Lane|Ln\.?|Way|Court|Ct\.?|Place|Pl\.?)[^\n,]{0,60}",
        r"(?:located at|address is|office at|based at|our address)\s+([^\n.]{10,80})",
    ]
    result = first_match(patterns, text)
    # Reject false positives: if result looks like a time (contains AM/PM or digits with colon), discard
    if result and re.search(r"\b(?:\d{1,2}:\d{2}|am|pm)\b", result, re.I):
        return None
    return result

def extract_services(text):
    service_kws = [
        r"(fire\s+(?:protection|alarm|suppression|sprinkler)[^.\n]{0,40})",
        r"(sprinkler[^.\n]{0,40})",
        r"(HVAC[^.\n]{0,40})",
        r"(electrical?[^.\n]{0,40})",
        r"(plumbing[^.\n]{0,40})",
        r"(alarm[^.\n]{0,40})",
        r"(inspection[^.\n]{0,40})",
        r"(maintenance[^.\n]{0,40})",
        r"(backflow[^.\n]{0,40})",
        r"(landscaping[^.\n]{0,40})",
        r"(freezer[^.\n]{0,40})",
        r"(wiring[^.\n]{0,40})",
        r"(pressure\s+wash[^.\n]{0,40})",
    ]
    found = []
    lines = text.split("\n")
    for line in lines:
        if re.search(r"service|provide|offer|speciali|we do|also", line, re.I):
            for p in service_kws:
                m = re.search(p, line, re.I)
                if m:
                    svc = m.group(1).strip().rstrip(".,").lower()
                    if svc not in found:
                        found.append(svc)
    return found if found else all_matches(service_kws, text)

def extract_emergency_definition(text):
    triggers = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        ll = line.lower()
        is_answer = bool(re.search(r"^(client|ben|sarah|john|jim|tom|bp|caller)\s*:", line, re.I))
        has_emergency_q = any(kw in ll for kw in ["what.*emergency", "emergency.*what", "constitutes.*emergency", "define.*emergency"])
        if has_emergency_q:
            for j in range(i+1, min(i+4, len(lines))):
                if re.search(r"^(client|ben|sarah|john|jim|tom|bp|caller)\s*:", lines[j], re.I):
                    triggers.append(clean(lines[j]))
                    break
        # also grab inline client statements about emergencies
        if is_answer and re.search(r"emergency|emergenc", ll):
            if re.search(r"(leak|flood|fire|alarm|power|spark|wire|loss|safety|heat|cool|freez|burst|water)", ll):
                triggers.append(clean(line))
    return list(dict.fromkeys([t for t in triggers if len(t) > 5]))

def extract_emergency_routing(text):
    patterns = [
        r"(?:route|send|transfer|forward|page|call)\s+(?:emergencies?|emergency calls?)\s+(?:to|directly to)\s+([^.\n]+)",
        r"(?:emergencies?\s+(?:should|must|will|need to)\s+(?:go|be sent|be routed|be forwarded)(?:\s+\w+){0,3}to)\s+([^.\n]+)",
        r"(?:on[\s-]call|lead tech|dispatch|hotline|my (?:cell|phone|number))\s*(?:at|is|:|=)?\s*([\d\s()+\-ext.]+)",
    ]
    return first_match(patterns, text)

def extract_phone_numbers(text):
    return re.findall(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", text)

def extract_integration_constraints(text):
    constraints = []
    patterns = [
        r"(?:never|don'?t|do not|cannot|must not)\s+([^.\n]{5,120})",
        r"(?:always|make sure to|tag all|do NOT)\s+([^.\n]{5,120})",
        r"(?:integration|constraint|restriction|ServiceTrade|HousecallPro|system)[^.\n]{0,20}:\s*([^.\n]{5,120})",
    ]
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            constraint = m.group(0).strip()
            if constraint not in constraints:
                constraints.append(constraint)
    return constraints[:5]  # cap at 5 to avoid noise

def extract_non_emergency(text):
    patterns = [
        r"non[\s-]emergency\s+(?:calls?)?\s+(?:should|will|can)\s+([^.\n]+)",
        r"(?:if not emergency|for non[\s-]emergency|non[\s-]urgent)\s*[,:]\s*([^.\n]+)",
    ]
    result = first_match(patterns, text)
    return result if result else None

def extract_transfer_rules(text):
    patterns = [
        r"(?:transfer fails?|if (?:no answer|transfer fails?|it fails?))[^.\n]{0,20}[,:]?\s*([^.\n]+)",
        r"(?:after|within|wait)\s+(\d+\s*seconds?)[^.\n]{0,60}",
        r"timeout\s+(?:is|of|at)?\s*(\d+\s*seconds?)[^.\n]{0,40}",
    ]
    return first_match(patterns, text)

# ── main extractor ────────────────────────────────────────────────────────────
def extract_memo_v1(account_id: str, transcript_path: str):
    if not os.path.exists(transcript_path):
        log.error(f"Transcript not found: {transcript_path}")
        sys.exit(1)

    with open(transcript_path, "r", encoding="utf-8") as f:
        text = f.read()

    log.info(f"Processing account {account_id} from {transcript_path}")

    company_name = extract_company(text)
    business_hours = extract_business_hours(text)
    timezone = extract_timezone(text)
    address = extract_address(text)
    services = extract_services(text)
    emergency_def = extract_emergency_definition(text)
    emergency_routing = extract_emergency_routing(text)
    phone_numbers = extract_phone_numbers(text)
    integration = extract_integration_constraints(text)
    non_emergency = extract_non_emergency(text)
    transfer_rules = extract_transfer_rules(text)

    # Build questions_or_unknowns – only from truly missing fields
    unknowns = []
    if not company_name:
        unknowns.append("company_name: Not found in transcript")
    if not business_hours:
        unknowns.append("business_hours: Not specified in demo call")
    if not timezone:
        unknowns.append("timezone: Not mentioned – confirm during onboarding")
    if not emergency_def:
        unknowns.append("emergency_definition: Emergency types not defined – confirm during onboarding")
    if not emergency_routing or emergency_routing == "Unknown":
        unknowns.append("emergency_routing_rules: No routing number provided – confirm during onboarding")
    if not services:
        unknowns.append("services_supported: No explicit services mentioned")

    hours_str = business_hours or "UNKNOWN – see questions_or_unknowns"
    if timezone and business_hours:
        hours_str = f"{business_hours} {timezone}"

    memo = {
        "account_id": account_id,
        "company_name": company_name or "UNKNOWN",
        "business_hours": hours_str,
        "timezone": timezone or "UNKNOWN",
        "office_address": address or "UNKNOWN",
        "phone_numbers_mentioned": phone_numbers,
        "services_supported": services,
        "emergency_definition": emergency_def,
        "emergency_routing_rules": emergency_routing or "UNKNOWN – to be confirmed at onboarding",
        "non_emergency_routing_rules": non_emergency or "Take a message and confirm follow-up during business hours",
        "call_transfer_rules": transfer_rules or "Default: 30 second timeout – to be confirmed at onboarding",
        "integration_constraints": integration,
        "after_hours_flow_summary": (
            "Greet caller > Confirm purpose > If emergency: collect name/number/address "
            "> Attempt transfer > Fallback if fails > If non-emergency: take message > Close"
        ),
        "office_hours_flow_summary": (
            "Greet > Ask purpose > Collect name/number > Transfer/Route > "
            "Fallback if fails > Confirm next steps > Anything else? > Close"
        ),
        "questions_or_unknowns": unknowns,
        "data_source": "demo_call",
        "extracted_at": datetime.now().isoformat(),
        "notes": f"v1 – Preliminary. Generated from demo call transcript. {len(unknowns)} unknown(s) flagged."
    }

    output_dir = f"outputs/accounts/{account_id}/v1"
    os.makedirs(output_dir, exist_ok=True)
    out_path = f"{output_dir}/memo_v1.json"
    with open(out_path, "w") as f:
        json.dump(memo, f, indent=4)

    log.info(f"[{account_id}] memo_v1.json written → {out_path}  ({len(unknowns)} unknowns flagged)")
    return memo

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_memo_v1.py <account_id> <transcript_path>")
        sys.exit(1)
    extract_memo_v1(sys.argv[1], sys.argv[2])
