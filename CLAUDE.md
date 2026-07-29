# quake-lens CLAUDE.md

## 開発コマンド

- lint: `ruff check .`
- テスト: `python3 -m pytest -q`
- CLI実行例: `python3 -m quake_lens recent --limit 5`

## docstring規約

このリポジトリのPythonソース（`quake_lens/` 配下）におけるdocstringは、以下の規約に従うこと。

### 形式

- **PEP 257 素書き**: 1行要約（1行に収まる短い文）。長い説明が必要な場合は、1行要約の後に空行を1行あけて自由記述を続ける。
- `Args:` / `Returns:` / `Raises:` などのセクションヘッダは **使わない**。引数・戻り値・例外の説明が必要な場合は、自由記述の本文中に自然な文章として書く。
- 三重ダブルクォート `"""` で囲む。

### 言語

- 日本語で書く。
- 例外として、以下は原文の英語のまま可:
  - 固有名詞（例: USGS, P2P, Aki, Gutenberg-Richter）
  - API名・関数名・変数名（例: `http_get`, `User-Agent`, `Request`）
  - 数式・記号（例: `b = log10(e) / (mean(M) - (Mc - ΔM/2))`）
  - コード片・URL

### 参考実装

`quake_lens/sources/http_client.py` を参照。この形式に揃えること。

### lint

`ruff check .` で `[tool.ruff.lint.pydocstyle]` の `convention = "pep257"` によりdocstringのフォーマットを検証している。既存の英語docstringを追加する前に、上記規約に沿って書き直すこと。
