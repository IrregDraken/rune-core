import json
import pytest

from rune.core.model import ModelResponse
from rune.core.orchestrator import OrchestrationError, RUNEOrchestrator


class FakeModel:
    def __init__(self,response): self.response=response
    def respond(self,prompt): return ModelResponse(self.response,0.9)


class FakeRemote:
    def list_devices(self):
        return [{"id":"phone-1","device_name":"Phone","platform":"android","status":"online",
                 "capabilities":["app.list","app.launch","ui.observe","ui.interact"]}]
    def create_task(self,device_id,capability,arguments,*,expires_in_seconds=60):
        return {"task":{"id":"task-1","status":"awaiting_approval"}}
    def approve_task(self,task_id): return {"task":{"id":task_id,"status":"queued"}}


def propose(action):
    return RUNEOrchestrator(
        FakeModel(json.dumps({"summary":"Do an action","actions":[action]})),
        FakeRemote(),
    ).propose("Do the action")


def test_proposal_is_capability_checked_and_not_executed():
    proposal=propose({"device_id":"phone-1","capability":"app.launch",
                      "arguments":{"packageName":"com.example.app"}})
    assert proposal["status"]=="proposed_not_executed"
    assert proposal["approval_required"] is True


def test_unknown_device_or_capability_is_rejected():
    with pytest.raises(OrchestrationError):
        propose({"device_id":"unknown","capability":"app.launch","arguments":{"packageName":"x"}})
    with pytest.raises(OrchestrationError):
        propose({"device_id":"phone-1","capability":"shell.execute","arguments":{}})


def test_sensitive_arguments_are_rejected():
    with pytest.raises(OrchestrationError):
        propose({"device_id":"phone-1","capability":"app.launch","arguments":{"api_key":"secret"}})
    with pytest.raises(OrchestrationError):
        propose({"device_id":"phone-1","capability":"app.launch","arguments":{"refreshToken":"secret"}})


def test_ui_interaction_schema_is_enforced():
    with pytest.raises(OrchestrationError):
        propose({"device_id":"phone-1","capability":"ui.interact","arguments":{"action":"tap","x":"left","y":3}})
    with pytest.raises(OrchestrationError):
        propose({"device_id":"phone-1","capability":"ui.interact","arguments":{"action":"type","text":""}})
