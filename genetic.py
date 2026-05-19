import random
from copy import deepcopy

# --- DATA CONFIGURATION ---
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SLOTS = ["09:11", "12:02", "02:04"]
POPULATION_SIZE = 100
GENERATIONS = 500

teachers = {
    "Teacher A": {"slots": ["09:11", "02:04"], "subs": ["Computer Networks"]},
    "Teacher B": {"slots": ["12:02", "02:04"], "subs": ["Developing Dynamic Websites"]},
    "Teacher C": {"slots": ["09:11", "12:02", "02:04"], "subs": ["Machine Learning and Deep Learning"]},
    "Teacher D": {"slots": ["09:11", "12:02", "02:04"], "subs": ["Data Structure and Algorithms"]},
}

subjects_needed = {
    "Computer Networks": 2, "Developing Dynamic Websites": 2,
    "Machine Learning and Deep Learning": 2, "Data Structure and Algorithms": 2,
}

# --- CORE FUNCTIONS ---

def generate_random_timetable():
    """Creates a completely random timetable without checking rules yet."""
    timetable = []
    for day in DAYS:
        for slot in SLOTS:
            # Pick a random subject or FREE
            sub = random.choice(list(subjects_needed.keys()) + ["FREE"])
            # Pick a random teacher for that subject (even if they aren't qualified yet)
            teacher = random.choice(list(teachers.keys()))
            timetable.append({"day": day, "slot": slot, "sub": sub, "teacher": teacher})
    return timetable

def calculate_fitness(timetable):
    score = 1000
    counts = {s: 0 for s in subjects_needed}
    day_subs = {d: [] for d in DAYS}
    
    # Track how many classes each teacher is assigned
    teacher_load = {name: 0 for name in teachers.keys()}
    
    for entry in timetable:
        if entry["sub"] == "FREE": continue
        
        # Standard rules...
        counts[entry["sub"]] += 1
        teacher_load[entry["teacher"]] += 1
        
        # Rule: Teacher Qualification/Availability
        t_data = teachers[entry["teacher"]]
        if entry["sub"] not in t_data["subs"] or entry["slot"] not in t_data["slots"]:
            score -= 100 
            
        # Rule: No duplicates per day
        if entry["sub"] in day_subs[entry["day"]]:
            score -= 50
        day_subs[entry["day"]].append(entry["sub"])

    # --- NEW: LOAD BALANCING LOGIC ---
    loads = list(teacher_load.values())
    max_load = max(loads)
    min_load = min(loads)
    
    # Penalty: The bigger the gap between the busiest and freest teacher, 
    # the lower the score.
    load_gap = max_load - min_load
    score -= (load_gap * 30) 
    
    # Rule: Match curriculum
    for sub, needed in subjects_needed.items():
        score -= abs(counts[sub] - needed) * 40
        
    return score

def crossover(parent1, parent2):
    """Combines two parents to make a child."""
    point = random.randint(0, len(parent1)-1)
    return parent1[:point] + parent2[point:]

def mutate(timetable):
    idx = random.randint(0, len(timetable)-1)
    new_sub = random.choice(list(subjects_needed.keys()) + ["FREE"])
    if new_sub == "FREE":
        new_teacher = "None"
    else:
        new_teacher = random.choice(list(teachers.keys()))
    timetable[idx] = {"day": timetable[idx]["day"], "slot": timetable[idx]["slot"], 
                      "sub": new_sub, "teacher": new_teacher}

# --- EVOLUTION LOOP ---

# 1. Initialize
population = [generate_random_timetable() for _ in range(POPULATION_SIZE)]

for gen in range(GENERATIONS):
    # 2. Score and Sort
    population = sorted(population, key=lambda x: calculate_fitness(x), reverse=True)
    
    if calculate_fitness(population[0]) >= 1000: # Perfect score check
        print(f"Perfect timetable found at Generation {gen}!")
        break
        
    # 3. Selection (Keep the top 20%)
    top_tier = population[:20]
    next_generation = deepcopy(top_tier)
    
    # 4. Breeding & Mutation
    while len(next_generation) < POPULATION_SIZE:
        p1, p2 = random.sample(top_tier, 2)
        child = crossover(p1, p2)
        if random.random() < 0.15: # 15% mutation chance
            mutate(child)
        next_generation.append(child)
    
    population = next_generation

# --- OUTPUT BEST RESULT ---
best = population[0]
for day in DAYS:
    day_slots = [e for e in best if e["day"] == day]
    print(f"{day}: ", end="")
    for s in day_slots:
        print(f"[{s['slot']} | {s['sub']} ({s['teacher']})] ", end="")
    print()