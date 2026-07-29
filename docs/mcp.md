# MCPサーバ — 設計と使い方

quake-lens は CLI に加えて MCP (Model Context Protocol) サーバとしても動く。
MCP は LLM クライアント (Claude Code / Claude Desktop 等) にツールを公開する
標準プロトコルで、これにより LLM エージェントが「直近の地震を取って b値を
推定して」といった依頼を、シェルを介さず型付き tool 呼び出しで実行できる。

## 提供する 4 tools

| tool | 主な引数 | 返り値 | 対応するCLI |
|------|---------|--------|------------|
| `get_recent` | `src` (`p2p`/`jma`), `limit`, `min_scale` | 正規化イベントのリスト | `recent` |
| `get_catalog` | `start`, `end`, `min_mag`, `bbox` | 正規化イベントのリスト | `catalog` |
| `estimate_bvalue` | `mc` (必須), + get_catalog と同じ絞り込み | 統計dict + `n_events_fetched` | `catalog \| bvalue` |
| `fit_omori` | `mainshock` (必須), + 同上 | 統計dict + `n_events_fetched` | `catalog \| omori` |

統計フィールドの意味は [glossary.md](glossary.md)、推定の中身は
[likelihood.md](likelihood.md) を参照。

## 設計判断

### 1. mcp SDK は optional dependency

base install の「ランタイム依存は標準ライブラリのみ」という方針 (README
Design principles) を壊さないため、mcp SDK (pydantic 等を連れてくる) は
extra `[mcp]` に隔離した。`pip install quake-lens` では従来どおり依存ゼロ、
MCP を使うときだけ `pip install "quake-lens[mcp]"`。

### 2. mcp_tools.py と mcp_server.py の分離

- `mcp_tools.py` — tool 実装の本体。**mcp SDK を import しない**
  stdlib 純関数で、既存の sources/stats を呼ぶ薄い層。`http_get` 注入引数を
  持ち、fixture ベースでネットワーク非依存にテストできる
- `mcp_server.py` — FastMCP への登録と stdio 起動だけの薄いラッパ

この分離により、ロジックのテストは SDK 不在環境 (CI の base 環境) でも全件
実行され、SDK が必要なのは登録の smoke テストだけになる
(`pytest.importorskip("mcp")` で SDK 不在時は skip)。

### 3. 統計 tool はイベント配列を引数に取らない

CLI では `catalog --format json | bvalue -` とパイプで繋ぐが、MCP で同じ
2段構成にすると数千件のイベント配列が LLM のコンテキストを往復してしまう
(取得結果は一度 LLM に返り、次の tool 呼び出しの引数として再送される)。
`estimate_bvalue` / `fit_omori` はカタログ取得を tool 内部で行い、統計値
だけを返すことでこの往復を避ける。代わりに `n_events_fetched` (取得総数)
を返り値に含め、推定に使った件数 `n` と区別して LLM が規模を把握できる
ようにしている。

### 4. エラーは ValueError をそのまま送出

引数不正 (未知の `src`、bbox 形式不正、`min_scale` と `src="jma"` の併用等)
は tool 内で ValueError にして送出する。FastMCP が例外を tool error として
クライアントに返すため、CLI の exit 1 + stderr と同等の役割を果たす。
`src="jma"` + `min_scale` の拒否は CLI (`--src jma --min-scale`) と同一挙動。

## mcp SDK のバージョン注意 (1.x → 2.0)

mcp SDK 2.0.0 で FastMCP クラスは `MCPServer` に改称され、
`mcp.server.fastmcp` モジュールは**削除**された (`from mcp.server import
MCPServer` に移動)。デコレータ (`@mcp.tool()`)・`run()` (stdioデフォルト)・
`list_tools()` のAPIは同型なので、mcp_server.py は import の try/except で
1.x / 2.x 両対応にしている。

教訓として、この非互換は当初レビューで検出できなかった: SDK は optional
dependency のため CI (base環境) では `importorskip` が server テストを
skip し、**import が通るかどうか自体が検証されていなかった**。optional
依存のコードは「SDK を実際にインストールした venv での実行」を検証に
含める必要がある (このリポジトリでは venv で `pip install -e ".[mcp]"` →
全テスト実行で確認済み)。

## 使い方

### インストールと起動

```bash
pip install "quake-lens[mcp]"
quake-lens-mcp            # stdio で起動 (通常はクライアントが起動する)
```

### Claude Code に登録

```bash
claude mcp add quake-lens -- quake-lens-mcp
```

### Claude Desktop に登録

`claude_desktop_config.json` の `mcpServers` に追記:

```json
{
  "mcpServers": {
    "quake-lens": {
      "command": "quake-lens-mcp"
    }
  }
}
```

### 動作確認の例

クライアントから見える tool は `get_recent` / `get_catalog` /
`estimate_bvalue` / `fit_omori` の4つ。例えば「能登半島地震の余震の
p値を出して」に対して LLM は
`fit_omori(mainshock="2024-01-01T07:10:00Z", start="2024-01-01", end="2024-01-11", min_mag=2.5)`
を1回呼ぶだけでよい。

## テスト戦略

- `tests/test_mcp_tools.py` — fixture 注入によるロジックテスト。SDK 不要で
  常に実行される。統計 tool は合成カタログ (指数分布 / 大森分布) からの
  真値回復まで検証
- `tests/test_mcp_server.py` — SDK がある環境でのみ実行される smoke テスト。
  tool 登録が import 時に通ること、登録名 4 つのピン留め、entry point の
  存在を確認する
