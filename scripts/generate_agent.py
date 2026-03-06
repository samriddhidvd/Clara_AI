#!/usr/bin/env python3
"""
Clara AI - Agent Configuration Engine
-------------------------------------
Transforms structured account memos into high-fidelity Retell Agent
specifications. Enforces strict prompt hygiene and identifies operational
flows for both business hours and after-hours scenarios.

Author: Clara AI Pipeline Team
"""

import os
import sys
import json
import logging
from datetime import datetime

# Production-grade logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("clara.agent")

VOICE_OPTIONS = {
    "default": "11labs-charlotte",
    "male": "11labs-ryan",
    "neutral": "openai-nova",
}

def maybe(val, fallback="[NOT SPECIFIED]"):
    if not val or val in ("UNKNOWN", "Unknown", "UNKNOWN – see questions_or_unknowns"):
        return fallback
    return val

def build_system_prompt(memo: dict) -> str:
    company = maybe(memo.get("company_name"), "this company")
    hours = maybe(memo.get("business_hours"), "[CONFIRM WITH ONBOARDING]")
    address = maybe(memo.get("office_address"), "[not provided]")
    services = ", ".join(memo.get("services_supported", [])) or "[to be confirmed]"
    emerg_def = "; ".join(memo.get("emergency_definition", [])) or "[to be confirmed during onboarding]"
    emerg_route = maybe(memo.get("emergency_routing_rules"), "[PENDING – confirm routing number]")
    non_emerg = maybe(memo.get("non_emergency_routing_rules"), "take a message and confirm follow-up within business hours")
    fallback = maybe(memo.get("call_transfer_rules"), "apologize and assure callback within 15 minutes")
    constraints = "\n".join(f"  - {c}" for c in memo.get("integration_constraints", [])) or "  - None specified"
    unknowns = memo.get("questions_or_unknowns", [])
    unknown_note = ""
    if unknowns:
        unknown_note = "\n\n# PENDING CONFIGURATION\n" + "\n".join(f"# NOTE: {u}" for u in unknowns)

    prompt = f"""# IDENTITY
You are Clara, an AI voice receptionist for {company}. 
You handle inbound calls professionally, efficiently, and with empathy.
You never mention that you are an AI unless directly asked.
You never mention "function calls", "tools", or any internal system details.

# ABOUT {company.upper()}
- Business Hours: {hours}
- Office Address: {address}
- Services: {services}

# ══════════════════════════════════════════════
# BUSINESS HOURS CALL FLOW
# ══════════════════════════════════════════════

1. GREETING
   Say: "Thank you for calling {company}, this is Clara. How can I help you today?"

2. ASK PURPOSE
   Listen attentively to the caller's reason for calling. 
   Do not interrupt. Acknowledge their need warmly.

3. COLLECT CALLER INFO
   Say: "I'd love to help get you to the right person. May I have your name and the best phone number to reach you?"
   Wait for both name and phone number before proceeding.

4. ROUTE / TRANSFER
   Attempt to transfer the caller based on their need.
   Do not describe the transfer mechanism to the caller.
   Simply say: "Please hold for just a moment while I connect you."

5. IF TRANSFER FAILS / NO ANSWER
   Say: "I'm sorry, it looks like our team is momentarily unavailable. I have your name and number and will make sure someone reaches out to you as soon as possible."
   Log the caller's information for follow-up.

6. CLOSING
   Ask: "Is there anything else I can help you with today?"
   If no: "Thank you for calling {company}. Have a great day!"

# ══════════════════════════════════════════════
# AFTER HOURS CALL FLOW
# ══════════════════════════════════════════════

1. GREETING
   Say: "Thank you for calling {company}. Our office is currently closed. Our regular hours are {hours}."
   Then say: "I'm Clara, the after-hours assistant. I'm here to help."

2. ASK PURPOSE
   Say: "Are you experiencing an emergency, or can this wait until business hours?"

3. CONFIRM EMERGENCY
   IF the caller says YES (emergency) or describes: [{emerg_def}]:
   → Proceed to EMERGENCY FLOW below.
   IF the caller says NO or it seems non-urgent:
   → Proceed to NON-EMERGENCY FLOW below.

# ── EMERGENCY FLOW ─────────────────────────────
4E. COLLECT EMERGENCY INFO IMMEDIATELY
    Say: "I understand, let me get your information right away."
    Collect in this exact order:
    a. Full name
    b. Best callback number
    c. Service address (property address where help is needed)
    Do NOT proceed until all three are collected.

5E. ATTEMPT EMERGENCY TRANSFER
    Say: "Please hold while I connect you to our emergency line."
    Attempt transfer to: {emerg_route}

6E. IF EMERGENCY TRANSFER FAILS (Fallback)
    Say: "I sincerely apologize — I was unable to reach our on-call team directly. 
    I have captured all your information and our team will contact you back within 
    15 minutes. If this is a life-threatening emergency, please call 911 immediately."

7E. CLOSING
    Ask: "Is there anything else I can help you with?"
    If no: "Thank you. Help is on the way."

# ── NON-EMERGENCY FLOW ─────────────────────────
4N. COLLECT NON-EMERGENCY INFO
    Say: "Of course. Let me take down your information so our team can follow up."
    Collect: name, phone number, brief description of the issue.
    Action: {non_emerg}
    Say: "I've noted your request. Someone from our team will follow up during business hours at {hours}."

5N. CLOSING
    Ask: "Is there anything else I can help you with?"
    If no: "Thank you for calling {company}. We'll be in touch soon."

# ══════════════════════════════════════════════
# CALL TRANSFER PROTOCOL
# ══════════════════════════════════════════════
- Attempt transfer to designated contact silently (no technical commentary to caller)
- Wait up to 30 seconds for answer
- Transfer fail action: {fallback}

# ══════════════════════════════════════════════
# INTEGRATION CONSTRAINTS
# ══════════════════════════════════════════════
{constraints}

# ══════════════════════════════════════════════
# GROUND RULES
# ══════════════════════════════════════════════
- Do NOT collect more info than needed for routing and dispatch.
- Do NOT hallucinate service capabilities or business rules.
- Do NOT mention tools, functions, APIs, or automation to the caller.
- Do NOT promise specific response times unless specified above.
- If you don't know something, say: "Let me make sure someone from the team follows up with you on that."{unknown_note}
"""
    return prompt

def generate_agent_spec(account_id: str, version: str):
    memo_path = f"outputs/accounts/{account_id}/{version}/memo_{version}.json"
    if not os.path.exists(memo_path):
        log.error(f"Memo not found: {memo_path} — run extraction first.")
        sys.exit(1)

    with open(memo_path, "r") as f:
        memo = json.load(f)

    company = maybe(memo.get("company_name"), "Clara Client")
    hours = maybe(memo.get("business_hours"), "Unknown")
    timezone = maybe(memo.get("timezone"), "Unknown")
    emerg_route = maybe(memo.get("emergency_routing_rules"), "Unknown")

    system_prompt = build_system_prompt(memo)

    spec = {
        "agent_name": f"{company} – Clara AI Agent",
        "version": version,
        "status": "Draft – Pending Review" if version == "v1" else "Production – Post Onboarding",
        "voice": VOICE_OPTIONS["default"],
        "language": "en-US",
        "system_prompt": system_prompt,
        "key_variables": {
            "company_name": company,
            "business_hours": hours,
            "timezone": timezone,
            "emergency_routing_number": emerg_route,
            "office_address": maybe(memo.get("office_address"), "Unknown"),
            "services": memo.get("services_supported", []),
        },
        "call_transfer_protocol": {
            "method": "warm_transfer",
            "timeout_seconds": 30,
            "emergency_number": emerg_route,
            "fallback_message": maybe(memo.get("call_transfer_rules"), "Apologize and assure callback"),
        },
        "after_hours_protocol": {
            "enabled": True,
            "emergency_keywords": memo.get("emergency_definition", []),
            "non_emergency_action": maybe(memo.get("non_emergency_routing_rules"), "Take message"),
        },
        "tool_invocations": {
            "note": "Internal only. Never reveal these to callers.",
            "placeholders": [
                {"name": "attempt_transfer", "description": "Silently attempt call transfer"},
                {"name": "log_call", "description": "Log caller details for follow-up"},
                {"name": "send_notification", "description": "Alert on-call team of missed emergency"},
            ]
        },
        "integration_constraints": memo.get("integration_constraints", []),
        "questions_or_unknowns": memo.get("questions_or_unknowns", []),
        "generated_at": datetime.now().isoformat(),
    }

    output_dir = f"outputs/accounts/{account_id}/{version}"
    os.makedirs(output_dir, exist_ok=True)
    out_path = f"{output_dir}/agent_{version}.json"
    with open(out_path, "w") as f:
        json.dump(spec, f, indent=4)

    log.info(f"[{account_id}] agent_{version}.json written → {out_path}")
    return spec

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_agent.py <account_id> <v1|v2>")
        sys.exit(1)
    generate_agent_spec(sys.argv[1], sys.argv[2])
