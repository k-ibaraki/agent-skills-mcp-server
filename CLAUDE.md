# Agent Skills MCP Server - 開発ガイド

このファイルは Claude Code を使った開発のためのプロジェクト固有のガイドラインです。

## プロジェクト概要

Agent Skills を MCP サーバー経由で管理・実行するシステムです。スキルの仕様を MCP サーバーに隔離することでガバナンスを実現します。

**技術スタック**:
- **MCP**: FastMCP (stdio/HTTP 両対応)
- **LLM**: Strands Agents + LiteLLM (Anthropic API、AWS Bedrock、Google Vertex AI 対応)
- **Agent Skills**: Anthropic 公式仕様準拠
- **セマンティック検索**: ChromaDB + sentence-transformers
- **Python**: 3.13+

## 提供する MCP ツール

1. **skills-search**: スキル検索 (セマンティック検索対応、name/description で検索、メタデータ含む)
2. **skills-execute**: スキル実行 (LLM にスキルコンテキスト注入して実行)

### セマンティック検索 (RAG)

`skills-search` はセマンティック検索を使用してスキルを検索します。

**技術スタック**:
- **埋め込みモデル**: `paraphrase-multilingual-MiniLM-L12-v2` (50+言語対応、日本語含む)
- **ベクトルストア**: ChromaDB (インメモリ)

**パラメータ**:
- `query`: セマンティック検索クエリ
- `name_filter`: 名前プレフィックスフィルタ
- `limit`: 最大結果数 (デフォルト: 10)

**レスポンス**: 各結果に `score` (0-1) が含まれます。しきい値未満の結果は自動的に除外されます。

**起動時初期化**: サーバー起動時にモデルロードとインデックス構築を実行します。これにより初回検索のタイムアウトを防止しています。

**フォールバック**: セマンティック検索が失敗した場合、従来のキーワード検索にフォールバックします。

**設定** (`.env`):
```bash
# セマンティック検索の設定（オプション）
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2  # 埋め込みモデル
SEMANTIC_SEARCH_LIMIT=10  # デフォルト結果数
SEMANTIC_SEARCH_ENABLED=true  # セマンティック検索の有効/無効
SEMANTIC_SEARCH_THRESHOLD=0.3  # 最小類似度しきい値 (0-1)
```

## Agent Skills で使用可能なツール

スキル内から以下のツールを使用できます：

1. **file_read**: ファイル読み込み（アクセス制限あり）
2. **file_write**: ファイル書き込み（アクセス制限あり）
3. **shell**: シェルコマンド実行（30秒タイムアウト）
4. **web_fetch**: URL取得（100KB制限、自動要約対応）

これらのツールは Strands Agents のエージェントループで自動的に呼び出されます。

### ファイルアクセス制限

セキュリティのため、`file_read` と `file_write` は以下のディレクトリ内のファイルのみアクセス可能です：

- `skills/` - スキルファイル
- `.tmp/` - 一時ファイル

これらのディレクトリ外へのアクセスは拒否されます。これにより、スキルが意図しない場所のファイルを読み書きすることを防ぎます。

### web_fetch とコンテキスト管理

`web_fetch` ツールは URL からコンテンツを取得して返します（100KB制限）。

大きなレスポンスが会話履歴に蓄積してコンテキストウィンドウを圧迫する問題は、**SummarizingConversationManager** で自動的に解決されます：

- コンテキストウィンドウが溢れそうになると、古いメッセージを自動要約
- ツール呼び出しと結果のペアは保護される
- 直近の10メッセージは常に保持される
- 重要な情報は要約によって保持される

これにより、複数回の `web_fetch` 呼び出しでも "Prompt is too long" エラーが発生しません。

## コーディングガイドライン

### 型アノテーション

- Python 3.13+ の型構文を使用
- 小文字組み込み型を優先: `list[str]`, `dict[str, Any]`
- Union は パイプ構文を使用: `str | None` (Optional の代わり)

```python
# Good
def process_skills(names: list[str]) -> dict[str, Any] | None:
    ...

# Avoid
from typing import Optional, List, Dict
def process_skills(names: List[str]) -> Optional[Dict[str, Any]]:
    ...
```

### インポート順序

標準ライブラリ → サードパーティ → ローカルインポートの順で配置。必ずファイル冒頭に記述し、関数内インポートは禁止。

```python
# Good
import re
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

from agent_skills_mcp.config import get_config
from agent_skills_mcp.models import Skill
```

### エラーハンドリング

- スキル検出時は不正なスキルを静かにスキップ (discover_skills)
- スキルロード時は明示的なエラーを発生 (load_skill)
- LLM API エラーは詳細なコンテキストを含める

```python
# Discovery: Skip invalid skills silently
try:
    skill = self._parse_skill_md(skill_file)
    results.append(skill)
except (ValidationError, ValueError, yaml.YAMLError):
    continue  # Skip invalid skills

# Load: Raise explicit errors
if not skill_file.exists():
    raise ValueError(f"SKILL.md not found in: {skill_dir}")
```

### ロギング

- MCP サーバーは stdio モードで動作するため、標準出力への出力は禁止
- デバッグ情報は stderr またはファイルログに出力
- 本番環境では最小限のログのみ

## プロジェクト固有要件

### スキル管理

- スキルは `skills/` ディレクトリに配置
- 各スキルディレクトリに `SKILL.md` が必須
- YAML frontmatter + Markdown body の形式
- スキル名は kebab-case (例: `example-skill`)

### SKILL.md フォーマット

```yaml
---
name: skill-name
description: Brief description (1-1024 chars)
license: MIT  # Optional
metadata:  # Optional
  author: Author Name
  version: "1.0"
---

# Skill Title

Instructions for the LLM...
```

### LLM プロバイダー対応

モデル指定形式 (必ずプレフィックスが必要):
- **Anthropic API**:
  - `anthropic/claude-3-5-sonnet-20241022`
  - `anthropic/claude-sonnet-4-5-20250929` (最新)
- **AWS Bedrock**:
  - `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0`
  - `bedrock/us.anthropic.claude-sonnet-4-5-v1:0` (最新)
- **Google Vertex AI (Claude)**:
  - `vertex_ai/claude-3-5-sonnet-v2@20241022`
  - `vertex_ai/claude-sonnet-4-5@20250929` (最新)
- **Google Vertex AI (Gemini)**:
  - `vertex_ai/gemini-3-flash-preview` (最新プレビュー)
  - `vertex_ai/gemini-2.5-pro`
  - `vertex_ai/gemini-2.0-flash-exp`
  - `vertex_ai/gemini-1.5-pro`
  - `vertex_ai/gemini-1.5-flash`

認証情報は環境変数で管理 (.env ファイル)。詳細は `.env.example` を参照。

## OIDC/OAuth認証（オプション）

HTTPトランスポートでOAuth/OIDC認証を有効にできます。**標準OIDC仕様に準拠した任意のプロバイダー**で利用可能です。

### 対応プロバイダー
- **Google OAuth 2.0**
- **Azure AD**
- **Okta**
- その他標準OIDC準拠プロバイダー

### 設定例: Google OAuth

以下では**Google OAuthを例**に説明しますが、他のOIDC準拠プロバイダーでも同様の手順で設定できます。

1. **OAuthプロバイダーでの設定**（Google Cloud Consoleの場合）:
   - OAuth 2.0クライアントIDを作成
   - 承認済みのリダイレクトURIに `http://localhost:8080/auth/callback` を追加
   - クライアントIDとシークレットを取得

2. **.envファイルに設定追加**:
   ```bash
   OAUTH_ENABLED=true
   OAUTH_CONFIG_URL=https://accounts.google.com/.well-known/openid-configuration
   OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
   OAUTH_CLIENT_SECRET=your-client-secret
   OAUTH_SERVER_BASE_URL=http://localhost:8080
   OAUTH_REQUIRED_SCOPES=openid,email,profile
   ```

3. **HTTPモードで起動**:
   ```bash
   uv run agent-skills-mcp --transport http --port 8080
   ```

### セキュリティ設定

- **開発環境**: `OAUTH_ALLOWED_REDIRECT_URIS` 未設定（全許可）
- **本番環境**: 明示的なパターン指定を推奨
  ```bash
  OAUTH_ALLOWED_REDIRECT_URIS=https://claude.ai/*,https://*.anthropic.com/*
  ```

### 注意事項
- OAuth認証はHTTPトランスポートでのみ動作（stdioは非対応）
- リフレッシュトークンが必要な場合: `GOOGLE_OAUTH_ACCESS_TYPE=offline`

### スコープエイリアスの仕組み（Google OAuth）

**問題**: GoogleのOAuthは、トークン検証レスポンスで完全なURI形式のスコープを返します：
```json
{
  "scope": "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"
}
```

しかし、設定ファイルでは短い名前を使用します：
```bash
OAUTH_REQUIRED_SCOPES=openid,email,profile
```

**解決策**: `GoogleTokenVerifier`は自動的にスコープエイリアスを処理します：
- `email` ↔ `https://www.googleapis.com/auth/userinfo.email`
- `profile` ↔ `https://www.googleapis.com/auth/userinfo.profile`

これにより、設定ファイルでは短い名前を使用でき、トークン検証時に自動的にマッピングされます。

### 他のOAuthプロバイダーへの対応

Azure ADやOktaなど、他のプロバイダーでスコープ形式の不一致がある場合：

1. **カスタムTokenVerifierを作成**:
   ```python
   from agent_skills_mcp.auth import OpaqueTokenVerifier

   AZURE_SCOPE_ALIASES = {
       "email": ["https://graph.microsoft.com/User.Read"],
       # 他のエイリアスを追加
   }

   verifier = OpaqueTokenVerifier(
       tokeninfo_url="https://...",
       client_id="your-client-id",
       required_scopes=["openid", "email"],
       scope_aliases=AZURE_SCOPE_ALIASES,
   )
   ```

2. **`server.py`で使用**:
   `_create_auth_provider`関数を修正して、Azure AD検出時にカスタムverifierを使用します。

3. **テストを追加**:
   `tests/test_opaque_token_verifier.py`を参考に、プロバイダー固有のテストを追加します。

### Transport モード

- **stdio**: Claude Desktop 統合用 (デフォルト)
- **http**: Web 展開用 (`--transport http --port 8080`)
- **http + OAuth**: OAuth認証付きHTTP (`--transport http` + 環境変数でOAuth有効化)

## テスト戦略

### テストマーカー

- `@pytest.mark.unit`: ユニットテスト (外部依存なし)
- `@pytest.mark.integration`: 統合テスト (LLM API 呼び出しなど)
- `@pytest.mark.slow`: 実行時間が長いテスト

### カバレッジ目標

- コアモジュール (skills_manager, llm_client): 80%+
- 設定・モデル: 60%+

### テスト実行

```bash
# 全テスト
uv run pytest

# ユニットテストのみ
uv run pytest -m unit

# カバレッジレポート
uv run pytest --cov-report=html
```

## コード品質チェック

### 推奨: 開発用コマンドを使用

```bash
# Lint + フォーマットチェック
uv run check

# Lint + フォーマット自動修正
uv run fix

# テスト実行
uv run test
```

### 手動実行 (Ruff直接使用)

```bash
# Lint チェック
uv run ruff check src/ tests/

# 自動修正
uv run ruff check --fix src/ tests/

# フォーマット
uv run ruff format src/ tests/
```

### 型チェック (将来的に追加予定)

mypy または pyright を使用した型チェックを検討。

## 開発ワークフロー

1. **機能追加/バグ修正**
   - 該当するモジュールを編集
   - テストを追加/更新
   - Ruff でコード品質チェック

2. **スキル追加**
   - `skills/your-skill-name/` ディレクトリ作成
   - `SKILL.md` を作成
   - skills-search で検出確認

3. **リリース**
   - バージョン番号更新 (pyproject.toml)
   - CHANGELOG 更新
   - テスト全実行

## よくある問題と解決策

### スキルが検出されない

- `skills/` ディレクトリの存在確認
- `SKILL.md` の YAML frontmatter 構文確認
- skills_manager.validate_skill() でバリデーション

### LLM API エラー

- 環境変数の設定確認 (.env ファイル)
- モデル指定形式の確認
- API キーの有効性確認

### MCP ツールが認識されない

- FastMCP のデコレータ構文確認 (`@mcp.tool()`)
- サーバー起動方法確認 (stdio vs http)
- Claude Desktop 設定ファイル確認

### デバッグ用詳細ログを有効にしたい

デフォルトでは最小限のログ出力ですが、詳細なデバッグ情報が必要な場合：

- `.env` ファイルに `LOG_LEVEL=DEBUG` を追加
- LLMのレスポンス全文や区切り線、LiteLLM内部ログなどが stderr に出力されます
- 本番環境では `LOG_LEVEL=INFO`（デフォルト）を推奨

**ログレベル別の出力内容:**
- `INFO` (デフォルト): スキル実行の最小限の履歴（スキル名、実行時間、トークン数）
- `DEBUG`: 詳細ログ（LLMレスポンス全文、LiteLLM内部ログ、API呼び出し詳細など）

## 参考資料

- [Agent Skills Specification](https://agentskills.io/specification)
- [FastMCP Documentation](https://gofastmcp.com)
- [Strands Agents Documentation](https://strandsagents.com/)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Pydantic Documentation](https://docs.pydantic.dev)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Sentence-Transformers Documentation](https://sbert.net/)
