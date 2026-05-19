import random
from copy import deepcopy

# --- CONFIGURATION ---
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SLOTS = ["09:11", "12:02", "02:04"]
VARIATION_LIMIT = 5

teachers = {
    "Teacher A": {"slots": ["09:11", "02:04"], "subs": ["Computer Networks"]},
    "Teacher B": {"slots": ["12:02", "02:04"], "subs": ["Developing Dynamic Websites"]},
    "Teacher C": {"slots": ["09:11", "12:02", "02:04"], "subs": ["Machine Learning and Deep Learning"]},
    "Teacher D": {"slots": ["09:11", "12:02", "02:04"], "subs": ["Data Structure and Algorithms"]},
}

subjects_needed = {
    "Computer Networks": 2,
    "Developing Dynamic Websites": 2,
    "Machine Learning and Deep Learning": 2,
    "Data Structure and Algorithms": 2,
}

all_results = []

# Pre-calculate all slot coordinates and shuffle them
ALL_POSITIONS = [(d, s) for d in DAYS for s in SLOTS]

def get_subjects_already_in_day(schedule, day):
    assigned = []
    for slot_val in schedule[day].values():
        if isinstance(slot_val, dict):
            assigned.append(slot_val["subject"])
    return assigned

def solve(pos_index, current_schedule, remaining_subs):
    if sum(remaining_subs.values()) == 0:
        all_results.append(deepcopy(current_schedule))
        return True

    if len(all_results) >= VARIATION_LIMIT or pos_index >= len(ALL_POSITIONS):
        return False

    # Pick the next random day/slot from our shuffled list
    day_name, slot_time = ALL_POSITIONS[pos_index]
    subjects_today = get_subjects_already_in_day(current_schedule, day_name)

    subs_list = list(remaining_subs.keys())
    random.shuffle(subs_list)

    # Try assigning a subject to this random slot
    for sub in subs_list:
        if remaining_subs[sub] > 0 and sub not in subjects_today:
            
            available_teachers = [
                name for name, data in teachers.items() 
                if sub in data["subs"] and slot_time in data["slots"]
            ]
            random.shuffle(available_teachers)
            
            for t_name in available_teachers:
                current_schedule[day_name][slot_time] = {"subject": sub, "teacher": t_name}
                remaining_subs[sub] -= 1
                
                if solve(pos_index + 1, current_schedule, remaining_subs):
                    if len(all_results) >= VARIATION_LIMIT: return True
                
                # Backtrack
                remaining_subs[sub] += 1
                current_schedule[day_name][slot_time] = "FREE"

    # Also try leaving this slot FREE and moving to the next random slot
    current_schedule[day_name][slot_time] = "FREE"
    if solve(pos_index + 1, current_schedule, remaining_subs):
        if len(all_results) >= VARIATION_LIMIT: return True

    return False

# --- EXECUTION ---
# Randomize the slot filling order every time the script runs
random.shuffle(ALL_POSITIONS)

initial_timetable = {d: {s: "FREE" for s in SLOTS} for d in DAYS}
solve(0, initial_timetable, subjects_needed)

# --- OUTPUT ---
if not all_results:
    print("Zero variations found.")
else:
    for i, var in enumerate(all_results):
        print(f"--- Variation {i+1} ---")
        for day in DAYS:
            row = f"{day}: "
            for slot in SLOTS:
                content = var[day][slot]
                if isinstance(content, dict):
                    row += f"[{slot} | {content['subject']} ({content['teacher']})] "
                else:
                    row += f"[{slot} | FREE] "
            print(row)
        print()