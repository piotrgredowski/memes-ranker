______________________________________________________________________

## allowed-tools: Bash(git diff:*), Bash(git commit -m:*), Bash(git log:\*) description: Commit changes to the git repository with a message summarizing the changes

## Context

- Recent changes: !`git log -n 5 --pretty=format:"%h %s" --abbrev-commit`
- Current status: !`git status`
- Current diff: !`git diff --cached`
- Files staged for commit: !`git diff --cached --name-only`

## Your task

Based on the current diff write a concise commit message summarizing the changes made.
Use conventional commit format described in @.vscode/settings.json file at the json key `github.copilot.chat.commitMessageGeneration.instructions`.
Use this commit to commit the changes to the git repository.
If there any issues reported by pre-commit hooks or linters, fix them first using the `fix_issues` command.
Never use --no-verify flag with git commit command.
