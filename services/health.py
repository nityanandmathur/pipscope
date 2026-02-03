from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from core import PackageInfo

def analyze_environment(packages: List[PackageInfo]) -> Dict:
    """
    Returns a structured report for CLI.
    """

    report = {
        "summary": {},
        "duplicates": [],
        "editable": [],
        "warnings": [],
    }

    name_map = defaultdict(list)

    for pkg in packages:
        name_map[pkg.name_lower].append(pkg)

    for name, pkgs in name_map.items():
        if len(pkgs) > 1:
            report["duplicates"].append({
                "name": name,
                "versions": [p.version for p in pkgs],
                "locations": [p.location for p in pkgs],
            })

    for pkg in packages:
        if pkg.location and (
            "site-packages" not in pkg.location
            and "dist-packages" not in pkg.location
        ):
            report["editable"].append({
                "name": pkg.name,
                "location": pkg.location,
            })

    for pkg in packages:
        if not pkg.summary:
            report["warnings"].append(
                f"{pkg.name} has no package summary"
            )

        if not pkg.version or pkg.version.lower() == "unknown":
            report["warnings"].append(
                f"{pkg.name} has unknown version"
            )

    report["summary"] = {
        "total_packages": len(packages),
        "duplicate_packages": len(report["duplicates"]),
        "editable_packages": len(report["editable"]),
        "warnings": len(report["warnings"]),
    }

    return report