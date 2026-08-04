from .config import DAYS

def teacher_movement(data: dict) -> dict[str, dict[str, str]]:
    teachers = sorted({item["teacher"] for item in data["assignments"]})
    result = {teacher: {day: "" for day in DAYS} for teacher in teachers}
    for item in data["assignments"]:
        current = result[item["teacher"]][item["day"]]
        if not current:
            result[item["teacher"]][item["day"]] = item["school"]
        elif item["school"] not in current.split(", "):
            result[item["teacher"]][item["day"]] += f", {item['school']}"
    return result

def coverage_audit(data: dict) -> list[dict]:
    rows = []
    for teacher, schedule in teacher_movement(data).items():
        assigned = [day for day in DAYS if schedule[day]]
        missing = [day for day in DAYS if not schedule[day]]
        schools = sorted({school for value in schedule.values() for school in value.split(", ") if school})
        rows.append({"teacher": teacher, "days_count": len(assigned), "assigned_days": assigned,
                     "missing_days": missing, "schools": schools,
                     "status": "OK" if not missing else "MISSING DAYS"})
    return rows
