def parse_rubric(raw_rubric):
    """
    Convert Canvas rubric into clean structure for grading.

    Args:
        raw_rubric (list): Canvas rubric (list of dicts)

    Returns:
        list: Cleaned rubric list with criterion, max_points, and ratings
    """
    parsed = []

    for item in raw_rubric:
        try:
            title = item.get("criterion_description") or item.get("description") or "Untitled"
            description = item.get("long_description") or item.get("description") or "No description provided"
            points = item.get("points", 0)

            parsed.append({
                "title": title,
                "description": description,
                "points": points
            })

        except Exception as e:
            print(" Rubric parse error:", e)
    return parsed
