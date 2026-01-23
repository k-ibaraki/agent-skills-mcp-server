# Agent Skills MCP Server - 開発ガイド

このファイルは Claude Code を使った開発のためのプロジェクト固有のガイドラインです。

## プロジェクト概要

Agent Skills を MCP サーバー経由で管理・実行するシステムです。スキルの仕様を MCP サーバーに隔離することでガバナンスを実現します。

**技術スタック**:
- **MCP**: FastMCP (stdio/HTTP 両対応)
- **LLM**: LiteLLM (Bedrock、Vertex AI、Anthropic API 対応)
- **Agent Skills**: Anthropic 公式仕様準拠
- **Python**: 3.13+

## 提供する MCP ツール

1. **skills-search**: スキル検索 (name/description で検索、メタデータ含む)
2. **skills-execute**: スキル実行 (LLM にスキルコンテキスト注入して実行)

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
license: Apache-2.0  # Optional
metadata:  # Optional
  author: Author Name
  version: "1.0"
---

# Skill Title

Instructions for the LLM...
```

### LLM プロバイダー対応

モデル指定形式:
- Anthropic: `anthropic/claude-3-5-sonnet-20241022`
- Bedrock: `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0`
- Vertex AI: `vertex_ai/claude-3-5-sonnet-v2@20241022`

認証情報は環境変数で管理 (.env ファイル)。

### Transport モード

- **stdio**: Claude Desktop 統合用 (デフォルト)
- **http**: Web 展開用 (`--transport http --port 8000`)

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

## 参考資料

- [Agent Skills Specification](https://agentskills.io/specification)
- [FastMCP Documentation](https://gofastmcp.com)
- [LiteLLM Documentation](https://docs.litellm.ai)
- [Pydantic Documentation](https://docs.pydantic.dev)
