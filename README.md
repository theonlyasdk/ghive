# ghive

A clean, accurate, and stable GUI frontend for GitHub CLI (`gh`) written in Python 3 using Tkinter.

Inspired by clean desktop utility aesthetics, `ghive` provides a fast, lightweight, and native desktop interface to manage repositories, issues, pull requests, actions, and gists without unnecessary UI bloat or latency.

## Features

- **Repositories & Releases**: Search, filter by visibility/fork, inspect stars/forks/languages, clone locally, sync forks, create new repositories, and manage releases.
  - **Releases & Artifacts**: Detailed releases view, create draft/prerelease releases, edit descriptions, upload assets with live streaming metrics (upload rate, rate acceleration, ETA, and percentage), and download or delete release artifacts.
- **Issues**: Explore repo issues, filter by state (open/closed), view discussion threads and comments, submit comments, create issues, and toggle state.
- **Pull Requests**: Review PRs, inspect unified color-coded git diffs, checkout branches locally, merge PRs (merge, squash, rebase), and create pull requests.
- **Actions & Workflow Runs**: Monitor CI/CD execution runs, filter by status, view live execution logs with keyword search, rerun, and cancel runs.
- **Gists**: Browse code snippets, view and edit files with page addition/renaming, copy IDs, create new public or secret gists, and clone gists locally.
- **Authentication**: Seamless detection of GitHub CLI authentication, token login, and account status indicator in the status bar.
- **External Tool Detection & Audit Logging**: Automatically detects `gh` and `git` binaries with quick download links and full audit logging in `~/.ghive/audit.log`.

## Dependencies & Installation

### 1. Python 3 (3.8 or higher)
- **Windows / macOS**: Download from [python.org](https://www.python.org/downloads/) (Tkinter is included by default).
- **Linux**: Python is usually pre-installed. Ensure `python3-tk` is installed:
  - Debian / Ubuntu: `sudo apt install python3 python3-tk`
  - Fedora / RHEL: `sudo dnf install python3 python3-tkinter`
  - Arch Linux: `sudo pacman -S python tk`

### 2. GitHub CLI (`gh`)
Download installer or install via your preferred package manager:
- **Direct Download**: [GitHub CLI Official Releases](https://github.com/cli/cli/releases)
- **Windows**:
  ```powershell
  winget install --id GitHub.cli
  # or
  choco install gh
  # or
  scoop install gh
  ```
- **macOS**:
  ```bash
  brew install gh
  # or
  sudo port install gh
  ```
- **Linux**:
  - Debian / Ubuntu: `sudo apt install gh`
  - Fedora / RHEL: `sudo dnf install gh`
  - Arch Linux: `sudo pacman -S github-cli`

### 3. Git (Optional, for local repository cloning)
- **Direct Download**: [Git Downloads](https://git-scm.com/downloads)
- **Windows**: `winget install --id Git.Git`
- **macOS**: `brew install git`
- **Linux**: `sudo apt install git` or `sudo dnf install git` or `sudo pacman -S git`

## Running the App

Clone the repository and run `ghive.py`:

### Windows
```powershell
python ghive.py
```

### Linux & macOS
```bash
chmod +x ghive.py
./ghive.py
```
or:
```bash
python3 ghive.py
```

## Building Standalone Executable

You can generate a standalone executable for your operating system using PyInstaller:

```bash
# Using the automated build tool
python tools/build.py
```

Or manually using PyInstaller:
```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name=ghive --paths=src ghive.py
```

The compiled application will be placed in the `dist/ghive` folder.

## License

This project is licensed under MIT License (link this to [LICENSE](LICENSE)) file.
