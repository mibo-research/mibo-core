# Core v2 波の原記録監査

`runtime/audit-core-v2-wave.py` は、既存の原記録を読み取り、本文の評価をせずに技術的な記録状態を調べる。ネットワーク通信、API要求、再収集、封印、権限変更は行わない。Python標準ライブラリだけを使う。

## 入力と実行

- baseline manifest は、その波の全4系統・全予定枠を含む初回要求のCSVとする。W01/W04/W07/W10は1,120枠、通常波は960枠。実行可能だった系統だけを分母にしない。
- version別に、`version`, `raw_root`, `manifest`, `protocol`, `freeze`, `lineages` を指定する。`lineages` は当該実行版に認めた系統の明示的な一覧であり、実行記録から推定しない。
- version別manifestも全予定枠を保存しているものを使う。namespaceに含める系統は `lineages` で限定する。
- 入力JSON、原記録、出力は私有研究保存領域に置く。公開リポジトリには入れない。

私有JSONの例（パスは説明用）：

```json
[
  {
    "version": "2.0.2",
    "raw_root": "/srv/mibo-data/v2.0.2/JP01/MIBO2-W01",
    "manifest": "/srv/mibo-private/inputs/W01-v2.0.2.csv",
    "protocol": "/srv/mibo-private/inputs/core-v2.0.2.json",
    "freeze": "/srv/mibo-private/inputs/freeze-v2.0.2.json",
    "lineages": ["MIBO-SL-001", "MIBO-SL-002", "MIBO-SL-004"]
  },
  {
    "version": "2.0.4",
    "raw_root": "/srv/mibo-data/v2.0.4/JP01/MIBO2-W01",
    "manifest": "/srv/mibo-private/inputs/W01-v2.0.4.csv",
    "protocol": "/srv/mibo-private/inputs/core-v2.0.4.json",
    "freeze": "/srv/mibo-private/inputs/freeze-v2.0.4.json",
    "lineages": ["MIBO-SL-003"]
  }
]
```

```sh
python -B runtime/audit-core-v2-wave.py \
  --wave MIBO2-W01 \
  --baseline-manifest /srv/mibo-private/inputs/W01-all-planned.csv \
  --namespace-spec /srv/mibo-private/inputs/W01-audit-inputs.json \
  --output-dir /srv/mibo-private/W01-audit-20261010
```

W02には `--wave MIBO2-W02` と対応する凍結入力・原記録を使う。出力先の親ディレクトリは事前に作成し、出力ディレクトリ自体は存在しないものを指定する。原記録の内部と公開ソース内には出力できない。出力ディレクトリは0700、ファイルは0600で新規作成し、既存結果を上書きしない。

## 出力の意味

`AUDIT_REPORT.json` と `OBSERVATION_STATUS.csv` を作成する。標準出力は集計数だけで、回答、要求本文、APIキー、エラーメッセージ、応答ヘッダー、設定内容、私有入力パスを出さない。

dispatch記録は現行の `dispatched_at_utc` と旧形式の `dispatch_at_utc` の両方に対応する。どちらも送信前のローカルな実行意図の時刻として扱い、provider到達の証明にはしない。

| 項目 | 意味 |
|---|---|
| `planned` | baselineにある全予定初回要求数 |
| `submitted` | HTTP応答を含む原記録から確認できた送信枠数の下限。再試行を重複計上しない |
| `verified_capture` | 初回IDとの対応、原記録ハッシュ、構造metadata、HTTP 2xx、窓内の要求開始、開始から完了への時系列、再試行規則が確認できた保存枠 |
| `failed` | 技術失敗の確定記録があり、確認可能なcaptureがない枠。送信確認の有無とは別 |
| `window_expired` | `window_expired_before_attempt` の記録がある枠。送信として数えない |
| `incomplete_write` | metadataのないraw、rawを欠くmetadata等がある枠 |
| `evidence_missing` | dispatch意図だけ、ハッシュ・識別子・時刻・再試行の不整合、重複capture等がある枠 |
| `unsubmitted_unknown` | 確定記録がない枠。未送信と断定しない |

各予定枠の状態は上表の6状態のいずれかにまとめる。`submitted` と `dispatch_intent_logical_slots` はその状態とは別の指標であり、足し合わせない。dispatch記録はアダプター呼出前の意図であり、サーバー受信の証明ではない。旧 `first-dispatch-*` 記録は系統の初回のみなので、各枠の送信数に拡張しない。

`technical_capture_candidate_n_ge_8` は、実行版・profile hash・モデル識別値hash・系統・質問・言語・窓ごとの、技術的capture候補数が8以上という意味である。回答拒否・非回答等の内容分類、有効性、独立性、比較可能性の最終判断は未実施であり、この数を「解析可能な有効セル数」と書かない。

同じlogical初回IDが異なる実行版の予定にある場合、`variant_count`、profile・model・protocol・freezeのhashと窓を残す。両版に実記録がある場合は異版重複を報告し、同一IDの複数captureを黙って統合しない。W01のWAとW02のSTDは窓の設計が異なるので、WBを除くだけで波間比較が成立するわけではない。

窓内に開始した要求の応答が窓の終了後に完了した場合、その実時刻と `capture_completed_after_registered_window_close` を `review_notes` に記録する。これは新たな科学的除外規則や最終的な解析適格性の判断ではない。技術候補は、登録窓内の開始と開始≦完了、HTTP 2xx、構造・ハッシュの整合等によって数える。

監査の前後で入力ファイルの一覧・サイズ・更新時刻・inodeを比較し、途中の変更を検出した場合は報告を作成せず中断する。この変更検知は、封印一覧のハッシュ検証や独立バックアップの復元試験の代わりにはならない。

metadataとrawのSHA-256は常に確認する。`SHA256SUMS.txt` がある場合は封印一覧への対応と一致も確認し、封印全体の異常を別記する。封印一覧がない場合は `seal_present=false` であり、ローカルのmetadata/raw一致だけでは外部由来の真正性や復元成功まで証明しない。スナップショットのREADY表示、封印時刻、実際の応答時刻も同一視しない。

## 検証範囲

合成データで、全予定分母、混在版の系統スコープ、異版重複、profile差、再試行の時刻・適格性、欠損・重複・ハッシュ・封印・登録窓、秘密非出力、入力不変更、排他的私有出力を検証する。

```sh
python -m unittest discover -s automation/tests -p 'test_core_v2_wave_audit.py' -v
```

W01の原因特定には実際の私有原記録・失敗記録等が必要である。合成テストの合格は、その原記録の監査完了やGoogleの277枠の原因解明を意味しない。波間の改善だけから修正の因果効果を断定しない。
