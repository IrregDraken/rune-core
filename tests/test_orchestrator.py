import json
import pytest

from rune.core.model import ModelResponse
from rune.core.orchestrator import OrchestrationError, RUNEOrchestrator


class FakeModel:
    def __init__(self, response):
        self.response=response
    def respond(self,prompt):
        self.prompt=prompt
        return ModelResponse(self.response,0.9)


class FakeRemote:
    def __init__(self):
        self.created=[]
        self.approved=[]
    def list_devices(self):
        return [{"id":"phone-1","device_name":"Phone","platform":"android",
                 "status":"online","capabilities":["app.list","app.launch","ui.observe"]}]
    def create_task(self,device_id,capability,arguments,*,expires_in_seconds=60):
        self.created.append((device_id,capability,arguments))
        return {"task":{"id":"task-1","status":"awaiting_approval"}}
    def approve_task(self,task_id):
        self.approved.append(task_id)
        return {"task":{"id":task_id,"status":"queued"}}


def test_proposal_is_not_executed_until_submitted():
    model=FakeModel(json.dumps({"summary":"Open app","actions":[
        {"device_id":"phone-1","capability":"app.launch","arguments":{"packageName":"com.example.app"}}
    ]}))
    remote=FakeRemote()
    orchestrator=RUNEOrchestrator(model,remote)
    proposal=orchestrator.propose("Open the app")
    assert proposal["status"]=="proposed_not_executed"
    assert proposal["approval_required"] is True
    assert remote.created==[]
    tasks=orchestrator.submit_proposal(proposal)
    assert tasks[0]["status"]=="awaiting_approval"


def test_proposal_rejects_unknown_device_capability():
    model=FakeModel(json.dumps({"summary":"Run shell","actions":[
        {"device_id":"phone-1","capability":"shell.execute","arguments":{}}
    ]}))
    with pytest.raises(OrchestrationError):
        RUNEOrchestrator(model,FakeRemote()).propose("Run a shell command")


def test_proposal_rejects_secret_arguments():
    model=FakeModel(json.dumps({"summary":"Bad","actions":[
        {"device_id":"phone-1","capability":"app.launch","arguments":{"api_key":"secret"}}
    ]}))
    with pytest.raises(OrchestrationError):
        RUNEOrchestrator(model,FakeRemote()).propose("Do a thing")


def test_malformed_model_output_is_not_executed():
    with pytest.raises(OrchestrationError):
        RUNEOrchestrator(FakeModel("not json"),FakeRemote()).propose("Do a thing")
