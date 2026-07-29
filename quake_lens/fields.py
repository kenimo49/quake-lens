"""bvalue/omori 結果フィールドの表示仕様とドメイン説明の一元管理。

各テーブルの1エントリは (表示ラベル, 参照元, formatスペック, 説明) の4要素。
参照元は結果dictのキー名、または結果dictから表示値を導出する呼び出し可能
オブジェクト。formatスペックの空文字は str() 相当を意味する。説明文は
docs/glossary.md の用語解説と対応させる。
"""

from __future__ import annotations

from typing import Any, Callable

FieldSource = str | Callable[[dict[str, Any]], Any]
FieldSpec = tuple[str, FieldSource, str, str]


def _omori_window(result: dict[str, Any]) -> str:
    """フィットに使った時間窓を `[開始, 終了] days` 形式に組み立てる。"""
    return f"[{result['t_start']:.4f}, {result['t_end']:.4f}] days"


BVALUE_FIELDS: tuple[FieldSpec, ...] = (
    ("b", "b", ".4f", "b値。Gutenberg-Richter則の傾きで、Mが1上がるごとに地震数が約1/10になる度合い"),
    ("se", "se", ".4f", "b値推定の標準誤差"),
    ("n_used", "n", "", "推定に使ったイベント数（Mc以上）"),
    ("mc", "mc", ".2f", "完全性マグニチュード。この規模以上ならカタログに漏れなく記録されているとみなす下限"),
    ("mean_m", "mean_m", ".3f", "Mc以上のイベントの平均マグニチュード。最尤推定の入力"),
)

OMORI_FIELDS: tuple[FieldSpec, ...] = (
    ("K", "K", ".4f", "改良大森則（大森・宇津則）の振幅。余震活動の規模"),
    ("c", "c", ".4f", "本震直後の観測飽和を表す時定数（日）"),
    ("p", "p", ".4f", "余震レートの減衰の速さ。典型的には1.0前後"),
    ("logL", "logL", ".4f", "フィットの対数尤度。K/c/pのデータへの当てはまりの良さ"),
    ("n_used", "n", "", "フィットに使った余震数"),
    ("window", _omori_window, "", "フィットに使った本震後の時間窓 [開始, 終了]（日）"),
)


def field_value(result: dict[str, Any], source: FieldSource) -> Any:
    """フィールド仕様の参照元から表示値を取り出す。"""
    if callable(source):
        return source(result)
    return result[source]
