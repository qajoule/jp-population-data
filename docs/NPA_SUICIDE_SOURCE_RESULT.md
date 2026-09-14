# NPA_SUICIDE_SOURCE_RESULT

調査日: 2026-09-07

## 結論

警察庁の掲載入口には、2004年から2026年までを対象に55件のファイルリンクがある。2026年の月別暫定値には CSV が1件あるが、年次確定値の掲載ファイルは全て PDF であった。最新の年報 PDF は、全国・年次・年齢階級の長期表を1978年から2025年まで48年分掲載する。ただし、当該長期表は性別とのクロスを持たない。年齢階級別・性別・全国・年次を同時に満たす47年系列を、この入口の1本の機械可読ファイル又は1本のPDFから得られることは確認できなかった。

これは「存在しない」と断定する結論ではない。確認に用いた道具は Web の公式ページ閲覧と PDF 本文閲覧であり、構造上、掲載ページにリンクされていないファイル、又は PDF 内に表章されない元データは見られない。分母は、警察庁入口の掲載ファイルリンク55件中55件、最新年報 PDF 33頁中33頁である。

厚生労働省は同じ警察庁自殺統計原票を受けて資料を掲載している。年別入口は現行ページから「令和4年以前」の1階層だけを辿る構造であり、平成16年から令和7年までのファイルを掲載する。ページ表示上の「図表の元データ」は、実URLを開いた結果 PDF であり、XLS/XLSX/CSVではなかった。

## 調査方法と範囲

- 警察庁入口: [自殺者数](https://www.npa.go.jp/publications/statistics/safetylife/jisatsu.html)
- 厚生労働省入口: [自殺の統計: 各年の状況](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/seikatsuhogo/jisatsu/jisatsu_year.html)、及び [自殺統計に基づく自殺者数](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/seikatsuhogo/jisatsu/jisatsutoukei-jisatsusyasu.html)
- 厚労省の旧年分への遷移: [令和4年以前](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/seikatsuhogo/jisatsu/jisatsu_year_old.html)

入口から年別入口への遷移は厚労省だけで1階層までとした。それより下の個別ファイルから別ページを再帰的には辿っていない。データファイルを保存又はダウンロードしていない。

## 1-1. 掲載ファイルの目録

### 警察庁「自殺者数」

形式は、実URL末尾と Web が返した Content-Type を個別に確認した。年齢・性別・地域・時間は、各資料の表題とPDF本文を確認できた範囲で記した。`年齢: 10歳` は `10〜19歳` 等の10歳階級、`全国/都道府県` は全国表と都道府県表を併載することを表す。

| 年 | 資料名 | URL | 形式 | 年齢区分 | 性別 | 地域 | 時間 |
|---|---|---|---|---|---|---|---|
| 2026 | 令和8年中の月別自殺者数について（7月末の暫定値） | [PDF](https://www.npa.go.jp/safetylife/seianki/jisatsu/R08/zantei0807.pdf) | PDF | 無し | 有り | 全国/都道府県 | 月次 |
| 2026 | 統計データ | [CSV](https://www.npa.go.jp/safetylife/seianki/jisatsu/R08/zantei0807.csv) | CSV | 無し | 有り | 全国/都道府県 | 月次 |
| 2025 | 令和7年中における自殺の状況 資料 | [PDF](https://www.npa.go.jp/safetylife/seianki/jisatsu/R08/R7jisatsunojoukyou.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2025 | 令和7年中における自殺の状況 参考 | 掲載リンク | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 |
| 2024 | 令和6年中における自殺の状況 資料 | [PDF](https://www.npa.go.jp/safetylife/seianki/jisatsu/R07/R6jisatsunojoukyou.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2024 | 令和6年中における自殺の状況 参考 | 掲載リンク | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 |
| 2023 | 令和5年中における自殺の状況 資料 | [PDF](https://www.npa.go.jp/safetylife/seianki/jisatsu/R06/R5jisatsunojoukyou.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2023 | 令和5年中における自殺の状況 参考 | 掲載リンク | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 |
| 2022 | 資料 | [PDF](https://www.npa.go.jp/publications/statistics/safetylife/R04_jisatsunojoukyou_02.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2022 | 付録1 / 付録2 / 正誤表 | [PDF 4頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/R05/R4jisatsunojoukyou_huroku1.pdf) / [PDF 27頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/R05/R4jisatsunojoukyou_huroku2.pdf) / [PDF 7頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/R05/R4seigohyou.pdf) | PDF | 資料による | 資料による | 資料による | 年次 |
| 2021 | 資料 / 付録 | [PDF 37頁](https://www.npa.go.jp/publications/statistics/safetylife/R03_jisatsunojoukyou_02.pdf) / [PDF 18頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/R04/R3jisatsunojoukyou_huroku.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2020 | 資料 / 付録 | [PDF 37頁](https://www.npa.go.jp/publications/statistics/safetylife/R02_jisatsunojoukyou_02.pdf) / [PDF 18頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/R03/R02_huroku.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2019 | 資料 / 付録 | [PDF 37頁](https://www.npa.go.jp/publications/statistics/safetylife/R01_jisatsunojoukyou_02.pdf) / [PDF 18頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/R02/R01_huroku.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2018 | 資料 / 付録 | [PDF 38頁](https://www.npa.go.jp/publications/statistics/safetylife/H30_jisatsunojoukyou_02.pdf) / [PDF 18頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H30/H30_jisatunojoukyou_huroku.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2017 | 資料 / 付録 | [PDF 39頁](https://www.npa.go.jp/publications/statistics/safetylife/H29_jisatsunojoukyou_02.pdf) / [PDF 18頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H29/H29_jisatsunojoukyou_02.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2016 | 資料 / 付録 | [PDF 39頁](https://www.npa.go.jp/publications/statistics/safetylife/H28_jisatsunojoukyou_02.pdf) / [PDF 18頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H28/H28_jisatunojokyou_02.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2015 | 資料 / 付録 / 参考図表 | [PDF 19頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H27/H27_jisatunojoukyou_01.pdf) / [PDF 18頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H27/H27_jisatunojoukyou_02.pdf) / [PDF 20頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H27/H27_jisatunojoukyou_03.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2014 | 資料 / 付録1 / 付録2 / 参考図表 / 正誤表 | [19頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H26/H26_jisatunojoukyou_01.pdf) / [3頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H26/H26_jisatunojoukyou_02-1.pdf) / [15頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H26/H26_jisatunojoukyou_02-2.pdf) / [12頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H26/H26_jisatunojoukyou_03.pdf) / [1頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H26/H26_jisatunojoukyou_seigohyou.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2013 | 資料 / 付録 / 参考図表 | [19頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H25/H25_jisatunojoukyou_01.pdf) / [18頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H25/H25_jisatunojoukyou_02.pdf) / [22頁](https://www.npa.go.jp/safetylife/seianki/jisatsu/H25/H25_jisatunojoukyou_03.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2012 | 資料1-5 / 付録1-2 | [資料1](https://www.npa.go.jp/safetylife/seianki/jisatsu/H24/H24_jisatunojoukyou_01.pdf) / [資料2](https://www.npa.go.jp/safetylife/seianki/jisatsu/H24/H24_jisatunojoukyou_02.pdf) / [資料3](https://www.npa.go.jp/safetylife/seianki/jisatsu/H24/H24_jisatunojoukyou_03.pdf) / [資料4](https://www.npa.go.jp/safetylife/seianki/jisatsu/H24/H24_jisatunojoukyou_04.pdf) / [資料5](https://www.npa.go.jp/safetylife/seianki/jisatsu/H24/H24_jisatunojoukyou_05.pdf) / [付録1](https://www.npa.go.jp/safetylife/seianki/jisatsu/H24/H24jisatu-huroku_01.pdf) / [付録2](https://www.npa.go.jp/safetylife/seianki/jisatsu/H24/H24jisatu-huroku_02.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2011 | 資料1-5 / 付録 | [資料1](https://www.npa.go.jp/safetylife/seianki/jisatsu/H23/H23_jisatunojoukyou_01.pdf) / [資料2](https://www.npa.go.jp/safetylife/seianki/jisatsu/H23/H23_jisatunojoukyou_02.pdf) / [資料3](https://www.npa.go.jp/safetylife/seianki/jisatsu/H23/H23_jisatunojoukyou_03.pdf) / [資料4](https://www.npa.go.jp/safetylife/seianki/jisatsu/H23/H23_jisatunojoukyou_04.pdf) / [資料5](https://www.npa.go.jp/safetylife/seianki/jisatsu/H23/H23_jisatunojoukyou_05.pdf) / [付録](https://www.npa.go.jp/safetylife/seianki/jisatsu/H23/H23jisatu-huroku.pdf) | PDF | 10歳 | 有り（単年表） | 全国/都道府県 | 年次 |
| 2004-2010 | 各年の自殺の概要資料 | [2004](https://www.npa.go.jp/safetylife/seianki/jisatsu/H16/H16_jisatunogaiyou.pdf) / [2005](https://www.npa.go.jp/safetylife/seianki/jisatsu/H17/H17_jisatunogaiyou.pdf) / [2006](https://www.npa.go.jp/safetylife/seianki/jisatsu/H18/H18_jisatunogaiyou.pdf) / [2007](https://www.npa.go.jp/safetylife/seianki/jisatsu/H19/H19_jisatunogaiyou.pdf) / [2008](https://www.npa.go.jp/safetylife/seianki/jisatsu/H20/H20_jisatunogaiyou.pdf) / [2009](https://www.npa.go.jp/safetylife/seianki/jisatsu/H21/H21_jisatunogaiyou.pdf) / [2010](https://www.npa.go.jp/safetylife/seianki/jisatsu/H22/H22_jisatunogaiyou.pdf) | PDF | 10歳相当 | 有り | 全国/都道府県 | 年次 |

警察庁入口の分母は55リンク中55リンクを開いた。うち、Web閲覧器が対応しないため本文を表示しなかったPDF又はCSVが4件あり、表では `未確認` とした。形式が未確認のものをPDFとは扱っていない。

### 厚生労働省「自殺の統計: 各年の状況」

現行ページと旧年ページを合わせ、平成16年から令和7年を対象とする掲載を確認した。個別リンクを開いた結果、年報本体、年次概要、付録、速報、訂正、参考、及びページ上で「図表の元データ」と表記されたリンクは、確認できたものはすべてPDFであった。ZIPは平成23-25年の分析・参考図表等に3件掲載される。年齢・性別の詳細は年報・年次概要にはあるが、全ファイルで一様ではないため、個別表が必要な次工程では年報本体又は「年齢別」付録を選ぶ必要がある。

| 対象年 | 掲載資料の内訳 | 実URLを開いて確認した形式 | 年齢/性別/地域/時間 |
|---|---|---|---|
| 2004-2010 | 各年「自殺の概要資料」各1件 | PDF | 年齢相当・性別・全国/都道府県・年次 |
| 2011 | 概況、章1-3、付録1-2、震災関連 | PDF 6件、ZIP 1件 | 章・付録による。年齢別付録あり |
| 2012 | 概況、章1-3、付録1-2、震災関連 | PDF 6件、ZIP 2件 | 同上 |
| 2013 | 概況、章1-2、付録1-2、参考図表、震災関連 | PDF 6件、ZIP 1件 | 同上 |
| 2014-2015 | 章、付録、参考図表、震災関連、訂正 | PDF | 年齢別付録あり |
| 2016-2022 | 年間速報、年間暫定値、章1-3、図表の元データ、付録等 | PDF（「図表の元データ」を含む） | 章・資料による。年齢階級/性別資料あり |
| 2023-2025 | 年間暫定値、本体、参考 | PDF | 本体に年齢階級・性別・都道府県別の単年表あり |

厚労省の旧年ページで見た掲載リンクは、年別ファイル106件中106件をリンクとして列挙表示で確認し、そのうち106件を個別に開く試行をした。Web閲覧器がZIP又は一部のPDF本文を表示できない場合は、URLが返されず、実URLを報告書へ転記できなかった。そのため上表は掲載資料を年・資料種別単位で全件列挙し、実URLを確認できた個別ファイルの例を次節に限定している。これは完全な個別URL目録ではなく、未確認範囲を明示した部分成果である。

実URLを確認できた代表的な年報・年齢別資料:

- 2004年: [概要 PDF](https://www.mhlw.go.jp/file/06-Seisakujouhou-12200000-Shakaiengokyokushougaihokenfukushibu/H16_jisatunogaiyou.pdf)
- 2011年: [第2章 PDF](https://www.mhlw.go.jp/file/06-Seisakujouhou-12200000-Shakaiengokyokushougaihokenfukushibu/H2302-2_1.pdf)、[年齢別付録 PDF](https://www.mhlw.go.jp/file/06-Seisakujouhou-12200000-Shakaiengokyokushougaihokenfukushibu/H2304-furoku1_1.pdf)
- 2016年: [第1章 PDF](https://www.mhlw.go.jp/file/06-Seisakujouhou-12200000-Shakaiengokyokushougaihokenfukushibu/h28kakutei_1.pdf)、[図表の元データ PDF](https://www.mhlw.go.jp/content/001362221.pdf)
- 2018年: [第1章 PDF](https://www.mhlw.go.jp/content/H30kakutei-01.pdf)、[図表の元データ PDF](https://www.mhlw.go.jp/content/001362226.pdf)
- 2019年: [第1章 PDF](https://www.mhlw.go.jp/content/R1kakutei-01.pdf)、[図表の元データ PDF](https://www.mhlw.go.jp/content/001362235.pdf)
- 2020年: [第1章 PDF](https://www.mhlw.go.jp/content/R2kakutei-01.pdf)、[図表の元データ PDF](https://www.mhlw.go.jp/content/001362248.pdf)
- 2021年: [第1章 PDF](https://www.mhlw.go.jp/content/R3kakutei01.pdf)、[図表の元データ PDF](https://www.mhlw.go.jp/content/001362253.pdf)
- 2022年: [第1章 PDF](https://www.mhlw.go.jp/content/R4kakutei01.pdf)、[図表の元データ PDF](https://www.mhlw.go.jp/content/R4kakutei01-2.pdf)
- 2023年: [本体 PDF](https://www.mhlw.go.jp/content/001236073.pdf)
- 2024年: [本体 PDF](https://www.mhlw.go.jp/content/001464717.pdf)
- 2025年: [本体 PDF](https://www.mhlw.go.jp/content/001680736.pdf)

## 1-2. 全国・年齢階級別・性別・年次系列の取得範囲

| 要件への適合 | 年の範囲 | 件数 | 形式 | 根拠と制約 |
|---|---:|---:|---|---|
| 全国年次・年齢階級（性別なしの長期表） | 1978-2025 | 48年 | PDF 1件、該当頁1頁 | 警察庁2025年年報の図表4-12（PDF 31頁）。 |
| 全国年次・年齢階級・性別（単年表を年ごとに集める） | 2004-2025 | 22年 | PDF年報・概要資料 | 警察庁入口で2004-2025の各年資料を確認。単年表の年齢・性別クロスは資料内にある。 |
| 同上、1978-2003 | 未確認 | 26年 | 未確認 | 警察庁入口に個別年報リンクがない。リンクされない資料は入口巡回では検出できない。分母は入口55リンク中55リンク。 |
| 機械可読で全国年次・年齢階級・性別 | 未確認 | 未確認 | CSVは2026月次1件のみ | CSVを実URLで確認したが、年齢階級を含まない月次暫定値である。XLS/XLSX/CSVの年次確定値は、この入口群では確認できなかった。 |

「1978-2003の個別年報リンクがない」は、警察庁入口の掲載リンク55件を全件確認した結果である。道具はWeb公式ページ閲覧であり、同ページに掲載されないアーカイブ、別のサイト、非公開ファイルは構造的に見られない。分母は55件中55件である。

PDFしかない年の範囲を、資料を最小化して47年分（1978-2024）として取る場合は、2024年年報 PDF 1件の図表4-12、該当1頁で足りる。ただし性別クロスを満たさない。年齢・性別クロスを保持して2004-2025を取る場合、PDF 22年分が必要である。1978-2003の26年分はこの入口では取得経路未確認であるため、PDF件数・ページ数を確定できない。

## 1-3. 年齢区分の literal

警察庁2025年年報の図表4-12（PDF 31頁）の区分名は、本文表記のまま `～９歳`、`10～19歳`、`20～29歳`、`30～39歳`、`40～49歳`、`50～59歳`、`60～69歳`、`70～79歳`、`80歳～`、`不詳`、`合計` である。2024年年報にも `～９歳`、`10～19歳`、`20～29歳` 等がある。

- `10-19歳` に相当する literal は `10～19歳` であり、長期表では1978-2025の48年に存在する。
- `20-29歳` に相当する literal は `20～29歳` であり、長期表では1978-2025の48年に存在する。
- 2004年概要資料の年齢表は `～19`、`20～29`、`30～39`、`40～49`、`50～59`、`60～`、`不詳` であり、若年側の刻みが後年の `10～19歳` と異なる。
- 前年比較表には `19歳以下` が使われる。これは年次推移の本表 `10～19歳` と同一の区分ではないため、混在させられない。

## 1-4. 次工程の作業量

- 1978-2024の47年を、性別を使わない全国年齢階級表として揃える: PDF 1件、該当ページ1頁（2024年年報の図表4-12）。
- 2004-2025の22年を、年齢・性別クロスを保って揃える: 年次PDF 22件。各PDFで該当表ページを特定し、22年分を転記又は抽出する必要がある。
- 1978-2003の26年を、年齢・性別クロスで揃える: この入口群では取得経路が未確認。必要PDF件数、該当総ページ数とも未確定。
- CSVは1件だが、2026年の月次暫定値で、年齢階級・性別の年次確定系列ではない。

## 実行した確認と未実行の確認

### 実行した確認

- 警察庁入口の掲載ファイルリンク55件を全件開いた。PDFはURL末尾と `application/pdf`、CSVはURL末尾と閲覧器の `text/csv` エラーで形式を確認した。
- 厚労省の現行入口、旧年入口、及び「自殺統計に基づく自殺者数」を開いた。旧年入口は1階層だけ辿り、掲載された個別リンク106件を開く試行をした。
- 警察庁2025年年報33頁を閲覧し、PDF 31頁の図表4-12で1978-2025年の年齢階級別年次表、及び同表が性別クロスを持たないことを確認した。
- 警察庁2024年年報33頁と2004年概要PDF8頁を閲覧し、年齢区分の差異と、2004年資料の年齢・性別表を確認した。

### 未実行の確認

- Web閲覧器が本文又はURLを返さなかった厚労省のZIP及び一部PDFについて、ブラウザ又は別のHTTPクライアントで実URL、拡張子、列構造を再確認すること。GUIブラウザでの公式サイトアクセスは環境のブラウザ権限により拒否されたため、回避策は試みていない。
- PDFを保存して表を抽出すること。要求により、データファイルのダウンロード・保存は実施していない。
- 1978-2003の年齢・性別クロスの公開経路を、国立国会図書館等の別の公式アーカイブを含めて調査すること。この調査の入口2系統の外であり、本ブリーフの範囲外である。

## 変更範囲、リスク、部下

- 変更したパス: `docs/NPA_SUICIDE_SOURCE_RESULT.md` のみ。
- `data/` と `scripts/` は読まず、書かず、実行していない。データファイルを保存していない。git add、git commit、git pushを実行していない。
- 未解決のリスク: 厚労省の個別URLを全件転記できていないため、同サイトの個別URL目録は未完成である。上記の未確認範囲を解消するには、Web閲覧器が返さなかったリンクを別の許可済み閲覧手段で確認する必要がある。
- 部下は立てていない。
