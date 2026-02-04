#!/usr/bin/env python3
"""
Repo Orchestrator - Cleans empty directories, finds sensitive data, and fills README brackets with repository info
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List


def run_command(command: list[str], cwd: Optional[str] = None) -> Optional[str]:
    """Run a shell command and return the output or None if failed."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_repo_info() -> Dict[str, Any]:
    """Gather repository information from git and GitHub CLI."""
    info = {}

    # Get remote URL
    remote_url = run_command(["git", "remote", "get-url", "origin"])
    if remote_url:
        info["remote_url"] = remote_url
        # Extract repo name from remote URL (preserve original casing)
        if remote_url.endswith('.git'):
            remote_url = remote_url[:-4]
        repo_name = remote_url.split('/')[-1]
        info["repo_name"] = repo_name

    # Get repo description from GitHub CLI
    gh_output = run_command(["gh", "repo", "view", "--json", "description"])
    if gh_output:
        try:
            gh_data = json.loads(gh_output)
            info["description"] = gh_data.get("description", "")
        except json.JSONDecodeError:
            pass

    return info


def fill_readme_brackets(content: str, repo_info: Dict[str, Any]) -> str:
    """Fill in bracketed placeholders in README content."""
    # Convert repo name from kebab-case to title case
    repo_name_raw = repo_info.get("repo_name", "")
    repo_name_title = " ".join(word.capitalize() for word in repo_name_raw.split("-"))

    replacements = {
        "[Project Name]": repo_name_title,
        "[Brief description of the project - one or two sentences]": repo_info.get("description", ""),
        "[repo-name]": repo_info.get("repo_name", ""),
        "[description]": repo_info.get("description", ""),
        "[remote-url]": repo_info.get("remote_url", ""),
    }

    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    return content


def clean_repo():
    """Clean the repository by removing .gitkeep from empty directories and adding them to .gitignore."""
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


def scan_sensitive_data() -> List[str]:
    """Scan for sensitive files and data that should not be tracked by git."""
    sensitive_files = []
    sensitive_patterns = [
        r'API_KEY\s*=\s*["\'][^"\']+["\']',
        r'SECRET\s*=\s*["\'][^"\']+["\']',
        r'PASSWORD\s*=\s*["\'][^"\']+["\']',
        r'TOKEN\s*=\s*["\'][^"\']+["\']',
        r'KEY\s*=\s*["\'][^"\']+["\']',
        r'aws_access_key_id',
        r'aws_secret_access_key',
        r'private_key',
        r'ssh_key',
    ]
    
    # Sensitive file names
    sensitive_file_names = [
        '.env',
        '.secrets',
        'secrets.json',
        'config.json',
        'credentials.json',
        'key.pem',
        'private.pem',
        '.pem',
        '.key',
    ]
    
    root = '.'
    
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip .git directory
        if '.git' in dirpath:
            continue
            
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root)
            
            # Check if file name is sensitive
            if any(sensitive_name in filename.lower() for sensitive_name in sensitive_file_names):
                sensitive_files.append(rel_path)
                continue
                
            # Check file content for sensitive patterns (only text files)
            try:
                if filename.endswith(('.py', '.js', '.ts', '.json', '.txt', '.md', '.yml', '.yaml', '.env', '.ini', '.cfg')):
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        for pattern in sensitive_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                sensitive_files.append(rel_path)
                                break
            except (UnicodeDecodeError, OSError):
                # Skip binary files or files that can't be read
                pass
    
    return list(set(sensitive_files))  # Remove duplicates


def clean_sensitive_data(sensitive_files: List[str]):
    """Add sensitive files to .gitignore and warn about them."""
    if not sensitive_files:
        print("No sensitive files or data found")
        return
        
    gitignore_path = '.gitignore'
    
    # Check if files are already tracked by git
    tracked_files = []
    for file in sensitive_files:
        result = run_command(["git", "ls-files", file])
        if result:
            tracked_files.append(file)
    
    if tracked_files:
        print("Warning: The following sensitive files are already tracked by git:")
        for file in tracked_files:
            print(f"  - {file}")
        print("Consider removing them from git history using: git rm --cached <file>")
    
    # Add to .gitignore
    with open(gitignore_path, 'a') as f:
        f.write('\n# Sensitive files and data\n')
        for file in sensitive_files:
            f.write(f'{file}\n')
    
    print(f"Added {len(sensitive_files)} sensitive files to .gitignore")


def main():
    parser = argparse.ArgumentParser(description="Repo Orchestrator - Clean empty directories, find sensitive data, and fill README brackets with repository info")
    parser.add_argument("--path", required=True, help="Local path to the target repository")

    args = parser.parse_args()

    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Path {target_path} does not exist")
        sys.exit(1)

    if not target_path.is_dir():
        print(f"Error: Path {target_path} is not a directory")
        sys.exit(1)

    # Change to target directory
    os.chdir(target_path)

    # Check if it's a git repository
    if not Path(".git").exists():
        print("Warning: Target directory is not a git repository.")

    # Clean repo
    clean_repo()

    # Scan and clean sensitive data
    sensitive_files = scan_sensitive_data()
    clean_sensitive_data(sensitive_files)

    # Gather repository information
    repo_info = get_repo_info()
    print(f"Repository Info: {repo_info}")

    # Read and update README.md
    readme_path = Path("README.md")
    if readme_path.exists():
        try:
            content = readme_path.read_text(encoding='utf-8')
            updated_content = fill_readme_brackets(content, repo_info)
            readme_path.write_text(updated_content, encoding='utf-8')
            print("Updated README.md with repository information")
        except Exception as e:
            print(f"Error: Failed to update README.md: {e}")
    else:
        print("No README.md file found")


if __name__ == "__main__":
    main()