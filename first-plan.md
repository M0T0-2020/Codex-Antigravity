実装するなら、まずは **「Codex が軽い調査だけ Antigravity CLI に委譲する」MVP** を作り、その後 MCP 化するのがよいです。

## 実装方針

```text
User
  │
  ▼
Codex CLI
  │
  ├─ 実装・設計・修正 ────────────> Codex自身
  │
  └─ 軽量調査
        │
        ▼
  antigravity-research Skill
        │
        ▼
  delegate.py
        │
        ▼
  agy -p "..." --output-format json
        │
        ▼
  調査結果(JSON)
        │
        ▼
      Codex
        │
        ▼
  判断・実装
```

### Phase 1 — Antigravity CLI 単体ラッパー

最初に Codex とは独立して、Antigravity を1タスク実行できるラッパーを作ります。

```text
scripts/
└── antigravity_delegate.py
```

インターフェースは例えば：

```bash
python scripts/antigravity_delegate.py \
  --task "ONNX Runtime CUDA 13 supportを調査" \
  --type research \
  --effort low
```

出力：

```json
{
  "success": true,
  "summary": "...",
  "findings": [
    "...",
    "..."
  ],
  "sources": [
    "..."
  ],
  "usage": {
    "duration": 8.2
  }
}
```

内部では：

```text
subprocess
   ↓
agy -p ...
   --output-format json
   --effort low
```

を実行します。

ここで実装するものは、

* timeout
* return code確認
* JSON parse
* stderr処理
* 最大出力サイズ
* retry 1回
* Antigravity未インストール時のエラー
* `agy models` から利用可能モデル確認

あたりです。

---

## Phase 2 — 調査用プロンプトを固定する

単にユーザーの質問をそのまま `agy` に渡すのは避けます。

例えば内部プロンプトを、

```text
You are a lightweight research subagent.

Task:
{TASK}

Rules:

1. Research only.
2. Do not modify files.
3. Do not make architectural decisions.
4. Prefer primary sources.
5. Clearly separate facts from inference.
6. Keep the answer concise.
7. Include URLs/source names whenever possible.

Return:

SUMMARY
FINDINGS
SOURCES
UNCERTAINTIES
```

のようにします。

これによって、

```text
Codex
→ 「調べて」
→ Antigravity
→ 長大な実装まで勝手に始める
```

という状況を防げます。

---

## Phase 3 — Codex Skill

次に Codex Plugin を作ります。

```text
codex-antigravity/
├── .codex-plugin/
│   └── plugin.json
│
├── skills/
│   └── antigravity-research/
│       └── SKILL.md
│
├── scripts/
│   └── antigravity_delegate.py
│
└── config/
    └── defaults.toml
```

`SKILL.md` が非常に重要です。

例えば：

```markdown
# Antigravity Research

Delegate lightweight, read-only research tasks
to Antigravity CLI.

## Delegate

Use Antigravity for:

- documentation lookup
- web research
- GitHub issue investigation
- library/framework comparison
- API compatibility checks
- checking current versions
- collecting references
- small repository investigations

## Do NOT delegate

Do not use Antigravity for:

- implementing code
- modifying files
- debugging complex repository issues
- architecture decisions
- security-sensitive decisions
- final technical decisions

## Workflow

1. Identify the smallest independent research question.
2. Delegate only that question.
3. Read the Antigravity result.
4. Verify important claims if necessary.
5. Continue the main task yourself.
```

ここまでで、かなり使える状態になります。

---

# Phase 4 — Routing rule

次に「いつ Antigravity を呼ぶか」を明確化します。

おすすめは **read-only × low complexity** の2条件です。

```text
                    Task
                      │
                      ▼
              Requires file edit?
                 /          \
              YES            NO
              │               │
           Codex       Current info needed?
                          /        \
                        YES         NO
                        │            │
                  complexity?       Codex
                    /     \
                  LOW      HIGH
                   │        │
             Antigravity   Codex
```

具体的には：

| タスク            | 担当          |
| -------------- | ----------- |
| 最新ライブラリバージョン   | Antigravity |
| README調査       | Antigravity |
| GitHub Issue検索 | Antigravity |
| API仕様確認        | Antigravity |
| 論文3本を探す        | Antigravity |
| 技術A/Bの簡単な比較    | Antigravity |
| コード実装          | Codex       |
| バグ修正           | Codex       |
| アーキテクチャ設計      | Codex       |
| repo全体分析       | Codex       |
| テスト修正          | Codex       |

重要なのは、

> **調査結果を Antigravity の最終判断にしない**

ことです。

Antigravity は情報収集担当。

```text
Research → Antigravity
Reasoning → Codex
Implementation → Codex
```

という分離にします。

---

# Phase 5 — 明示的なコマンドも用意

自動判定だけだと挙動確認が難しいので、

```text
/research
```

のような明示的コマンドも作ると便利です。

例えば：

```text
/research ONNX Runtime 1.24のCUDA要件を調べて
```

なら必ず Antigravity。

また、

```text
/research-deep
```

を作って、

```text
/research
   ↓
Antigravity low

/research-deep
   ↓
Codex native research
```

という分け方もできます。

---

# Phase 6 — コンテキストを渡しすぎない

ここはかなり重要です。

Codex の会話全文や repository 全体を Antigravity に渡すのではなく、

```text
Main task:
Matcha-TTSにRectified Flowを導入する

Subtask:
Rectified Flowをspeech synthesisへ適用した
2024-2026年の研究を5件調査せよ
```

だけ渡します。

つまり、

```text
Codex context
██████████████████████████████

          ↓ extract

Antigravity context
███
```

にする。

これによって、

* token削減
* 速度向上
* 情報漏洩範囲縮小
* hallucination低減
* 責務の明確化

ができます。

---

# Phase 7 — 並列調査

MVPが安定したら、次はここです。

例えば：

```text
「Matcha-TTSへRectified Flowを導入」
```

なら Codex が、

```text
Task A
Rectified Flow原論文・最新研究

Task B
speechへのRectified Flow適用例

Task C
Matcha-TTS architecture上の変更候補
```

に分解。

```text
          Codex
            │
      ┌─────┼─────┐
      │     │     │
     AG1   AG2   AG3
      │     │     │
      └─────┼─────┘
            │
          Codex
```

とできます。

ただし最初から並列化する必要はありません。

まずは `max_workers=1`。

安定したら、

```toml
[antigravity]

max_parallel = 3
```

くらいにします。

---

# Phase 8 — MCP 化

Skill + subprocess が安定した段階で MCP にします。

```text
Codex
 │
 ▼
Antigravity MCP Server
 │
 ├── research
 ├── compare
 ├── inspect_docs
 └── inspect_repo
       │
       ▼
      agy
```

例えばツール仕様：

```python
research(
    query: str,
    depth: Literal["quick", "normal"],
    context: str | None = None
)
```

Codexからは、

```text
antigravity.research(
    query="Find current ONNX Runtime CUDA requirements",
    depth="quick"
)
```

のように見えます。

ここまで来ると `subprocess` を Codex が直接意識しなくてよくなります。

---

# Phase 9 — モデル振り分け

設定ファイルを作ります。

```toml
[antigravity]

enabled = true

default_effort = "low"

timeout_seconds = 120

max_parallel = 3

max_output_chars = 20000


[routing]

web_research = true

docs_lookup = true

github_research = true

code_implementation = false

architecture = false

debugging = false
```

さらにモデルについて、

```toml
[models]

research = "flash系"

complex_research = "pro系"
```

としておけば、

```text
軽い検索
    ↓
Gemini Flash

少し複雑な調査
    ↓
Gemini Pro

実装
    ↓
Codex GPT-5.6
```

という構成にできます。

モデル名自体は Antigravity の利用可能モデルが変わる可能性があるので、ハードコードせず設定化するのがよいです。

---

# Phase 10 — 安全策

Antigravity は基本 **research-only** にします。

```text
Read repository       ✓
Web access            ✓
Search GitHub         ✓
Read documentation    ✓

Write repository      ✗
Delete file           ✗
Git commit            ✗
Git push              ✗
Install packages      ✗
Run arbitrary shell   原則✗
```

Codexだけが変更権限を持つ。

これなら、

```text
Antigravity = Scout
Codex       = Engineer
```

という分離になります。

---

# 最終的なディレクトリ構成

完成形はこんな感じがよいと思います。

```text
codex-antigravity/
│
├── .codex-plugin/
│   └── plugin.json
│
├── agents/
│   └── research-router.md
│
├── skills/
│   ├── antigravity-research/
│   │   └── SKILL.md
│   │
│   └── research-routing/
│       └── SKILL.md
│
├── commands/
│   ├── research.md
│   └── research-deep.md
│
├── mcp/
│   └── server.py
│
├── scripts/
│   ├── antigravity_delegate.py
│   ├── check_antigravity.py
│   └── models.py
│
├── config/
│   └── defaults.toml
│
└── tests/
    ├── test_delegate.py
    ├── test_routing.py
    ├── test_timeout.py
    └── test_output_parser.py
```

## 実装順

最初から全部作らず、この順番をおすすめします。

```text
① agy wrapper
       ↓
② Codex Skill
       ↓
③ /research command
       ↓
④ routing rule
       ↓
⑤ timeout / permissions
       ↓
⑥ 実際のタスクで評価
       ↓
⑦ 並列subtasks
       ↓
⑧ MCP化
```

特に **①〜④だけで実用レベル**になります。

最初のバージョンでは、「Codexが判断して `agy` を subprocess で呼ぶだけ」に留めるのがいいです。MCPや複数エージェントまで最初から作ると、routing自体がうまく機能しているのか、インフラの問題なのか切り分けにくくなります。

評価するときは、例えばあなたが普段やっているような **「このGitHubプロジェクトはONNX化できる？」「この論文に似た研究を探して」「最新API仕様を確認して」** を10〜20問用意し、`Codex only` と `Codex + Antigravity` で、速度・Codex側token消費・調査精度・不要な委譲率を比較するとかなり良いテストになります。
