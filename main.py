#!/usr/bin/env python3
"""
Thin CLI wrapper around the Clara AI batch and utility commands.

The goal of this module is ergonomics for humans running the project from a
terminal: it simply forwards arguments into the underlying implementation
modules (`run_pipeline`, `scripts.transcribe_audio`, `scripts.task_tracker`).
"""

import argparse
from typing import Optional

from run_pipeline import run_pipeline
from scripts.transcribe_audio import transcribe
from scripts import task_tracker


def _handle_run(args) -> None:
    run_pipeline(args.demo_dir, args.onboarding_dir, args.force)


def _handle_transcribe(args) -> None:
    transcribe(args.audio_file, args.output, args.model)


def _handle_status(args) -> None:
    task_tracker.init_db()
    if args.account:
        row = task_tracker.get_account(args.account)
        if row:
            print(f"ID: {row[0]} | Company: {row[1]} | Status: {row[2]} | Last Updated: {row[3]}")
        else:
            print(f"Account {args.account} not found in database.")
        return

    rows = task_tracker.list_all_accounts()
    print(f"{'ID':<5} {'Company':<25} {'Status':<25} {'Last Updated':<20}")
    print("-" * 80)
    for row in rows:
        print(f"{str(row[0]):<5} {str(row[1])[:24]:<25} {str(row[2]):<25} {str[row[3])[:19]:<20}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clara AI Automation Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser("run", help="Run the full batch pipeline")
    run_parser.set_defaults(handler=_handle_run)
    run_parser.add_argument("--demo-dir", default="data/demo", help="Demo transcripts directory")
    run_parser.add_argument("--onboarding-dir", default="data/onboarding", help="Onboarding transcripts directory")
    run_parser.add_argument("--force", action="store_true", help="Force reprocess even if outputs exist")

    trans_parser = subparsers.add_parser("transcribe", help="Transcribe an audio file locally (Whisper)")
    trans_parser.set_defaults(handler=_handle_transcribe)
    trans_parser.add_argument("audio_file", help="Path to .mp4, .m4a, or .mp3")
    trans_parser.add_argument("--output", help="Optional output path")
    trans_parser.add_argument("--model", default="base", help="tiny | base | small | medium")

    status_parser = subparsers.add_parser("status", help="Show pipeline status from database")
    status_parser.set_defaults(handler=_handle_status)
    status_parser.add_argument("--account", help="Specific account ID")

    return parser


def main(argv: Optional[list] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return
    handler(args)


if __name__ == "__main__":
    main()
