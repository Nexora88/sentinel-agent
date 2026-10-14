"""
Sentinel Agent - Main CLI
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

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


def main():
    parser = argparse.ArgumentParser(
        description="Sentinel Agent — Self-hosted multi-agent guardian"
    )
    sub = parser.add_subparsers(dest="command")

    # review
    p_review = sub.add_parser("review", help="Review a local file")
    p_review.add_argument("file", type=str)

    # repo
    p_repo = sub.add_parser("repo", help="Full pipeline on a git repository")
    p_repo.add_argument("url", type=str)
    p_repo.add_argument("--branch", default="main")

    # debug
    p_debug = sub.add_parser("debug", help="Debug an error message")
    p_debug.add_argument("error", type=str, help="Error message or stack trace")
    p_debug.add_argument("--code", type=str, default="", help="Related code (optional)")
    p_debug.add_argument("--file", type=str, default="", help="File path (optional)")

    # website
    p_web = sub.add_parser("website", help="Defensive scan of a website")
    p_web.add_argument("url", type=str)

    # fix
    p_fix = sub.add_parser("fix", help="Propose / apply a fix to a file (permission controlled)")
    p_fix.add_argument("file", type=str)
    p_fix.add_argument("issue", type=str, help="Description of the issue to fix")

    # expand knowledge once
    p_expand = sub.add_parser("expand", help="Expand knowledge universe once (internet digestion)")
    p_expand.add_argument("--topic", type=str, default=None, help="Optional topic to focus on")

    # schedule (nightly code + continuous knowledge)
    sub.add_parser("schedule", help="Start scheduler (nightly review + slow knowledge expansion)")

    # permissions
    sub.add_parser("permissions", help="Show permission status")

    # test
    sub.add_parser("test", help="Health check")

    # chat (CLI interactive)
    p_chat = sub.add_parser("chat", help="Talk to Sentinel interactively (terminal)")
    p_chat.add_argument("message", nargs="?", default=None, help="Optional single message")

    # web UI (main interface)
    p_webui = sub.add_parser("web", help="Start self-hosted web interface (recommended)")
    p_webui.add_argument("--port", type=int, default=8000)
    p_webui.add_argument("--host", type=str, default="0.0.0.0")

    args = parser.parse_args()
    pipeline = SentinelPipeline()

    if args.command == "review":
        print(pipeline.run_on_local_file(args.file))

    elif args.command == "repo":
        pipeline.run_on_repo(args.url, branch=args.branch)

    elif args.command == "debug":
        print(pipeline.debug_error(args.error, code=args.code, file_path=args.file))

    elif args.command == "website":
        print(pipeline.scan_website(args.url))

    elif args.command == "fix":
        print(pipeline.fix_file(args.file, args.issue))

    elif args.command == "expand":
        print("🌌 Bilgi evreni genişliyor...")
        result = pipeline.expand_knowledge(topic=args.topic)
        print(f"Konu          : {result.get('topic')}")
        print(f"Yeni sayfa    : {result.get('pages_ingested')}")
        print(f"Toplam bilgi  : {result.get('total_knowledge_pages')}")
        for d in result.get("details", []):
            print(f"  • {d.get('title', '')[:70]}")

    elif args.command == "schedule":
        scheduler = SentinelScheduler()

        def nightly_job():
            repos = settings.watch_repos
            if not repos:
                logger.warning("No repositories in WATCH_REPOS")
                return
            for repo in repos:
                try:
                    pipeline.run_on_repo(repo)
                except Exception as e:
                    logger.error(f"Failed on {repo}: {e}")

        def knowledge_job():
            try:
                result = pipeline.expand_knowledge()
                logger.info(
                    f"Knowledge expanded: +{result.get('pages_ingested', 0)} "
                    f"(total {result.get('total_knowledge_pages', 0)})"
                )
            except Exception as e:
                logger.error(f"Knowledge expansion failed: {e}")

        # Nightly code review
        scheduler.add_cron_job("nightly_review", nightly_job, settings.schedule_code_review)

        # Slow continuous knowledge growth (every 90 minutes)
        scheduler.add_cron_job("universe_expand", knowledge_job, "*/90 * * * *")

        scheduler.start()
        print("Scheduler started.")
        print("  • Nightly code review")
        print("  • Knowledge universe expands every ~90 minutes")
        print("Ctrl+C to stop.")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()

    elif args.command == "permissions":
        pm = PermissionManager()
        print(f"Require approval : {pm.require_approval}")
        print(f"Pending          : {len(pm.list_pending())}")
        for i, req in enumerate(pm.list_pending()):
            print(f"  [{i}] {req['action']} → {req['details']}")

    elif args.command == "test":
        print("Sentinel Agent ready.")
        print(f"Model      : {settings.model_name}")
        print(f"Ollama     : {settings.ollama_base_url}")
        print(f"Approval   : {settings.require_approval}")
        print(f"WhatsApp   : {'configured' if os.getenv('WHATSAPP_PHONE') else 'not configured'}")
        print(f"Watch list : {settings.watch_repos or '(empty)'}")
        print()
        print(pipeline.status())

    elif args.command == "chat":
        if args.message:
            print(pipeline.chat(args.message))
        else:
            print("🛡️  Sentinel Chat (Ctrl+C to exit)")
            print(pipeline.status())
            print("-" * 40)
            while True:
                try:
                    user_input = input("Sen: ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ("exit", "quit", "çık"):
                        break
                    reply = pipeline.chat(user_input)
                    print(f"\nSentinel: {reply}\n")
                except (KeyboardInterrupt, EOFError):
                    print("\nGörüşürüz.")
                    break

    elif args.command == "web":
        import uvicorn
        print(f"🌐 Sentinel Web UI → http://{args.host}:{args.port}")
        print("Tarayıcıdan aç. Emirlerini oradan ver.")
        uvicorn.run(
            "web.app:app",
            host=args.host,
            port=args.port,
            reload=False,
            log_level="info",
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
