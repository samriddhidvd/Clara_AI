# Loom Demo Script: Clara AI Automation Pipeline

**Total Duration:** 3–5 Minutes

## 0:00 - 0:30 Introduction
- **Visual:** Show the GitHub README.
- **Speak:** "Hi everyone, I'm [Your Name]. Today I'm demonstrating the Clara AI Automation Pipeline. This system takes messy demo and onboarding call transcripts and converts them into production-ready Retell AI voice agent configurations, 100% zero-cost."

## 0:30 - 1:15 Step 1: Demo → Agent v1
- **Visual:** Show `data/demo/account_1_demo.txt`.
- **Speak:** "We start with a demo call transcript. It's often vague. Our NLP extractor identifies the company name and directional rules without hallucinating missing data."
- **Action:** Run `python3 main.py run` (show terminal output).
- **Visual:** Open `outputs/accounts/1/v1/agent_v1.json`.
- **Speak:** "Here is the generated Agent Spec v1. It includes a complete system prompt with strict business hour flows and fallbacks, ready for a preliminary draft in Retell."

## 1:15 - 2:15 Step 2: Onboarding → Agent v2
- **Visual:** Show `data/onboarding/account_1_onboarding.txt`.
- **Speak:** "Now, the client has purchased and we have the onboarding call. This confirms the exact routing, emergency definitions, and business hours."
- **Visual:** Open `outputs/accounts/1/v2/changes.md`.
- **Speak:** "Our system produces a detailed changelog. You can see exactly what was updated from v1 to v2. We also generate the final v2 agent spec."

## 2:15 - 3:00 Step 3: Web Dashboard & Industrial Tracking
- **Visual:** Open `dashboard.html` in the browser.
- **Speak:** "To make this mission-critical, I've built a premium dark-mode dashboard. It shows batch stats and a side-by-side diff viewer for every account. You can see what changed in the prompt and memo at a glance."
- **Action:** Run `python3 main.py status`.
- **Speak:** "Under the hood, we use a real SQLite database to track every account's progress through the pipeline, fulfilling the requirement for industrial task tracking."

## 3:00 - 3:30 Conclusion & Zero-Cost
- **Speak:** "The entire stack—transcription via local Whisper, NLP extraction, SQLite tracking, and the web UI—runs locally with zero API costs. It's idempotent, batch-capable, and ready for deployment. Thanks for watching!"
