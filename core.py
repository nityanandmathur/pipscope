from dataclasses import dataclass, field


@dataclass
class PackageInfo:
    """Represents metadata for an installed Python package."""

    name: str
    version: str
    summary: str
    requires: list[str] = field(default_factory=list)
    location: str = ""

    @property
    def name_lower(self) -> str:
        return self.name.lower()