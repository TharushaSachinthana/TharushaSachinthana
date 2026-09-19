#!/usr/bin/env python3
"""
Auto-update the GitHub profile README with dynamic repository showcase cards.

This script fetches all public, non-fork repositories for a given GitHub user,
generates beautiful github-readme-stats pin cards arranged in a 2-column grid,
and injects them between marker comments in the README.md file.

Usage:
    python update_readme.py

Environment Variables:
    GITHUB_TOKEN  – (Optional) GitHub personal access token for higher API rate limits.
    GITHUB_USER   – (Optional) Override the default GitHub username.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
USERNAME = os.getenv("GITHUB_USER", "tharushasachinthana")
TOKEN = os.getenv("GITHUB_TOKEN", "")
README_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")

# Repos to exclude from the showcase (lowercase)
EXCLUDE_REPOS = {USERNAME.lower()}  # Exclude the profile repo itself

# Card theme – matches the existing README aesthetic
CARD_THEME = "radical"
CARD_BG = "0d1117"
CARD_TITLE_COLOR = "29e7cd"
CARD_ICON_COLOR = "29e7cd"

# Marker comments used to locate the injection zone
START_MARKER = "<!-- PROJECTS:START -->"
END_MARKER = "<!-- PROJECTS:END -->"

# Maximum number of repos to display (0 = unlimited)
MAX_REPOS = 0

# Number of columns in the grid
COLUMNS = 2


# ──────────────────────────────────────────────
# GitHub API helpers
# ──────────────────────────────────────────────
def fetch_repos(username: str, token: str) -> list[dict]:
    """Fetch all public repositories for *username* via the GitHub REST API."""
    repos: list[dict] = []
    page = 1
    per_page = 100

    while True:
        url = (
            f"https://api.github.com/users/{username}/repos"
            f"?type=owner&sort=updated&direction=desc&per_page={per_page}&page={page}"
        )
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "profile-readme-updater")
        if token:
            req.add_header("Authorization", f"Bearer {token}")

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            print(f"❌  GitHub API error: {exc.code} {exc.reason}", file=sys.stderr)
            sys.exit(1)

        if not data:
            break

        repos.extend(data)
        if len(data) < per_page:
            break
        page += 1

    return repos


def filter_repos(repos: list[dict]) -> list[dict]:
    """Keep only public, non-fork, non-excluded repos."""
    filtered = [
        r for r in repos
        if not r.get("fork")
        and not r.get("private")
        and not r.get("archived")
        and r["name"].lower() not in EXCLUDE_REPOS
    ]
    # Already sorted by updated_at from the API, but ensure it
    filtered.sort(key=lambda r: r.get("updated_at", ""), reverse=True)

    if MAX_REPOS > 0:
        filtered = filtered[:MAX_REPOS]

    return filtered


# ──────────────────────────────────────────────
# Markdown generation
# ──────────────────────────────────────────────
def build_card_url(repo_name: str) -> str:
    """Return the github-readme-stats pin card URL for a repo."""
    return (
        f"https://github-readme-stats.vercel.app/api/pin/"
        f"?username={USERNAME}"
        f"&repo={repo_name}"
        f"&theme={CARD_THEME}"
        f"&hide_border=true"
        f"&bg_color={CARD_BG}"
        f"&title_color={CARD_TITLE_COLOR}"
        f"&icon_color={CARD_ICON_COLOR}"
    )


def generate_showcase(repos: list[dict]) -> str:
    """Build the full HTML/Markdown showcase section."""
    if not repos:
        return "_No public repositories found._"

    lines: list[str] = []
    lines.append('<div align="center">')
    lines.append("")

    # Build rows of COLUMNS cards each
    for i in range(0, len(repos), COLUMNS):
        row_repos = repos[i : i + COLUMNS]
        for repo in row_repos:
            card_url = build_card_url(repo["name"])
            repo_url = repo["html_url"]
            lines.append(
                f'  <a href="{repo_url}">'
                f'<img src="{card_url}" alt="{repo["name"]}" />'
                f"</a>"
            )
        lines.append("")

    lines.append("</div>")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# README injection
# ──────────────────────────────────────────────
def inject_into_readme(showcase_md: str, readme_path: str) -> bool:
    """Replace content between the marker comments. Returns True if changed."""
    with open(readme_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    pattern = re.compile(
        rf"({re.escape(START_MARKER)})\n.*?\n({re.escape(END_MARKER)})",
        re.DOTALL,
    )

    if not pattern.search(content):
        print(f"⚠️  Markers not found in {readme_path}. Nothing to update.", file=sys.stderr)
        return False

    new_block = f"{START_MARKER}\n{showcase_md}\n{END_MARKER}"
    new_content = pattern.sub(new_block, content)

    if new_content == content:
        print("✅  README is already up-to-date — no changes needed.")
        return False

    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write(new_content)

    print("✅  README updated successfully.")
    return True


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main() -> None:
    print(f"📡  Fetching repos for @{USERNAME} …")
    all_repos = fetch_repos(USERNAME, TOKEN)
    print(f"   Found {len(all_repos)} total repos.")

    repos = filter_repos(all_repos)
    print(f"   {len(repos)} repos after filtering (excl. forks, archived, profile repo).")

    showcase = generate_showcase(repos)
    changed = inject_into_readme(showcase, README_PATH)

    if changed:
        print("🎉  Done! README.md has been updated with the latest project cards.")
    else:
        print("ℹ️   No update was necessary.")


if __name__ == "__main__":
    main()
