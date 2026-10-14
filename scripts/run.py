\"\"\"
Sentinel Agent - Main CLI
\"\"\"

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.config import settings
from core.pipeline import SentinelPipeline
from core.scheduler import SentinelScheduler
from core.permission_manager import PermissionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("sentinel")


def cmd_review_file(file_path: str):
    pipeline = SentinelPipeline()
    report = pipeline.run_on_local_file(file_path)
    print("\n" + report)


def cmd_scan_repo(repo_url: str, branch: str = "main"):
    pipeline = SentinelPipeline()
    report = pipeline.run_on_repo(repo_url, branch=branch)
    print("\nFinal report generated.")


def cmd_start_scheduler():
    """Start the background scheduler for nightly runs."""
    pipeline = SentinelPipeline()
    scheduler = SentinelScheduler()

    def nightly_job():
        repos = settings.watch_repos
        if not repos:
            logger.warning("No repositories configured in WATCH_REPOS or settings.yaml")
            return
        for repo in repos:
            try:
                logger.info(f"Nightly run starting for {repo}")
                pipeline.run_on_repo(repo)
            except Exception as e:
                logger.error(f"Failed on {repo}: {e}")

    scheduler.add_cron_job("nightly_code_review", nightly_job, settings.schedule_code_review)
    scheduler.start()

    print("Scheduler started. Nightly jobs are active.")
    print("Press Ctrl+C to stop.")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
        print("\nScheduler stopped.")


def cmd_permissions():
    pm = PermissionManager()
    print(f"Require approval : {pm.require_approval}")
    print(f"Pending approvals: {len(pm.list_pending())}")
    for i, req in enumerate(pm.list_pending()):
        print(f"  [{i}] {req['action']} → {req['details']}")


def main():
    parser = argparse.ArgumentParser(
        description="Sentinel Agent — Self-hosted multi-agent code & security guardian"
    )
    sub = parser.add_subparsers(dest="command")

    # review
    p_review = sub.add_parser("review", help="Review a local file")
    p_review.add_argument("file", type=str)

    # repo
    p_repo = sub.add_parser("repo", help="Run full pipeline on a git repository")
    p_repo.add_argument("url", type=str, help="Repository URL (https or git)")
    p_repo.add_argument("--branch", default="main")

    # scheduler
    sub.add_parser("schedule", help="Start nightly scheduler")

    # permissions
    sub.add_parser("permissions", help="Show permission status")

    # test
    sub.add_parser("test", help="Quick health check")

    args = parser.parse_args()

    if args.command == "review":
        cmd_review_file(args.file)
    elif args.command == "repo":
        cmd_scan_repo(args.url, branch=args.branch)
    elif args.command == "schedule":
        cmd_start_scheduler()
    elif args.command == "permissions":
        cmd_permissions()
    elif args.command == "test":
        print("Sentinel Agent is ready.")
        print(f"Model     : {settings.model_name}")
        print(f"Ollama    : {settings.ollama_base_url}")
        print(f"Approval  : {settings.require_approval}")
        print(f"Watch list: {settings.watch_repos or '(empty)'}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
