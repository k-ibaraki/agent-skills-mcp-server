---
name: skill-builder
description: Agent Skills MCP Server用のスキルを作成します。軽量で高品質なSKILL.mdファイルを生成します。
license: MIT
metadata:
  author: agent-skills-mcp-server
  version: "1.0"
  optimized_for: agent-skills-mcp-server
allowed_tools: file_write,file_read,web_fetch
---

# Skill Builder (Agent Skills MCP Server専用)

このスキルはAgent Skills MCP Server用の軽量で高品質なスキルを作成します。

## 目的

ユーザーの要求に基づいて、以下の要素を含む完全なSKILL.mdファイルを生成します：

- YAML frontmatter (name, description, metadata, allowed_tools)
- 目的セクション
- 使用方法セクション
- 具体的な実行例（2個以上）
- エラーハンドリング
- 注意事項

## 使用可能ツール

このMCPサーバーでは以下のツールが使用可能です：

1. **file_read**: ファイル読み込み（skills/, community-skills/, managed-skills/, .tmp/ のみ）
2. **file_write**: ファイル書き込み（managed-skills/, .tmp/ のみ）
3. **shell**: シェルコマンド実行（30秒タイムアウト）
4. **web_fetch**: Web取得（重要な制限あり）

### web_fetch の重要な制限

**取得可能**:
- 静的HTML（サーバー側でレンダリング済み）
- JSON APIエンドポイント
- XML/RSS フィード
- テキストデータ（100KB制限）

**取得不可**:
- JavaScript動的読み込みページ（React, Vue, SPAなど）
- ログインが必要なページ
- 100KB超のコンテンツ

**推奨アプローチ**:
1. **API優先**: 公式APIエンドポイントを探す（例: `/api/data.json`）
2. **静的HTML**: JavaScriptなしでも表示されるページを使用
3. **代替手段**: データ取得失敗時の対処法を必ず含める

## スキル作成の原則

### 1. 軽量性を重視

- 不要な説明は省略
- 簡潔で明確な指示のみ
- スクリプトファイルは作成しない（file_write で直接SKILL.md作成）

### 2. 実用性を重視

- 具体的な実行例を必ず含める（最低2個）
- エラーケースの処理方法を記載
- ユーザーが理解しやすい言語で記述

### 2-1. **重要**: スキルは動的な情報取得手順を定義する

スキルは「情報そのもの」ではなく、「最新情報を取得する方法」を定義します：

**❌ 悪い例（静的な情報を含む）**:
```markdown
## 東京の天気予報

今日: 晴れ（最高気温: 15℃）
明日: 曇り（最高気温: 12℃）
```

**✅ 良い例（動的取得の手順を定義）**:
```markdown
## 使用方法

毎回実行時に WebFetch で最新データを取得します：

WebFetch(
  url="https://api.example.com/weather/tokyo",
  prompt="最新の天気予報データから今日と明日の天気を抽出"
)

実行のたびに最新の天気情報が取得されます。
```

**重要な原則**:
- 実行例の出力には「（例）」を明記し、実際には動的に変わることを示す
- 具体的な日付・数値は避け、プレースホルダー（「X月X日」「XX℃」）を使用
- 「最新」「現在」「リアルタイム」などの表現を使用

### 3. web_fetch 使用時のベストプラクティス

**CRITICAL: 具体的な実装を必ず含める**

web_fetch を使用するスキルでは、以下を**必ず**記載すること：

1. **具体的なAPIエンドポイントURL**
   - ❌ 悪い: "気象庁APIを使用"
   - ✅ 良い: `https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json`

2. **実装手順を具体的に（WebFetch形式）**
   ```
   1. WebFetch(
        url="https://api.example.com/data",
        prompt="このJSONデータから{必要な情報}を抽出して整理してください"
      )
   2. 取得したデータをユーザー向けにフォーマット
   ```

3. **期待されるレスポンス例を含める**
   ```json
   {
     "data": {
       "temperature": 15,
       "weather": "晴れ"
     }
   }
   ```

**データソースの選択順**:
1. **公式API**: JSON/XMLエンドポイント（最優先）
   - 実在するAPIのみを記載（架空のAPIは禁止）
   - テスト可能なエンドポイントURLを明記
2. **静的HTML**: サーバー側レンダリングページ
   - JavaScriptなしで表示されることを確認
3. **代替手段**: データ取得失敗時の対処法を必ず含める
   - 公式サイトURLを案内

**例（天気情報）**:
- ✅ 良い: 気象庁API `https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json`
- ❌ 悪い: Yahoo天気（JavaScript動的読み込み）
- ❌ 悪い: "気象庁の花粉API"（実在しない架空のAPI）

**エラーハンドリング**:
- データ取得失敗時、ユーザーに公式URLを案内
- 簡潔なエラーメッセージ（長い技術的説明は不要）
- 代替データソースを提案（実在するサイトのみ）

### 4. フォーマット遵守

- 必要に応じて weather-forecast や example-skill を参考にする
- YAML frontmatter の構文を厳守
- Markdownの見出し構造を適切に使用

## スキル作成手順

1. **要件理解**: ユーザーの要求を分析
2. **参考確認**: 必要に応じて weather-forecast を file_read で確認
3. **データソース検証**（web_fetch使用時のみ）:
   - 具体的なAPIエンドポイントURLを特定
   - 静的HTML/JSONであることを確認（JavaScript動的ページは不可）
   - テスト可能な実在するURLのみを記載
   - 架空のAPIや未確認のエンドポイントは記載しない
4. **SKILL.md生成**: file_write で managed-skills/{skill_name}/SKILL.md を作成
   - **重要**: web_fetch使用時は具体的なURLを「使用方法」セクションに明記
   - 実装手順を番号付きリストで具体的に記載
   - 期待されるレスポンス例を含める（JSON/HTML構造）
5. **完了報告**: 生成したスキルのパスと概要を報告

## SKILL.mdのテンプレート構造

```markdown
---
name: {kebab-case-name}
description: {1-2文の簡潔な説明}
license: MIT
metadata:  # すべての値は文字列である必要があります（配列や数値は不可）
  author: agent-skills-mcp-server
  version: "1.0"
  language: "ja"  # オプション
  data_source: "example.com"  # オプション（複数の場合はカンマ区切り: "a.com, b.com"）
allowed_tools: web_fetch,file_read  # オプション、必要な場合のみ（カンマ区切り）
---

# {スキルタイトル}

{スキルの概要説明（1-2文）}

## 目的

{このスキルが解決する問題や提供する価値}

## 使用方法

### 必須ツール

{使用するツールとその用途}

### APIエンドポイント（web_fetch使用時は必須）

**CRITICAL: web_fetch使用時は具体的なURLを必ず記載**

```
https://api.example.com/endpoint/{parameter}
```

**パラメータ**:
- {parameter}: 説明と例

**レスポンス例**:
```json
{
  "data": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

**実装手順**:
```
1. WebFetch(
     url="https://api.example.com/endpoint/{parameter}",
     prompt="このJSONデータから data.field1 と data.field2 を抽出して整理してください"
   )
2. ユーザー向けにフォーマットして出力
```

### {その他の必要な情報}

{コマンド、設定など}

## 実行例

### 例1: {ユースケース名}

**入力**:
```
{ユーザーの入力例}
```

**処理**:
{スキルが実行する処理の説明}
{web_fetch使用時は「毎回最新データを取得」を明記}

**出力例**（実行のたびに最新情報に更新）:
```
{期待される出力}
※ 実際の出力は実行時の最新データに基づきます
```

### 例2: {別のユースケース}

{同様の構造で別の実行例}

## エラーハンドリング

{よくあるエラーとその対処法}

## 注意事項

{制限事項、注意点など}
```

## 実行例

### 例1: シンプルな挨拶スキル

**ユーザー要求**:
```
名前を受け取って挨拶を返すシンプルなスキルを作成して
```

**処理**:
1. 要求を分析し、スキル名を決定（simple-greeter）
2. SKILL.mdを生成し、file_write で保存
3. 完了を報告

**生成されるSKILL.md**（抜粋）:
```yaml
---
name: simple-greeter
description: ユーザーの名前を受け取り、パーソナライズされた挨拶メッセージを返します。
license: MIT
metadata:
  author: agent-skills-mcp-server
  version: "1.0"
---

# Simple Greeter

ユーザーの名前を受け取り、丁寧な挨拶を返すシンプルなスキルです。

## 目的

ユーザーとの対話を開始する際に、親しみやすい挨拶を提供します。

## 使用方法

このスキルはツールを使用せず、直接テキスト処理のみで動作します。

## 実行例

### 例1: 基本的な挨拶

**入力**: "私の名前は太郎です"
**出力**: "太郎さん、こんにちは！お会いできて嬉しいです。"

### 例2: フォーマルな挨拶

**入力**: "田中と申します"
**出力**: "田中様、初めまして。どのようなご用件でしょうか？"

## エラーハンドリング

- 名前が提供されない場合: 一般的な挨拶を返す
- 複数の名前がある場合: 最初の名前を使用

## 注意事項

- 敬称は自動的に付加されます
- 日本語での挨拶に最適化されています
```

### 例2: Web情報取得スキル

**ユーザー要求**:
```
URLから記事のタイトルと要約を抽出するスキル
allowed_tools: web_fetch
```

**処理**:
1. web_fetch を使用するスキルと認識
2. article-summarizer として SKILL.md を生成
3. web_fetch の使用方法を詳細に記載

**生成されるSKILL.md**（抜粋）:
```yaml
---
name: article-summarizer
description: URLから記事を取得し、タイトルと要約を抽出します。web_fetchツールを使用。
license: MIT
metadata:
  author: agent-skills-mcp-server
  version: "1.0"
allowed_tools: web_fetch
---

# Article Summarizer

Web記事のURLを受け取り、タイトルと要約を抽出して提供します。

## 目的

ユーザーが読む時間を節約するために、Web記事の重要な情報を素早く把握できるようにします。

## 使用方法

### 必須ツール

**web_fetch**: 指定されたURLからHTMLコンテンツを取得（100KB制限）

### 処理フロー

1. URLを受け取る
2. web_fetch でコンテンツを取得
3. タイトルと本文を抽出
4. 要約を生成（3-5文程度）

## 実行例

### 例1: ニュース記事の要約

**入力**: "https://example.com/news/article-123 の要約を教えて"

**処理**:
1. web_fetch でコンテンツ取得
2. タイトル抽出
3. 本文から主要ポイントを抽出

**出力**:
```
タイトル: 新技術が業界を変革

要約:
- 新しいAI技術が発表された
- 従来の手法より30%効率的
- 来年初めに市場投入予定
```

### 例2: ブログ記事の要約

**入力**: "https://blog.example.com/post/456"

**出力**:
```
タイトル: Pythonの最適化テクニック

要約:
- メモリ使用量を削減する5つの方法
- プロファイリングツールの活用
- 実践的なコード例を紹介
```

## エラーハンドリング

- **URLが無効**: エラーメッセージを返し、正しいURL形式を案内
- **100KB超過**: コンテンツが大きすぎる場合は最初の100KBのみ処理
- **取得失敗**: ネットワークエラーの場合は再試行を提案

## 注意事項

- web_fetch は100KB制限があります
- 大きなページの場合、自動要約が適用されます
- 認証が必要なページには対応していません
```

### 例3: 実用的なAPIスキル（推奨）

**ユーザー要求**:
```
天気予報APIを使って日本の天気情報を取得するスキル
```

**生成されるSKILL.md**（ベストプラクティス）:
```yaml
---
name: weather-api-fetcher
description: 気象庁APIから日本の天気予報を取得します。JSONエンドポイント使用。
license: MIT
metadata:
  author: agent-skills-mcp-server
  version: "1.0"
  data_source: "jma.go.jp"
allowed_tools: web_fetch
---

# Weather API Fetcher

気象庁の公式APIから天気予報データを取得します。

## 使用方法

### APIエンドポイント
```
https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json
```

### 主要都市コード
- 東京: 130000
- 大阪: 270000
- 名古屋: 230000

## 実行例

**入力**: "東京の天気を教えて"

**処理**:
1. 地域コード決定（東京 = 130000）
2. WebFetch を実行:
   ```
   WebFetch(
     url="https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json",
     prompt="この気象庁の予報JSONデータから今日と明日の天気と気温を抽出して整理してください"
   )
   ```
3. 期待されるJSONレスポンス:
   ```json
   {
     "timeSeries": [{
       "timeDefines": ["2024-02-15T..."],
       "areas": [{
         "area": {"name": "東京地方"},
         "weathers": ["晴れ"],
         "temps": ["15"]
       }]
     }]
   }
   ```
4. WebFetch が自動的に `timeSeries[0].areas[0]` から天気と気温を抽出

**出力例**（実行時の最新データ）:
```
【東京の天気予報】（気象庁公式データ - 取得時刻: X月X日 XX:XX）
今日: 晴れ（最高気温: 15℃）
明日: 曇り（最高気温: 12℃）

※ 実行のたびに気象庁APIから最新データを取得します
```

## エラーハンドリング

- **API呼び出し失敗**: 気象庁公式サイトURLを案内
- **地域コード不明**: 主要都市リストを表示
- **JSONパースエラー**: シンプルなエラーメッセージ

簡潔なエラー表示を心がけ、技術的詳細は省略。
```

**重要ポイント**:
- ✅ APIエンドポイント使用（JavaScript不要）
- ✅ JSONレスポンス（解析しやすい）
- ✅ シンプルなエラーハンドリング
- ✅ 代替手段（公式URL案内）

## エラーハンドリング

### よくある問題

1. **YAML構文エラー**
   - frontmatter の `---` が正しく閉じられているか確認
   - インデントがスペース2個で統一されているか確認

2. **metadata 型エラー**（最も多いエラー）
   - ❌ 間違い: `supported_languages: ["Japanese", "Tagalog"]` （配列形式）
   - ✅ 正解: `supported_languages: "Japanese, Tagalog"` （カンマ区切り文字列）
   - **重要**: metadata のすべての値は文字列である必要があります
   - 配列、数値、真偽値は使用できません

3. **ファイル書き込み失敗**
   - managed-skills/ ディレクトリが存在するか確認
   - パスが正しいか確認（managed-skills/{skill-name}/SKILL.md）

4. **web_fetch データ取得失敗**（最も重要）

   **問題**: 生成されたスキルが動作しない

   **原因**:
   - ❌ JavaScript動的読み込みページを指定（React, Vue, SPAなど）
   - ❌ 架空のAPIエンドポイントを記載（例: "気象庁の花粉API"は存在しない）
   - ❌ 具体的なURLを記載せず曖昧な説明のみ（例: "気象情報サイトから取得"）

   **必須対策**:
   - ✅ 実在する公式APIエンドポイントURLを明記
   - ✅ 静的HTML/JSONのみを使用（JavaScript不要）
   - ✅ 具体的な実装手順を番号付きで記載
   - ✅ 期待されるレスポンス例を含める

   **良い例**:
   ```
   ### APIエンドポイント
   https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json

   ### 実装手順
   1. WebFetch(
        url="https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json",
        prompt="この気象庁の予報JSONデータから天気と気温を抽出してください"
      )
   2. WebFetch が自動的にJSONをパースして必要な情報を抽出
   ```

   **悪い例**:
   ```
   気象庁の花粉APIから花粉情報を取得します。
   （具体的なURLなし、APIも実在しない）
   ```

5. **生成されたスキルの品質が低い**
   - weather-forecast を file_read で参考に確認
   - 実行例が具体的で分かりやすいか確認
   - web_fetch使用時は必ずURLとレスポンス例を含める

## 注意事項

- **scripts/ ディレクトリは作成しない**: すべてfile_write で直接SKILL.md作成
- **WebFetch 形式を使用**: `WebFetch(url="...", prompt="...")` の形式で記述（weather-forecast 参照）
- **動的情報取得を優先**: スキルは「最新情報を取得する手順」を定義する
  - ❌ 避ける: 具体的な日付や数値をスキル内に記載
  - ✅ 推奨: WebFetch で毎回最新データを取得する手順を記載
- **実行例は「例」として明示**: 出力例には「※実行のたびに最新データ」などの注記を含める
- **web_fetch を積極的に使用**: 外部情報が必要な場合は積極的に活用
- **軽量性を保つ**: 不要な説明は省略し、実用的な内容のみ含める
- **参考例を活用**: weather-forecast を file_read で確認して同じスタイルを使用
- **適切な言語を選択**: ユーザーの要求言語に合わせて記述
