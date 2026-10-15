"""
Bilgi Paketi — sanitize edilmiş, paylaşılabilir araştırma paketi.
Tam hafıza / kişisel veri dışarı çıkmaz.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.safety import sanitize_web_content


class KnowledgePack:
    def __init__(self, universe_dir: str = "./memory/universe", out_dir: str = "./memory/packs"):
        self.universe_dir = Path(universe_dir)
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def export_pack(
        self,
        title: str = "SEKA Araştırma Paketi",
        max_topics: int = 12,
        notes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        stats_path = self.universe_dir / "stats.json"
        seeds_path = self.universe_dir / "seeds.json"
        stats = {}
        seeds = []
        if stats_path.exists():
            try:
                stats = json.loads(stats_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        if seeds_path.exists():
            try:
                seeds = json.loads(seeds_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        topics = (stats.get("topics_explored") or seeds)[-max_topics:]
        topics = [sanitize_web_content(str(t))[:200] for t in topics]

        pack = {
            "format": "seka-knowledge-pack-v1",
            "title": sanitize_web_content(title)[:120],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "generator": "SEKA local agent",
            "disclaimer": (
                "Paylaşılabilir özet pakettir. Kişisel sohbet, şifre, cüzdan verisi içermez. "
                "Kaynaklar kullanıcı makinesinde doğrulanmalıdır."
            ),
            "stats": {
                "total_pages_ingested": stats.get("total_pages_ingested", 0),
                "total_runs": stats.get("total_runs", 0),
            },
            "topics": topics,
            "notes": [sanitize_web_content(n)[:500] for n in (notes or [])][:20],
        }

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
        path = self.out_dir / f"pack_{ts}.json"
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")

        md_path = self.out_dir / f"pack_{ts}.md"
        md_lines = [
            f"# {pack['title']}",
            "",
            f"_{pack['created_at']}_ · SEKA",
            "",
            pack["disclaimer"],
            "",
            f"- Toplam bilgi parçası: {pack['stats']['total_pages_ingested']}",
            f"- Tur: {pack['stats']['total_runs']}",
            "",
            "## Konular",
        ]
        for t in topics:
            md_lines.append(f"- {t}")
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        return {
            "success": True,
            "json_path": str(path),
            "md_path": str(md_path),
            "pack": pack,
        }
