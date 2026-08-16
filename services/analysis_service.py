import csv
from pathlib import Path

from config import Config
from repositories.chat_wheel_repository import ChatWheelRepository
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository


class AnalysisService:
    """Analiza partidas parseadas para construir un ranking combinado de rampages.

    Puntaje por posición dentro de la selección elegida: el rampage con la racha
    más corta y el que acumula más reacciones suman más puntos.
    """

    FIELDNAMES = [
        "rank",
        "match_id",
        "fecha_partida",
        "hero_id",
        "hero_name",
        "rampage_time",
        "rampage_time_min",
        "racha_seg",
        "n_reacciones",
        "puntaje_racha",
        "puntaje_reacciones",
        "puntaje_total",
        "chats_reaccion",
    ]

    def __init__(
        self,
        hero_repository: HeroRepository,
        match_repository: MatchRepository,
        chat_wheel_repository: ChatWheelRepository,
    ) -> None:
        self.hero_repo = hero_repository
        self.match_repo = match_repository
        self.chat_wheel_repo = chat_wheel_repository
        heroes = self.hero_repo.list_all()
        self.hero_names = {h["id"]: h["display_name"] for h in heroes}

    def list_dates(self) -> list[tuple[str, int]]:
        """Return the parsed dates with distinct match counts, newest first."""
        return self.match_repo.list_dates_with_parsed()

    def export_top(self, date_prefix: str | None = None) -> Path | None:
        """Build the combined ranking for a date (or all dates) and export it as CSV."""
        rows = self.match_repo.list_parsed_rows_by_date(date_prefix)
        if not rows:
            print("\nNo hay partidas parseadas para la selección indicada.")
            return None

        records = self._build_records(rows)
        if not records:
            print("\nNo se detectaron rampages en la selección.")
            return None

        ranked = self._rank_records(records)
        self._print_top(ranked)

        label = date_prefix if date_prefix else "all"
        csv_path = self._write_csv(label, ranked)
        print(f"\n✓ Exportado ranking combinado a {csv_path}")
        return csv_path

    def _build_records(self, rows: list[tuple[int, str, int]]) -> list[dict]:
        grouped: dict[int, dict] = {}
        for match_id, played_at, hero_id in rows:
            entry = grouped.setdefault(match_id, {"played_at": played_at, "hero_ids": []})
            if hero_id not in entry["hero_ids"]:
                entry["hero_ids"].append(hero_id)

        records: list[dict] = []
        for match_id, info in grouped.items():
            data = self.match_repo.get_match_details(match_id)
            if data is None:
                continue
            rampage = self._detect_shortest_rampage(info["hero_ids"], data)
            if rampage is None:
                continue
            hero_id, rampage_start, rampage_end, duration = rampage
            reactions = self._collect_reactions(data, rampage_end)
            chats_str = " | ".join(
                f"[{int(r['time'] // 60):02d}:{int(r['time'] % 60):02d}] "
                f"{r['sender_hero_name']}: {r['message']}".rstrip()
                for r in reactions
            )
            records.append(
                {
                    "match_id": match_id,
                    "fecha_partida": info["played_at"][:10],
                    "hero_id": hero_id,
                    "hero_name": self.hero_names.get(hero_id, ""),
                    "rampage_time": rampage_start,
                    "rampage_time_min": round(rampage_start / 60, 2),
                    "racha_seg": duration,
                    "n_reacciones": len(reactions),
                    "chats_reaccion": chats_str,
                }
            )
        return records

    def _detect_shortest_rampage(
        self, hero_ids: list[int], data: dict
    ) -> tuple[int, int, int, int] | None:
        """Return (hero_id, start_time, end_time, duration) for the shortest
        5-kill window (<=18s) among the given heroes."""
        players = {p.get("hero_id"): p for p in data.get("players") or []}
        best: tuple[int, int, int, int] | None = None
        for hero_id in hero_ids:
            player = players.get(hero_id)
            if not player:
                continue
            kills = sorted(
                player.get("kills_log") or [],
                key=lambda k: k.get("time", 0),
            )
            if len(kills) < 5:
                continue
            for i in range(len(kills) - 4):
                window = kills[i : i + 5]
                times = [k.get("time", 0) for k in window]
                duration = times[-1] - times[0]
                if duration <= 18 and (best is None or duration < best[3]):
                    best = (hero_id, times[0], times[-1], duration)
        return best

    def _collect_reactions(self, data: dict, rampage_end: int) -> list[dict]:
        """Return chat messages right after the rampage (within the reaction window)."""
        player_slots = {
            p["player_slot"]: p["hero_id"]
            for p in data.get("players") or []
            if p.get("player_slot") is not None and p.get("hero_id") is not None
        }
        limit = rampage_end + Config.ANALYSIS_REACTION_WINDOW_SECONDS
        reactions: list[dict] = []
        for msg in sorted(data.get("chat") or [], key=lambda m: m.get("time", 0)):
            t = msg.get("time")
            if t is None or t <= rampage_end or t > limit:
                continue
            player_slot = msg.get("player_slot")
            sender_hero_id = (
                player_slots.get(player_slot) if player_slot is not None else None
            )
            reactions.append(
                {
                    "time": t,
                    "message": self._resolve_chat_message(msg),
                    "sender_hero_name": self.hero_names.get(sender_hero_id, ""),
                }
            )
        return reactions

    def _resolve_chat_message(self, msg: dict) -> str:
        msg_type = msg.get("type", "")
        key = msg.get("key", "")
        if msg_type != "chatwheel":
            return str(key)
        try:
            chat_wheel_id = int(key)
        except (ValueError, TypeError):
            return str(key)
        entry = self.chat_wheel_repo.get_by_id(chat_wheel_id)
        if entry is None:
            return f"chatwheel:{key}"
        return (
            entry.get("label")
            or entry.get("message")
            or entry.get("name")
            or f"chatwheel:{key}"
        )

    def _rank_records(self, records: list[dict]) -> list[dict]:
        n = len(records)
        by_speed = sorted(records, key=lambda r: (r["racha_seg"], r["match_id"]))
        for pos, rec in enumerate(by_speed, start=1):
            rec["puntaje_racha"] = n - pos + 1
        by_reactions = sorted(records, key=lambda r: (-r["n_reacciones"], r["match_id"]))
        for pos, rec in enumerate(by_reactions, start=1):
            rec["puntaje_reacciones"] = n - pos + 1
        for rec in records:
            rec["puntaje_total"] = rec["puntaje_racha"] + rec["puntaje_reacciones"]
        ranked = sorted(
            records,
            key=lambda r: (-r["puntaje_total"], r["racha_seg"], r["match_id"]),
        )
        for pos, rec in enumerate(ranked, start=1):
            rec["rank"] = pos
        return ranked

    def _print_top(self, ranked: list[dict]) -> None:
        print(f"\n=== TOP {Config.ANALYSIS_TOP_N} RAMPAGES (puntaje combinado) ===")
        for rec in ranked[: Config.ANALYSIS_TOP_N]:
            print(
                f"#{rec['rank']:>3} | {rec['fecha_partida']} | {rec['match_id']} | "
                f"{rec['hero_name']:<20} | racha {rec['racha_seg']:>2}s | "
                f"reacciones {rec['n_reacciones']:>2} | pts {rec['puntaje_total']}"
            )

    def _write_csv(self, label: str, records: list[dict]) -> Path:
        export_dir = Config.ANALYSIS_EXPORT_DIR
        export_dir.mkdir(parents=True, exist_ok=True)
        csv_path = export_dir / f"rampages_{label}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            for rec in records:
                writer.writerow({name: rec.get(name) for name in self.FIELDNAMES})
        return csv_path
