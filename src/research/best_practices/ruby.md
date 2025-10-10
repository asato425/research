以下は「Rubyプロジェクト向けにGitHub Actionsでワークフローを設計・運用する際のベストプラクティス（箇条書きで10項目）」です。実践的な例・よくある失敗例・ツール比較・条件付きの利用方法などを含めています。

1) ワークフローのトリガー・権限・並行制御を明確にする
- 推奨事項：
  - on: push / pull_request / workflow_dispatch を基本に、デプロイなどは push to main や workflow_dispatch に限定する。
  - concurrency を使って同一ブランチで古いジョブをキャンセル（例: concurrency: group: ${{ github.workflow }}-${{ github.ref }} cancel-in-progress: true）。
  - permissions を最小権限化（例: permissions: contents: read など）。GITHUB_TOKEN の権限は必要最小限にする。
- よくある失敗：
  - pull_request_target を不用意に使う → マージ前の外部PRでシークレットが流出するリスク。
  - 無制限に並列実行され、無駄なコストやAPIレートリミットに到達。
- 実践例（概念）：
  - デプロイは main ブランチのみ、かつ protected environment を使って承認フローを挟む。

2) Rubyのセットアップとバージョン行列（matrix）
- 選択肢・使い分け：
  - ruby/setup-ruby アクション（推奨）：公式サポートやRubyGemsのキャッシュ統合があるため簡単。
  - asdf / rbenv / RVM：ローカル互換性や特殊要件がある場合に検討（CIでは基本的に setup-ruby が楽）。
- 推奨事項：
  - matrix でサポートする Ruby バージョンを定義（例: 2.7, 3.0, 3.2）。最低サポートと最新を含める。
  - OS（ubuntu-latest、macos-latest）を必要に応じてマトリクスに含め、ネイティブ拡張の互換性を確認。
- よくある失敗：
  - Runner の Ruby とローカル開発環境が異なり、CIでのみ発生する不具合。ローカルとCIで同じバージョンを使う。

3) 依存関係管理（Bundler中心）とキャッシュ戦略
- ツール比較：
  - Bundler（標準）：ほとんどのRubyプロジェクトで標準。Gemfile/Gemfile.lockでバージョン固定。
  - RubyGems（gem install 直接）：単純なスクリプトやCIの一時的インストールで利用。
  - vendor/cache（ベンダリング）: ネットワーク不安定な環境で有効。
- キャッシュ推奨：
  - ruby/setup-ruby の cache: 'bundler' オプションを使うか、actions/cache で vendor/bundle や ~/.bundle をキャッシュ。
  - キャッシュキーに Rubyバージョン + OS + Gemfile.lock のハッシュを含める（例: cache-key: ${{ runner.os }}-ruby-${{ matrix.ruby }}-${{ hashFiles('**/Gemfile.lock') }}）。
- よくある失敗：
  - Gemfile.lock をコミットしていない → 再現性がなくCIが異なる依存を解決する。
  - キャッシュキーが粗すぎて古いキャッシュを使い続ける（更新が反映されない）。

4) テストツールの比較と並列化（RSpec / Minitest 等）
- ツール比較：
  - RSpec：表現力が高く、DSLが豊富。成熟したマッチャーや拡張が多い。中〜大規模テストに向く。
  - Minitest：軽量でRuby標準に近く、シンプルな構成。高速で小規模プロジェクト向け。
  - 並列化ツール：parallel_tests、knapsack、Zeitwerkやtest-profの併用で並列・分割実行が可能。
- 推奨事項：
  - bundle exec rspec / bundle exec rake test を常に使う（bundle exec を忘れるとローカルと違うgemが使われる）。
  - 大規模テストは並列化（matrix単位ではなくジョブ内並列）でCI時間を短縮。ただしDBやファイル衝突に注意。
  - coverage は SimpleCov を使い、アップロードは CODECOV_TOKEN (必要な場合) を secrets に設定、ブランチ条件を付けて実行。
- よくある失敗：
  - 並列実行で同じDBやテストリソースを共有していて相互干渉。テスト用DBを個別に分けるか、Isolationを確保。

5) 静的解析・リンター・セキュリティスキャン
- 推奨ツール：
  - RuboCop（リンター）: フォーマット・静的検出。CIでfailにするか自動修正をPRで提案。
  - Brakeman（Rails専用）: セキュリティ脆弱性スキャン。
  - bundler-audit / rubysec（Gem脆弱性）：gemの既知脆弱性を検出。Dependabotと併用。
- 実践：
  - lint はテストより先に実行して早期ブロック。自動修正可能なルールは CI で auto-correct を検討し、PRで修正を送る。
  - セキュリティスキャンは nightly や定期ワークフローでも実行し、脆弱性の着目漏れを防止。
- よくある失敗：
  - bundler-audit のDB更新忘れ → スキャンが古い結果を返す。定期更新を入れる。

6) ビルド・パッケージング・リリース（gemやDocker）
- 選択肢：
  - RubyGems へ公開：rake release / gem push。公開は protect branch + manual approval 推奨。
  - Docker イメージ：アプリをコンテナ化する場合、build → push を行う。レイヤーキャッシュやマルチステージを活用。
- 推奨事項：
  - リリース用ジョブは main タグや version タグ Push でトリガー、かつ承認済み環境でのみ実行。
  - credentials は GitHub Secrets で管理。GITHUB_TOKEN はパブリッシュに不向き（明示の秘密鍵やAPIトークンを使う）。
- よくある失敗：
  - リリースジョブをPRでも動かしてしまい、誤って公開処理が走る。条件分岐を必須にする。

7) ワークフローの階層化・再利用（保守性）
- 推奨事項：
  - 共通処理（setup-ruby、cache、lintなど）は reusable workflows や composite actions に切り出して再利用。
  - 1ファイルに詰め込みすぎない。job単位で責務を分ける（lint, test, build, release）。
  - 明確なステップ名・注釈をつけ、失敗時に原因を追いやすくする。
- よくある失敗：
  - 同じステップを複数workflowにコピペ → 修正時に差分が広がり保守困難に。reusable workflowsを使う。

8) セキュリティ上の注意点（シークレット・Action固定化・依存関係）
- 推奨事項：
  - シークレットは GitHub Secrets に保存。ログ出力でシークレットが漏れないよう mask されるが、明示的に echo しない。
  - アクションはタグやコミットSHAで固定（例: actions/checkout@v4 でタグのままでも良いが、重大リスクを避けるため必要ならSHA固定）。
  - Dependabot / Renovate を使って依存の自動アップデート、かつ更新はCIで検証。
  - pull_request_target は必要時のみ使用。外部のPRにシークレットを与えない。
- よくある失敗：
  - サードパーティActionを unpinned で使い、悪意ある更新でCIを介して攻撃を受けるリスク。

9) ネットワーク・環境依存問題と回避策
- 問題と対策：
  - ネットワーク不安定や外部サービス不具合 → vendor/cache によるベンダリングや、企業内のミラーを利用。
  - ネイティブ拡張（mysql2、nokogiri など）はランナーにライブラリが不足すると fail。ubuntu-latest では apt-get で必要パッケージをインストールするステップを追加。
  - テストが外部APIに依存する場合は VCR や WebMock で切り離し、外部呼び出しは限定的に。
- よくある失敗：
  - CIだけで動かないネイティブ拡張のビルドエラーを見落とす → CIマトリクスにOSを入れて早期検出。

10) 推奨される yml 構造（最小限の例＋条件・キャッシュの取り扱い）
- 構造（概念）：
  - name, on, permissions, concurrency
  - jobs:
    - lint (runs-on, steps: checkout, setup-ruby, cache, bundle install, rubocop)
    - test (strategy.matrix ruby/os, steps: checkout, setup-ruby, cache, bundle install, run tests, upload-coverage)
    - release (needs: test, if: github.ref == 'refs/heads/main' && github.event_name == 'push', steps: deploy)
- 実践的な小さな例（概念的な抜粋）：
  - on:
      push:
        branches: [ main ]
      pull_request:
        branches: [ main ]
  - permissions:
      contents: read
  - concurrency:
      group: ${{ github.workflow }}-${{ github.ref }}
      cancel-in-progress: true
  - jobs:
      test:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            ruby: [ '2.7', '3.1' ]
        steps:
          - name: Checkout
            uses: actions/checkout@v4
            with:
              fetch-depth: 0   # git履歴が必要な場合
          - name: Setup Ruby
            uses: ruby/setup-ruby@v1
            with:
              ruby-version: ${{ matrix.ruby }}
              cache: 'bundler'   # ある場合
          - name: Install dependencies
            run: bundle config path vendor/bundle && bundle install --jobs 4 --retry 3
          - name: Run tests
            run: bundle exec rspec
          - name: Upload coverage
            if: github.event_name == 'push' && startsWith(github.ref, 'refs/heads/')
            run: bundle exec codecov  # CODECOV_TOKEN を必要とする場合は secrets に設定
- 条件付き利用の説明：
  - キャッシュは変更検出（Gemfile.lock）で更新する。ruby/setup-ruby の cache: 'bundler' か manual cache のどちらかを選択して重複させない。
  - リリースやトークンを要するアップロードは if 条件で main/tags のみに限定する。

最後に、よくある失敗例（まとめ）
- Gemfile.lock をコミットしない／ローカルとCIでバージョン不一致。
- シークレットを誤ってログに出す・pull_request_target の誤用。
- キャッシュキーの設計ミスで古い依存を使い続ける。
- 非固定化された外部Actionによるセキュリティリスク。
- 並列テストで共有リソース（DB/ファイル）に競合が生じる。

まとめ（簡潔な勧め）
- 基本は「ruby/setup-ruby + Bundler + Gemfile.lock を使う」こと。CIではテスト・lint・セキュリティスキャンを分離し、キャッシュと matrix を活用して再現性と効率を両立する。シークレット・Actionの固定化・最小権限を徹底して安全な運用を行う。
