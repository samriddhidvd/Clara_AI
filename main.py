#!/usr/bin/env python3
"""
Clara AI - Unified Command Line Interface
-----------------------------------------
The primary entry point for managing the Clara AI automation pipeline.
Supports batch processing, local transcription, and real-time status tracking.

Usage: python3 main.py [run|transcribe|status] --help

Author: Clara AI Pipeline Team
"""
import argparse
import sys
import os
from run_pipeline import run_pipeline
from scripts.transcribe_audio import transcribe
from scripts import task_tracker

def main():
    parser = argparse.ArgumentParser(description="Clara AI Automation Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run (Batch Pipeline)
    run_parser = subparsers.add_parser("run", help="Run the full batch pipeline")
    run_parser.add_argument("--demo-dir", default="data/demo", help="Demo transcripts directory")
    run_parser.add_argument("--onboarding-dir", default="data/onboarding", help="Onboarding transcripts directory")
    run_parser.add_argument("--force", action="store_true", help="Force reprocess even if outputs exist")

    # Command: transcribe
    trans_parser = subparsers.add_parser("transcribe", help="Transcribe an audio file locally (Whisper)")
    trans_parser.add_argument("audio_file", help="Path to .mp4, .m4a, or .mp3")
    trans_parser.add_argument("--output", help="Optional output path")
    trans_parser.add_argument("--model", default="base", help="tiny | base | small | medium")

    # Command: status
    status_parser = subparsers.add_parser("status", help="Show pipeline status from database")
    status_parser.add_argument("--account", help="Specific account ID")

    args = parser.parse_args()

    if args.command == "run":
        run_pipeline(args.demo_dir, args.onboarding_dir, args.force)
    
    elif args.command == "transcribe":
        transcribe(args.audio_file, args.output, args.model)
        
    elif args.command == "status":
        task_tracker.init_db()
        if args.account:
            row = task_tracker.get_account(args.account)
            if row:
                print(f"ID: {row[0]} | Company: {row[1]} | Status: {row[2]} | Last Updated: {row[3]}")
            else:
                print(f"Account {args.account} not found in database.")
        else:
            rows = task_tracker.list_all_accounts()
            print(f"{'ID':<5} {'Company':<25} {'Status':<25} {'Last Updated':<20}")
            print("-" * 80)
            for row in rows:
                print(f"{str(row[0]):<5} {str(row[1])[:24]:<25} {str(row[2]):<25} {str(row[3])[:19]:<20}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
