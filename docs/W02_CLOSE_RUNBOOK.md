# W02以降の終了・封印手順

この手順は `runtime/close-core-v2-wave.py` のためのものです。W01専用の
`close-core-v2-w01.py` は変更せず、W02には使いません。この文書も終了設定も、
実行承認や完了証明を自動生成しません。原記録・認証情報・私有承認書・以下の
設定ファイルは公開リポジトリに保存しません。

## 1. 登録どおりに終了する

W02の登録期間は2026年11月3日9時から11月5日9時まで（日本時間）です。
通常波の予定数は960枠、各系統240枠です。終了ツールは日付と件数を固定値で
判断せず、各namespaceの登録済みprotocolと全manifestから読み取ります。
較正波では1120枠、各系統280枠を検証します。混在する版も元のnamespaceの
まま保存し、予定枠の系統割当は重複なく四系統すべてを指定します。

終了後、担当者は対象systemdサービスを停止・無効化し、実際に読み込まれる
EnvironmentFileの `MIBO_CORE_V2_EXECUTION` を `DISABLED` にしてください。
終了ツール自体はサービス停止、環境書換え、API呼出しを行いません。
Unitのdrop-inがある場合は自動処理を中断します。読み込むファイルと起動引数が
設定どおりであること、子プロセスが残らないことを事前に確認します。

## 2. 私有の終了設定を確認する

形式は次のとおりです。例示は四系統を同じ版に割り当てる形ですが、実際には
当該波で事前に承認した版と系統だけを指定します。v2.0.2の三系統とv2.0.4の
Googleを混在させる場合は、別々のnamespace要素を指定します。終了時に版や
系統を選び直すことはできません。

```json
{
  "schema_version": "core-v2-wave-close-1",
  "wave_id": "MIBO2-W02",
  "site_id": "JP01",
  "data_root": "/srv/mibo-data",
  "backup_parent": "/srv/mibo-private",
  "namespaces": [{
    "version": "2.0.1",
    "lineages": ["MIBO-SL-001", "MIBO-SL-002", "MIBO-SL-003", "MIBO-SL-004"],
    "protocol": "/private/W02/protocol.json",
    "manifest": "/private/W02/manifest.csv",
    "freeze": "/private/W02/freeze.json",
    "authorization": "/private/W02/authorization.json",
    "unit": "reviewed-W02-collector.service",
    "unit_file": "/etc/systemd/system/reviewed-W02-collector.service",
    "environment_file": "/private/W02/collector.env",
    "expected_hashes": {
      "protocol": "REPLACE_WITH_REVIEWED_SHA256",
      "manifest": "REPLACE_WITH_REVIEWED_SHA256",
      "freeze": "REPLACE_WITH_REVIEWED_SHA256",
      "authorization": "REPLACE_WITH_REVIEWED_SHA256"
    }
  }]
}
```

四つのハッシュは実行時の承認対象と照合します。相対パスは設定ファイルの
所在を基準に解決されます。`raw_root` は省略可能ですが、指定する場合は
`data_root/v<version>/<site_id>/<wave_id>/` と完全一致が必要です。
署名対象は原記録の保存と欠測を保持した終了です。応答内容の適格性や、
完全な四系統解析が可能であることへの署名ではありません。

## 3. 読み取り監査と終了確認を併用する

終了後、オフライン監査ツール `automation/core_v2_wave_audit.py` を併用し、
`AUDIT_REPORT.json` と論理初回IDごとの `OBSERVATION_STATUS.csv` を確認します。
監査用namespace入力は終了設定から `version`、`manifest`、`protocol`、
`freeze`、`lineages` を取り出し、上記の `raw_root` を加えたものです。
監査ツールの起動引数は同ツールの `--help` を確認してください。

保存数、技術失敗数、送信前期限切れ、系統停止後の欠測を区別します。
`dispatch/*.json` は送信意図の記録であり、提供者の受信証明ではありません。
dispatchがあるのにcapture/failureがない要求は、送信後未保存の可能性があるため
終了ツールも中断します。原記録がない場合は未実施として扱い、完了用の空の
ディレクトリを作りません。

読取専用の終了確認（登録期間終了後のみ）:

```bash
python3 runtime/close-core-v2-wave.py --config /private/W02/close.json
```

この段階ではファイルを変更しません。全manifestの決定論的再生成一致、
私有承認、入力ハッシュ、raw/metadataのリンクとハッシュ、再試行ID、
登録時間窓、未完dispatch、サービス停止、sentinel無効を検証します。
応答本文やAPIキーは画面に出しません。封印済み・終了途中の原記録は中断し、
再実行で書き換えません。

## 4. 担当者が署名し、封印する

担当者が集計・欠測・監査結果を確認してから実行します。

```bash
sudo python3 runtime/close-core-v2-wave.py --config /private/W02/close.json --execute
```

実端末で担当者氏名を入力する必要があります。無入力なら中断します。
氏名をコマンド引数や設定ファイルから自動補完する経路はありません。
確認中に証拠が変わった場合も、書込み前に中断します。

成功時は各namespaceにclosure集計・入力の私有コピー・署名記録・
`SHA256SUMS.txt` を追加し、root所有・ディレクトリ0550・ファイル0440で
封印します。同VMのtar.gzについて全内容のハッシュ一致を検証します。
途中エラーでclosureが残った場合はその状態を保存し、再実行せず、担当者が
別の事故記録で原因と復旧方法を決定してください。

## 5. 独立保存と復元を別途確認する

同VMのアーカイブ検証は独立バックアップの確認ではありません。
終了記録は `independent_backup_at_signoff=not_verified`、レシートは
`same_VM_local_export_only` を明記します。VM外の保存先、保存先ハッシュ、
復元先での照合結果を別のバックアップ確認記録に残してください。
後日の確認のために封印済みの終了記録を書き換えてはいけません。

公開するのは承認済みの集計と証拠の識別値のみです。Googleの取得が改善しても、
単純なW01/W02差だけでは修正の因果効果を証明しません。通常波と較正波の
比較は共通する条件・適格性・時刻・版を確認したうえで報告します。
