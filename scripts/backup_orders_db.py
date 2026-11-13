"""
Резервная копия SQLite (orders.db).

Запуск из корня проекта:
  python scripts/backup_orders_db.py
  python scripts/backup_orders_db.py --keep 14

Использует API backup SQLite — можно при работающем боте.
Копии: backups/orders-YYYYMMDD-HHMMSS.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DATABASE_PATH  # noqa: E402

DEFAULT_BACKUP_DIR = ROOT / "backups"
DEFAULT_KEEP = 30


def _resolve_db_path() -> Path:
    path = Path(DATABASE_PATH)
    if not path.is_absolute():
        path = ROOT / path
    return path


def backup_db(*, db_path: Path, backup_dir: Path) -> Path:
    if not db_path.is_file():
        raise FileNotFoundError(f"База не найдена: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"orders-{stamp}.db"

    with sqlite3.connect(db_path) as src:
        with sqlite3.connect(dest) as dst:
            src.backup(dst)

    return dest


def prune_old_backups(backup_dir: Path, keep: int) -> int:
    if keep < 1:
        return 0
    files = sorted(
        backup_dir.glob("orders-*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    removed = 0
    for old in files[keep:]:
        old.unlink(missing_ok=True)
        removed += 1
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Бэкап orders.db в папку backups/")
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"Куда сохранять (по умолчанию {DEFAULT_BACKUP_DIR.name}/)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP,
        help=f"Сколько последних копий оставить (по умолчанию {DEFAULT_KEEP})",
    )
    args = parser.parse_args()

    db_path = _resolve_db_path()
    try:
        dest = backup_db(db_path=db_path, backup_dir=args.dir)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        raise SystemExit(1) from e

    removed = prune_old_backups(args.dir, args.keep)
    print(f"OK: {dest}")
    if removed:
        print(f"Удалено старых копий: {removed}")


if __name__ == "__main__":
    main()
