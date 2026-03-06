#!/usr/bin/env python3
"""
Batch runner for the Clara AI pipeline.

This module is intentionally small but opinionated: it discovers demo transcripts,
routes each account through the v1 and v2 flows, and leaves a structured audit
trail in `outputs/`.
"""

import os
import sys
import json
import logging
import argparse
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional

from scripts.extract_memo_v1 import extract_memo_v1
from scripts.update_memo_v2 import update_memo_v2
from scripts.generate_agent import generate_agent_spec
from scripts import task_tracker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("outputs/pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("clara.pipeline")


def _ensure_output_dirs() -> None:
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("outputs/accounts", exist_ok=True)


def _derive_account_id(filename: str) -> Optional[str]:
    """Derive an account identifier from a demo filename."""
    import re

    match = re.search(r"account[_\-](\d+)", filename)
    return match.group(1) if match else None


def _discover_demo_files(demo_dir: str) -> List[str]:
    if not os.path.isdir(demo_dir):
        log.error(f"Demo directory not found: {demo_dir}")
        sys.exit(1)

    files = [
        name
        for name in os.listdir(demo_dir)
        if name.endswith((".txt", ".md")) and "demo" in name.lower()
    ]
    files.sort()
    return files


@dataclass
class AccountRun:
    account_id: str
    demo_file: str
    onboarding_file: Optional[str]
    v1_status: Optional[str] = None
    v2_status: Optional[str] = None
    errors: List[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        # normalise None list for JSON readability
        data["errors"] = self.errors or []
        return data


def _run_for_single_account(
    demo_dir: str,
    onboarding_dir: str,
    demo_file: str,
    force: bool,
) -> AccountRun:
    """Execute both v1 and v2 flows for one account."""
    account_id = _derive_account_id(demo_file)
    if not account_id:
        raise ValueError(f"Could not determine account id from {demo_file!r}")

    demo_path = os.path.join(demo_dir, demo_file)
    onboarding_filename = f"account_{account_id}_onboarding.txt"
    onboarding_path = os.path.join(onboarding_dir, onboarding_filename)

    account = AccountRun(
        account_id=account_id,
        demo_file=demo_file,
        onboarding_file=onboarding_filename if os.path.exists(onboarding_path) else None,
        errors=[],
    )

    log.info(f"═══ Account {account_id} ═══")
    task_tracker.update_account_status(account_id, "PROCESSING_V1")

    # v1 – demo transcript → memo + agent
    v1_memo_path = f"outputs/accounts/{account_id}/v1/memo_v1.json"
    v1_agent_path = f"outputs/accounts/{account_id}/v1/agent_v1.json"

    if os.path.exists(v1_memo_path) and not force:
        log.info(f"[{account_id}] v1 already exists (idempotent). Skipping extraction.")
        account.v1_status = "skipped (already exists)"
    else:
        memo = extract_memo_v1(account_id, demo_path)
        generate_agent_spec(account_id, "v1")
        account.v1_status = "success"
        log.info(f"[{account_id}] ✅ v1 complete")
        task_tracker.update_account_status(
            account_id,
            "V1_COMPLETED",
            company_name=memo.get("company_name"),
            v1_memo_path=v1_memo_path,
            v1_agent_path=v1_agent_path,
        )

    # v2 – onboarding transcript → updated memo + agent
    v2_memo_path = f"outputs/accounts/{account_id}/v2/memo_v2.json"
    v2_agent_path = f"outputs/accounts/{account_id}/v2/agent_v2.json"
    changelog_path = f"outputs/accounts/{account_id}/v2/changes.json"

    if os.path.exists(v2_memo_path) and not force:
        log.info(f"[{account_id}] v2 already exists (idempotent). Skipping onboarding update.")
        account.v2_status = "skipped (already exists)"
        task_tracker.update_account_status(account_id, "V2_COMPLETED")
    elif not os.path.exists(onboarding_path):
        log.warning(f"[{account_id}] No onboarding file found at {onboarding_path} – skipping v2")
        account.v2_status = "skipped (no onboarding file)"
        task_tracker.update_account_status(account_id, "AWAITING_ONBOARDING")
    else:
        task_tracker.update_account_status(account_id, "PROCESSING_V2")
        update_memo_v2(account_id, onboarding_path)
        generate_agent_spec(account_id, "v2")
        account.v2_status = "success"
        log.info(f"[{account_id}] ✅ v2 complete")
        task_tracker.update_account_status(
            account_id,
            "V2_COMPLETED",
            v2_memo_path=v2_memo_path,
            v2_agent_path=v2_agent_path,
            changelog_path=changelog_path,
        )

    return account


def run_pipeline(demo_dir: str = "data/demo", onboarding_dir: str = "data/onboarding", force: bool = False):
    """
    High‑level orchestration entry.

    The signature intentionally matches the original version so external callers
    (including `main.py`) can continue to import it unchanged.
    """
    _ensure_output_dirs()
    task_tracker.init_db()

    summary = {
        "started_at": datetime.now().isoformat(),
        "accounts": [],
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
    }

    demo_files = _discover_demo_files(demo_dir)
    log.info(f"Found {len(demo_files)} demo transcripts in {demo_dir}")

    for demo_file in demo_files:
        try:
            account_run = _run_for_single_account(demo_dir, onboarding_dir, demo_file, force)
        except ValueError as e:
            log.warning(str(e))
            summary["skipped"] += 1
            continue
        except Exception as e:  # defensive: treat as hard failure of this account
            log.error(f"[{demo_file}] pipeline FAILED: {e}")
            account_id = _derive_account_id(demo_file) or "unknown"
            task_tracker.update_account_status(account_id, f"PIPELINE_FAILED: {str(e)[:50]}")
            summary["failed"] += 1
            summary["accounts"].append(
                {
                    "account_id": account_id,
                    "demo_file": demo_file,
                    "onboarding_file": None,
                    "v1_status": f"FAILED: {e}",
                    "v2_status": None,
                    "errors": [str(e)],
                }
            )
            continue

        summary["total"] += 1
        if account_run.v1_status and account_run.v1_status.startswith("FAILED"):
            summary["failed"] += 1
        else:
            summary["succeeded"] += 1
        summary["accounts"].append(account_run.to_dict())

    summary["finished_at"] = datetime.now().isoformat()

    with open("outputs/batch_summary.json", "w") as f:
        json.dump(summary, f, indent=4)

    log.info("\n" + "═" * 60)
    log.info(f"{'ACCOUNT':<12} {'V1':<20} {'V2':<20}")
    log.info("═" * 60)
    for acc in summary["accounts"]:
        log.info(f"{acc['account_id']:<12} {str(acc['v1_status']):<20} {str(acc['v2_status']):<20}")
    log.info("═" * 60)
    log.info(
        f"Total: {summary['total']}  ✅ Succeeded: {summary['succeeded']}  ❌ Failed: {summary['failed']}  ⏭ Skipped: {summary['skipped']}"
    )
    log.info("Batch summary written → outputs/batch_summary.json")
    log.info("Industrial tracking updated → outputs/pipeline_tracker.db")

    return summary


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Clara AI – Batch Pipeline Runner")
    parser.add_argument("--demo-dir", default="data/demo", help="Path to demo transcripts directory")
    parser.add_argument("--onboarding-dir", default="data/onboarding", help="Path to onboarding transcripts directory")
    parser.add_argument("--force", action="store_true", help="Reprocess even if outputs already exist")
    args = parser.parse_args()
    run_pipeline(args.demo_dir, args.onboarding_dir, args.force)


if __name__ == "__main__":
    _cli()
