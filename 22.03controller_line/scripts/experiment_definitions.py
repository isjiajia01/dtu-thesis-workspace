EXPERIMENTS = {
    "EXP00": {
        "name": "BAU_Baseline",
        "description": "Business-as-usual baseline with no capacity crunch.",
        "params": {
            "ratio": 1.0,
            "total_days": 12,
            "crunch_start": None,
            "crunch_end": None,
            "base_compute": 60,
            "high_compute": 60,
            "max_trips": 2,
        },
        "seeds": list(range(1, 11)),
        "resource": "standard",
    },
    "EXP-BASELINE": {
        "name": "exp-baseline",
        "description": "Business-as-usual greedy baseline on the retained HPC pipeline.",
        "params": {
            "ratio": 1.0,
            "total_days": 12,
            "crunch_start": None,
            "crunch_end": None,
            "base_compute": 60,
            "high_compute": 60,
            "max_trips": 2,
            "mode": "greedy",
        },
        "seeds": list(range(1, 11)),
        "resource": "standard",
    },
    "EXP01": {
        "name": "Crunch_Baseline",
        "description": "Single-wave crunch baseline at the thesis reference ratio.",
        "params": {
            "ratio": 0.59,
            "total_days": 12,
            "crunch_start": 5,
            "crunch_end": 10,
            "base_compute": 60,
            "high_compute": 60,
            "max_trips": 2,
        },
        "seeds": list(range(1, 11)),
        "resource": "standard",
    },
}


def get_experiment_count() -> int:
    return sum(len(exp.get("seeds", [1])) for exp in EXPERIMENTS.values())


if __name__ == "__main__":
    print("=" * 70)
    print("THESIS EXPERIMENT PLAN")
    print("=" * 70)
    print()
    for exp_id, exp in EXPERIMENTS.items():
        print(f"{exp_id}: {exp['name']}")
        print(f"  Description: {exp['description']}")
        print(f"  Seeds: {len(exp.get('seeds', [1]))}")
        print(f"  Resource: {exp.get('resource', 'standard')}")
        print()
    print("=" * 70)
    print(f"TOTAL RUNS: {get_experiment_count()}")
    print("=" * 70)
