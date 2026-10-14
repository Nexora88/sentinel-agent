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
from core.energy_policy import should_run_heavy_job

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

    p_review = sub.add_parser("review", help="Review a local file")
    p_review.add_argument("file", type=str)

    p_repo = sub.add_parser("repo", help="Full pipeline on a git repository")
    p_repo.add_argument("url", type=str)
    p_repo.add_argument("--branch", default="main")

    p_debug = sub.add_parser("debug", help="Debug an error message")
    p_debug.add_argument("error", type=str)
    p_debug.add_argument("--code", type=str, default="")
    p_debug.add_argument("--file", type=str, default="")

    p_web = sub.add_parser("website", help="Defensive scan of a website")
    p_web.add_argument("url", type=str)

    p_fix = sub.add_parser("fix", help="Propose / apply a fix (permission controlled)")
    p_fix.add_argument("file", type=str)
    p_fix.add_argument("issue", type=str)

    p_expand = sub.add_parser("expand", help="Expand knowledge universe once")
    p_expand.add_argument("--topic", type=str, default=None)

    p_secrets = sub.add_parser("secrets", help="Scan project for hardcoded secrets")
    p_secrets.add_argument("--path", type=str, default=".")

    p_lic = sub.add_parser("licenses", help="License / copyright hygiene scan")
    p_lic.add_argument("--path", type=str, default=".")

    p_ingest = sub.add_parser("ingest", help="Ingest local PDF/MD/TXT into knowledge base")
    p_ingest.add_argument("file", type=str)

    p_doc = sub.add_parser("doc-analyze", help="Analyze document text (suggestions only)")
    p_doc.add_argument("file", type=str, help="Path to text/md file")

    p_legacy = sub.add_parser("legacy-backup", help="Encrypted local memory backup")
    p_legacy.add_argument("--passphrase", required=True)
    p_legacy.add_argument("--out", default="./memory/legacy_backup.bin")

    sub.add_parser("discover", help="Read-only localhost port discovery")
    sub.add_parser("curiosity", help="One curiosity-driven knowledge cycle")
    sub.add_parser("night", help="Run one safe night research cycle")
    sub.add_parser("finance", help="Run one paper-trading cycle")
    sub.add_parser("schedule", help="Scheduler: review + knowledge + night + finance + curiosity")
    sub.add_parser("permissions", help="Show permission status")
    sub.add_parser("test", help="Health check")

    p_chat = sub.add_parser("chat", help="Interactive terminal chat")
    p_chat.add_argument("message", nargs="?", default=None)

    p_webui = sub.add_parser("web", help="Start web UI (recommended)")
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
        if result.get("deferred"):
            print(f"Ertelendi: {result.get('reason')}")
        else:
            print(f"Konu          : {result.get('topic')}")
            print(f"Yeni sayfa    : {result.get('pages_ingested')}")
            print(f"Toplam bilgi  : {result.get('total_knowledge_pages')}")

    elif args.command == "secrets":
        print(pipeline.scan_secrets(args.path))

    elif args.command == "licenses":
        print(pipeline.check_licenses(args.path))

    elif args.command == "ingest":
        print(pipeline.ingest_document(args.file))

    elif args.command == "doc-analyze":
        text = Path(args.file).read_text(encoding="utf-8", errors="ignore")
        print(pipeline.analyze_document_text(text))

    elif args.command == "legacy-backup":
        print(pipeline.legacy_export(args.passphrase, out_path=args.out))

    elif args.command == "discover":
        print(pipeline.discover_local())

    elif args.command == "curiosity":
        print("🔭 Merak döngüsü...")
        r = pipeline.run_curiosity()
        print(f"Konu: {r.get('topic')}")
        print(f"Sayfa: {r.get('expand', {}).get('pages_ingested')}")
        print(r.get("reflection", "")[:1500])

    elif args.command == "night":
        print("🌙 Gece araştırma döngüsü...")
        result = pipeline.run_night_research()
        print(result.get("summary", str(result)))

    elif args.command == "finance":
        print("💰 Paper trading döngüsü (sanal para)...")
        result = pipeline.run_finance_cycle()
        st = result.get("status") or {}
        dec = result.get("decision") or {}
        print(f"Mode     : {st.get('mode')}")
        print(f"Equity   : ${st.get('equity', 0):.2f}")
        print(f"Cash     : ${st.get('cash', 0):.2f}")
        print(f"PnL      : {st.get('pnl_total_pct', 0):+.2f}%")
        print(f"Decision : {dec}")
        if result.get("stops_triggered"):
            print(f"Stops    : {result['stops_triggered']}")

    elif args.command == "schedule":
        scheduler = SentinelScheduler()

        def nightly_job():
            repos = settings.watch_repos
            if not repos:
                return
            for repo in repos:
                try:
                    pipeline.run_on_repo(repo)
                except Exception as e:
                    logger.error(f"Failed on {repo}: {e}")

        def knowledge_job():
            try:
                advice = should_run_heavy_job("universe_expand")
                if advice.get("prefer_defer") and not advice.get("off_peak"):
                    logger.info("Knowledge expand deferred (energy policy)")
                    return
                result = pipeline.expand_knowledge()
                logger.info(f"Knowledge +{result.get('pages_ingested', 0)}")
            except Exception as e:
                logger.error(f"Knowledge failed: {e}")

        def night_job():
            try:
                r = pipeline.run_night_research()
                summary = r.get("summary", "")[:800]
                if summary:
                    pipeline.notifier.notify(f"🌙 Night Report\n{summary}", whatsapp=True)
            except Exception as e:
                logger.error(f"Night research failed: {e}")

        def finance_job():
            try:
                r = pipeline.run_finance_cycle()
                st = r.get("status") or {}
                logger.info(
                    f"Paper finance: equity=${st.get('equity')} pnl={st.get('pnl_total_pct')}%"
                )
            except Exception as e:
                logger.error(f"Finance cycle failed: {e}")

        def curiosity_job():
            try:
                advice = should_run_heavy_job("curiosity")
                if advice.get("prefer_defer") and not advice.get("off_peak"):
                    logger.info("Curiosity deferred (energy policy)")
                    return
                r = pipeline.run_curiosity()
                logger.info(f"Curiosity: {r.get('topic')}")
            except Exception as e:
                logger.error(f"Curiosity failed: {e}")

        scheduler.add_cron_job("nightly_review", nightly_job, settings.schedule_code_review)
        scheduler.add_cron_job("universe_expand", knowledge_job, "*/90 * * * *")
        scheduler.add_cron_job("night_research", night_job, "30 3 * * *")
        scheduler.add_cron_job("paper_finance", finance_job, "15 */2 * * *")
        scheduler.add_cron_job("curiosity", curiosity_job, "45 */3 * * *")

        scheduler.start()
        print("Scheduler started:")
        print("  • Nightly code review")
        print("  • Knowledge expand ~90 min (energy-aware)")
        print("  • Night research ~03:30")
        print("  • Paper finance ~2 hours")
        print("  • Curiosity ~3 hours")
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
        print(f"GitHub     : {'configured' if os.getenv('GITHUB_TOKEN') else 'not configured'}")
        print()
        print(pipeline.status())

    elif args.command == "chat":
        if args.message:
            print(pipeline.chat(args.message))
        else:
            print("🛡️  Sentinel Chat (Ctrl+C / exit)")
            print(pipeline.status())
            print("-" * 40)
            while True:
                try:
                    user_input = input("Sen: ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ("exit", "quit", "çık"):
                        break
                    print(f"\nSentinel: {pipeline.chat(user_input)}\n")
                except (KeyboardInterrupt, EOFError):
                    print("\nGörüşürüz.")
                    break

    elif args.command == "web":
        import uvicorn
        print(f"🌐 Sentinel Web UI → http://{args.host}:{args.port}")
        uvicorn.run("web.app:app", host=args.host, port=args.port, reload=False, log_level="info")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
