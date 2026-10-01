#!/usr/bin/env python
"""Restores the live dashboard and re-enables the scout schedule."""

import os
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def restore():
    print("Restoring active dashboard files...")
    pub_active = os.path.join(BASE_DIR, "public", "index.html.active")
    pub_index = os.path.join(BASE_DIR, "public", "index.html")
    root_active = os.path.join(BASE_DIR, "index.html.active")
    root_index = os.path.join(BASE_DIR, "index.html")
    cat_active = os.path.join(BASE_DIR, "public", "catalog.json.active")
    cat_json = os.path.join(BASE_DIR, "public", "catalog.json")

    if os.path.exists(pub_active):
        shutil.copy2(pub_active, pub_index)
        print("Restored public/index.html")
    if os.path.exists(root_active):
        shutil.copy2(root_active, root_index)
        print("Restored index.html")
    if os.path.exists(cat_active):
        shutil.copy2(cat_active, cat_json)
        print("Restored public/catalog.json")

    # Restore cron schedule in daily_scout.yml
    workflow_path = os.path.join(BASE_DIR, ".github", "workflows", "daily_scout.yml")
    if os.path.exists(workflow_path):
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()
        old_block = """# on:
#   schedule:
#     # Runs every day at 06:00 UTC (9:00 AM Egypt / Saudi time)
#     - cron: '0 6 * * *'
on:
  workflow_dispatch:"""
        new_block = """on:
  schedule:
    # Runs every day at 06:00 UTC (9:00 AM Egypt / Saudi time)
    - cron: '0 6 * * *'
  workflow_dispatch:"""
        if old_block in content:
            content = content.replace(old_block, new_block)
            with open(workflow_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Restored daily_scout.yml cron schedule")

    # Git push
    print("Pushing restoration to GitHub...")
    subprocess.run(
        [
            "git",
            "add",
            "public/index.html",
            "index.html",
            "public/catalog.json",
            ".github/workflows/daily_scout.yml",
        ],
        cwd=BASE_DIR,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "chore: restore live site and re-enable schedule"],
        cwd=BASE_DIR,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=True)
    print("Live site restored and pushed successfully!")


if __name__ == "__main__":
    restore()
