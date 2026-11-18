from rune.core.identity import IdentityAssurance, IdentityVerifier, LocalIdentityProvider


def test_local_identity_is_observed_not_verified() -> None:
    identity = LocalIdentityProvider().current()
    assert identity.subject
    assert identity.device_id
    assert identity.assurance == IdentityAssurance.OBSERVED


def test_identity_verifier_requires_matching_token() -> None:
    identity = LocalIdentityProvider().current()
    verifier = IdentityVerifier(identity)
    assert verifier.verify_session(
        presented_token="secret",
        expected_token="secret",
        presented_subject=identity.subject,
    )
    assert not verifier.verify_session(
        presented_token="wrong",
        expected_token="secret",
        presented_subject=identity.subject,
    )


class _RemoteOwner:
    def current_owner(self):
        return {"owner_id": "00000000-0000-0000-0000-000000000001", "email": "owner@example.test"}


def test_control_plane_identity_is_verified_and_uses_owner_subject():
    from rune.core.identity import ControlPlaneIdentityProvider

    identity = ControlPlaneIdentityProvider(_RemoteOwner()).current()
    assert identity.subject == "00000000-0000-0000-0000-000000000001"
    assert identity.display_name == "owner@example.test"
    assert identity.assurance == IdentityAssurance.VERIFIED
