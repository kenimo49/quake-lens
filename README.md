# quake-lens

公開地震データの取得と統計分析を行うCLI。地震の「予知」はできないが、「予測(forecasting)」として科学的に成立している統計量 — b値、大森・宇津則による余震減衰 — を公開APIのカタログから計算する。

## Status

v1 実装済み: `recent` / `catalog` / `bvalue` / `omori`

## Install / run

```bash
python3 -m quake_lens --help
# または pip install 後は
quake-lens --help
```

ランタイム依存は Python 標準ライブラリのみ（`urllib` / `json` / `math` / `datetime` / `argparse`）。

## Subcommands

### `recent` — 直近の地震リスト (P2P地震情報 / 気象庁)

```bash
python3 -m quake_lens recent --limit 5 --min-scale 30
python3 -m quake_lens recent --limit 5 --src jma
```

出力（table形式）:

```
time                      lat       lon   depth   mag  src   place
2024-01-01T07:10:00Z    37.500   137.300    10.0   7.6  p2p   石川県能登地方
2024-01-01T07:12:00Z    37.400   137.200    10.0   5.8  p2p   石川県能登地方
```

`--format json` で正規化イベントJSONを出力。

`--src` で取得元を選べる（default: `p2p`）。`jma` は気象庁の地震リスト
(list.json) を直接取得する。同一地震の続報は最新の1件に集約される。
`--min-scale` はP2Pのscale値前提のフィルタなので `--src p2p` 専用
（`jma` と併用するとエラー）。

### `catalog` — USGSカタログ取得

```bash
python3 -m quake_lens catalog \
  --start 2024-01-01 --end 2024-01-02 \
  --min-mag 5.0 --bbox 24,122,46,146 \
  --format json
```

出力（json形式）:

```json
[
  {
    "time": "2024-01-01T09:10:00Z",
    "lat": 37.5,
    "lon": 137.3,
    "depth_km": 10.0,
    "mag": 7.6,
    "place": "Noto Peninsula, Japan",
    "source": "usgs"
  }
]
```

`--bbox` のデフォルトは日本周辺 `24,122,46,146`。

### `bvalue` — Gutenberg-Richter b値推定 (Aki MLE)

正規化イベントJSON（ファイル or stdin）から b値を推定:

```bash
python3 -m quake_lens catalog --min-mag 2.0 --format json > events.json
python3 -m quake_lens bvalue events.json --mc 2.5
```

出力:

```
b       = 0.9873
se      = 0.0139
n_used  = 5024
mc      = 2.50
mean_m  = 2.990
```

stdin 経由:

```bash
cat events.json | python3 -m quake_lens bvalue - --mc 2.5 --format json
```

`--mc` は completeness magnitude（必須）。`M < Mc` のイベントは除外される。SE は Aki (1965) 近似 `b / √N`。

### `omori` — 修正大森・宇津則フィット (Ogata MLE)

余震系列に対して `λ(t) = K / (t + c)^p` をフィット:

```bash
python3 -m quake_lens omori aftershocks.json \
  --mainshock 2024-01-01T07:10:00Z
```

出力:

```
K       = 152.7413
c       = 0.0219
p       = 1.0834
logL    = -234.5610
n_used  = 812
window  = [0.0000, 10.5432] days
```

最適化は pure Python の Nelder-Mead（外部ライブラリなし）。

出力フィールド（`b` / `se` / `mc` / `K` / `c` / `p` / `logL` など）の意味は [docs/glossary.md](docs/glossary.md) を、尤度計算の中身（Aki MLE / Ogata MLE の導出と最適化手順）は [docs/likelihood.md](docs/likelihood.md) を参照。

## Data sources

- [P2P地震情報 API](https://www.p2pquake.net/develop/json_api_v2/) — 気象庁情報のリレー、認証不要
- [気象庁 地震リスト list.json](https://www.jma.go.jp/bosai/quake/data/list.json) — 気象庁の一次ソース、認証不要
- [USGS Earthquake Catalog API](https://earthquake.usgs.gov/fdsnws/event/1/)

## Design principles

- ランタイム依存は標準ライブラリのみ
- HTTP取得は `quake_lens/sources/` に隔離、fetch関数は注入可能（テストではfixture JSONを注入）
- 統計計算 `quake_lens/stats/` は純関数（ネットワーク・IOなし）
- テストは fixture ベースで決定的（実APIを叩かない）

## Normalized event schema

全ソースはこの形に正規化される:

```json
{
  "time":     "2024-01-01T07:10:00Z",
  "lat":      37.5,
  "lon":      137.3,
  "depth_km": 10.0,
  "mag":      7.6,
  "place":    "石川県能登地方",
  "source":   "p2p"
}
```

`source` は `"p2p"`, `"usgs"`, `"jma"` のいずれか。

## Tests

```bash
python3 -m pytest -q
```

## License

MIT
