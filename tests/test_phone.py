import pytest

from app.core.phone import normalize_bd_phone


@pytest.mark.parametrize(
    "raw",
    ["01712345678", "8801712345678", "+8801712345678", "017-1234-5678", "+880 1712 345 678"],
)
def test_accepted_forms_become_e164(raw: str) -> None:
    assert normalize_bd_phone(raw) == "+8801712345678"


@pytest.mark.parametrize(
    "raw",
    [
        "0171234567",  # one digit short
        "017123456789",  # one digit long
        "01212345678",  # 012 is not a mobile operator prefix
        "+447123456789",  # not Bangladesh
        "01712abc678",  # letters
        "",
    ],
)
def test_rejected_forms_raise(raw: str) -> None:
    with pytest.raises(ValueError, match="Bangladeshi mobile"):
        normalize_bd_phone(raw)
