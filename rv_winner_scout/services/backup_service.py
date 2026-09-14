import json
import os
from datetime import datetime, timezone
from typing import Any, List, Optional
from rv_winner_scout.config.settings import Settings, get_settings


class BackupService:
    """Creates timestamped immutable backups prior to sheet and database mutations."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.backup_dir = os.path.join(self.settings.data_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    def backup_records(self, prefix: str, records: List[Any]) -> str:
        """Serializes records to an immutable JSON backup file."""
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{now_str}.json"
        filepath = os.path.join(self.backup_dir, filename)

        serializable: List[Any] = []
        for r in records:
            if hasattr(r, "model_dump"):
                serializable.append(r.model_dump(mode="json"))
            elif hasattr(r, "__dict__"):
                serializable.append(r.__dict__)
            else:
                serializable.append(r)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, default=str)

        return filepath
