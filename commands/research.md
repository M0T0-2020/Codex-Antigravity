# /research

Execute a fast, lightweight external research task using Google Antigravity CLI (`agy`).

## Usage

```text
/research <question or topic>
```

## Description

Triggers Antigravity CLI delegation in `low` effort mode to quickly scout documentation, versions, issues, or library features without consuming heavy reasoning tokens or modifying local files.

## Workflow

1. Take the user's query after `/research`.
2. Execute (by default, output is formulated in English; pass `--lang ja` if Japanese is specifically requested):
   ```bash
   python3 scripts/antigravity_delegate.py --task "<query>" --type research --effort low
   ```
3. Parse the JSON result and display the findings with citations to the user.
