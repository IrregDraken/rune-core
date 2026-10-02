from rune.core.authority import Authority


def test_authority_accepts_only_matching_token() -> None:
    authority = Authority("secret")
    assert authority.accepts("secret")
    assert not authority.accepts("wrong")
    assert not authority.accepts(None)
