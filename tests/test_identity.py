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
