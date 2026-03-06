#!/usr/bin/env python3
"""
Clara AI - Batch Pipeline Orchestrator
--------------------------------------
The master engine that iterates over customer accounts and coordinates the
transition from Demo (v1) to Onboarding (v2). It ensures idempotency and
provides detailed batch reporting.

Author: Clara AI Pipeline Team
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from scripts.extract_memo_v1 import extract_memo_v1
from scripts.update_memo_v2 import update_memo_v2
from scripts.generate_agent import generate_agent_spec
from scripts import task_tracker

# Global pipeline logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("outputs/pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("clara.pipeline")

def get_account_id(filename):
    """Extract account ID from filename like account_3_demo.txt → '3'"""
    import re
    m = re.search(r"account[_\-](\d+)", filename)
    return m.group(1) if m else None

def run_pipeline(demo_dir="data/demo", onboarding_dir="data/onboarding", force=False):
    os.makedirs("outputs/accounts", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    
    # Initialize Tracker
    task_tracker.init_db()

    summary = {
        "started_at": datetime.now().isoformat(),
        "accounts": [],
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
    }

    # Find all demo files
    if not os.path.isdir(demo_dir):
        log.error(f"Demo directory not found: {demo_dir}")
        sys.exit(1)

    demo_files = sorted([
        f for f in os.listdir(demo_dir)
        if f.endswith((".txt", ".md")) and "demo" in f.lower()
    ])

    log.info(f"Found {len(demo_files)} demo transcripts in {demo_dir}")

    for demo_file in demo_files:
        account_id = get_account_id(demo_file)
        if not account_id:
            log.warning(f"Skipping {demo_file} – could not extract account ID")
            summary["skipped"] += 1
            continue

        demo_path = os.path.join(demo_dir, demo_file)
        onboarding_pattern = f"account_{account_id}_onboarding.txt"
        onboarding_path = os.path.join(onboarding_dir, onboarding_pattern)

        account_result = {
            "account_id": account_id,
            "demo_file": demo_file,
            "onboarding_file": onboarding_pattern if os.path.exists(onboarding_path) else None,
            "v1_status": None,
            "v2_status": None,
            "errors": [],
        }
        summary["total"] += 1

        log.info(f"═══ Account {account_id} ═══")
        task_tracker.update_account_status(account_id, "PROCESSING_V1")

        # ── Pipeline A: Demo → v1 ──────────────────────────────────────────────
        v1_memo_path = f"outputs/accounts/{account_id}/v1/memo_v1.json"
        v1_agent_path = f"outputs/accounts/{account_id}/v1/agent_v1.json"
        
        if os.path.exists(v1_memo_path) and not force:
            log.info(f"[{account_id}] v1 already exists (idempotent). Skipping extraction.")
            account_result["v1_status"] = "skipped (already exists)"
        else:
            try:
                memo = extract_memo_v1(account_id, demo_path)
                generate_agent_spec(account_id, "v1")
                account_result["v1_status"] = "success"
                log.info(f"[{account_id}] ✅ v1 complete")
                task_tracker.update_account_status(account_id, "V1_COMPLETED", 
                                                 company_name=memo.get("company_name"),
                                                 v1_memo_path=v1_memo_path,
                                                 v1_agent_path=v1_agent_path)
            except Exception as e:
                account_result["v1_status"] = f"FAILED: {e}"
                account_result["errors"].append(str(e))
                log.error(f"[{account_id}] v1 FAILED: {e}")
                task_tracker.update_account_status(account_id, f"V1_FAILED: {str(e)[:50]}")
                summary["failed"] += 1
                summary["accounts"].append(account_result)
                continue

        # ── Pipeline B: Onboarding → v2 ───────────────────────────────────────
        v2_memo_path = f"outputs/accounts/{account_id}/v2/memo_v2.json"
        v2_agent_path = f"outputs/accounts/{account_id}/v2/agent_v2.json"
        changelog_path = f"outputs/accounts/{account_id}/v2/changes.json"
        
        if os.path.exists(v2_memo_path) and not force:
            log.info(f"[{account_id}] v2 already exists (idempotent). Skipping onboarding update.")
            account_result["v2_status"] = "skipped (already exists)"
            task_tracker.update_account_status(account_id, "V2_COMPLETED")
        elif not os.path.exists(onboarding_path):
            log.warning(f"[{account_id}] No onboarding file found at {onboarding_path} – skipping v2")
            account_result["v2_status"] = "skipped (no onboarding file)"
            task_tracker.update_account_status(account_id, "AWAITING_ONBOARDING")
        else:
            try:
                task_tracker.update_account_status(account_id, "PROCESSING_V2")
                update_memo_v2(account_id, onboarding_path)
                generate_agent_spec(account_id, "v2")
                account_result["v2_status"] = "success"
                log.info(f"[{account_id}] ✅ v2 complete")
                task_tracker.update_account_status(account_id, "V2_COMPLETED",
                                                 v2_memo_path=v2_memo_path,
                                                 v2_agent_path=v2_agent_path,
                                                 changelog_path=changelog_path)
            except Exception as e:
                account_result["v2_status"] = f"FAILED: {e}"
                account_result["errors"].append(str(e))
                log.error(f"[{account_id}] v2 FAILED: {e}")
                task_tracker.update_account_status(account_id, f"V2_FAILED: {str(e)[:50]}")
                summary["failed"] += 1
                summary["accounts"].append(account_result)
                continue

        summary["succeeded"] += 1
        summary["accounts"].append(account_result)

    summary["finished_at"] = datetime.now().isoformat()

    # Write summary
    with open("outputs/batch_summary.json", "w") as f:
        json.dump(summary, f, indent=4)

    # Print table
    log.info("\n" + "═" * 60)
    log.info(f"{'ACCOUNT':<12} {'V1':<20} {'V2':<20}")
    log.info("═" * 60)
    for a in summary["accounts"]:
        log.info(f"{a['account_id']:<12} {str(a['v1_status']):<20} {str(a['v2_status']):<20}")
    log.info("═" * 60)
    log.info(f"Total: {summary['total']}  ✅ Succeeded: {summary['succeeded']}  ❌ Failed: {summary['failed']}  ⏭ Skipped: {summary['skipped']}")
    log.info("Batch summary written → outputs/batch_summary.json")
    log.info("Industrial tracking updated → outputs/pipeline_tracker.db")

    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clara AI – Batch Pipeline Runner")
    parser.add_argument("--demo-dir", default="data/demo", help="Path to demo transcripts directory")
    parser.add_argument("--onboarding-dir", default="data/onboarding", help="Path to onboarding transcripts directory")
    parser.add_argument("--force", action="store_true", help="Reprocess even if outputs already exist")
    args = parser.parse_args()
    run_pipeline(args.demo_dir, args.onboarding_dir, args.force)
