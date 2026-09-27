from app.models import Pregnancy, RiskLevel
from app.services.care_pathway import is_multiple_gestation, is_primigravida

DANGER_SIGN_SCORES = {
    "bleeding": 5,
    "severe_headache": 5,
    "swelling": 3,
    "reduced_movement": 3,
    "other": 2,
}


def calculate_risk(pregnancy: Pregnancy, danger_signs: list[str] | None = None) -> tuple[int, str]:
    score = 0
    danger_signs = danger_signs or []

    if pregnancy.age and (pregnancy.age < 18 or pregnancy.age > 35):
        score += 3
    if pregnancy.previous_cs:
        score += 3
    if pregnancy.hypertension:
        score += 3
    if is_multiple_gestation(pregnancy):
        score += 4
    if is_primigravida(pregnancy):
        score += 2
    weeks = pregnancy.weeks_pregnant or 0
    if weeks >= 40:
        score += 2

    for sign in danger_signs:
        score += DANGER_SIGN_SCORES.get(sign, 2)

    if "bleeding" in danger_signs or (
        "severe_headache" in danger_signs and "swelling" in danger_signs
    ):
        return score, RiskLevel.EMERGENCY.value
    if score >= 6:
        return score, RiskLevel.RED.value
    if score >= 3:
        return score, RiskLevel.AMBER.value
    return score, RiskLevel.GREEN.value
