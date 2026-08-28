# Claude Code Outline Skill

This skill bypasses MCP/ACP entirely and talks directly to Outline's REST API.

It covers documents (create/read/update/append/move/restore), collections
(list/create/update), comments (list/create/update), attachments, users, and
templates — see `SKILL.md` for the full command reference. There is
intentionally no delete command for documents, collections, or comments;
deletion is left to the Outline UI.

## Install

From PowerShell in this cloned/extracted folder:

```powershell
.\install.ps1 -OutlineUrl "https://docs.your-outline-instance.com"
```

Then set your API key as a Windows user environment variable:

```powershell
[Environment]::SetEnvironmentVariable("OUTLINE_API_KEY", "ol_api_YOUR_NEW_KEY", "User")
```

Fully quit and reopen your editor/terminal so it inherits the new environment variables.

## Test outside Claude

```powershell
python "$HOME\.claude\skills\outline\scripts\outline_cli.py" collections
python "$HOME\.claude\skills\outline\scripts\outline_cli.py" search "test"
```

## Test inside Claude Code

Invoke:

```text
/outline
```

or ask:

```text
Search Outline for our existing ADC research and summarize the relevant documents.
```

Claude Code automatically discovers personal skills in `~/.claude/skills/`.
