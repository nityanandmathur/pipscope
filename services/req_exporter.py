from pathlib import Path
from typing import Iterable

def export_requirements(packages: Iterable, filename: str = "requirements.txt") -> Path:
    """
    Returns requirements.txt file
    """
    lines = []

    for pkg in packages:
        if pkg.version:
            lines.append(f"{pkg.name}=={pkg.version}")
        else:
            lines.append(pkg.name)

    path = Path(filename)

    with path.open("w") as f:
        f.write("\n".join(sorted(lines)))

    return path