import pytest
from pydantic import ValidationError

from rune_backend.schemas import DeviceRegistration, TaskCreate


def test_device_registration_rejects_unknown_platform():
    with pytest.raises(ValidationError):
        DeviceRegistration(device_name="Phone", platform="unknown")


def test_task_expiry_is_bounded():
    with pytest.raises(ValidationError):
        TaskCreate(device_id="00000000-0000-0000-0000-000000000001", capability="ui.tap", expires_in_seconds=99999)


def test_task_defaults_to_approval_required():
    task = TaskCreate(device_id="00000000-0000-0000-0000-000000000001", capability="ui.tap")
    assert task.requires_approval is True
