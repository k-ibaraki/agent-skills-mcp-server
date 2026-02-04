# OAuth/OIDC認証アーキテクチャ

このドキュメントは、Agent Skills MCP ServerのOAuth/OIDC認証実装の設計と、スコープエイリアス機能の詳細を説明します。

## アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Client                              │
│                   (Claude Desktop等)                          │
└─────────────────┬───────────────────────────────────────────┘
                  │ OAuth認証フロー
                  ↓
┌─────────────────────────────────────────────────────────────┐
│               FastMCP + OIDCProxy                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Custom TokenVerifier                          │   │
│  │  - OpaqueTokenVerifier (汎用)                         │   │
│  │  - GoogleTokenVerifier (Google専用)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────────┘
                  │ トークン検証
                  ↓
┌─────────────────────────────────────────────────────────────┐
│             OAuth Provider (Google, Azure, etc.)             │
│              tokeninfo/introspection endpoint                │
└─────────────────────────────────────────────────────────────┘
```

## コンポーネント説明

### 1. OpaqueTokenVerifier（汎用ベースクラス）

**目的**: 非JWTトークン（Opaque Token）を検証する汎用的な実装

**主な機能**:
- tokeninfoエンドポイントへのHTTPリクエスト
- クライアントID検証
- トークン有効期限チェック
- **スコープエイリアス機能**（オプショナル）

**スコープエイリアス機能**:
```python
scope_aliases = {
    "email": ["https://www.googleapis.com/auth/userinfo.email"],
    "profile": ["https://www.googleapis.com/auth/userinfo.profile"],
}
```

この機能により：
1. 設定ファイルで短い名前（`email`）を使用可能
2. tokeninfoレスポンスの完全なURI（`https://...`）と自動マッピング
3. FastMCPの内部スコープ検証との互換性を確保

### 2. GoogleTokenVerifier（Google専用サブクラス）

**目的**: Googleの特性に合わせた事前設定済みverifier

**特徴**:
- Googleのtokeninfo URLを自動設定
- Googleのスコープエイリアスをデフォルトで含む
- ユーザーは設定不要（`openid,email,profile`と記述するだけ）

### 3. サーバー統合（server.py）

**自動プロバイダー検出**:
```python
if "oauth2.googleapis.com" in tokeninfo_url:
    token_verifier = GoogleTokenVerifier(...)
else:
    token_verifier = OpaqueTokenVerifier(...)
```

## スコープエイリアスの必要性

### 問題の背景

1. **OAuthプロバイダーの返すスコープ形式**:
   - Google: `https://www.googleapis.com/auth/userinfo.email`（完全なURI）
   - Azure AD: `https://graph.microsoft.com/User.Read`
   - 標準OIDC: プロバイダーにより異なる

2. **ユーザーの設定方法**:
   ```bash
   OAUTH_REQUIRED_SCOPES=openid,email,profile  # 短い名前を使いたい
   ```

3. **FastMCPの内部動作**:
   - `token_verifier.required_scopes`と`AccessToken.scopes`を比較
   - 形式が一致しないと`insufficient_scope`エラー（403）

### 解決策：スコープエイリアス

**2段階の処理**:

1. **検証時**（`verify_token`内）:
   ```python
   # 設定: required_scopes = ["email"]
   # トークン: scopes = ["https://www.googleapis.com/auth/userinfo.email"]
   # エイリアス経由でマッチ → 検証成功
   ```

2. **AccessToken作成時**:
   ```python
   # 完全なURIに加えて、短い名前も追加
   enriched_scopes = [
       "https://www.googleapis.com/auth/userinfo.email",  # 元のスコープ
       "email",  # エイリアスを追加
       ...
   ]
   ```

これにより、FastMCPの比較チェックでも両方の形式でマッチします。

## 他のプロバイダーへの拡張方法

### Azure ADの例

1. **スコープエイリアスの定義**:
   ```python
   # src/agent_skills_mcp/auth/azure_token_verifier.py
   AZURE_SCOPE_ALIASES = {
       "user_read": ["https://graph.microsoft.com/User.Read"],
       "mail_read": ["https://graph.microsoft.com/Mail.Read"],
   }

   class AzureTokenVerifier(OpaqueTokenVerifier):
       def __init__(self, *, client_id: str, required_scopes: list[str] | None = None):
           super().__init__(
               tokeninfo_url="https://graph.microsoft.com/v1.0/me",
               client_id=client_id,
               required_scopes=required_scopes,
               scope_aliases=AZURE_SCOPE_ALIASES,
           )
   ```

2. **サーバー統合**:
   ```python
   # src/agent_skills_mcp/server.py
   if "oauth2.googleapis.com" in tokeninfo_url:
       token_verifier = GoogleTokenVerifier(...)
   elif "graph.microsoft.com" in tokeninfo_url:
       token_verifier = AzureTokenVerifier(...)
   else:
       token_verifier = OpaqueTokenVerifier(...)
   ```

3. **テスト追加**:
   ```python
   # tests/test_azure_token_verifier.py
   def test_azure_scope_aliases():
       verifier = AzureTokenVerifier(
           client_id="test-client",
           required_scopes=["user_read"],
       )
       # テストロジック
   ```

## トラブルシューティング

### 403 Forbidden（insufficient_scope）エラー

**症状**: OAuth認証は成功するが、`/mcp`エンドポイントへのアクセスで403エラー

**原因**:
1. スコープ形式の不一致（完全なURI vs 短い名前）
2. エイリアス設定の不足または誤り
3. FastMCPの内部スコープ検証の失敗

**デバッグ手順**:

1. **デバッグログを有効化**:
   ```bash
   LOG_LEVEL=DEBUG uv run agent-skills-mcp --transport http --port 8080
   ```

2. **tokeninfoレスポンスを確認**:
   ```
   [DEBUG] Tokeninfo response: {'scope': '...', ...}
   ```

3. **スコープエイリアスを確認**:
   ```
   [DEBUG] GoogleTokenVerifier created with scope_aliases: {...}
   ```

4. **スコープ検証ログを確認**:
   - `"Required scope '...' not found"`が出る場合：エイリアス設定の問題
   - ログが出ない場合：FastMCPの内部検証の問題

**解決策**:
1. エイリアスマッピングが正しいか確認
2. `required_scopes`の設定を確認
3. プロバイダー固有の`TokenVerifier`を実装

## 参考資料

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [Google OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes)
- [Azure AD Scopes](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent)
- [FastMCP Documentation](https://gofastmcp.com)
