"""Command-line maintenance for the local runtime store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from k9_expert.application.composition import load_settings
from k9_expert.application.store_reset import StoreResetError, inventory_store, reset_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or reset one K9 runtime store.")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-store-id")
    parser.add_argument("--remove-backups", action="store_true")
    parser.add_argument("--confirm-backup-removal", action="store_true")
    parser.add_argument("--destructive-fallback", action="store_true")
    args = parser.parse_args()
    root = args.data_dir or load_settings().data_dir
    try:
        if not args.execute:
            result: dict[str, object] = {
                "status": "preview",
                **inventory_store(root).as_dict(),
            }
        else:
            if not args.confirm_store_id:
                parser.error("--execute requires --confirm-store-id")
            result = reset_store(
                root,
                confirm_store_id=args.confirm_store_id,
                remove_backups=args.remove_backups,
                confirm_backup_removal=args.confirm_backup_removal,
                destructive_fallback=args.destructive_fallback,
            )
    except StoreResetError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
