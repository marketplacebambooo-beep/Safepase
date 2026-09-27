from datetime import date, timedelta


def weeks_to_lmp_edd(weeks: int) -> tuple[date, date]:
    today = date.today()
    lmp = today - timedelta(weeks=weeks)
    edd = lmp + timedelta(days=280)
    return lmp, edd
