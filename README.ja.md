# Codex-Antigravity (`codex-antigravity`)

[English](README.md) | [日本語](README.ja.md)

**Codex-Antigravity** は、**Coding Agent (Codex 等)** と **Google Antigravity CLI (`agy`)** を連携させ、**「コードベースの現状把握・影響調査」**、**「テスト実行＆AI障害トリアージ」**、および**「軽量な外部ドキュメント調査」**を安全・自律的に委譲するためのプラグイン＆ツールキットです。

```text
Coding Agent (Codex)
        │
        ├── ① コード実装・リファクタ・修正 ──────► Codex 自身が担当（書き込み権限）
        │
        ├── ② コードベース現状把握 & 外部調査 ───► Antigravity Scout (Read-only)
        │        │
        │        ├── /codebase [status|impact|audit]
        │        └── scripts/antigravity_delegate.py --dir . --type codebase
        │                 │ - 高速ローカルスキャン (言語/スタック/Git状態/構成)
        │                 │ - agy --add-dir による安全な読み取り専用調査
        │                 ▼
        │        構造化アーキテクチャレポート (JSON)
        │
        └── ③ テスト実行 & 障害トリアージ ────────► Test Delegator + Antigravity QA
                 │
                 ├── /test [cmd]
                 └── scripts/test_delegate.py --dir .
                          │ - テスト自動実行 & メトリクス集計 (passed/failed)
                          │ - 失敗時: スタックトレースから根本原因 & 修正指針をAI診断
                          ▼
                 構造化テスト & 診断結果 (JSON) ──► Codex (原因を把握し即座に修正)
```

---

## 主な特徴

- 🧠 **Manager型エージェント・オーケストレーター (v1.2)**:
  - ユーザーの複合タスク（例:「最新仕様を調べてコードを対応させてテストして」）を、依存関係付き DAG（Task Graph）に自動分解 (`decompose_task`)。
  - 外部調査・コードベース調査を並列で実行し、**Quality Gate** による客観的品質評価（一次ソース比率・不確実性ペナルティ等）を実施。
  - 複数エージェントの結果を **Evidence Merger** で統合し、バージョン不一致や極性矛盾などの競合 (Conflict) を自動検出。
  - 実装は Codex Native、テストは Test Delegator に委譲する完全自律フローを提供 (`antigravity-orchestrate`)。
- 🚀 **Coding Agent 向け責務の最適分離**:
  - **Codex (Lead Engineer)**: 実装コードの編集、リファクタリング、Gitコミット、最終設計判断。
  - **Antigravity (Scout & QA)**: コードベース構造調査、依存/影響分析、テスト実行＆失敗トリアージ、外部ドキュメント検索。
- 🔍 **コードベース現状把握 (Codebase Reconnaissance)**:
  - ゼロ外部依存の高速ローカルスキャナー (`scripts/codebase_analyzer.py`) が言語・フレームワーク・Git状態・ツリー構造を瞬時に抽出し、AIプロンプトに統合。
- 🧪 **テスト委任＆AI障害トリアージ (Test Delegation & Failure Triage)**:
  - pytest, unittest, cargo test, npm/vitest, go test などを自動検知・実行。
  - テスト失敗時は膨大なスタックトレースをCoding Agentのコンテキストに垂れ流さず、AIが根本原因（Root Cause）と具体的な修正指針（Suggested Fix）を構造化報告。
- 📋 **公式 `--json-schema` & Evidence 検証ステータス**:
  - `schemas/research_result.json` により Antigravity CLI から信頼性の高い構造化出力を取得。
  - 安易な `verified: true` を廃止し、`verification_status` (`source_retrieved`, `source_provided`, `unverified`, `contradicted`) に分離。
- 🛡️ **安全な読み取り専用制約 & Policy-as-Code**:
  - 調査・スカウトタスクではプロンプトレベルおよび引数レベルでファイル変更やGit書き込みを厳格に禁止。
- ⚡ **ゼロ外部依存 (Zero-dependency)**:
  - Python 3.9+ の標準ライブラリのみで完全動作。
- 📦 **豊富な連携方式**:
  - **CLI スクリプト**: `scripts/orchestrator.py`, `scripts/router.py`, `scripts/antigravity_delegate.py`, `scripts/test_runner.py`
  - **Codex Plugin / Skills**: `skills/antigravity-research`, `skills/research-routing`, `skills/test-delegation`
  - **Slash Commands**: `/codebase`, `/test`, `/research`, `/research-deep`
  - **MCP サーバー**: `mcp/server.py` (`antigravity_orchestrate`, `antigravity_decompose`, `antigravity_research`, etc.)

---

## ⚡ 30秒 Quick Start

最短で導入して使い始めるためのクイックスタートです:

```bash
# 1. リポジトリのクローン & 移動
git clone git@github.com:M0T0-2020/Codex-Antigravity.git
cd Codex-Antigravity

# 2. 環境診断 (agy CLI のインストール状態を確認)
python3 scripts/check_antigravity.py

# 3. Codex CLI プラグインとしてワンコマンド追加
codex plugin marketplace add .
codex plugin add codex-antigravity@codex-antigravity-market
```

登録完了後、Codex チャット上で直ちに以下のコマンドを利用できます:

```text
/research ONNX Runtime 1.18 の最新変更点と注意点
/codebase status
/test
```

---

## ディレクトリ構成

```text
Codex-Antigravity/
├── .agents/
│   └── plugins/
│       └── marketplace.json           # Codex プラグインマーケットプレイス定義
│
├── .codex-plugin/
│   └── plugin.json                    # Codex プラグインマニフェスト
│
├── .github/
│   └── workflows/
│       └── test.yml                   # CI 自動テストワークフロー (Python 3.9〜3.13)
│
├── .mcp.json                          # MCP サーバー構成定義
│
├── agents/
│   └── research-router.md             # ルーティングサブエージェント定義
│
├── skills/
│   ├── antigravity-research/
│   │   └── SKILL.md                   # 調査委譲スキル（コードベース調査対応）
│   ├── research-routing/
│   │   └── SKILL.md                   # Coding Agent向けルーティング基準
│   └── test-delegation/
│       └── SKILL.md                   # テスト委任＆AI障害トリアージスキル
│
├── commands/
│   ├── codebase.md                    # /codebase コマンド定義
│   ├── test.md                        # /test コマンド定義
│   ├── research.md                    # /research コマンド定義
│   └── research-deep.md               # /research-deep コマンド定義
│
├── config/
│   └── defaults.toml                  # 設定ファイル (モデルTier, テスト, 安全ポリシー等)
│
├── mcp/
│   ├── __init__.py
│   └── server.py                      # MCP stdio サーバー (tools/call)
│
├── scripts/
│   ├── __init__.py
│   ├── safety.py                      # 安全ポリシー層 (境界検査, command検証, envサニタイズ)
│   ├── router.py                      # Policy-as-Code ルーター (変更要求遮断)
│   ├── antigravity_delegate.py        # コア委譲スクリプト (プロンプト防御, claims抽出, sandbox)
│   ├── codebase_analyzer.py           # 高速ローカルプロジェクトスキャナー (<100ms)
│   ├── test_runner.py                 # テスト実行＆AI障害トリアージ (shell=False, process-group kill)
│   ├── check_antigravity.py           # 環境診断スクリプト
│   ├── config_loader.py               # TOML 設定ローダー (tomllib優先)
│   └── models.py                      # 動的モデルTier解決 (flash/pro/claude)
│
├── tests/
│   ├── __init__.py
│   ├── test_safety.py                 # 安全ポリシー＆インジェクション拒絶テスト
│   ├── test_router.py                 # Policy-as-Code ルーターテスト
│   ├── test_codebase_analyzer.py      # コードベーススキャナーテスト
│   ├── test_test_runner.py            # テスト実行＆障害診断テスト
│   ├── test_delegate.py               # 委譲・プロンプト・モックテスト
│   ├── test_output_parser.py          # 構造化パーステスト
│   ├── test_timeout.py                # タイムアウト制御テスト
│   ├── test_routing.py                # 設定読み込み・ルーティングテスト
│   └── test_mcp_server.py             # MCP サーバーテスト
│
├── pyproject.toml
├── README.ja.md                       # 日本語ドキュメント
└── README.md                          # 英語ドキュメント (デフォルト)
```

---

## Codex CLI へのインストールとセットアップ手順

Codex CLI (`codex`) から Codex-Antigravity を利用するための詳細な導入手順です。
環境や用途に合わせて、以下の **3 つの方式** から選択できます。

| 方式 | 特徴 | 推奨ユースケース |
| :--- | :--- | :--- |
| **方法 A: Codex 公式プラグインとしてインストール** | コマンド一発でスキル・コマンド・MCP を一括導入 | **最も推奨**。Codex CLI 全体で恒常的に利用したい場合 |
| **方法 B: Codex MCP サーバーとして登録** | Codex が調査・テスト診断ツールを自律的に Function Call | MCP ツールとして直接モデルに連携させたい場合 |
| **方法 C: 特定プロジェクト内への直接配置** | グローバル設定を変更せずリポジトリ配下のみで動作 | 既存の特定プロジェクトのみで試したい場合 |

---

### ステップ 0: 前提条件の確認と事前準備 (Prerequisites)

インストール前に、ターミナルで以下の前提条件を確認してください。

#### 1. Google Antigravity CLI (`agy`) の確認 & 初回認証
Antigravity CLI がインストールされ、認証が完了しているか確認します:

```bash
# バージョン確認
agy --version
```

> [!IMPORTANT]
> **初回認証・プロジェクト信頼の確認**:
> まだ一度も `agy` を起動していない場合は、ターミナルで単体起動して認証を完了させてください:
> ```bash
> agy
> ```
> 画面に `Do you trust the contents of this project?` と表示されたら、`Yes, I trust this folder` を選択して Enter を押します。Google アカウントでのログインおよびモデルクォータ画面が表示されれば準備完了です（Esc キーで終了できます）。

#### 2. OpenAI Codex CLI (`codex`) の確認
Codex CLI が利用可能か確認します:

```bash
# バージョン確認
codex --version

# 健全性チェック (任意)
codex doctor
```

#### 3. Python 3.9+ の確認
本ツールは外部ライブラリを必要とせず、Python 標準ライブラリのみで動作します:

```bash
python3 --version
```

#### 4. 環境診断スクリプトの実行
リポジトリ内の診断スクリプトを実行し、`agy` との疎通を確認します:

```bash
python3 scripts/check_antigravity.py
```

正常に検知された場合の出力例:
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

### 方法 A: Codex 公式プラグインとしてインストール（推奨）

Codex CLI の公式プラグイン管理システム（Marketplace 機能）を利用してインストールします。
プラグインマニフェスト (`.codex-plugin/plugin.json`)、マーケットプレイス定義 (`.agents/plugins/marketplace.json`)、および MCP 設定 (`.mcp.json`) が自動的に Codex に登録されます。

#### 1. マーケットプレイスの追加
Codex に本リポジトリをマーケットプレイスソースとして登録します:

```bash
# Codex-Antigravity ディレクトリ外から実行する場合 (絶対パスを指定)
codex plugin marketplace add /path/to/Codex-Antigravity

# Codex-Antigravity ディレクトリ直下にいる場合
codex plugin marketplace add .
```

実行結果:
```text
Added marketplace `codex-antigravity-market` from /path/to/Codex-Antigravity.
Installed marketplace root: /path/to/Codex-Antigravity
```

#### 2. プラグインのインストール
マーケットプレイスから `codex-antigravity` プラグインを追加します:

```bash
codex plugin add codex-antigravity@codex-antigravity-market
```

実行結果:
```text
Added plugin `codex-antigravity` from marketplace `codex-antigravity-market`.
Installed plugin root: ~/.codex/plugins/cache/codex-antigravity-market/codex-antigravity/1.0.0
```

#### 3. インストール状態の確認
プラグイン一覧を表示し、有効化されているか確認します:

```bash
codex plugin list
```

出力例:
```text
Marketplace `codex-antigravity-market`
/path/to/Codex-Antigravity/.agents/plugins/marketplace.json

PLUGIN                                      STATUS              VERSION  PATH
codex-antigravity@codex-antigravity-market  installed, enabled  1.0.0    /path/to/Codex-Antigravity
```
`installed, enabled` と表示されていればセットアップ完了です！

#### 4. プラグインの更新・アンインストール
```bash
# プラグインの最新化
codex plugin marketplace upgrade

# プラグインの無効化・削除
codex plugin remove codex-antigravity@codex-antigravity-market
codex plugin marketplace remove codex-antigravity-market
```

---

### 方法 B: Codex MCP サーバーとして登録（自律ツール呼び出し）

Codex の **Model Context Protocol (MCP)** クライアント機能を利用し、Codex の推論ループ内から Antigravity の各機能（調査、コードベース分析、テスト診断など）を関数として直接呼び出せるように登録します。

#### 1. `codex mcp add` コマンドで追加
ターミナルから以下のコマンドを実行します:

```bash
# ※ 必ず server.py の絶対パスを指定してください
codex mcp add codex-antigravity -- python3 /絶対パス/to/Codex-Antigravity/mcp/server.py
```

> [!TIP]
> 現在の作業ディレクトリが `Codex-Antigravity` の場合、以下のように指定できます:
> ```bash
> codex mcp add codex-antigravity -- python3 "$(pwd)/mcp/server.py"
> ```

実行結果:
```text
Added global MCP server 'codex-antigravity'.
```

#### または `~/.codex/config.toml` に直接記述する場合:
お好みのエディタで `~/.codex/config.toml` を開き、以下のセクションを追記します:

```toml
[mcp_servers.codex-antigravity]
command = "python3"
args = ["/絶対パス/to/Codex-Antigravity/mcp/server.py"]
```

#### 2. 登録確認
MCP サーバーが正常に登録され、有効化されているか確認します:

```bash
codex mcp list
```

出力例:
```text
Name               Command  Args                                      Env  Cwd  Status   Auth       
codex-antigravity  python3  /path/to/Codex-Antigravity/mcp/server.py  -    -    enabled  Unsupported
```
`Status: enabled` になっていれば完了です。

#### 3. MCP サーバーの削除
```bash
codex mcp remove codex-antigravity
```

---

### 方法 C: 特定プロジェクト内への直接配置（ワークスペースローカル）

Codex CLI のグローバル設定を変更せず、特定の開発プロジェクト単体で Antigravity 連携機能を利用したい場合の手順です。

#### 1. プロジェクトの `.agents/skills` にコピー
対象プロジェクトのルートディレクトリで実行します:

```bash
# 対象プロジェクトのディレクトリへ移動
cd /path/to/my-project

# スキル用ディレクトリを作成
mkdir -p .agents/skills

# Codex-Antigravity からスキルをコピー
cp -r /path/to/Codex-Antigravity/skills/* .agents/skills/
```

#### 2. プロジェクトの `AGENTS.md` または `CODEX.md` にルーティング指針を追加
プロジェクトルートに `AGENTS.md`（または `CODEX.md`）を作成・追記し、Codex が自動で Antigravity を活用できるように設定します:

```markdown
# Agent Delegation Rules

## Antigravity Research & QA Delegation
- 外部APIドキュメント、最新バージョン、GitHub Issue調査は `skills/antigravity-research` に委譲すること。
- プロジェクト構成把握・影響範囲分析は `/codebase` または `skills/antigravity-research` に委譲すること。
- テスト実行および障害原因のトリアージは `/test` または `skills/test-delegation` に委譲すること。
- 実装コードの編集、Gitコミット、最終的な意思決定は Codex 自身が行うこと。
```

---

### ステップ 3: Codex CLI での初回動作確認 (Verification)

セットアップ完了後、実際に Codex CLI を起動して連携を確認します。

#### 1. Codex CLI を対話モードで起動
```bash
codex
```

#### 2. スラッシュコマンドによる動作テスト
Codex のプロンプトから以下のコマンドを入力します:

```text
# 1. 外部調査コマンドのテスト
> /research ONNX Runtime 1.20 の CUDA 要件を調べて

# 2. コードベース現状把握コマンドのテスト
> /codebase status

# 3. テスト委任＆AIトリアージコマンドのテスト
> /test
```

#### 3. 自然言語での MCP ツール自動呼び出しテスト
MCP サーバーを登録している場合、Codex に対話で依頼するだけで、Codex がバックグラウンドで Antigravity MCP ツールを自律的に呼び出します:

```text
> FastAPI の lifespan context manager の最新仕様を調べて
  ⎿  Codex が antigravity_inspect_docs ツールを呼び出して仕様を取得

> このプロジェクトのモジュール構成とエントリーポイントを調査して
  ⎿  Codex が antigravity_inspect_codebase ツールを呼び出して構成を取得

> テストを実行して、もし失敗したら原因を診断して
  ⎿  Codex が antigravity_run_tests ツールを呼び出して自動診断
```

---

### トラブルシューティング & よくある質問 (FAQ)

#### Q1: `agy: command not found` と表示される
- **原因**: `agy` コマンドがインストールされていないか、PATH に含まれていません。
- **対処法**:
  1. ターミナルで `which agy` を実行し、実行バイナリが存在するか確認します。
  2. PATH が通っていない場合は、シェル設定ファイル（`~/.zshrc` や `~/.bashrc`）に PATH を追加するか、`config/defaults.toml` の `agy_path` に絶対パスを指定してください:
     ```toml
     [antigravity]
     agy_path = "/usr/local/bin/agy"  # または実際の絶対パス
     ```

#### Q2: `Do you trust the contents of this project?` で止まってしまう
- **原因**: Antigravity CLI 初回起動時のワークスペース信頼確認プロンプトです。
- **対処法**:
  一度ターミナルから手動で `agy` を起動し、キーボードの矢印キーで `Yes, I trust this folder` を選択して Enter を押してください。一度承認すると次回以降は自動スキップされます。

#### Q3: `Operation not permitted (os error 1)` やサンドボックスエラーが出る
- **原因**: macOS のアクセス権限制御、または Codex / Antigravity のサンドボックス制限によるものです。
- **対処法**:
  - `mcp/server.py` や `scripts/antigravity_delegate.py` の指定パスが、ユーザー権限で読み取り可能な場所にあることを確認してください。
  - Codex 起動時に必要に応じて `--sandbox workspace-write` や適切な権限フラグを付与してください。

#### Q4: MCP サーバーのツールが Codex 内で呼び出されない
- **原因**: MCP サーバーの起動コマンドやパスが誤っている可能性があります。
- **対処法**:
  1. `codex mcp list` を実行し、`Status: enabled` になっているか確認します。
  2. 以下のテストコマンドで、MCP サーバーが JSON-RPC 経由で正常に応答するか単体テストします:
     ```bash
     python3 mcp/server.py --mock
     ```
  3. 全単体テストを実行して、環境全体の整合性を確認します:
     ```bash
     python3 -m unittest discover -s tests -v
     ```

---

## 使い方 (CLI ツール単体利用)

### 1. コードベース現状把握 (Codebase Reconnaissance)

```bash
# プロジェクト構成・技術スタック・エントリーポイントの現状把握
python3 scripts/antigravity_delegate.py \
  --dir . \
  --type codebase \
  --task "プロジェクトの全体構成と主要モジュールを把握する"

# リファクタ・変更前の影響範囲（Impact）分析
python3 scripts/antigravity_delegate.py \
  --dir . \
  --type impact \
  --task "execute_agy_cli 関数の引数変更による影響範囲"

# コード品質・技術的負債・TODO の静的監査
python3 scripts/antigravity_delegate.py \
  --dir . \
  --type audit
```

### 2. テスト委任＆AI障害トリアージ (Test Delegation)

```bash
# 自動検知されたテストランナー (pytest, cargo test, npm test等) で実行
python3 scripts/test_runner.py --dir .

# テストコマンドを明示指定して実行
python3 scripts/test_runner.py --dir . --cmd "pytest tests/test_runner.py -v"

# 人間が読みやすいテキスト形式で出力
python3 scripts/test_runner.py --dir . --text
```

テスト失敗時、AIが根本原因と修正指針を自動診断して返却します：

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

### 3. 外部ドキュメント・Web 調査

```bash
# ドキュメント・API 仕様の確認
python3 scripts/antigravity_delegate.py \
  --task "FastAPI lifespan context manager signature" \
  --type docs

# 比較調査
python3 scripts/antigravity_delegate.py \
  --task "uv vs poetry performance and feature comparison" \
  --type compare
```

### 4. Codex からの利用

Codex では、以下のスキルおよびコマンドが利用可能です:

- **スキル**:
  - `skills/antigravity-research/SKILL.md`: 外部調査およびコードベース現状把握。
  - `skills/test-delegation/SKILL.md`: テスト実行＆AI障害トリアージの委任。
  - `skills/research-routing/SKILL.md`: Coding Agent 向けルーティング指針。
- **スラッシュコマンド**:
  - `/codebase [status|impact|audit]`: コードベースの現状把握・影響調査。
  - `/test [command]`: テスト実行＆失敗時の自動AI障害診断。
  - `/research <query>`: 外部Web・ドキュメント調査。
  - `/research-deep <query>`: Codex ネイティブによる詳細な設計調査。

### 5. MCP サーバーとしての利用

stdio 経由で MCP クライアント（Codex, Claude Desktop 等）にツールを提供します:

```bash
python3 mcp/server.py
```

提供ツール:
- `antigravity_inspect_codebase(path?: str, focus?: "codebase"|"impact"|"audit", query?: str)`: ローカルコードベースの現状把握・影響調査
- `antigravity_run_tests(path?: str, command?: str, diagnose?: bool)`: テスト実行・集計・AI障害診断
- `antigravity_diagnose_failure(error_trace: str, context?: str)`: 任意のエラーログ・トレースのAI原因診断
- `antigravity_research(query: str, depth?: "quick"|"normal", model?: str, context?: str)`: 外部調査実行
- `antigravity_compare(item_a: str, item_b: str, criteria?: str)`: 技術・ライブラリ比較
- `antigravity_inspect_docs(library: str, topic: str)`: ドキュメント・API仕様検索
- `antigravity_inspect_repo(repo_or_path: str, question: str)`: リモートリポジトリ構成調査
- `antigravity_list_models(query?: str)`: 利用可能なモデル一覧

---

## 設定 (`config/defaults.toml`)

```toml
[antigravity]
enabled = true
agy_path = "agy"
default_effort = "low"
timeout_seconds = 120
max_parallel = 3
max_output_chars = 20000
retry_count = 1
output_language = "en"    # リサーチ結果の出力言語（デフォルト: "en"、必要時 "ja"）

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

## セキュリティ & 安全ポリシー層 (`SafetyPolicy`)

Codex-Antigravity は単なるプロンプト指示依存の安全性ではなく、**コードレベルの厳格な執行レイヤー (`scripts/safety.py`)** を備えています。

```text
SafetyPolicy
 ├── validate_workspace(path)       # ../ パストラバーサル, ルート外アクセスの完全遮断
 ├── validate_command(cmd)          # shell=False, ALLOWED_RUNNERS (pytest, cargo, npm等) 検証
 ├── sanitize_environment()        # GITHUB_TOKEN, AWS_SECRET 等の機密変数を事前除去
 ├── build_agy_permissions()        # readonly_enforced 時の agy --sandbox 強制
 └── Prompt Injection Isolation     # リポジトリ・外部WebコンテンツをUNTRUSTED DATAとしてタグ隔離
```

1. **`/test` の `shell=False` 実行**:
   任意文字列のシェル評価を廃止し、ホワイトリストされたランナーのみを安全な `argv[]` 形式で直接実行。シェルメタ文字（`;`, `&&`, `|`, `$()` 等）は即座に拒絶。
2. **Process-Tree 一括終了**:
   POSIX 環境下で `start_new_session=True` を設定し、タイムアウト時にはプロセスグループ単位（`os.killpg`）で Vitest や Node ワーカー等の子プロセスを確実に消滅。
3. **Workspace Boundary の厳格制限**:
   `--dir` や MCP の `path` に対し、ワークスペースルート外への脱出（パストラバーサル）を自動検知して `SecurityError` を送出。
4. **Prompt Injection 防御**:
   調査対象のリポジトリコードやドキュメントをすべて「UNTRUSTED DATA」として扱い、エージェントロールや制約を上書きする指示を無効化。
5. **Claim ↔ Evidence (根拠) 構造化**:
   調査結果において「どの主張がどのソースに裏付けられているか」を `claims: [{claim, source, confidence, verified}]` として構造化抽出。
6. **Policy-as-Code ルーター**:
   コード編集・ファイル書き込み・Gitコミットを伴うタスクは、LLMの判断に関わらずコード判定で **Codex Native** へ強制誘導。

---

## テストの実行

全単体テストを Python 標準の `unittest` で実行します:

```bash
python3 -m unittest discover -s tests -v
```
