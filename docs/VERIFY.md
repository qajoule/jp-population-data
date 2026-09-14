# 検査で見ていることと見ていないこと

ここにある検査は、定めた比較対象の中に反例がないかを見るものです。比較対象の外にある事実や、入力データ自体の正しさまでは扱いません。

## Tier 1: このリポジトリで機械的に見られること

`curl -I https://jp-population-data.pages.dev/` を除き、ネットワーク接続や e-Stat のアプリケーション ID を使わずに、コミット済みのファイルを比較します。Python の検査はリポジトリ直下で、サイトの検査は `site/` で実行します。

| コマンド | 比較するもの | 違った時に出るもの |
|---|---|---|
| `python scripts/verify_rederivation.py` | 同じ一次入力から 2 回作る派生 CSV とコミット済みの派生 CSV | ファイル、行、列、異なる値 |
| `python scripts/verify_derived_invariants.py` | 派生 CSV 内の率、自然増減、年齢帯などの計算結果と、その行から計算し直した値 | 条件と不一致の行 |
| `python scripts/verify_figures.py` | `site/dist/` の SVG の点・軸・凡例・座標と、派生 CSV および図の定義 | 図 ID、条件、欠けた要素または不一致 |
| `python scripts/verify_figure_sources.py` | 図の帰属文と `data/figure_sources.json` の表題、省庁名、URL | 図 ID と異なる項目 |
| `python scripts/verify_pdf_extraction.py` | 同じ PDF から 2 回抽出する CSV とコミット済み CSV。PDF の SHA-256 も manifest と比べる | ハッシュ、行、列、異なる値。PDF がなければ `SKIPPED` |
| `npm run verify:figure-table-values` | `site/dist/index.html` の SVG の点と直下の数値表を、図 ID・年・系列・指標ごとに対応させた値 | 図、年、系列、指標、表と点の値または点の欠落・重複 |
| `npm run verify:csp` | `site/dist/index.html` の meta CSP、`site/dist/_headers`、`site/public/_headers` と `site/src/csp-policy.mjs` の文字列 | 欠けた層、異なる directive、許可されないリソース |
| `curl -I https://jp-population-data.pages.dev/` | 応答の `Content-Security-Policy` ヘッダーと、`default-src 'none'; base-uri 'none'; connect-src 'none'; font-src 'none'; form-action 'none'; frame-ancestors 'none'; img-src 'self'; manifest-src 'none'; media-src 'none'; object-src 'none'; worker-src 'none'; script-src 'self'; style-src 'self'` | ヘッダー層が適用されていること。数値は見ないため、数値については示さない |
| `npm run verify:layout` | ヘッドレスブラウザで開く `site/dist/` の文書幅とスクロール幅 | 画面幅、文書幅、スクロール幅、該当要素 |
| `npm run verify:rule-contrast` | 明暗テーマの罫線・グリッド線の色と背景色から計算したコントラスト比 | テーマ、要素、コントラスト比 |
| `npm run verify:series-styles` | 図に描く系列名と `site/src/lib/figures.ts` の `seriesStyles` | 定義のない系列名 |

サイトのコマンドは `site/` で実行します。ブラウザを使う 2 つのコマンドは、Google Chrome のヘッドレス実行と `site/dist/` を必要とし、サイトをビルドしません。

## Tier 2: 人が一次資料と見比べた範囲

警察庁年報の年齢階級別長期表は、1978-2025 年の 48 年のうち次の 2 年を人が一次資料と見比べました。いずれも年報 PDF の 32 頁、図表４－12 です。

| 年 | 比べた行 |
|---|---|
| 2009 年（平成21年） | `～９歳` から `合計` までの 11 行 |
| 1978 年（昭和53年） | `～19歳` から `合計` までの 8 行 |

繰り返すには、`data/sources_manifest.csv` で年報 PDF の URL を確認して PDF を取得し、32 頁の図表４－12 の該当年の行を `data/npa/npa_suicide_age_annual.csv` と比べます。

残る 46 年は、抽出結果の内部的な整合だけに依っています。人が一次資料と見比べたものではありません。

## Tier 3: このリポジトリでは見られないこと

- pdfplumber が PDF の罫線、結合セル、文字配置を正しく解釈したかは、ここでは判断できません。同じ PDF から同じ出力を繰り返し得られることは、同じ読み方を繰り返したことだけを示します。
- e-Stat が統計表を後から改訂したかは、ここでは検出できません。コミット済みの取得結果と、その時点の派生物・サイトを比べるだけです。
