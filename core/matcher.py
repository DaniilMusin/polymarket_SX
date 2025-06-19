from rapidfuzz import fuzz


def _normalize(s: str) -> str:
    return s.lower().replace(" at ", " @ ").replace("-", " ")


def _extract_teams(title: str) -> tuple[str, str]:
    """`Boston Celtics @ LA Clippers` -> ('boston celtics','la clippers')"""
    if "@" in title:
        return tuple(_normalize(x.strip()) for x in title.split("@", 1))
    return (_normalize(title), "")


def match(pm_list, sx_list, min_score: int = 87):
    pairs = []
    sx_index = {_normalize(x.title): x for x in sx_list}

    for pm in pm_list:
        key = _normalize(pm.title)
        if key in sx_index:
            pairs.append((pm, sx_index[key]))
            continue

        pteams = _extract_teams(pm.title)
        date_tag = pm.t_start.strftime("%Y-%m-%d")
        candidates = [
            (
                sx,
                fuzz.token_set_ratio(
                    " ".join(_extract_teams(sx.title)) + " " + date_tag,
                    " ".join(pteams) + " " + date_tag,
                ),
            )
            for sx in sx_list
        ]
        best, score = max(candidates, key=lambda x: x[1])
        if score >= min_score:
            pairs.append((pm, best))
    return pairs
