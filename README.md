# Agent Skills MCP Server

MCP (Model Context Protocol) サーバーを使って Agent Skills を管理・実行するシステムです。スキルの仕様をMCPサーバーに隔離することでガバナンスを実現します。

## 特徴

- **2つのMCPツール**: スキル検索と実行機能を提供
- **マルチプロバイダー対応**: Anthropic API、AWS Bedrock、Google Vertex AI に対応（LiteLLM経由）
- **Transport柔軟性**: STDIO（Claude Desktop統合）とHTTPの両方をサポート
- **型安全**: Pydanticによる完全な型チェックとバリデーション
- **Agent Skills仕様準拠**: Anthropic公式仕様に準拠したスキル管理

## インストール

### 前提条件

- Python 3.13 以上
- [uv](https://docs.astral.sh/uv/) - Pythonパッケージマネージャー

uvのインストール:
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/agent-skills-mcp-server.git
cd agent-skills-mcp-server
```

### 2. 依存関係のインストール

[uv](https://docs.astral.sh/uv/)を使用して依存関係をインストールします：

```bash
# 本番用依存関係のみ
uv sync --no-dev

# 開発用依存関係も含める（推奨）
uv sync
```

### 3. 環境変数の設定

`.env.example` をコピーして `.env` を作成：

```bash
cp .env.example .env
```

`.env` ファイルを編集してAPIキーを設定：

```bash
# Anthropic API（推奨）
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# AWS Bedrock（オプション）
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
# AWS_REGION_NAME=us-east-1

# Google Vertex AI（オプション）
# VERTEXAI_PROJECT=your-project-id
# VERTEXAI_LOCATION=us-central1
```

## 使用方法

### Claude Desktop との統合（STDIO）

Claude Desktopの設定ファイル（`claude_desktop_config.json`）に以下を追加：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/agent-skills-mcp-server",
        "run",
        "agent-skills-mcp"
      ],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-your-api-key-here"
      }
    }
  }
}
```

**注意**: `/path/to/agent-skills-mcp-server` は実際のプロジェクトディレクトリのフルパスに置き換えてください。

Claude Desktopを再起動すると、MCPツールが利用可能になります。

### HTTPサーバーとして起動（streamable-http）

```bash
# ローカルで起動
uv run agent-skills-mcp --transport http --host 127.0.0.1 --port 8000

# または0.0.0.0でリッスン（外部からアクセス可能）
uv run agent-skills-mcp --transport http --host 0.0.0.0 --port 8000
```

**注意**: HTTPモードは、MCPプロトコルのstreamable-http transportを使用します。通常のREST APIではなく、MCP対応クライアントからの接続が必要です。

### Dockerで起動

```bash
# イメージをビルドして起動
docker compose up -d

# ログを確認
docker compose logs -f

# 停止
docker compose down
```

**前提条件**: `.env` ファイルを作成してAPIキーなどの環境変数を設定してください。

## 提供するMCPツール

### 1. `skills-search`

スキルを検索します（description/nameでフィルタリング）。

**パラメータ**:
- `query` (optional): description内を検索（部分一致、大文字小文字区別なし）
- `name_filter` (optional): name前方一致フィルタ（大文字小文字区別なし）

**レスポンス**:
- `name`: スキル名
- `description`: スキルの説明
- `license`: ライセンス（存在する場合）
- `metadata`: 追加メタデータ（author、versionなど）

### 2. `skills-execute`

スキルをLLMに注入して実行します。

**パラメータ**:
- `skill_name` (required): 実行するスキルの名前
- `user_prompt` (required): ユーザーのプロンプト

**注意**: 使用するモデルはサーバーの環境変数`DEFAULT_MODEL`で設定します。

## スキルの作成

スキルは `skills/` ディレクトリ内に配置します。

### ディレクトリ構造

```
skills/
└── your-skill-name/
    └── SKILL.md
```

### SKILL.md フォーマット

```markdown
---
name: your-skill-name
description: Brief description of what this skill does
license: Apache-2.0
metadata:
  author: Your Name
  version: "1.0"
---

# Your Skill Name

Detailed instructions for the LLM when this skill is loaded.

## Instructions

1. Step one
2. Step two
3. etc.
```

**フロントマター必須フィールド**:
- `name`: kebab-caseのスキル名（ディレクトリ名と一致させる）
- `description`: スキルの説明（1-1024文字）

**オプションフィールド**:
- `license`: ライセンス識別子
- `metadata`: 追加のメタデータ（author、versionなど）
- `compatibility`: 互換性情報
- `allowed_tools`: 許可するツールのリスト

### スキル例

`skills/example-skill/SKILL.md` を参照してください。

## サポートするLLMモデル

### Anthropic API

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

モデル指定例:
- `anthropic/claude-3-5-sonnet-20241022`
- `anthropic/claude-3-5-haiku-20241022`

### AWS Bedrock

```bash
# .env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION_NAME=us-east-1
```

モデル指定例:
- `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0`

### Google Vertex AI

```bash
# .env
VERTEXAI_PROJECT=your-project-id
VERTEXAI_LOCATION=us-central1
```

モデル指定例:
- `vertex_ai/claude-3-5-sonnet-v2@20241022`

## 開発

### 開発用コマンド

プロジェクトには便利な開発用コマンドが用意されています。

#### コード品質チェック

```bash
# Lint + フォーマットチェック
uv run check
```

#### コード自動修正

```bash
# Lint + フォーマット自動修正
uv run fix
```

#### テスト実行

```bash
# 全テスト実行
uv run test

# ユニットテストのみ
uv run test -m unit

# カバレッジレポート生成
uv run test --cov-report=html
```

### 手動実行（直接Ruff/pytestを使用）

```bash
# Lint チェック
uv run ruff check src/ tests/

# フォーマット
uv run ruff format src/ tests/

# テスト
uv run pytest
```

## アーキテクチャ

```
┌─────────────────┐
│ Claude Desktop  │
│   (MCP Client)  │
└────────┬────────┘
         │ STDIO/HTTP
         ▼
┌─────────────────────────┐
│   FastMCP Server        │
│  ┌──────────────────┐   │
│  │ skills-search    │   │
│  │ skills-execute   │   │
│  └──────────────────┘   │
└────┬─────────────┬──────┘
     │             │
     ▼             ▼
┌──────────┐  ┌─────────┐
│ Skills   │  │ LiteLLM │
│ Manager  │  │ Client  │
└──────────┘  └────┬────┘
     │             │
     ▼             ▼
┌──────────┐  ┌──────────────┐
│ skills/  │  │ Anthropic    │
│ (SKILL.md│  │ Bedrock      │
│  files)  │  │ Vertex AI    │
└──────────┘  └──────────────┘
```

## トラブルシューティング

### スキルが検出されない

- `skills/` ディレクトリが存在するか確認
- 各スキルディレクトリに `SKILL.md` が存在するか確認
- SKILL.mdのYAMLフロントマターが正しいか確認

### LLM APIエラー

- `.env` ファイルでAPIキーが設定されているか確認
- 使用しようとしているモデルに対応する認証情報が設定されているか確認

### Claude Desktopで認識されない

- `claude_desktop_config.json` のパスが正しいか確認
- Claude Desktopを再起動
- ログを確認（macOS: `~/Library/Logs/Claude/`）

## ライセンス

Apache-2.0

## 参考資料

- [Agent Skills Specification](https://agentskills.io/specification)
- [GitHub - anthropics/skills](https://github.com/anthropics/skills)
- [FastMCP Documentation](https://gofastmcp.com)
- [LiteLLM Documentation](https://docs.litellm.ai)
