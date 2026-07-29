# 用語集 — 出力フィールドの読み方

`bvalue` / `omori` コマンドが出力する統計量の意味をまとめる。各フィールドの
表示ラベル・書式・1行説明のコード上の定義は `quake_lens/fields.py` にある。

## b値解析（`bvalue` コマンド / Gutenberg-Richter則）

「マグニチュード M 以上の地震がどれくらいの頻度で起きるか」は
Gutenberg-Richter則

```
log10 N = a − bM
```

に従う（N は M 以上の地震の数）。`bvalue` はこの b を Aki の最尤推定法で求める。

| フィールド | 意味 |
|-----------|------|
| `b` | b値。G-R則の傾きで、マグニチュードが1上がるごとに地震数が約1/10になる度合い。世界平均でほぼ1.0。低いほど「大きい地震の比率が高い」ことを意味し、応力集中の指標として使われる |
| `se` | b値推定の標準誤差（standard error）。推定の信頼幅 |
| `n_used` | 推定に使ったイベント数（Mc以上のみ） |
| `mc` | 完全性マグニチュード（completeness magnitude）。この規模以上ならカタログに漏れなく記録されているとみなす下限。これ未満は観測網が拾いきれないため推定から除外する |
| `mean_m` | Mc以上のイベントの平均マグニチュード。Aki の最尤推定はこの平均値から b を計算する |

## 改良大森則フィット（`omori` コマンド / 大森・宇津則）

本震のあと余震の発生レート n(t) は時間とともに

```
n(t) = K / (t + c)^p
```

で減衰する（t は本震からの経過日数）。`omori` はこの K/c/p を最尤推定
（Ogata MLE）でフィットする。

| フィールド | 意味 |
|-----------|------|
| `K` | 余震活動の規模（振幅）。大きいほど余震が多い |
| `c` | 本震直後の観測飽和を表す時定数（日）。直後は検知が追いつかず見かけ上レートが頭打ちになる、その補正項 |
| `p` | 減衰の速さ。典型的には1.0前後で、大きいほど余震が早く収まる |
| `logL` | 対数尤度（log-likelihood）。この K/c/p の組がデータにどれだけ当てはまっているかのスコア。フィットはこれを最大化して求める |
| `n_used` | フィットに使った余震数 |
| `window` | フィットに使った本震後の時間窓 `[開始, 終了]`（日） |

## 参考文献

- Aki, K. (1965). Maximum likelihood estimate of b in the formula log N = a − bM and its confidence limits.
- Utsu, T. (1961). A statistical study on the occurrence of aftershocks.
- Ogata, Y. (1983). Estimation of the parameters in the modified Omori formula for aftershock frequencies by the maximum likelihood procedure.
