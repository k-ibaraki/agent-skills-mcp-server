# Community Skills

ユーザーが自由に追加・カスタマイズできるスキルディレクトリです。

## 使い方

1. `.env` に以下を追加:
   ```bash
   ADDITIONAL_SKILLS_DIRS=community-skills
   ```

2. このディレクトリ内にスキルフォルダを作成:
   ```
   community-skills/
   ├── your-skill-name/
   │   └── SKILL.md
   └── another-skill/
       ├── SKILL.md
       └── scripts/
           └── helper.py
   ```

3. `SKILL.md` の形式は `skills/example-skill/SKILL.md` を参照してください。

## Git管理について

このディレクトリ内のファイルは `.gitignore` で除外されています（この README.md を除く）。
個人のスキルやAPIキーを含む設定を安全に管理できます。

## skills/ との違い

| 項目 | `skills/` | `community-skills/` |
|------|-----------|---------------------|
| Git管理 | 対象 | 対象外 |
| 用途 | サンプル・公式スキル | ユーザー追加スキル |
| 品質保証 | リポジトリオーナーが管理 | ユーザー責任 |
