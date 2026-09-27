from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Any
from .models import Event

class SQLiteEventStore:
    """Small durable event store. SQLite keeps the first runtime dependency-free."""
    def __init__(self, path: str | Path = "data/rune.db") -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:" and self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self.path))
        self._db.execute("CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, type TEXT NOT NULL, payload TEXT NOT NULL)")
        self._db.commit()
    def append(self, event: Event) -> None:
        self._db.execute("INSERT OR REPLACE INTO events(id,timestamp,type,payload) VALUES (?,?,?,?)",
                         (event.id,event.timestamp.isoformat(),event.type.value,json.dumps(event.payload)))
        self._db.commit()
    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        rows=self._db.execute("SELECT id,timestamp,type,payload FROM events ORDER BY rowid DESC LIMIT ?",(limit,)).fetchall()
        return [{"id":r[0],"timestamp":r[1],"type":r[2],"payload":json.loads(r[3])} for r in rows]
    def close(self) -> None:
        self._db.close()
