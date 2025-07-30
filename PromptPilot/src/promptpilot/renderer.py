import json
from pathlib import Path
from typing import Dict, Iterable

def load_template(path: Path) -> Dict:
    with path.open() as f:
        return json.load(f)


def fill_placeholders(lines: Iterable[str], vars: Dict[str, str]) -> str:
    filled = []
    for line in lines:
        for k, v in vars.items():
            line = line.replace(f"{{{{{k}}}}}", v)
        filled.append(line)
    return "\n".join(filled)
