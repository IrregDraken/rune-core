from rune.core.node import Capability, NodeAction, NodeInfo, NullNode


def test_null_node_blocks_unavailable_capabilities():
    node = NullNode(NodeInfo("test", "test", "host"))
    result = node.execute(NodeAction(Capability.SYSTEM_REBOOT))
    assert result["status"] == "blocked"


def test_node_action_defaults_to_unauthorized():
    action = NodeAction(Capability.SYSTEM_REBOOT)
    assert action.authorized is False


def test_mobile_device_capabilities_are_registered():
    assert Capability.APP_LAUNCH.value == "app.launch"
    assert Capability.UI_OBSERVE.value == "ui.observe"
    assert Capability.UI_INTERACT.value == "ui.interact"
    assert Capability.MEDIA_CONTROL.value == "media.control"
    assert Capability.DEVICE_STATUS.value == "device.status"
