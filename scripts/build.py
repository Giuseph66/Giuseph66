"""Regenerate every card and README block in both languages from the committed data.

Runs offline: the stats cards re-render from data/contributions.json and
data/github-stats.json instead of fetching (the GitHub Action refreshes those).
    python scripts/build.py
"""

from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parent
STEPS = [
    ["generate_terminal.py"],
    ["generate_stack.py"],
    ["generate_featured.py"],
    ["generate_repo_index.py"],
    ["update_profile_art.py", "--cached"],
    ["update_github_stats.py", "--cached"],
]


def main():
    for script, *args in STEPS:
        print(f"→ {script} {' '.join(args)}".rstrip(), flush=True)
        subprocess.run([sys.executable, str(SCRIPTS / script), *args], check=True)


if __name__ == "__main__":
    main()
