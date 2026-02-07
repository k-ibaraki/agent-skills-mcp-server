# Agent Skills MCP Server

MCP (Model Context Protocol) サーバーを使って Agent Skills を管理・実行するシステムです。スキルの仕様をMCPサーバーに隔離することでガバナンスを実現します。

## 特徴

- **3つのMCPツール**: スキル検索、実行、管理機能を提供
- **セマンティック検索**: ChromaDB + sentence-transformers による高精度な多言語スキル検索（日本語含む50+言語対応）
- **マルチプロバイダー対応**: Anthropic API、AWS Bedrock、Google Vertex AI に対応（Strands Agents + LiteLLM経由）
- **Transport柔軟性**: STDIO（Claude Desktop統合）とHTTPの両方をサポート
- **OAuth認証**: Google、Azure AD、Okta等の標準OIDC準拠プロバイダーに対応（HTTPモード）
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

`.env` ファイルを編集してAPIキーとデフォルトモデルを設定：

```bash
# ログレベル（オプション）
# INFO: 最小限の実行履歴のみ（デフォルト）
# DEBUG: 詳細なログ（LLMレスポンス全文含む）
# LOG_LEVEL=INFO

# デフォルトLLMモデル（以下のいずれかを選択）
DEFAULT_MODEL=anthropic/claude-3-5-sonnet-20241022
# DEFAULT_MODEL=bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
# DEFAULT_MODEL=vertex_ai/claude-3-5-sonnet-v2@20241022
# DEFAULT_MODEL=vertex_ai/gemini-3-flash-preview  # Gemini 3 (最新プレビュー)
# DEFAULT_MODEL=vertex_ai/gemini-2.5-pro  # Gemini via Vertex AI

# Anthropic API（直接APIを使用する場合）
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# AWS Bedrock（Bedrockを使用する場合）
# AWS_ACCESS_KEY_ID=your-access-key-id
# AWS_SECRET_ACCESS_KEY=your-secret-access-key
# AWS_REGION_NAME=us-east-1

# Google Vertex AI（ClaudeまたはGeminiを使用する場合）
# VERTEXAI_PROJECT=your-gcp-project-id
# VERTEXAI_LOCATION=us-central1
# 注: 認証には gcloud auth application-default login が必要

# OAuth/OIDC認証（HTTPモードのみ、オプション）
# 以下はGoogle OAuthの例。Azure AD、Oktaなど他のOIDC準拠プロバイダーでも利用可能
# OAUTH_ENABLED=true
# OAUTH_CONFIG_URL=https://accounts.google.com/.well-known/openid-configuration
# OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
# OAUTH_CLIENT_SECRET=your-client-secret
# 詳細は「OAuth認証付きHTTPサーバー」セクションを参照
```

詳細なモデル指定例は「[サポートするLLMモデル](#サポートするllmモデル)」セクションを参照してください。OAuth認証の設定方法は「[OAuth認証付きHTTPサーバー](#oauth認証付きhttpサーバーオプション)」セクションを参照してください。

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
uv run agent-skills-mcp --transport http --host 127.0.0.1 --port 8080

# または0.0.0.0でリッスン（外部からアクセス可能）
uv run agent-skills-mcp --transport http --host 0.0.0.0 --port 8080
```

**注意**: HTTPモードは、MCPプロトコルのstreamable-http transportを使用します。通常のREST APIではなく、MCP対応クライアントからの接続が必要です。

### OAuth認証付きHTTPサーバー（オプション）

HTTPモードでOAuth/OIDC認証を有効にできます。**標準OIDC仕様に準拠した任意のプロバイダー**（Google、Azure AD、Oktaなど）で利用可能です。

以下では**Google OAuthを例**に説明しますが、他のOIDC準拠プロバイダーでも同様の手順で設定できます。

#### 設定例: Google OAuth

1. **OAuthプロバイダーでの設定**（Google Cloud Consoleの場合）:
   - [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
   - 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuth 2.0 クライアント ID」を選択
   - アプリケーションの種類: 「ウェブアプリケーション」
   - 承認済みのリダイレクトURIに以下を追加: `http://localhost:8080/auth/callback`
   - クライアントIDとクライアントシークレットをコピー

2. **`.env` ファイルに設定追加**:

```bash
# OAuth認証を有効化
OAUTH_ENABLED=true

# Google OIDC設定
OAUTH_CONFIG_URL=https://accounts.google.com/.well-known/openid-configuration
OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
OAUTH_CLIENT_SECRET=your-client-secret

# サーバーのベースURL
OAUTH_SERVER_BASE_URL=http://localhost:8080

# 必須スコープ（カンマ区切り）
OAUTH_REQUIRED_SCOPES=openid,email,profile

# リフレッシュトークンサポート（オプション）
GOOGLE_OAUTH_ACCESS_TYPE=offline
```

3. **サーバー起動**:

```bash
uv run agent-skills-mcp --transport http --port 8080
```

起動時に以下のようなログが表示されます：
```
Starting MCP server with http transport and OAuth authentication on 127.0.0.1:8080...
OAuth callback URL: http://localhost:8080/auth/callback
```

#### セキュリティ設定

**開発環境**: リダイレクトURI制限なし（すべて許可）
```bash
# OAUTH_ALLOWED_REDIRECT_URIS を未設定
```

**本番環境**: 明示的なリダイレクトURI制限を推奨
```bash
# 信頼できるドメインのみ許可（ワイルドカード対応）
OAUTH_ALLOWED_REDIRECT_URIS=https://claude.ai/*,https://*.anthropic.com/*
```

#### その他のOIDCプロバイダーでの設定例

すべてのOIDC準拠プロバイダーで同様に設定できます。以下は代表的な例です。

**Azure AD**:
```bash
OAUTH_CONFIG_URL=https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration
OAUTH_CLIENT_ID=your-azure-client-id
OAUTH_CLIENT_SECRET=your-azure-client-secret
```

**Okta**:
```bash
OAUTH_CONFIG_URL=https://your-domain.okta.com/.well-known/openid-configuration
OAUTH_CLIENT_ID=your-okta-client-id
OAUTH_CLIENT_SECRET=your-okta-client-secret
```

詳細は `.env.example` を参照してください。

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

スキルをセマンティック検索します。日本語や英語など50+言語に対応しています。

**パラメータ**:
- `query` (optional): セマンティック検索クエリ（例: "天気予報", "ドキュメント検索"）
- `name_filter` (optional): name前方一致フィルタ（大文字小文字区別なし）
- `limit` (optional): 最大結果数（デフォルト: 10）

**レスポンス**:
- `name`: スキル名
- `description`: スキルの説明
- `score`: 類似度スコア (0-1)。しきい値未満の結果は自動除外
- `license`: ライセンス（存在する場合）
- `metadata`: 追加メタデータ（author、versionなど）

**検索例**:
- `query="天気予報"` → `weather-forecast` スキルが上位にヒット
- `query="ドキュメント検索"` → `notepm-search` スキルが上位にヒット
- `query="code review"` → `code-review` スキルが上位にヒット

**設定** (`.env`):
```bash
SEMANTIC_SEARCH_THRESHOLD=0.3  # 最小類似度しきい値（デフォルト: 0.3）
```

### 2. `skills-execute`

スキルをLLMに注入して実行します。

**パラメータ**:
- `skill_name` (required): 実行するスキルの名前
- `user_prompt` (required): ユーザーのプロンプト

**注意**: 使用するモデルはサーバーの環境変数`DEFAULT_MODEL`で設定します。

### 3. `skills-manage`

スキルを動的に作成・更新・削除します。内部でskill-builderスキルを使用してSKILL.mdファイルを生成します。

**パラメータ**:
- `operation` (required): 操作タイプ ("create", "update", "delete")
- `skill_name` (required): スキル名（kebab-case、例: "my-new-skill"）
- `purpose` (optional): スキルの目的（create/update時に必須）
- `detailed_requirements` (optional): 詳細要件（create/update時に必須）
- `allowed_tools` (optional): 使用可能なツール（カンマ区切り）
- `metadata` (optional): メタデータ（JSONオブジェクト）

**ディレクトリ構造**:
- `skills/` - 公式スキル（Git管理、読み取り専用）
- `community-skills/` - ユーザー手動追加スキル（Git管理外、読み取り専用）
- `managed-skills/{user}/` - MCPツール管理スキル（Git管理外、読み書き可能）
  - デフォルト: `managed-skills/default/`
  - 環境変数 `MANAGED_SKILLS_USER` で変更可能

**セキュリティ**:
- managed-skills/{user}/ 内のスキルのみ作成・更新・削除可能
- skills/ および community-skills/ は完全保護
- 環境変数 `SKILLS_CREATION_ENABLED=false` で機能を無効化可能

**自動スキル作成**:
skills-search のスコアが0.5未満の場合、システムが自動的に新しいスキルの作成を提案します。

**設定** (`.env`):
```bash
SKILLS_CREATION_ENABLED=true  # スキル管理機能の有効/無効（デフォルト: 有効）
MANAGED_SKILLS_USER=default   # サブディレクトリ名（デフォルト: "default"）
```

## スキル実行で使用可能なツール

`skills-execute` で実行されるスキル内から、以下のツールを使用できます：

### 1. `file_read`
ファイルの内容を読み込みます。

```markdown
# SKILL.md 内での使用例
file_read を使ってファイルを読み込んでください。
```

### 2. `file_write`
ファイルに内容を書き込みます。親ディレクトリが存在しない場合は自動的に作成されます。

### 3. `shell`
シェルコマンドを実行します（30秒タイムアウト）。

```markdown
# SKILL.md 内での使用例
shell コマンドで `curl` を使ってデータを取得できます。
```

### 4. `web_fetch`
URLからコンテンツを取得します（非同期、50000文字制限、30秒タイムアウト）。

```markdown
# SKILL.md 内での使用例
web_fetch を使って https://example.com からデータを取得してください。
```

**重要**: これらのツールはスキルの指示（SKILL.md）内で自然言語で指示することで、Strands Agents が自動的に呼び出します。特殊なタグは不要です。

## スキルの作成

スキルは以下の3つの場所に配置できます：

### ディレクトリ構造

```
# 公式スキル（Git管理、手動配置）
skills/
└── your-skill-name/
    └── SKILL.md

# ユーザー追加スキル（手動配置）
community-skills/
└── your-skill-name/
    └── SKILL.md

# MCPツール管理スキル（skills-manage で自動作成）
managed-skills/
└── default/              # または {user-id}
    └── your-skill-name/
        └── SKILL.md
```

**推奨**: 新しいスキルは `skills-manage` ツールで作成することを推奨します。手動作成する場合は、開発中のスキルを `skills/` または `community-skills/` に配置してください。

### SKILL.md フォーマット

```markdown
---
name: your-skill-name
description: Brief description of what this skill does
license: MIT
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

Strands Agents + LiteLLM 経由で複数のプロバイダーに対応しています。`.env` ファイルで `DEFAULT_MODEL` を設定してください。

### Anthropic API

直接Anthropic APIを使用する場合:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_MODEL=anthropic/claude-3-5-sonnet-20241022
```

モデル指定例:
- `anthropic/claude-3-5-sonnet-20241022` - Claude 3.5 Sonnet
- `anthropic/claude-3-5-haiku-20241022` - Claude 3.5 Haiku
- `anthropic/claude-sonnet-4-5-20250929` - Claude Sonnet 4.5 (最新)

### AWS Bedrock

AWS Bedrockを経由してClaudeを使用する場合:

```bash
# .env
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION_NAME=us-east-1
DEFAULT_MODEL=bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
```

モデル指定例:
- `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0` - Claude 3.5 Sonnet
- `bedrock/anthropic.claude-3-5-haiku-20241022-v1:0` - Claude 3.5 Haiku
- `bedrock/us.anthropic.claude-sonnet-4-5-v1:0` - Claude Sonnet 4.5 (USリージョン)

**注意**: Bedrockのモデル名はリージョンによって異なる場合があります。

### Google Vertex AI

Google Cloud Vertex AIを経由してClaudeを使用する場合:

```bash
# .env
VERTEXAI_PROJECT=your-gcp-project-id
VERTEXAI_LOCATION=us-central1
DEFAULT_MODEL=vertex_ai/claude-3-5-sonnet-v2@20241022
```

モデル指定例:
- `vertex_ai/claude-3-5-sonnet-v2@20241022` - Claude 3.5 Sonnet
- `vertex_ai/claude-3-5-haiku@20241022` - Claude 3.5 Haiku
- `vertex_ai/claude-sonnet-4-5@20250929` - Claude Sonnet 4.5 (最新)

**注意**:
- Vertex AIの認証にはApplication Default Credentials (ADC)を使用します
- 初回利用時に `gcloud auth application-default login` を実行してください
- `VERTEXAI_LOCATION` は `us-central1`、`europe-west1`、`asia-southeast1`、`global` などが利用可能です

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
│  │ skills-manage    │   │
│  └──────────────────┘   │
└────┬─────────────┬──────┘
     │             │
     ▼             ▼
┌──────────┐  ┌───────────────┐
│ Skills   │  │ Strands       │
│ Manager  │  │ Agents        │
└──────────┘  │ + LiteLLM     │
              └─────┬─────────┘
     │              │
     ▼              ▼
┌──────────────┐  ┌──────────────┐
│ skills/      │  │ Anthropic    │
│ community-   │  │ Bedrock      │
│ skills/      │  │ Vertex AI    │
│ managed-     │  │              │
│ skills/{user}│  │              │
└──────────────┘  └──────────────┘
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

### OAuth認証でエラーが発生する

- HTTPモードで起動しているか確認（OAuth認証はstdioモードでは動作しません）
- `.env` ファイルで必須設定が揃っているか確認:
  - `OAUTH_ENABLED=true`
  - `OAUTH_CONFIG_URL`（使用するOIDCプロバイダーの設定エンドポイント）
  - `OAUTH_CLIENT_ID`
  - `OAUTH_CLIENT_SECRET`
- OAuthプロバイダー側で承認済みのリダイレクトURIが正しく設定されているか確認
  - 例（Google Cloud Consoleの場合）: `http://localhost:8080/auth/callback`
  - プロバイダーによって設定画面が異なります
- ログレベルを `DEBUG` に設定して詳細なログを確認: `.env` に `LOG_LEVEL=DEBUG` を追加

### skills-manage が使用できない

- `.env` ファイルで `SKILLS_CREATION_ENABLED=true` が設定されているか確認（デフォルト: 有効）
- skill-builder スキルが存在するか確認: `skills/skill-builder/SKILL.md`
- 既存スキルの更新・削除は managed-skills/{user}/ 内のスキルのみ可能（skills/ と community-skills/ は保護されています）

### スキル作成がタイムアウトする

- skill-builder スキルは軽量化されていますが、複雑なスキルの生成には時間がかかることがあります
- `detailed_requirements` を簡潔にすることでタイムアウトを回避できます
- LLMモデルを高速なモデル（例: claude-3-5-haiku）に変更することも検討してください

## ライセンス

MIT

## 参考資料

- [Agent Skills Specification](https://agentskills.io/specification)
- [GitHub - anthropics/skills](https://github.com/anthropics/skills)
- [FastMCP Documentation](https://gofastmcp.com)
- [Strands Agents Documentation](https://strandsagents.com/)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Sentence-Transformers Documentation](https://sbert.net/)
