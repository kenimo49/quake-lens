# quake-lens

公開地震データの取得と統計分析を行うCLI。地震の「予知」はできないが、「予測(forecasting)」として科学的に成立している統計量 — b値、大森・宇津則による余震減衰 — を公開APIのカタログから計算する。

## Status

🚧 v1 実装中（loop-dev-ops駆動）

## Planned subcommands (v1)

```
quake-lens recent    # 直近の地震リスト（P2P地震情報API / 気象庁JSON）
quake-lens catalog   # USGSカタログの期間・領域・規模指定取得
quake-lens bvalue    # Gutenberg-Richter b値（Aki MLE法）
quake-lens omori     # 大森・宇津則の余震減衰フィット
```

## Design principles

- ランタイム依存は標準ライブラリのみ（urllib / json / math）
- ネットワークアクセスは fetch 層に隔離、統計層は純関数
- テストは fixture ベースで決定的（実APIを叩かない）

## Data sources

- [P2P地震情報 API](https://www.p2pquake.net/develop/json_api_v2/) — 気象庁情報のリレー、認証不要
- [気象庁 地震情報JSON](https://www.jma.go.jp/bosai/quake/data/list.json)
- [USGS Earthquake Catalog API](https://earthquake.usgs.gov/fdsnws/event/1/)

## License

MIT
