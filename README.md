# Clara Answers — Zero-Cost Automation Pipeline

> AI voice agent onboarding automation for service trade businesses.  
> Demo Call → Account Memo → Retell Agent v1 → Onboarding → Agent v2  
> **100% zero-cost. Local-first. GitHub-native.**

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/Om334exe/clara-ai-agent.git
cd clara-ai-agent

# 2. Add your transcripts (or use the included synthetic ones)
#    data/demo/account_<id>_demo.txt
#    data/onboarding/account_<id>_onboarding.txt

# 3. Run the full pipeline
python3 run_pipeline.py

# 4. View outputs
ls outputs/accounts/

# 5. Launch the dashboard
python3 -m http.server 8080
# Open: http://localhost:8080/dashboard.html
```

---

## Architecture & Data Flow

```
Audio/Video File (.mp4, .m4a)
        │
        ▼ [scripts/transcribe_audio.py] — local Whisper, zero-cost
  Transcript (.txt)
        │
        ▼ [scripts/extract_memo_v1.py] — NLP heuristic extraction
  Account Memo v1 (memo_v1.json)  ◄── DEMO CALL DATA ONLY
        │
        ▼ [scripts/generate_agent.py v1]
  Retell Agent Spec v1 (agent_v1.json)  ← DRAFT / Preliminary
        │
        │  ← Onboarding Call Transcript OR Form (JSON)
        ▼ [scripts/update_memo_v2.py] or [scripts/process_onboarding_form.py]
  Account Memo v2 (memo_v2.json) + changes.json + changes.md
        │
        ▼ [scripts/generate_agent.py v2]
  Retell Agent Spec v2 (agent_v2.json)  ← PRODUCTION READY

All accounts tracked in:
  outputs/batch_summary.json   ← Batch status per account
  outputs/pipeline.log         ← Full run log
  outputs/task_tracker.log     ← Mock task tracker entries
```

---

## File Structure

```
clara-ai-agent/
├── data/
│   ├── demo/                          # Demo call transcripts (account_<id>_demo.txt)
│   ├── onboarding/                    # Onboarding transcripts (account_<id>_onboarding.txt)
│   ├── real_samples/                  # Downloaded real meeting samples
│   └── example_onboarding_form.json   # Example structured onboarding form
├── scripts/
│   ├── extract_memo_v1.py             # Demo transcript → Account Memo v1
│   ├── generate_agent.py              # Unified Memo → Retell Agent Spec (v1 or v2)
│   ├── update_memo_v2.py              # Onboarding transcript → Memo v2 + changelog
│   ├── process_onboarding_form.py     # JSON onboarding form → Memo v2 + conflict log
│   ├── transcribe_audio.py            # Audio → transcript via local Whisper
│   ├── task_tracker.py                # Industrial SQLite status tracking
│   └── generate_synthetic_data.py     # Generate test transcripts
├── workflows/
│   └── clara_pipeline.json            # n8n workflow export (importable)
├── outputs/
│   ├── accounts/                      # Per-account versioned configurations
│   ├── pipeline_tracker.db            # SQLite persistence layer
│   └── pipeline.log                   # Full structured run log
├── main.py                            # Unified CLI Entry Point (Status, Run, Transcribe)
├── dashboard.html                     # Web dashboard (Side-by-side Diff Viewer)
├── docker-compose.yml                 # Local n8n setup
└── README.md
```

---

## Account Memo Schema

Every `memo_v1.json` and `memo_v2.json` has these exact fields:

```json
{
  "account_id": "1",
  "company_name": "Bob's Plumbing",
  "business_hours": "Mon-Fri 8am-5pm Eastern",
  "timezone": "Eastern",
  "office_address": "UNKNOWN",
  "phone_numbers_mentioned": ["555-0199"],
  "services_supported": ["general plumbing maintenance"],
  "emergency_definition": ["burst pipes"],
  "emergency_routing_rules": "555-0199 (Dispatch)",
  "non_emergency_routing_rules": "Take a message ...",
  "call_transfer_rules": "Fallback: text them immediately and hang up",
  "integration_constraints": ["Don't schedule jobs for weekends"],
  "after_hours_flow_summary": "...",
  "office_hours_flow_summary": "...",
  "questions_or_unknowns": [],
  "data_source": "onboarding_call",
  "extracted_at": "2026-03-06T...",
  "notes": "v2 – Confirmed onboarding. 3 field(s) updated."
}
```

**Key discipline:** `questions_or_unknowns` is populated ONLY when information is genuinely absent. No hallucination, no silent assumptions.

---

## Retell Agent Spec Schema

Every `agent_v1.json` and `agent_v2.json` includes:

```json
{
  "agent_name": "Bob's Plumbing – Clara AI Agent",
  "version": "v2",
  "status": "Production – Post Onboarding",
  "voice": "11labs-charlotte",
  "language": "en-US",
  "system_prompt": "... full prompt ...",
  "key_variables": { "company_name", "business_hours", "timezone", "emergency_routing_number", ... },
  "call_transfer_protocol": { "method": "warm_transfer", "timeout_seconds": 30, ... },
  "after_hours_protocol": { "enabled": true, "emergency_keywords": [...], ... },
  "tool_invocations": { "note": "Internal only. Never reveal to callers.", "placeholders": [...] },
  "integration_constraints": [...],
  "questions_or_unknowns": [],
  "generated_at": "..."
}
```

---

## Agent Prompt Flows

Both v1 and v2 prompts strictly implement:

### Business Hours Flow
1. **Greeting** — "Thank you for calling {company}, this is Clara."
2. **Ask purpose** — Listen, do not interrupt
3. **Collect name + number** — before any transfer
4. **Route / Transfer** — silently, do not narrate mechanism
5. **Fallback if fails** — apologize, log info, assure follow-up
6. **Anything else?** — ask
7. **Close** — "Have a great day!"

### After Hours Flow
1. **Greeting** — announce closed, give hours
2. **Ask purpose** — "Are you experiencing an emergency?"
3. **If Emergency** → collect name, number, address → attempt transfer → fallback
4. **If Non-Emergency** → collect details → confirm next-business-day follow-up
5. **Anything else?** → Close

**Prompt hygiene rules enforced in every generated spec:**
- ❌ Never mention "function calls", "tools", or "APIs"
- ❌ Never ask for more info than needed for routing/dispatch
- ❌ Never hallucinate business rules not in the memo
- ✅ Always have a fallback for failed transfers

---

## Audio Transcription (Zero-Cost)

If you receive `.mp4` or `.m4a` files instead of transcripts:

```bash
# Install (one-time)
pip install openai-whisper

# Transcribe
python3 scripts/transcribe_audio.py data/demo/account_1_demo.m4a
# → Creates: data/demo/account_1_demo_transcript.txt

# Then run pipeline
python3 run_pipeline.py
```

Models available: `tiny`, `base` (default), `small`, `medium` — all free, all local.

---

## Onboarding Form (Structured Input)

Instead of a call transcript, clients can submit a JSON form:

```bash
# Generate a filled example
python3 scripts/process_onboarding_form.py --generate-example
# → data/example_onboarding_form.json

# Process a form
python3 scripts/process_onboarding_form.py 1 data/example_onboarding_form.json
```

The form handler detects **conflicts** (where the form overrides demo data) and logs them explicitly in `changes.md`.

---

## n8n Setup

```bash
# Start n8n locally (Docker required)
docker-compose up -d

# Open: http://localhost:5678
# Import: workflows/clara_pipeline.json
```

**Environment variables for n8n:**
```
CLARA_ROOT=/path/to/clara-ai-agent
CLARA_DEMO_DIR=data/demo
CLARA_ONBOARDING_DIR=data/onboarding
```

The workflow includes both a **Manual Trigger** and an optional **24h Scheduled Trigger**.

---

## Retell Integration

Retell's programmatic API requires a paid plan. Manual import:

1. Open [retell.ai](https://retell.ai) → Create Agent
2. Open `outputs/accounts/<id>/v2/agent_v2.json`
3. Copy `system_prompt` → paste into Retell System Prompt field
4. Set voice to match `voice` field (`11labs-charlotte`)
5. Agent is ready ✅

---

## Web Dashboard (Bonus)

```bash
python3 -m http.server 8080
# Open: http://localhost:8080/dashboard.html
```

**Dashboard features:**
- 📊 Batch stats (total, v2-ready, unknowns)
- 🃏 Account cards with details
- 🔍 **Diff viewer** — side-by-side v1 vs v2 for every field
- 📝 Agent prompt viewer for v1 and v2
- 🔄 Live reads from `outputs/` JSON files

---

## Running the Pipeline

```bash
# Default (idempotent — skips already-processed accounts)
python3 run_pipeline.py

# Force reprocess all accounts
python3 run_pipeline.py --force

# Custom directories
python3 run_pipeline.py --demo-dir /path/to/demos --onboarding-dir /path/to/onboarding

# Simple bash alternative (no Python import required)
./scripts/process_all.sh
```

---

## Zero-Cost Stack

| Component | Tool | Cost |
|---|---|---|
| Transcription | OpenAI Whisper (local CPU) | $0 |
| Extraction | Python heuristic NLP | $0 |
| Agent templating | Python f-strings | $0 |
| Orchestration | Python + bash + n8n (local Docker) | $0 |
| Storage | Local JSON files + GitHub repo | $0 |
| Task tracking | Local log file (mock) | $0 |
| Dashboard | Static HTML served by http.server | $0 |
| Repository | GitHub (public) | $0 |
| **Total** | | **$0** |

---

## Known Limitations

| Limitation | Notes |
|---|---|
| Transcript quality | Heuristic extraction works best on structured dialogues. Quality degrades with heavy crosstalk or very informal speech. |
| Whisper on CPU | ~3–10 min per 30min audio file. GPU dramatically faster. |
| Retell API | Free tier does not support programmatic agent creation. Manual import required. |
| Fireflies.ai | Requires browser auth; transcripts cannot be scraped automatically. Export manually. |
| Company name extraction | Can misfire on very unstructured intros — add company name manually to form if needed. |

---

## What I'd Improve with Production Access

1. **Retell API integration** — auto-deploy agent spec directly on save
2. **AssemblyAI or Deepgram** free tier — better speaker diarization for messy calls
3. **GPT-4o with structured output** — LLM extraction for unstructured edge cases
4. **Supabase** — multi-user, multi-tenant account management with row-level security
5. **Webhook triggers** — form submission or CRM event auto-triggers pipeline v2
6. **Asana/Linear integration** — real task tracking per account
7. **Slack alerts** — notify team when a new account completes onboarding or has unresolved unknowns
