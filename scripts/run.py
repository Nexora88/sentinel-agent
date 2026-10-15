"""
SEKA — Sentinel Egemen Kişisel Ajan · CLI
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
logger = logging.getLogger("seka")


def main():
    parser = argparse.ArgumentParser(description="SEKA — yerel süper ajan (Ollama, apisiz)")
    sub = parser.add_subparsers(dest="command")

    p_review = sub.add_parser("review", help="Yerel dosya incele")
    p_review.add_argument("file", type=str)

    p_repo = sub.add_parser("repo", help="Git repo pipeline")
    p_repo.add_argument("url", type=str)
    p_repo.add_argument("--branch", default="main")

    p_debug = sub.add_parser("debug", help="Hata ayıkla")
    p_debug.add_argument("error", type=str)
    p_debug.add_argument("--code", type=str, default="")
    p_debug.add_argument("--file", type=str, default="")

    p_web = sub.add_parser("website", help="Site savunma taraması")
    p_web.add_argument("url", type=str)

    p_fix = sub.add_parser("fix", help="Düzeltme öner / uygula (onaylı)")
    p_fix.add_argument("file", type=str)
    p_fix.add_argument("issue", type=str)

    p_expand = sub.add_parser("expand", help="Bilgi evrenini genişlet")
    p_expand.add_argument("--topic", type=str, default=None)

    p_secrets = sub.add_parser("secrets", help="Gizli anahtar tara")
    p_secrets.add_argument("--path", type=str, default=".")

    p_lic = sub.add_parser("licenses", help="Lisans hijyeni")
    p_lic.add_argument("--path", type=str, default=".")

    p_ingest = sub.add_parser("ingest", help="PDF/MD/TXT yükle + analiz")
    p_ingest.add_argument("file", type=str)

    p_doc = sub.add_parser("doc-analyze", help="Belge metni analiz")
    p_doc.add_argument("file", type=str)

    p_legacy = sub.add_parser("legacy-backup", help="Şifreli yerel yedek")
    p_legacy.add_argument("--passphrase", required=True)
    p_legacy.add_argument("--out", default="./memory/legacy_backup.bin")

    sub.add_parser("discover", help="Localhost port keşfi (salt okuma)")
    sub.add_parser("curiosity", help="Merak turu")
    sub.add_parser("night", help="Gece araştırması")
    sub.add_parser("podcast", help="Son gece raporundan podcast taslağı")
    sub.add_parser("finance", help="Paper trading döngüsü")
    sub.add_parser("schedule", help="Zamanlayıcı")
    sub.add_parser("permissions", help="Onay durumu")
    sub.add_parser("test", help="Sağlık kontrolü")

    p_chat = sub.add_parser("chat", help="Terminal sohbet")
    p_chat.add_argument("message", nargs="?", default=None)

    p_webui = sub.add_parser("web", help="SEKA Web UI")
    p_webui.add_argument("--port", type=int, default=8000)
    p_webui.add_argument("--host", type=str, default="0.0.0.0")

    args = parser.parse_args()

    # The web panel must start even when Ollama/Chroma cannot initialize yet.
    # Initialize the full agent graph only for commands that actually need it.
    if args.command == "web":
        import uvicorn
        print(f"◈ SEKA → http://{args.host}:{args.port}")
        uvicorn.run("web.app:app", host=args.host, port=args.port, reload=False, log_level="info")
        return

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
            print(f"Konu: {result.get('topic')} | +{result.get('pages_ingested')} | toplam {result.get('total_knowledge_pages')}")
    elif args.command == "secrets":
        print(pipeline.scan_secrets(args.path))
    elif args.command == "licenses":
        print(pipeline.check_licenses(args.path))
    elif args.command == "ingest":
        r = pipeline.ingest_document(args.file)
        print(r.get("message") or r.get("error") or r)
        if r.get("analysis_report"):
            print("\n" + r["analysis_report"])
    elif args.command == "doc-analyze":
        text = Path(args.file).read_text(encoding="utf-8", errors="ignore")
        print(pipeline.analyze_document_text(text))
    elif args.command == "legacy-backup":
        print(pipeline.legacy_export(args.passphrase, out_path=args.out))
    elif args.command == "discover":
        print(pipeline.discover_local_report())
    elif args.command == "curiosity":
        print("🔭 Merak...")
        r = pipeline.run_curiosity()
        print(f"Konu: {r.get('topic')}\nSayfa: {r.get('expand', {}).get('pages_ingested')}\n{r.get('reflection', '')[:1500]}")
    elif args.command == "night":
        print("🌙 Gece...")
        print(pipeline.run_night_research().get("summary", ""))
    elif args.command == "podcast":
        print("🎙 Podcast taslağı...")
        r = pipeline.podcast_from_night()
        if r.get("success"):
            print(f"Dosya: {r.get('path')}\n\n{r.get('script', '')[:4000]}")
        else:
            print(r.get("error", r))
    elif args.command == "finance":
        result = pipeline.run_finance_cycle()
        st = result.get("status") or {}
        print(f"Mode {st.get('mode')} | Equity ${st.get('equity', 0):.2f} | PnL {st.get('pnl_total_pct', 0):+.2f}%")
        print(result.get("decision"))
    elif args.command == "schedule":
        scheduler = SentinelScheduler()

        def nightly_job():
            for repo in settings.watch_repos or []:
                try:
                    pipeline.run_on_repo(repo)
                except Exception as e:
                    logger.error(f"repo {repo}: {e}")

        def knowledge_job():
            try:
                advice = should_run_heavy_job("universe_expand")
                if advice.get("prefer_defer") and not advice.get("off_peak"):
                    return
                pipeline.expand_knowledge()
            except Exception as e:
                logger.error(f"knowledge: {e}")

        def night_job():
            try:
                r = pipeline.run_night_research()
                s = (r.get("summary") or "")[:800]
                if s:
                    pipeline.notifier.notify(f"🌙 SEKA Gece\n{s}", whatsapp=True)
            except Exception as e:
                logger.error(f"night: {e}")

        def finance_job():
            try:
                pipeline.run_finance_cycle()
            except Exception as e:
                logger.error(f"finance: {e}")

        def curiosity_job():
            try:
                advice = should_run_heavy_job("curiosity")
                if advice.get("prefer_defer") and not advice.get("off_peak"):
                    return
                pipeline.run_curiosity()
            except Exception as e:
                logger.error(f"curiosity: {e}")

        scheduler.add_cron_job("nightly_review", nightly_job, settings.schedule_code_review)
        scheduler.add_cron_job("universe_expand", knowledge_job, "*/90 * * * *")
        scheduler.add_cron_job("night_research", night_job, "30 3 * * *")
        scheduler.add_cron_job("paper_finance", finance_job, "15 */2 * * *")
        scheduler.add_cron_job("curiosity", curiosity_job, "45 */3 * * *")
        scheduler.start()
        print("SEKA zamanlayıcı aktif. Ctrl+C durdurur.")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
    elif args.command == "permissions":
        pm = PermissionManager()
        print(f"Onay gerekli: {pm.require_approval} | Bekleyen: {len(pm.list_pending())}")
    elif args.command == "test":
        print("SEKA hazır.")
        print(f"Model: {settings.model_name} | Ollama: {settings.ollama_base_url}")
        print(pipeline.status())
    elif args.command == "chat":
        if args.message:
            print(pipeline.chat(args.message))
        else:
            print("SEKA sohbet (exit / çık)")
            while True:
                try:
                    u = input("Sen: ").strip()
                    if not u:
                        continue
                    if u.lower() in ("exit", "quit", "çık"):
                        break
                    print(f"\nSEKA: {pipeline.chat(u)}\n")
                except (KeyboardInterrupt, EOFError):
                    break
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
