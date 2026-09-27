from __future__ import annotations
from .core.context import ContextAssembler, Retriever
from .core.engine import RUNEEngine
from .core.persistence import SQLiteEventStore
from .core.model import ModelProvider

class RUNERuntime:
    """Composition root for a persistent local RUNE process."""
    def __init__(self, model: ModelProvider, db_path: str="data/rune.db", retriever: Retriever|None=None) -> None:
        self.engine=RUNEEngine(model)
        self.store=SQLiteEventStore(db_path)
        self.retriever=retriever
        self.context=ContextAssembler(self.engine.memory)
    def receive(self,text:str)->str:
        evidence=self.retriever.search(text) if self.retriever else []
        prompt=self.context.build(text,evidence)
        response=self.engine.receive(prompt)
        for event in self.engine.state.events[-2:]: self.store.append(event)
        return response
    def close(self)->None: self.store.close()
