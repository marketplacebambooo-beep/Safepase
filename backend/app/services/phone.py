import re


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("263") and len(digits) >= 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+263{digits[1:]}"
    if len(digits) == 9:
        return f"+263{digits}"
    if phone.startswith("+"):
        return phone
    return phone


def phone_variants(phone: str | None) -> list[str]:
    """All common formats for matching CHW/nurse numbers from USSD gateways."""
    if not phone:
        return []
    normalized = normalize_phone(phone) or phone
    digits = re.sub(r"\D", "", phone)
    variants = {phone.strip(), normalized, digits, f"+{digits}"}
    if digits.startswith("263") and len(digits) >= 12:
        variants.add(f"0{digits[3:]}")
    if digits.startswith("0") and len(digits) == 10:
        variants.add(f"263{digits[1:]}")
    return [v for v in variants if v]
