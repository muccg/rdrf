def sgc_functional_score(raw_score, range_value):
    if raw_score is None:
        return None
    result = (1.0 - (raw_score - 1.0) / range_value) * 100.0
    return round(result, 2)


def sgc_symptom_score(raw_score, range_value):
    if raw_score is None:
        return None
    result = ((raw_score - 1.0) / range_value) * 100.0
    return round(result, 2)


def sgc_hsqol_score(raw_score, range_value):
    if raw_score is None:
        return None
    result = ((raw_score - 1.0) / range_value) * 100.0
    return round(result, 2)
