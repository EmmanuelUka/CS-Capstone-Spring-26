"""
Delete all recruits using the hashmark_db.py data-layer API.

No Flask endpoints are used.

Examples:
  python backend/data/delete_all_recruits_via_api.py --yes
  python backend/data/delete_all_recruits_via_api.py
"""

from __future__ import annotations

import argparse
import sys

import hashmark_db as hdb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete all recruits using hashmark_db API.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    recruits_df = hdb.get_recruits_df()
    recruit_ids = [] if recruits_df is None or recruits_df.empty else recruits_df["id"].tolist()

    print(f"Database: {hdb.get_db_path()}")
    print(f"Found {len(recruit_ids)} recruits.")
    if not recruit_ids:
        print("Nothing to delete.")
        return 0

    if not args.yes:
        confirmation = input("Type DELETE to remove all recruits: ").strip()
        if confirmation != "DELETE":
            print("Cancelled.")
            return 0

    deleted = 0
    failed = 0

    for recruit_id in recruit_ids:
        try:
            hdb.delete_player(int(recruit_id))
            deleted += 1
        except Exception as exc:
            failed += 1
            print(f"Failed to delete recruit id={recruit_id}: {exc}", file=sys.stderr)

    print(f"Deleted: {deleted}")
    print(f"Failed : {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
