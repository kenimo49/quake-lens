# 尤度計算 — bvalue / omori の中身

`bvalue` と `omori` はどちらも最尤推定（MLE: maximum likelihood estimation）で
パラメータを求める。このドキュメントは「何の尤度を、どう最大化しているか」を
数式とコードの対応付きでまとめる。各フィールドの読み方は
[glossary.md](glossary.md) を参照。

## bvalue — Aki (1965) の閉形式MLE

Gutenberg-Richter則 `log10 N = a − bM` が成り立つとき、完全性マグニチュード
Mc 以上のマグニチュードの分布は指数分布になる。指数分布の最尤推定は平均値だけ
で決まるので、b値は閉形式（反復計算なし）で求まる:

```
b  = log10(e) / (mean(M) − (Mc − ΔM/2))
SE = b / √N
```

- `mean(M)` は Mc 以上のイベントの平均マグニチュード
- `ΔM/2` はビン幅補正。カタログのマグニチュードは ΔM（既定 0.1）刻みで
  丸められているため、連続分布として扱うには下限を半ビンずらす必要がある
- `SE` は Aki (1965) の近似標準誤差

実装は `quake_lens/stats/bvalue.py` の `estimate()`。式が1行で済むため、
最適化ルーチンは使わない。

## omori — Ogata (1983) のMLE

### 完全な対数尤度

余震の発生を、レート `λ(t) = K / (t + c)^p` の非同次Poisson過程とみなす。
観測窓 `[t_start, t_end]` 内の余震時刻 `t_1, ..., t_N` に対する点過程の
対数尤度は次の一般形をとる:

```
log L = Σ log λ(t_i) − ∫ λ(t) dt
```

第1項は「観測された各時刻でイベントが起きた」確率、第2項は「それ以外の時刻
では起きなかった」確率に対応する。λ(t) を代入すると:

```
log L(K, c, p) = N·log K − p·Σ log(t_i + c) − K·I(c, p)

I(c, p) = ∫ (t + c)^(−p) dt   （t_start から t_end まで）
```

積分 `I` は閉形式で書ける。`p = 1` のときだけ式の形が変わる:

```
p ≠ 1:  I = ((t_end + c)^(1−p) − (t_start + c)^(1−p)) / (1 − p)
p = 1:  I = log((t_end + c) / (t_start + c))
```

### プロファイル尤度 — 3次元を2次元に落とす

`log L` を K で偏微分して 0 と置くと、(c, p) を固定したときの最適な K が
閉形式で求まる:

```
∂log L/∂K = N/K − I(c, p) = 0   →   K* = N / I(c, p)
```

この `K*` を `log L` に代入し、(c, p) に依存しない定数項を落とすと、
最大化問題は次の2次元関数の**最小化**に帰着する:

```
f(c, p) = N·log I(c, p) + p·Σ log(t_i + c)
```

これがプロファイル尤度（profile likelihood）。探索空間が3次元から2次元に
減るぶん最適化が安定し、K は最後に `K* = N / I` で復元すればよい。

### 最適化の手順

`fit()` は次の3段階でパラメータを求める:

1. **粗いグリッドサーチ** — c と p の対数スケール格子上で `f(c, p)` を
   総当たりし、最良点を初期値にする。Nelder-Mead は局所解に落ちうるため、
   初期値をデータから選ぶ
2. **Nelder-Mead 単体法** — `(log c, log p)` 空間で `f` を最小化する。
   対数空間で探索することで `c > 0, p > 0` の制約が自動的に満たされ、
   制約付き最適化を避けられる。導関数を使わないため pure Python で書ける
3. **復元** — `c, p` を exp で戻し、`K* = N / I` を計算。報告する `logL` は
   プロファイル値ではなく、完全な対数尤度 `log L(K*, c, p)` を再計算した値

### 定義域外のセンチネル

パラメータが定義域を外れたとき（`K, c, p ≤ 0` や `t_i + c ≤ 0`）、尤度は
定義できない。最適化ルーチンを壊さないよう、例外ではなく番兵値を返す:

- `loglik` は **−inf**（最大化の文脈なので「最悪の値」）
- `_neg_profile` は **+inf**（最小化の文脈なので符号が逆）

共通部分 `Σ log(t_i + c)` の計算は `_sum_log_shifted` に一元化されており、
定義域外では `ValueError` を送出する。それをどちらの番兵値に変換するかは
呼び出し側の責務になっている。

## 数式とコードの対応

| 数式 | 実装 |
|------|------|
| `b = log10(e) / (mean(M) − (Mc − ΔM/2))` | `stats/bvalue.py` の `estimate()` |
| `log L(K, c, p)`（完全な対数尤度） | `stats/omori.py` の `loglik()` |
| `Σ log(t_i + c)` | `stats/omori.py` の `_sum_log_shifted()` |
| `I(c, p)`（レートの積分） | `stats/omori.py` の `_integral()` |
| `f(c, p)`（プロファイル尤度の最小化対象） | `stats/omori.py` の `_neg_profile()` |
| 初期値のグリッドサーチ | `stats/omori.py` の `_grid_search()` |
| Nelder-Mead 単体法 | `stats/_optim.py` の `_nelder_mead()` |
| `K* = N / I` と全体の制御 | `stats/omori.py` の `fit()` |

## 参考文献

- Aki, K. (1965). Maximum likelihood estimate of b in the formula log N = a − bM and its confidence limits.
- Utsu, T. (1961). A statistical study on the occurrence of aftershocks.
- Ogata, Y. (1983). Estimation of the parameters in the modified Omori formula for aftershock frequencies by the maximum likelihood procedure.
- Nelder, J. A. & Mead, R. (1965). A simplex method for function minimization.
