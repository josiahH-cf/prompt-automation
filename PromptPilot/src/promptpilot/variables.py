from typing import Dict, List


def get_variables(placeholders: List[Dict[str, str]]) -> Dict[str, str]:
    vars: Dict[str, str] = {}
    for ph in placeholders:
        name = ph["name"]
        label = ph.get("label", name)
        opts = ph.get("options")
        if opts:
            print(f"{label} options: {', '.join(opts)}")
            choice = input(f"Select {label}: ")
            if choice not in opts:
                choice = opts[0]
            vars[name] = choice
        else:
            vars[name] = input(f"{label}: ")
    return vars
