# Setup Claude Project for Mom (one-time, you do this)

## 1. MCP must be installed (already done on your Mac)

```bash
cd ~/ZamiraHealth && source .venv/bin/activate && python scripts/install_mcp.py
```

Repeat on **her Mac** when you deliver the app.

## 2. Create Claude Project

1. Claude Desktop → **Projects** → **New project**
2. Name: **Здоровье** (or **Zamira Health**)
3. Open **Custom instructions**
4. Paste **entire contents** of:

   `ZamiraHealth/profiles/zamira/claude_project_instructions.md`

5. Save project

## 3. Pin for easy access

- Keep project in sidebar
- Optional: set project icon/color so she finds it easily

## 4. Test as mom would

1. New chat **inside project** (not general chat)
2. Attach one lab photo
3. Send empty message or just «вот»
4. Claude should auto-import + short Russian reply

## 5. What mom sees vs what happens

| Mom does | System does (invisible) |
|----------|-------------------------|
| Drop photo in project chat | Claude → import_chat_datapoints → refresh dashboard |
| «Как дела?» | Claude → get_lab_results → warm summary |
| Opens dashboard.html | Sees updated labs/tasks |

## 6. Important

- **General Claude chat** (outside project) = weaker instructions → tell her to always use **Здоровье** project
- MCP works in all chats, but project instructions make attachment auto-processing reliable
- Print `MOM_GUIDE_RU.md` for her if helpful

## 7. Optional: project knowledge files

Upload to project (Claude Project files):
- Empty or link to `profile_context.json` summary — optional, MCP has live data

**Do NOT rely on project files for labs** — live data is in MCP/SQLite.
