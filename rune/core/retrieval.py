from __future__ import annotations
import json
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

@dataclass
class HttpJsonRetriever:
    """Provider-neutral HTTP JSON retrieval adapter."""
    endpoint: str
    timeout: float = 10.0
    def search(self, query: str, limit: int = 5) -> list[dict]:
        url=self.endpoint.replace("{query}",quote(query)).replace("{limit}",str(limit))
        req=Request(url,headers={"Accept":"application/json","User-Agent":"RUNE/0.1"})
        with urlopen(req,timeout=self.timeout) as response:
            payload=json.loads(response.read().decode())
        if isinstance(payload,list): return payload[:limit]
        if isinstance(payload,dict) and isinstance(payload.get("results"),list): return payload["results"][:limit]
        return []
