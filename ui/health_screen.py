from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from services.health import analyze_environment
from core import PackageInfo

class HealthScreen(Screen):
    """
    TUI for environment health report.
    """

    BINDINGS = [
        Binding("escape", "close", "Back", show=False),
    ]

    CSS = """
    Screen {
        background: #0d0d12;
    }

    .title {
        height: 2;
        padding: 1 2;
        background: #161620;
        color: #5e6ad2;
        text-style: bold;
        border-bottom: solid #26263d;
    }

    .section-title {
        margin-top: 1;
        color: #6e6e80;
        text-style: bold;
    }

    #content {
        padding: 1 2;
        color: #b4b4c0;
    }

    .warn {
        color: #e5a50a;
    }

    .ok {
        color: #4cc38a;
    }

    .muted {
        color: #5c5c6a;
    }
    """

    def __init__(self, packages: list[PackageInfo]) -> None:
        super().__init__()
        self.packages = packages
        self.report = analyze_environment(packages)

    def compose(self) -> ComposeResult:
        yield Static("ENVIRONMENT HEALTH", id="title")

        with VerticalScroll(id="content"):
            yield from self._summary_section()
            yield from self._duplicates_section()
            yield from self._editable_section()
            yield from self._warnings_section()

            yield Static("Press Esc to return", classes="section-title")

    def _summary_section(self):
        s = self.report["summary"]

        yield Static("SUMMARY", classes="section-title")
        yield Static(f"Total packages     : {s['total_packages']}")
        yield Static(f"Duplicate packages : {s['duplicate_packages']}")
        yield Static(f"Editable installs  : {s['editable_packages']}")
        yield Static(f"Warnings           : {s['warnings']}")

    def _duplicates_section(self):
        duplicates = self.report["duplicates"]

        yield Static("DUPLICATE PACKAGES", classes="section-title")

        if not duplicates:
            yield Static("✓ No duplicate packages detected", classes="ok")
            return

        for item in duplicates:
            yield Static(f"⚠ {item['name']}", classes="warn")
            for v, loc in zip(item["versions"], item["locations"]):
                yield Static(f"  ├─ {v}  {loc}", classes="muted")

    def _editable_section(self):
        editable = self.report["editable"]

        yield Static("EDITABLE INSTALLS", classes="section-title")

        if not editable:
            yield Static("✓ No editable installs detected", classes="ok")
            return

        for pkg in editable:
            yield Static(f"⚠ {pkg['name']}", classes="warn")
            yield Static(f"  ↳ {pkg['location']}", classes="muted")

    def _warnings_section(self):
        warnings = self.report["warnings"]

        yield Static("WARNINGS", classes="section-title")

        if not warnings:
            yield Static("✓ No warnings detected", classes="ok")
            return

        for w in warnings:
            yield Static(f"• {w}", classes="warn")

    def action_close(self) -> None:
        self.app.pop_screen()