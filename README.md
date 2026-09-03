# Codex-Antigravity (`codex-antigravity`)

[English](README.md) | [日本語](README.ja.md)

**Codex-Antigravity** is a plugin and toolkit that bridges **Coding Agents (such as OpenAI Codex)** and the **Google Antigravity CLI (`agy`)**. It safely and autonomously delegates **"codebase reconnaissance & impact analysis"**, **"test execution & AI failure triage"**, and **"lightweight external documentation research"**.

```text
Coding Agent (Codex)
        │
        ├── ① Code Implementation, Refactoring & Fixes ──► Handled by Codex itself (Write permissions)
        │
        ├── ② Codebase Reconnaissance & Research ────────► Antigravity Scout (Read-only)
        │        │
        │        ├── /codebase [status|impact|audit]
        │        └── scripts/antigravity_delegate.py --dir . --type codebase
        │                 │ - High-speed local scan (languages/stack/Git status/tree)
        │                 │ - Safe read-only inspection via agy --add-dir
        │                 ▼
        │        Structured Architecture Report (JSON)
        │
        └── ③ Test Execution & Failure Triage ───────────► Test Delegator + Antigravity QA
                 │
                 ├── /test [cmd]
                 └── scripts/test_runner.py --dir .
                          │ - Automated test execution & metrics aggregation (passed/failed)
                          │ - On failure: AI diagnoses root causes & suggested fixes from tracebacks
                          ▼
                 Structured Test & Diagnosis Report (JSON) ──► Codex (identifies cause and fixes immediately)
```

---

## Key Features

- 🧠 **Manager-Style Agent Orchestrator (v1.2)**:
  - Automatically decomposes compound/mixed user tasks into a bounded subtask DAG (TaskGraph) (`decompose_task`).
  - Dispatches external research and codebase reconnaissance concurrently, evaluated by an objective **Quality Gate** (primary source ratio, confidence, and uncertainty penalties).
  - Synthesizes findings across agents using **Evidence Merger**, automatically detecting factual contradictions and version discrepancies (Conflict Detection).
  - Emits a clean implementation packet for Codex Native with automated follow-up test execution (`antigravity-orchestrate`).
- 🚀 **Optimal Division of Responsibilities for Coding Agents**:
  - **Codex (Lead Engineer)**: Production code modifications, refactoring, Git commits, and final architectural decisions.
  - **Antigravity (Scout & QA)**: Codebase structure exploration, dependency/impact analysis, test execution & failure triage, and external documentation lookup.
- 🔍 **Codebase Reconnaissance**:
  - Zero-dependency, ultra-fast local scanner (`scripts/codebase_analyzer.py`) extracts languages, frameworks, Git status, and directory trees in under 100ms, seamlessly integrated into AI prompt context.
- 🧪 **Test Delegation & AI Failure Triage**:
  - Automatically detects and runs pytest, unittest, cargo test, npm/vitest, go test, and more.
  - When tests fail, instead of flooding the Coding Agent's context window with massive stack traces, AI provides structured root cause analysis and concrete suggested fixes.
- 📋 **Official `--json-schema` & Verification Status**:
  - Uses `schemas/research_result.json` to obtain guaranteed structured output directly from Antigravity CLI.
  - Replaced naive `verified: true` flags with granular `verification_status` (`source_retrieved`, `source_provided`, `unverified`, `contradicted`).
- 🛡️ **Strict Read-Only Safety Guarantees & Policy-as-Code**:
  - Research and scout tasks strictly prohibit file modifications and Git write operations via prompt-level guardrails and CLI parameter enforcement.
- ⚡ **Zero External Dependencies**:
  - Fully functional using only the Python 3.9+ standard library.
- 📦 **Rich Integration Options**:
  - **CLI Scripts**: `scripts/orchestrator.py`, `scripts/router.py`, `scripts/antigravity_delegate.py`, `scripts/test_runner.py`
  - **Codex Plugin / Skills**: `skills/antigravity-research`, `skills/research-routing`, `skills/test-delegation`
  - **Slash Commands**: `/codebase`, `/test`, `/research`, `/research-deep`
  - **MCP Server**: `mcp/server.py` (`antigravity_orchestrate`, `antigravity_decompose`, `antigravity_research`, etc.)

---

## ⚡ 30-Second Quick Start

Get up and running in 30 seconds:

```bash
# 1. Clone the repository & navigate into it
git clone git@github.com:M0T0-2020/Codex-Antigravity.git
cd Codex-Antigravity

# 2. Run environment diagnostics (verifies agy CLI installation and authentication)
python3 scripts/check_antigravity.py

# 3. Add as a Codex CLI plugin with a single command
codex plugin marketplace add .
codex plugin add codex-antigravity@codex-antigravity-market
```

After registration, you can immediately use the following commands in your Codex chat interface:

```text
/research Latest changes and gotchas in ONNX Runtime 1.18
/codebase status
/test
```

---

## Directory Structure

```text
Codex-Antigravity/
├── .agents/
│   └── plugins/
│       └── marketplace.json           # Codex plugin marketplace definition
│
├── .codex-plugin/
│   └── plugin.json                    # Codex plugin manifest
│
├── .github/
│   └── workflows/
│       └── test.yml                   # CI automated test workflow (Python 3.9–3.13)
│
├── .mcp.json                          # MCP server configuration definition
│
├── agents/
│   └── research-router.md             # Routing sub-agent prompt definition
│
├── skills/
│   ├── antigravity-research/
│   │   └── SKILL.md                   # Research delegation skill (with codebase inspection)
│   ├── research-routing/
│   │   └── SKILL.md                   # Routing guidelines for Coding Agents
│   └── test-delegation/
│       └── SKILL.md                   # Test delegation & AI failure triage skill
│
├── commands/
│   ├── codebase.md                    # /codebase command definition
│   ├── test.md                        # /test command definition
│   ├── research.md                    # /research command definition
│   └── research-deep.md               # /research-deep command definition
│
├── config/
│   └── defaults.toml                  # Default settings (model tiers, test, safety policies)
│
├── mcp/
│   ├── __init__.py
│   └── server.py                      # MCP stdio server (tools/call)
│
├── scripts/
│   ├── __init__.py
│   ├── safety.py                      # Safety policy layer (boundary check, command validation, env sanitization)
│   ├── router.py                      # Policy-as-Code router (intercepts mutation tasks)
│   ├── antigravity_delegate.py        # Core delegation script (prompt defense, claims extraction, sandbox)
│   ├── codebase_analyzer.py           # Fast local project scanner (<100ms)
│   ├── test_runner.py                 # Test runner & AI triage (shell=False, process-group kill)
│   ├── check_antigravity.py           # Environment diagnostics script
│   ├── config_loader.py               # TOML configuration loader (prefers tomllib)
│   └── models.py                      # Dynamic model tier resolution (flash/pro/claude)
│
├── tests/
│   ├── __init__.py
│   ├── test_safety.py                 # Safety policy & prompt injection rejection tests
│   ├── test_router.py                 # Policy-as-Code router tests
│   ├── test_codebase_analyzer.py      # Codebase scanner tests
│   ├── test_test_runner.py            # Test execution & failure diagnosis tests
│   ├── test_delegate.py               # Delegation, prompt & mock tests
│   ├── test_output_parser.py          # Structured parsing tests
│   ├── test_timeout.py                # Timeout handling tests
│   ├── test_routing.py                # Config loading & routing tests
│   └── test_mcp_server.py             # MCP server tests
│
├── pyproject.toml
├── README.ja.md                       # Japanese documentation
└── README.md                          # English documentation (default)
```

---

## Installation & Setup for Codex CLI

Detailed setup instructions for using Codex-Antigravity with the Codex CLI (`codex`).
You can choose from **3 integration methods** depending on your workflow:

| Method | Characteristics | Recommended Use Case |
| :--- | :--- | :--- |
| **Method A: Install as Official Codex Plugin** | One-command installation of skills, slash commands, and MCP | **Most Recommended**. For persistent use across all Codex CLI sessions |
| **Method B: Register as Codex MCP Server** | Enables Codex to autonomously invoke research & test diagnosis tools | When you want the LLM to call tools directly via Function Calling |
| **Method C: Workspace-Local Placement** | Works strictly within a specific repository without touching global configurations | When testing within a single project repository |

---

### Step 0: Prerequisites & Preparation

Before installation, verify the following prerequisites in your terminal:

#### 1. Google Antigravity CLI (`agy`) Verification & Initial Authentication
Ensure that the Antigravity CLI is installed and authenticated:

```bash
# Check version
agy --version
```

> [!IMPORTANT]
> **Initial Authentication & Workspace Trust**:
> If you have never launched `agy`, start it once manually in your terminal to complete initial authentication:
> ```bash
> agy
> ```
> When prompted with `Do you trust the contents of this project?`, select `Yes, I trust this folder` and press Enter. Once the Google account sign-in and model quota screen appears, setup is complete (press Esc to exit).

#### 2. OpenAI Codex CLI (`codex`) Verification
Ensure that the Codex CLI is available:

```bash
# Check version
codex --version

# Health check (optional)
codex doctor
```

#### 3. Python 3.9+ Verification
This tool requires no third-party libraries and runs entirely on the Python standard library:

```bash
python3 --version
```

#### 4. Run Environment Diagnostics Script
Run the diagnostics script included in the repository to verify connectivity with `agy`:

```bash
python3 scripts/check_antigravity.py
```

Example output on success:
```text
==================================================
Antigravity Environment Diagnostics
==================================================
Platform              : Darwin 25.0.0 (arm64)
Python Version        : 3.9.6
Antigravity CLI Binary: /usr/local/bin/agy
CLI Status            : Available
CLI Version           : Antigravity CLI 1.1.24
Available Models      : 6 model(s) discovered
Active Model          : gemini-3.8-flash-high (configured default)
Diagnostics Result    : SUCCESS (Ready for delegation)
==================================================
```

---

### Method A: Install as Official Codex Plugin (Recommended)

Install using the official Codex CLI plugin management system (Marketplace feature).
The plugin manifest (`.codex-plugin/plugin.json`), marketplace definition (`.agents/plugins/marketplace.json`), and MCP configuration (`.mcp.json`) are registered with Codex automatically.

#### 1. Add Marketplace
Register this repository as a marketplace source in Codex:

```bash
# If running outside the Codex-Antigravity directory (specify absolute path)
codex plugin marketplace add /path/to/Codex-Antigravity

# If running directly inside the Codex-Antigravity directory
codex plugin marketplace add .
```

Output:
```text
Added marketplace `codex-antigravity-market` from /path/to/Codex-Antigravity.
Installed marketplace root: /path/to/Codex-Antigravity
```

#### 2. Install Plugin
Add the `codex-antigravity` plugin from the marketplace:

```bash
codex plugin add codex-antigravity@codex-antigravity-market
```

Output:
```text
Added plugin `codex-antigravity` from marketplace `codex-antigravity-market`.
Installed plugin root: ~/.codex/plugins/cache/codex-antigravity-market/codex-antigravity/1.0.0
```

#### 3. Verify Installation
List plugins to confirm it is enabled:

```bash
codex plugin list
```

Example output:
```text
Marketplace `codex-antigravity-market`
/path/to/Codex-Antigravity/.agents/plugins/marketplace.json

PLUGIN                                      STATUS              VERSION  PATH
codex-antigravity@codex-antigravity-market  installed, enabled  1.0.0    /path/to/Codex-Antigravity
```
If `installed, enabled` is displayed, setup is complete!

#### 4. Upgrading & Removing Plugin
```bash
# Upgrade plugin to the latest version
codex plugin marketplace upgrade

# Disable and remove plugin
codex plugin remove codex-antigravity@codex-antigravity-market
codex plugin marketplace remove codex-antigravity-market
```

---

### Method B: Register as Codex MCP Server (Autonomous Tool Calling)

Leverage Codex's **Model Context Protocol (MCP)** client capability so Codex can autonomously call Antigravity features (research, codebase analysis, test diagnosis) as function tools during reasoning.

#### 1. Add via `codex mcp add` Command
Run the following command in your terminal:

```bash
# Note: Always specify the absolute path to server.py
codex mcp add codex-antigravity -- python3 /absolute/path/to/Codex-Antigravity/mcp/server.py
```

> [!TIP]
> If your current working directory is `Codex-Antigravity`, you can specify:
> ```bash
> codex mcp add codex-antigravity -- python3 "$(pwd)/mcp/server.py"
> ```

Output:
```text
Added global MCP server 'codex-antigravity'.
```

#### Or Configure Directly in `~/.codex/config.toml`:
Open `~/.codex/config.toml` in your editor of choice and append the following section:

```toml
[mcp_servers.codex-antigravity]
command = "python3"
args = ["/absolute/path/to/Codex-Antigravity/mcp/server.py"]
```

#### 2. Verify Registration
Verify that the MCP server is registered and enabled:

```bash
codex mcp list
```

Example output:
```text
Name               Command  Args                                      Env  Cwd  Status   Auth       
codex-antigravity  python3  /path/to/Codex-Antigravity/mcp/server.py  -    -    enabled  Unsupported
```
If `Status: enabled` is shown, the registration is active.

#### 3. Remove MCP Server
```bash
codex mcp remove codex-antigravity
```

---

### Method C: Workspace-Local Placement (Project-Level)

Use this method when you want to use Antigravity integration within a single specific repository without modifying global Codex CLI configurations.

#### 1. Copy to `.agents/skills` in Target Project
Run the following from your target project's root:

```bash
# Navigate to the target project directory
cd /path/to/my-project

# Create the skills directory
mkdir -p .agents/skills

# Copy skills from Codex-Antigravity
cp -r /path/to/Codex-Antigravity/skills/* .agents/skills/
```

#### 2. Add Delegation Rules to `AGENTS.md` or `CODEX.md`
Create or update `AGENTS.md` (or `CODEX.md`) at the root of your project:

```markdown
# Agent Delegation Rules

## Antigravity Research & QA Delegation
- Delegate external API documentation, latest version queries, and GitHub issue research to `skills/antigravity-research`.
- Delegate codebase structure reconnaissance and impact analysis to `/codebase` or `skills/antigravity-research`.
- Delegate test execution and failure root cause triage to `/test` or `skills/test-delegation`.
- Production code editing, Git commits, and final decisions must be performed by Codex directly.
```

---

### Step 3: Verification with Codex CLI

After setup, launch Codex CLI to test the integration.

#### 1. Launch Codex CLI in Interactive Mode
```bash
codex
```

#### 2. Test Slash Commands
Enter the following commands at the Codex prompt:

```text
# 1. Test external research command
> /research What are the CUDA requirements for ONNX Runtime 1.20?

# 2. Test codebase reconnaissance command
> /codebase status

# 3. Test test delegation & AI triage command
> /test
```

#### 3. Test Autonomous MCP Tool Calling via Natural Language
When the MCP server is registered, Codex automatically invokes Antigravity MCP tools in the background based on natural language requests:

```text
> Look up the latest specification for the FastAPI lifespan context manager
  ⎿  Codex invokes antigravity_inspect_docs tool to retrieve the spec

> Investigate module structure and entry points in this project
  ⎿  Codex invokes antigravity_inspect_codebase tool to inspect structure

> Run the test suite, and if any test fails, diagnose the root cause
  ⎿  Codex invokes antigravity_run_tests tool for automated diagnosis
```

---

### Troubleshooting & FAQ

#### Q1: `agy: command not found`
- **Cause**: The `agy` command is not installed, or its location is not in your `PATH`.
- **Solution**:
  1. Run `which agy` in your terminal to check if the executable binary exists.
  2. If it is not in your PATH, add it to your shell configuration (`~/.zshrc` or `~/.bashrc`), or specify the absolute path in `config/defaults.toml`:
     ```toml
     [antigravity]
     agy_path = "/usr/local/bin/agy"  # or actual absolute path
     ```

#### Q2: Execution hangs at `Do you trust the contents of this project?`
- **Cause**: Workspace trust confirmation prompt on first launch of the Antigravity CLI.
- **Solution**:
  Launch `agy` once manually in your terminal, use arrow keys to select `Yes, I trust this folder`, and press Enter. Once approved, this prompt is automatically skipped for subsequent runs.

#### Q3: `Operation not permitted (os error 1)` or sandbox errors
- **Cause**: macOS permission restrictions or Codex / Antigravity sandbox limitations.
- **Solution**:
  - Ensure paths passed to `mcp/server.py` and `scripts/antigravity_delegate.py` are readable by your user account.
  - When launching Codex, specify `--sandbox workspace-write` or appropriate permission flags if needed.

#### Q4: MCP server tools are not invoked within Codex
- **Cause**: Incorrect command or path configuration for the MCP server.
- **Solution**:
  1. Run `codex mcp list` and confirm `Status: enabled`.
  2. Test the MCP server standalone via mock JSON-RPC:
     ```bash
     python3 mcp/server.py --mock
     ```
  3. Run the full test suite to verify overall environment integrity:
     ```bash
     python3 -m unittest discover -s tests -v
     ```

---

## CLI Usage (Standalone)

### 1. Codebase Reconnaissance

```bash
# Scan project structure, tech stack, and entry points
python3 scripts/antigravity_delegate.py \
  --dir . \
  --type codebase \
  --task "Analyze overall project structure and key modules"

# Impact analysis before refactoring or making changes
python3 scripts/antigravity_delegate.py \
  --dir . \
  --type impact \
  --task "Impact scope of changing arguments in execute_agy_cli"

# Static audit for code quality, technical debt, and TODOs
python3 scripts/antigravity_delegate.py \
  --dir . \
  --type audit
```

### 2. Test Delegation & AI Failure Triage

```bash
# Run auto-detected test runner (pytest, cargo test, npm test, etc.)
python3 scripts/test_runner.py --dir .

# Run with an explicitly specified test command
python3 scripts/test_runner.py --dir . --cmd "pytest tests/test_runner.py -v"

# Output in human-readable plain text format
python3 scripts/test_runner.py --dir . --text
```

When tests fail, AI automatically analyzes the root cause and provides suggested fixes:

```text
============================================================
Test Status : FAILED
Command     : /usr/bin/python3 -m unittest discover tests
Duration    : 0.42s
Metrics     : 4 passed, 1 failed, 0 errors (total 5)

Failing Tests:
  ✖ test_validate_token_expiry (tests.test_auth.TestAuth)

========================= AI Diagnosis =========================
Root Cause:
Token expiration check uses local machine time rather than UTC, causing expired tokens to evaluate as currently valid.

Affected Components:
  - src/auth.py:35 (validate_token)
  - tests/test_auth.py:42 (test_validate_token_expiry)

Suggested Fix:
  • Replace datetime.now() with datetime.now(timezone.utc) in src/auth.py line 35.
  • Verify JWT exp claim comparison uses UTC seconds epoch.
============================================================
```

### 3. External Documentation & Web Research

```bash
# Look up documentation and API specifications
python3 scripts/antigravity_delegate.py \
  --task "FastAPI lifespan context manager signature" \
  --type docs

# Comparative technical research
python3 scripts/antigravity_delegate.py \
  --task "uv vs poetry performance and feature comparison" \
  --type compare
```

### 4. Usage from Codex

Codex provides out-of-the-box skills and commands:

- **Skills**:
  - `skills/antigravity-research/SKILL.md`: External research and codebase reconnaissance.
  - `skills/test-delegation/SKILL.md`: Test execution and AI failure triage delegation.
  - `skills/research-routing/SKILL.md`: Routing standards for Coding Agents.
- **Slash Commands**:
  - `/codebase [status|impact|audit]`: Codebase reconnaissance and impact assessment.
  - `/test [command]`: Test execution with automated failure diagnosis.
  - `/research <query>`: External web and documentation research.
  - `/research-deep <query>`: Deep architectural research via native Codex reasoning.

### 5. Usage as an MCP Server

Provides tools to MCP clients (Codex, Claude Desktop, etc.) over stdio:

```bash
python3 mcp/server.py
```

Available Tools:
- `antigravity_inspect_codebase(path?: str, focus?: "codebase"|"impact"|"audit", query?: str)`: Local codebase status and impact analysis
- `antigravity_run_tests(path?: str, command?: str, diagnose?: bool)`: Test execution, aggregation, and AI failure diagnosis
- `antigravity_diagnose_failure(error_trace: str, context?: str)`: Root cause diagnosis for any error trace/log
- `antigravity_research(query: str, depth?: "quick"|"normal", model?: str, context?: str)`: External research execution
- `antigravity_compare(item_a: str, item_b: str, criteria?: str)`: Technology and library comparison
- `antigravity_inspect_docs(library: str, topic: str)`: Documentation and API spec lookup
- `antigravity_inspect_repo(repo_or_path: str, question: str)`: Remote repository structure inspection
- `antigravity_list_models(query?: str)`: List available models

---

## Configuration (`config/defaults.toml`)

```toml
[antigravity]
enabled = true
agy_path = "agy"
default_effort = "low"
timeout_seconds = 120
max_parallel = 3
max_output_chars = 20000
retry_count = 1

[models]
research = "flash"
complex_research = "pro"
diagnosis = "flash"

[codebase]
enabled = true
auto_detect_stack = true
max_file_tree_depth = 3
exclude_dirs = [".git", "node_modules", ".venv", "__pycache__", "target", "dist", "build"]

[testing]
enabled = true
auto_detect_runner = true
default_timeout_seconds = 180
max_failure_lines = 150
auto_diagnose_on_failure = true

[routing]
web_research = true
docs_lookup = true
github_research = true
codebase_status = true
codebase_impact = true
test_execution = true
test_failure_diagnosis = true
code_implementation = false
architecture = false
debugging = false

[safety]
readonly_enforced = true
disallow_file_writes = true
disallow_git_write = true
disallow_package_install = true
disallow_arbitrary_shell = true
allowed_roots = ["."]
allow_parent_paths = false
allow_absolute_paths = false
```

---

## Security & Safety Policy Layer (`SafetyPolicy`)

Codex-Antigravity does not rely merely on prompt instructions for safety; it implements an **enforced code-level security layer (`scripts/safety.py`)**:

```text
SafetyPolicy
 ├── validate_workspace(path)       # Completely blocks ../ path traversal and out-of-root access
 ├── validate_command(cmd)          # shell=False, verifies ALLOWED_RUNNERS (pytest, cargo, npm, etc.)
 ├── sanitize_environment()        # Preemptively strips sensitive tokens (GITHUB_TOKEN, AWS_SECRET, etc.)
 ├── build_agy_permissions()        # Enforces agy --sandbox when readonly_enforced is true
 └── Prompt Injection Isolation     # Isolates repo & external web content inside UNTRUSTED DATA tags
```

1. **`shell=False` Execution for `/test`**:
   Arbitrary shell evaluation is abolished. Only whitelisted runners are executed directly using safe `argv[]` lists. Shell metacharacters (`;`, `&&`, `|`, `$()`, etc.) are immediately rejected.
2. **Process-Tree Termination**:
   Configured with `start_new_session=True` on POSIX systems; on timeouts, child worker processes (such as Vitest or Node workers) are reliably killed at the process group level (`os.killpg`).
3. **Strict Workspace Boundary Validation**:
   Attempts to escape the workspace root via `--dir` or MCP `path` arguments are detected, raising a `SecurityError`.
4. **Prompt Injection Defense**:
   All target repository code and external documentation are treated as "UNTRUSTED DATA", neutralizing adversarial instructions attempting to override agent roles or safety boundaries.
5. **Structured Claim ↔ Evidence Mapping**:
   Research results extract source grounding as structured records: `claims: [{claim, source, confidence, verified}]`.
6. **Policy-as-Code Routing**:
   Tasks requiring file editing, writing, or Git commits are hard-routed to **Codex Native** via programmatic policy checks, regardless of LLM judgment.

---

## Running Tests

Run the full unit test suite using standard Python `unittest`:

```bash
python3 -m unittest discover -s tests -v
```
