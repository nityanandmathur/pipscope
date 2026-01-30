#!/usr/bin/env python3
"""
pipscope: Interactive TUI for exploring installed Python packages.

A fast, keyboard-driven terminal interface for browsing installed Python packages,
viewing their details, dependencies, and reverse dependencies.

Usage:
    python pipscope.py
    pipscope  (if installed via pip)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from importlib.metadata import distributions

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, ListItem, ListView, Static


# -----------------------------------------------------------------------------
# Data Model
# -----------------------------------------------------------------------------


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


def normalize_package_name(name: str) -> str:
    """Normalize package name for comparison (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def extract_dependency_name(req: str) -> str:
    """Extract the package name from a requirement string."""
    match = re.match(r"^([a-zA-Z0-9][-a-zA-Z0-9._]*)", req)
    return match.group(1) if match else req


def load_packages() -> list[PackageInfo]:
    """Load all installed packages using importlib.metadata."""
    packages = []
    
    for dist in distributions():
        try:
            name = dist.metadata.get("Name", "Unknown")
            version = dist.metadata.get("Version", "Unknown")
            summary = dist.metadata.get("Summary", "") or ""
            
            requires = []
            if dist.requires:
                requires = [str(r) for r in dist.requires]
            
            location = ""
            if dist._path:
                location = str(dist._path.parent)
            
            packages.append(PackageInfo(
                name=name,
                version=version,
                summary=summary,
                requires=requires,
                location=location,
            ))
        except Exception:
            continue
    
    return packages


def build_reverse_deps(packages: list[PackageInfo]) -> dict[str, list[str]]:
    """Build a mapping of package -> list of packages that depend on it."""
    reverse_deps: dict[str, list[str]] = {}
    installed_normalized = {normalize_package_name(p.name) for p in packages}
    
    for pkg in packages:
        for req in pkg.requires:
            dep_name = extract_dependency_name(req)
            dep_normalized = normalize_package_name(dep_name)
            
            if dep_normalized in installed_normalized:
                if dep_normalized not in reverse_deps:
                    reverse_deps[dep_normalized] = []
                reverse_deps[dep_normalized].append(pkg.name)
    
    return reverse_deps


# -----------------------------------------------------------------------------
# Widgets
# -----------------------------------------------------------------------------


class PackageListItem(ListItem):
    """A list item representing a package."""
    
    def __init__(self, package: PackageInfo) -> None:
        super().__init__()
        self.package = package
    
    def compose(self) -> ComposeResult:
        yield Static(f"[#ededf0]{self.package.name}[/#ededf0] [#5c5c6a]v{self.package.version}[/#5c5c6a]", markup=True)


class PackageListView(ListView):
    """Custom ListView for packages."""
    
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
    ]


class DetailContent(Static):
    """Static widget for displaying package details with rich markup."""
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._reverse_deps: dict[str, list[str]] = {}
    
    def set_reverse_deps(self, reverse_deps: dict[str, list[str]]) -> None:
        self._reverse_deps = reverse_deps
    
    def show_package(self, package: PackageInfo | None) -> None:
        if package is None:
            self.update("[#5c5c6a italic]Select a package to view details[/#5c5c6a italic]")
            return
        
        pkg = package
        lines = []
        
        # Package name - large and prominent (Linear violet)
        lines.append(f"[bold #ededf0]{pkg.name}[/bold #ededf0]")
        lines.append(f"[#5e6ad2]v{pkg.version}[/#5e6ad2]")
        lines.append("")
        
        # Summary
        if pkg.summary:
            lines.append("[bold #6e6e80]DESCRIPTION[/bold #6e6e80]")
            lines.append(f"[#a2a2b0]{pkg.summary}[/#a2a2b0]")
            lines.append("")
        
        # Location
        if pkg.location:
            lines.append("[bold #6e6e80]LOCATION[/bold #6e6e80]")
            lines.append(f"[#5c5c6a]{pkg.location}[/#5c5c6a]")
            lines.append("")
        
        # Dependencies (green accent)
        dep_count = len(pkg.requires)
        lines.append(f"[bold #6e6e80]DEPENDENCIES[/bold #6e6e80] [#5c5c6a]({dep_count})[/#5c5c6a]")
        
        if pkg.requires:
            for req in sorted(pkg.requires)[:30]:
                lines.append(f"  [#4cc38a]{req}[/#4cc38a]")
            if len(pkg.requires) > 30:
                lines.append(f"  [#5c5c6a]... and {len(pkg.requires) - 30} more[/#5c5c6a]")
        else:
            lines.append("  [#5c5c6a]No dependencies[/#5c5c6a]")
        lines.append("")
        
        # Reverse dependencies (amber/orange accent)
        pkg_normalized = normalize_package_name(pkg.name)
        dependents = self._reverse_deps.get(pkg_normalized, [])
        
        lines.append(f"[bold #6e6e80]USED BY[/bold #6e6e80] [#5c5c6a]({len(dependents)})[/#5c5c6a]")
        
        if dependents:
            for dep in sorted(dependents)[:30]:
                lines.append(f"  [#e5a50a]{dep}[/#e5a50a]")
            if len(dependents) > 30:
                lines.append(f"  [#5c5c6a]... and {len(dependents) - 30} more[/#5c5c6a]")
        else:
            lines.append("  [#5c5c6a]Not used by any installed package[/#5c5c6a]")
        
        self.update("\n".join(lines))


class SearchInput(Input):
    """Search input with custom styling."""
    
    class SearchChanged(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value
    
    class SearchSubmitted(Message):
        """Emitted when Enter is pressed."""
        pass
    
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("placeholder", "Search packages...")
        super().__init__(*args, **kwargs)
    
    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        self.post_message(self.SearchChanged(event.value))
    
    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.post_message(self.SearchSubmitted())


# -----------------------------------------------------------------------------
# Main Application
# -----------------------------------------------------------------------------


class PipScope(App):
    """Interactive TUI for exploring installed Python packages."""
    
    CSS = """
    /* Linear-inspired dark theme */
    Screen {
        background: #0d0d12;
    }
    
    /* Header with search */
    #header {
        height: 3;
        background: #161620;
        padding: 0 2;
        border-bottom: solid #26263d;
    }
    
    #header-title {
        dock: left;
        width: auto;
        padding: 1 2 0 0;
        color: #5e6ad2;
        text-style: bold;
    }
    
    #search-box {
        margin-top: 0;
        background: #0d0d12;
        border: tall #2e2e3f;
        padding: 0 1;
    }
    
    #search-box:focus {
        border: tall #5e6ad2;
    }
    
    #search-box > .input--placeholder {
        color: #4e4e5c;
    }
    
    /* Main layout */
    #main-container {
        height: 1fr;
    }
    
    /* Package list pane */
    #list-pane {
        width: 38%;
        background: #161620;
        border-right: solid #26263d;
    }
    
    #list-header {
        height: 2;
        background: #161620;
        padding: 0 1;
        border-bottom: solid #26263d;
        color: #6e6e80;
        text-style: bold;
    }
    
    #package-list {
        background: #161620;
        scrollbar-background: #161620;
        scrollbar-color: #2e2e3f;
        scrollbar-color-hover: #5e6ad2;
        scrollbar-color-active: #8b92e8;
    }
    
    #package-list > ListItem {
        padding: 0 1;
        height: 2;
        background: #161620;
        color: #b4b4c0;
    }
    
    #package-list > ListItem:hover {
        background: #1e1e2a;
    }
    
    #package-list > ListItem.-highlight {
        background: #252538;
    }
    
    #package-list:focus > ListItem.-highlight {
        background: #5e6ad2;
    }
    
    #package-list > ListItem.-highlight > Static {
        color: #ededf0;
    }
    
    /* Detail pane */
    #detail-pane {
        width: 62%;
        background: #0d0d12;
    }
    
    #detail-header {
        height: 2;
        background: #161620;
        padding: 0 2;
        border-bottom: solid #26263d;
        color: #6e6e80;
        text-style: bold;
    }
    
    #detail-scroll {
        background: #0d0d12;
        padding: 1 2;
        scrollbar-background: #0d0d12;
        scrollbar-color: #2e2e3f;
        scrollbar-color-hover: #5e6ad2;
        scrollbar-color-active: #8b92e8;
    }
    
    #detail-content {
        background: #0d0d12;
        padding: 0;
        color: #b4b4c0;
    }
    
    /* Footer */
    #footer {
        height: 1;
        background: #161620;
        border-top: solid #26263d;
        padding: 0 1;
        color: #5c5c6a;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("/", "focus_search", "Search", show=False),
        Binding("escape", "escape_action", "Back", show=False),
        Binding("s", "toggle_sort", "Sort", show=False),
        Binding("e", "export_json", "Export", show=False),
    ]
    
    TITLE = "pipscope"
    
    sort_mode: reactive[str] = reactive("name")
    
    def __init__(self) -> None:
        super().__init__()
        self._all_packages: list[PackageInfo] = []
        self._filtered_packages: list[PackageInfo] = []
        self._reverse_deps: dict[str, list[str]] = {}
        self._search_query: str = ""
    
    def compose(self) -> ComposeResult:
        # Header with title and search
        with Horizontal(id="header"):
            yield Static("pipscope", id="header-title")
            yield SearchInput(id="search-box")
        
        # Main content
        with Horizontal(id="main-container"):
            # Left pane - package list
            with Vertical(id="list-pane"):
                yield Static("PACKAGES", id="list-header")
                yield PackageListView(id="package-list")
            
            # Right pane - details
            with Vertical(id="detail-pane"):
                yield Static("DETAILS", id="detail-header")
                with VerticalScroll(id="detail-scroll"):
                    yield DetailContent(id="detail-content")
        
        # Footer with keybindings (Linear style)
        yield Static(
            "[#5e6ad2]/[/] [#6e6e80]Search[/]  "
            "[#5e6ad2]Enter[/] [#6e6e80]Select[/]  "
            "[#5e6ad2]j/k[/] [#6e6e80]Navigate[/]  "
            "[#5e6ad2]s[/] [#6e6e80]Sort[/]  "
            "[#5e6ad2]e[/] [#6e6e80]Export[/]  "
            "[#5e6ad2]q[/] [#6e6e80]Quit[/]",
            id="footer"
        )
    
    def on_mount(self) -> None:
        """Load packages when the app starts."""
        self._load_packages()
        self._apply_filter()
        
        detail = self.query_one("#detail-content", DetailContent)
        detail.set_reverse_deps(self._reverse_deps)
        
        # Focus search input on start
        self.query_one("#search-box", SearchInput).focus()
    
    def _load_packages(self) -> None:
        """Load all installed packages."""
        self._all_packages = load_packages()
        self._reverse_deps = build_reverse_deps(self._all_packages)
        self._sort_packages()
    
    def _sort_packages(self) -> None:
        """Sort packages based on current sort mode."""
        if self.sort_mode == "name":
            self._all_packages.sort(key=lambda p: p.name_lower)
        elif self.sort_mode == "version":
            self._all_packages.sort(key=lambda p: (p.version, p.name_lower), reverse=True)
    
    def _apply_filter(self) -> None:
        """Filter packages based on search query."""
        query = self._search_query.lower().strip()
        
        if not query:
            self._filtered_packages = self._all_packages[:]
        else:
            self._filtered_packages = [
                p for p in self._all_packages
                if query in p.name_lower or query in p.summary.lower()
            ]
        
        self._update_list()
        self._update_header()
    
    def _update_header(self) -> None:
        """Update the list header with count."""
        total = len(self._all_packages)
        shown = len(self._filtered_packages)
        header = self.query_one("#list-header", Static)
        if shown == total:
            header.update(f"PACKAGES ({total})")
        else:
            header.update(f"PACKAGES ({shown}/{total})")
    
    def _update_list(self) -> None:
        """Update the package list view."""
        list_view = self.query_one("#package-list", PackageListView)
        list_view.clear()
        
        for pkg in self._filtered_packages:
            list_view.append(PackageListItem(pkg))
        
        if self._filtered_packages:
            list_view.index = 0
            self._show_package_detail(self._filtered_packages[0])
        else:
            self._show_package_detail(None)
    
    def _show_package_detail(self, package: PackageInfo | None) -> None:
        """Show package details in the detail panel."""
        detail = self.query_one("#detail-content", DetailContent)
        detail.show_package(package)
    
    @on(SearchInput.SearchChanged)
    def on_search_changed(self, event: SearchInput.SearchChanged) -> None:
        """Handle search input changes."""
        self._search_query = event.value
        self._apply_filter()
    
    @on(SearchInput.SearchSubmitted)
    def on_search_submitted(self, event: SearchInput.SearchSubmitted) -> None:
        """Handle Enter in search - move focus to package list."""
        list_view = self.query_one("#package-list", PackageListView)
        list_view.focus()
    
    @on(ListView.Highlighted)
    def on_list_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle package selection changes."""
        if event.item is not None and isinstance(event.item, PackageListItem):
            self._show_package_detail(event.item.package)
    
    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-box", SearchInput).focus()
    
    def action_escape_action(self) -> None:
        """Handle escape - clear search or move to list."""
        search = self.query_one("#search-box", SearchInput)
        list_view = self.query_one("#package-list", PackageListView)
        
        if search.has_focus:
            if search.value:
                search.value = ""
                self._search_query = ""
                self._apply_filter()
            else:
                list_view.focus()
        else:
            search.focus()
    
    def action_toggle_sort(self) -> None:
        """Toggle between sort modes."""
        if self.sort_mode == "name":
            self.sort_mode = "version"
        else:
            self.sort_mode = "name"
        
        self._sort_packages()
        self._apply_filter()
        
        self.notify(f"Sorted by {self.sort_mode}", timeout=1.5)
    
    def action_export_json(self) -> None:
        """Export all packages to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"packages_{timestamp}.json"
        
        export_data = []
        for pkg in self._all_packages:
            pkg_normalized = normalize_package_name(pkg.name)
            dependents = self._reverse_deps.get(pkg_normalized, [])
            
            export_data.append({
                "name": pkg.name,
                "version": pkg.version,
                "summary": pkg.summary,
                "requires": pkg.requires,
                "location": pkg.location,
                "used_by": dependents,
            })
        
        try:
            with open(filename, "w") as f:
                json.dump(export_data, f, indent=2)
            self.notify(f"Exported to {filename}", timeout=2)
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error", timeout=3)


def main() -> None:
    """Entry point for the application."""
    app = PipScope()
    app.run()


if __name__ == "__main__":
    main()
