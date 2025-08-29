def parse_rubric(raw_rubric):
    """
    Convert Canvas rubric into clean structure for grading.

    Args:
        raw_rubric (list): Canvas rubric (list of dicts)

    Returns:
        str: Human readable formatted rubric
    """
    output = []
    total_points = 0

    for item in raw_rubric:
        try:
            title = item.get("description", "Untitled")
            description = item.get("long_description", "No description provided")
            points = item.get("points", 0)
            total_points += points
            
            # Format the criterion section
            criterion = f"\n{title} ({points} points)"
            output.append(criterion)
            
            # Process description - split by <br/> tags and format
            if description:
                desc_parts = description.split("<br/>")
                for part in desc_parts:
                    if part.strip():
                        output.append(f"• {part.strip()}")
            
            # Add rating levels if available
            if "ratings" in item:
                output.append("\nRating Levels:")
                for rating in item["ratings"]:
                    rating_desc = rating.get("description", "")
                    rating_points = rating.get("points", 0)
                    output.append(f"- {rating_desc}: {rating_points} points")
            
            output.append("")  # Add blank line between criteria
            
        except Exception as e:
            print(f"Rubric parse error: {e}")
    
    # Add total points at the top
    output.insert(0, f"Total Points: {total_points}\n")
    
    return "\n".join(output)
