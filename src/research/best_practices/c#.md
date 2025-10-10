以下は、C#（.NET）プロジェクト向けにGitHub Actionsでワークフローを作る際の「実践的ベストプラクティス／推奨事項」を10項目にまとめたものです。各項目でツールの比較、状況に応じた使い分け、よくある失敗例、セキュリティ／保守性の注意点や実例（条件付きの利用方法）を含めています。

1) ワークフロー全体設計とトリガー設計
- 推奨
  - main/masterへのpush、PR作成、タグpush（リリース）、schedule（夜間の定期ビルド）をトリガーに分ける。
  - PRではビルド＋テスト＋静的解析、タグpushではバイナリ作成とデプロイ（publish）を分離する。
- ケース別
  - ライブラリ：複数ターゲットTFM（例 net6.0, net7.0）でマトリクスを回すのが有効。
  - アプリ（WPFなどWindows専用）：Windowsのみで実行するようにする（runs-on: windows-latest）。
- 注意点／失敗例
  - フォークからのPRではシークレットにアクセスできない（既定）。デプロイ権限のあるステップをPRで動かすと失敗／漏洩リスク。
  - 無駄にトリガーを広げるとCIコストが増える。

2) SDKとランナーの管理（setup）
- 推奨
  - actions/checkout@v4、actions/setup-dotnet@v3 を使い、明示的に SDK バージョンを指定（global.jsonがあればそれを尊重）。
  - matrixでOSとdotnet-versionを回す（互換性テスト）。
- 例（抜粋）
  - strategy.matrix:
      os: [ubuntu-latest, windows-latest]
      dotnet: [6.0.x, 7.0.x]
- 注意点
  - SDKバージョン指定を怠ると、ローカルとCIで動作差が出る（特にSDKのマイナー差でビルドエラーが出る）。
  - Windows専用ビルド（WPF、WinForms）はWindows runnerを指定する。

3) パッケージ管理の選択と使い分け
- 主流と特徴
  - NuGet (PackageReference + packages.lock.json)
    - 標準。推奨。依存性はcsproj/Directory.Packages.propsで管理可能。生成される packages.lock.json をコミットすると再現性が高い。
  - Paket
    - 大規模プロジェクトや複数リポジトリでの共有、トランスパレントな依存整理が得意。導入コストあり。
  - packages.config（古い方式）
    - 新規では非推奨。PackageReferenceへ移行推奨。
- 実践
  - ほとんどの場合は PackageReference を使い、packages.lock.json を有効にしてロックする（dotnet restore --use-lock-file / dotnet restore で自動）。
- CIの注意
  - プライベートフィードを使う場合は nuget.config をワークスペースに置き、認証情報は GitHub Secrets で渡す（例: dotnet nuget add source で PAT を使う、または GitHub Packages の場合は GITHUB_TOKEN を使用）。
- 失敗例
  - nuget.configを忘れるとCIが外部/privateフィードに接続できずビルド失敗。

4) ビルドツール／スクリプトの選択
- オプション
  - dotnet CLI（推奨）
    - cross-platform、標準。restore/build/test/publishが揃う。
  - MSBuild（詳細なビルド制御が必要な場合）
  - ビルドスクリプト（Cake/FAKE）
    - 複雑なリリースフローやカスタム処理がある場合に有効。軽いプロジェクトでは過剰。
- 推奨
  - 多くは dotnet CLI を使い、必要なら Directory.Build.props / targets で共通化。
- 例の流れ
  - dotnet restore → dotnet build --configuration Release → dotnet test --no-build → dotnet publish（リリース時）

5) テストツールとコードカバレッジ
- テストフレームワーク
  - xUnit（現行で人気、活発）、NUnit、MSTest（MS公式）。
  - 新規なら xUnit を第一候補に。既存プロジェクトは移行コストを考慮。
- カバレッジ
  - Coverlet（collector または msbuild パラメータ）で収集。出力を opencover 形式にして ReportGenerator でHTML化、あるいは codecov/coveralls などにアップロード。
- CIでの実践例（条件付き）
  - 小さなライブラリ：dotnet test --collect:"XPlat Code Coverage" で十分。
  - CIで詳細レポートを出す場合：dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=opencover
- 失敗例
  - テストを並列で動かしたら外部リソース（DB/ファイル同名）競合で不安定化。外部依存はスタブ／ローカルインスタンス化する。

6) キャッシュ戦略（ビルド時間短縮）
- 推奨
  - actions/cache を用いて ~/.nuget/packages（Linux/Mac）、%USERPROFILE%\.nuget\packages（Windows）をキャッシュ。
  - ただしキーは有効に設計（lockファイルや依存定義ファイルのハッシュを使う）：
    - key: nuget-${{ runner.os }}-${{ hashFiles('**/packages.lock.json', '**/*.csproj', '**/Directory.Packages.props') }}
- 注意点
  - キャッシュの不適切なキー設計は古い依存が使われる原因になる。
  - Paket利用時は .paket フォルダや paket-files をキャッシュ対象にする。
- 失敗例
  - restoreキャッシュを使っているのにlockが更新されてもキーが変わらない → 古いパッケージでビルドされて問題。

7) YML構造（推奨テンプレート）
- 推奨構造（要点）
  - workflow: name + on: [push, pull_request], permissions を最小化
  - jobs:
    - build:
      - runs-on / strategy.matrix (os, dotnet-version, tfm)
      - steps:
        - actions/checkout@v4 (fetch-depth: 0 if needed)
        - actions/setup-dotnet@v3 (with: dotnet-version)
        - キャッシュ restore（actions/cache）
        - dotnet restore
        - dotnet build --no-restore --configuration ${{ matrix.configuration }}
        - dotnet test --no-build --logger trx /p:CollectCoverage=true
        - upload test results（actions/upload-artifact）
        - 必要に応じて publish アーティファクト or release step
- 小さな例（抜粋）
  - permissions:
      contents: read
      packages: write  # publish時のみ追加にするのがベター
- 注意
  - ワークフロー冒頭で permissions を限定し、必要な権限だけ付与する（書き込み不要な場合は read のみ）。

8) セキュリティ対策
- シークレット管理
  - 全シークレットは GitHub Secrets に格納し、ワークフローから参照（secrets.MY_SECRET）。ログに出力しない。
- トークンと権限
  - GITHUB_TOKEN のスコープは最低にする。publishやパッケージ操作が必要なジョブだけ perms を拡張。
  - サードパーティActionはバージョンを固定（例 actions/checkout@v4）し、可能なら署名や公式を使う。
- フォークPR注意
  - フォークからのPRは secrets にアクセスできない（保護）。外部PRでの自動デプロイやパブリッシュは無効にするか、手動トリガーにする。
- 依存関係の脆弱性検査
  - Dependabot（自動PR）や GitHub Code Scanning、Snyk 等を導入する。
- 失敗例
  - ワークフロー内で秘密トークンを echo してしまいログに残す（取り返しがつかない）。

9) 再利用性と保守性（テンプレート化）
- 推奨
  - 共通処理（checkout、設定、キャッシュ、restore、publish）を reusable workflows / composite actions / 各種テンプレートで切り出す。
  - 複数リポジトリで同じ構成が必要な場合は Organization-level のテンプレートや shared workflow を利用。
- バージョン管理
  - 再利用ワークフローに変更を加えたら後方互換を考え、呼び出し側で必要な入力を明確化する。
- 失敗例
  - 1つの巨大ワークフローにすべて詰め込み、変更が難しくなる。結果としてCIが壊れやすくなる。

10) ログ、アーティファクト、モニタリング（運用）
- ログと成果物
  - テスト結果（TRX、JUnit）、カバレッジレポート、ビルド成果物は actions/upload-artifact で保存。失敗解析に有用。
- 失敗検知と通知
  - 通常はGitHubのPR表示で十分だが、Slack/Teams連携が必要ならステップで通知（通知にシークレットを使う場合は権限に注意）。
- 保守
  - アーティファクトの保持期間（retention-days）を用途に応じて設定。長期間の保管はコスト増。
- 典型的な失敗
  - テスト失敗時にのみログを保存するようにしていない → 成功時のベースラインが分からない。

補足：実践的なYAMLスニペット（概念的、必要なファイルがある場合のみ）
- 主要なポイントを満たす最小のCIジョブ例（概念）：
  - トリガー: push/PR
  - matrix: os、dotnet
  - steps: checkout → setup-dotnet → cache nuget → dotnet restore → dotnet build → dotnet test（collect coverage）→ upload artifacts
- 注意：上のsnippetでは実環境に合わせて nuget.config、packages.lock.json、publish用の secrets（PAT）や runner OS を調整すること。

最後に：よくある失敗のまとめ（短く）
- SDKのバージョン不整合（global.jsonを使って固定しよう）
- private feed の認証忘れ（nuget.config と secrets を用意）
- キャッシュキーの誤設計で古い依存を使う
- フォークPRでシークレットがない状況を想定しないデプロイ処理
- テストの並列実行で外部リソース競合
