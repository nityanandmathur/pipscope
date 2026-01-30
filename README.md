# pipscope

A fast, interactive terminal UI for exploring installed Python packages. Think `htop` for `pip`.

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)

## Features

- Browse all installed Python packages in a split-pane interface
- Live search filtering as you type
- View package details: version, summary, location, dependencies
- See reverse dependencies (which packages depend on each one)
- Sort by name or version
- Export all package data to JSON
- Keyboard-driven, works over SSH
- No subprocess calls — uses native Python APIs

## Installation

```bash
# Clone and install
git clone https://github.com/yourusername/pipscope.git
cd pipscope
pip install .

# Or install in development mode
pip install -e .
```

## Usage

```bash
# If installed via pip
pipscope

# Or run directly
python pipscope.py
```

## Keyboard Controls

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate package list |
| `j` / `k` | Navigate (vim-style) |
| `/` | Focus search bar |
| `Esc` | Clear search, return to list |
| `s` | Toggle sort: name / version |
| `e` | Export packages to JSON |
| `q` | Quit |

## Interface

```
┌──────────────────────────────────────────────────────────────┐
│ Type to search packages...                                   │
├──────────────────────────────┬───────────────────────────────┤
│ numpy (1.26.4)               │ numpy                         │
│ pandas (2.1.0)               │ Version: 1.26.4               │
│ requests (2.31.0)            │                               │
│ torch (2.0.1)                │ Summary:                      │
│ ...                          │   Fundamental package for     │
│                              │   scientific computing        │
│                              │                               │
│                              │ Location:                     │
│                              │   /usr/lib/python3/site-pkg   │
│                              │                               │
│                              │ Dependencies: (3)             │
│                              │   setuptools                  │
│                              │   ...                         │
│                              │                               │
│                              │ Used by: (12)                 │
│                              │   pandas                      │
│                              │   scipy                       │
│                              │   ...                         │
└──────────────────────────────┴───────────────────────────────┘
```

## Requirements

- Python 3.9+
- [Textual](https://github.com/Textualize/textual) (installed automatically)

## License

MIT
