from __future__ import annotations
import json
from dataclasses import dataclass
from urllib.request import Request, urlopen
from rune.core.model import ModelResponse

@dataclass
class OllamaModel:
    """Local Ollama adapter. RUNE remains independent of Ollama."""
    model: str = "llama3.2:3b"
    endpoint: str = "http://127.0.0.1:11434/api/generate"
    timeout: float = 120.0
    def respond(self, prompt: str) -> ModelResponse:
        body=json.dumps({"model":self.model,"prompt":prompt,"stream":False}).encode()
        req=Request(self.endpoint,data=body,headers={"Content-Type":"application/json","Accept":"application/json"},method="POST")
        with urlopen(req,timeout=self.timeout) as response:
            payload=json.loads(response.read().decode())
        return ModelResponse(content=payload.get("response",""),confidence=0.0)
