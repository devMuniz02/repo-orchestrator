#!/usr/bin/env python3
"""
Clean repo script: Adds all empty folders to .gitignore and removes .gitkeep if it's the only content.
"""

import os

def clean_repo():
    root = '.'
    gitignore_path = '.gitignore'
    empty_dirs = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip .git directory and hidden directories starting with .
        if '.git' in dirpath or os.path.basename(dirpath).startswith('.'):
            continue

        # Check if directory is empty or only contains .gitkeep
        if not filenames and not dirnames:
            # Completely empty directory
            empty_dirs.append(dirpath)
        elif filenames == ['.gitkeep'] and not dirnames:
            # Only contains .gitkeep, remove it
            gitkeep_path = os.path.join(dirpath, '.gitkeep')
            os.remove(gitkeep_path)
            empty_dirs.append(dirpath)

    # Add empty directories to .gitignore
    if empty_dirs:
        with open(gitignore_path, 'a') as f:
            f.write('\n# Empty directories\n')
            for d in sorted(empty_dirs):
                rel_path = os.path.relpath(d, root)
                f.write(rel_path + '/\n')
        print(f"Added {len(empty_dirs)} empty directories to .gitignore")
    else:
        print("No empty directories found")

if __name__ == '__main__':
    clean_repo()