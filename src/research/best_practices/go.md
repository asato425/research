以下は「GoプロジェクトをGitHub Actionsで運用する際のベストプラクティス／推奨事項」を、実践的な例や注意点を織り交ぜて10項目にまとめたものです。ツールの使い分けや条件付きの利用方法も明記しています。

1) 全体構成・ワークフロー分割（推奨yml構造）
- 推奨構成：CI（PR/Push検証） / Release（タグ付けに反応） / Scheduled（依存更新や定期チェック） / Reusable workflows（共通処理を呼び出す）
- 例（簡略）：on: [pull_request, push]; jobs: lint, test, build; Releaseはon: push: tags: ['v*.*.*']。
- 理由：PRでの高速フィードバックと、署名付きリリース等の重い処理は分離して失敗耐性・可読性を高める。
- 注意：workflow_callで再利用可能にすると複数リポジトリでメンテが楽になる。

2) 環境セットアップの安定化（actions/setup-go等の扱い）
- 常にactions/setup-go（または同等の確実なaction）を使い、Goバージョンは明示的に指定する（例: 1.20.x）。
- バージョン指定はメジャー固定+minor可変（例: 1.20.x）か、より厳格に固定するかはチームポリシーで決定。重要なCIでは完全固定も検討。
- 注意点：actionはメジャーバージョンを明示（例: actions/setup-go@v4）して、重大な互換性破壊を受けにくくする。可能ならcommit SHA固定も検討。

3) モジュール／依存管理（go modulesが標準、vendoringの条件付き利用）
- 標準はGo Modules（go.mod/go.sum）。常にgo.mod / go.sumをコミットし、CIでの検証（go mod verify / go mod tidy チェック）を行う。
- キャッシュ：actions/cacheで $GOMODCACHE（通常$GOPATH/pkg/mod）をキャッシュ。キー例: cache-go-mod-${{ hashFiles('**/go.sum') }}。
- Vendoringを使う場合：オフライン環境や厳格な再現性が必要なら vendor/ をコミットしてCIで GOFLAGS=-mod=vendor を使う。そうでなければ不要。
- セキュリティ：GOSUMDB（sum.golang.org）とGOPROXYを適切に使う。企業で内部プロキシを使う場合は明示的に設定し、外部への漏洩を防ぐ。

4) ビルド／リリースツールの選定（go build vs goreleaser 等）
- 単純なビルド・CIバイナリ確認：標準の go build で十分。クロスコンパイルは環境でのサポートを確認（CGOの有無、race detectorが利用不可など）。
- リリースパッケージ・multi-archビルド・署名・アップロード：goreleaser を推奨（設定ファイル .goreleaser.yml が必要）。goreleaserはGH Releases連携やアーカイブ生成を自動化する。
- Make / Task / Mage の選択：
  - Make：シンプルでCIから呼び出しやすいが、依存の調整やWindows互換性に注意。
  - Task（go-task/task）：YAMLベースで可読性あり。軽量。
  - Mage：Goでタスクを書くためGoスキルが活かせるが学習コストあり。
- 推奨：自動化が複雑化するなら goreleaser + Make/Task を使い、CIは「lint → test → build（go build）」→「goreleaser（release workflow）」と分離する。

5) テストとテスト出力の扱い（go test, gotestsum, coverage）
- 実行：go test ./... -v。CIでは -race を使うことが有用（ただし交差コンパイルでは利用不可／遅い）。
- 出力整形：gotestsum や go-junit-report を使うとテスト結果をJUnit形式でアップロードしやすい（GitHubのテスト注釈やレポート連携に便利）。
- カバレッジ：go test -coverprofile=coverage.out を生成し、coverallsやcodecovに送る。CIでは coverage 失敗条件を設けるかはチーム方針で。
- テスト分割：ユニット・インテグレーション・エンドツーエンドを分け、PRではユニットを必須、フル統合は別ジョブor夜間にする。

6) 静的解析・リンティング（golangci-lint, staticcheck など）
- golangci-lint は複数ツールを統合する便利ツール（staticcheck, govet, gofmt/ goimports, ineffassign 等）。CIで必須にすることを推奨。
- 設定はプロジェクトごとに .golangci.yml を用意し、CIでキャッシュや並列実行を活用。false positive は設定で抑制する。
- 使い分け：軽量・高速チェックのみなら staticcheck + go vet、総合チェックとルール管理が欲しいなら golangci-lint。

7) キャッシュと高速化（go mod cache, build cache, matrix）
- キャッシュ戦略：go.sumハッシュをキーに actions/cache で依存キャッシュ。ビルドキャッシュ（GOCACHE）もキャッシュ可能。
- Matrix活用：GoのバージョンやOS（linux/windows/macos）で matrix を用意して並列でテスト。不要な組み合わせは除外してコスト削減。
- 注意：キャッシュキー設計に注意（破棄や更新タイミング）。キャッシュの腐敗で古い依存が残ることがあるので、キャッシュミスやキー変更を意識した運用を。

8) セキュリティ・権限管理（GITHUB_TOKEN, OIDC, secrets）
- 最小権限：workflowで permissions を明示して GITHUB_TOKEN のスコープを制限（例: contents: read など）。Release系だけ write 権限を付与。
- シークレット：外部クラウド認証はGitHub OIDCを使い短期トークンで発行する方法を推奨（長期トークンをSecretsに保存しない）。
- 依存脆弱性：govulncheck（Go 1.18+）やOSVスキャンをCIに組み込む、Dependabotやrenovateで依存更新を自動化。
- ワークフローの信頼性：外部アクションは可能ならSHA固定、サードパーティのアクションは最小限に。PRビルドでSecretsを渡さない設定（pull_requestからのfork PRには機密情報を渡さない）を徹底。

9) よくある失敗例とその対策
- 失敗：go.sumをコミットしていない → 解決：必ずコミット、CIで差分チェック（git status --porcelainで差分があるとfail）。
- 失敗：actionsを無固定で使用してbreaking changeを受ける → 解決：バージョン固定（major）、重要ならSHA固定。
- 失敗：大きなリリース処理をPRで実行 → 解決：Releaseはタグ/branch許可のみに限定、mainでのみ実行。
- 失敗：Secrects漏洩（fork PRにSecretsを渡す） → 解決：workflowの if 条件で github.event.pull_request.head.repo.full_name == github.repository を確認する／permissionsで制御。
- 失敗：Race detectorを無条件でmatrixに入れて遅い／失敗する → 解決：raceは限定的に実行（例: Linuxのみ、あるいは nightly ジョブ）。

10) 保守性・可観測性のベストプラクティス
- ログとアーティファクト：テストログやカバレッジ結果、ビルド成果物は artifacts として保存。失敗解析が容易になる。
- 再利用性：共通のセットアップは reusable workflow や composite action に切り出す（複数リポジトリで同一処理を使う場合）。
- ドキュメント化：READMEまたは .github/workflows/README にワークフローの目的・トリガー・必要なSecretsを記載。
- バージョンポリシー：Goのサポートするバージョンを明示し、古いバージョンのサポート期間を決める。CIでは matrix でサポート範囲を網羅。
- メンテナンス負荷低減：Workflow ファイルは小さく、1ファイルに複数の大機能を詰め込まない。変更履歴はPRテンプレートにてCI影響の有無を明示。

参考になる実践的なステップ例（CIジョブの骨子、擬似記述）
- steps:
  - uses: actions/checkout@v3
  - uses: actions/setup-go@v4 with: go-version: 1.20.x
  - name: Cache modules → key: cache-go-mod-${{ hashFiles('**/go.sum') }}
  - name: go mod download
  - name: golangci-lint run (or staticcheck)
  - name: go test ./... -race -coverprofile=coverage.out
  - name: upload coverage artifact

ツールごとの使い分け（要約）
- 依存管理：常に Go Modules（go.mod）。vendoringはオフライン/再現性重視時に限定。
- ビルド：単純ビルドは go build。正式リリース（複数アーキ/プラットフォーム、アーカイブ、署名）は goreleaser。
- タスクランナー：Make（伝統的・軽量）、Task（明瞭なYAML）、Mage（Goで書けてテスト可能）。
- テスト出力：gotestsum（人間とCI双方に読みやすい）、go test標準もOK。
- 静的解析：golangci-lint（総合） vs staticcheck（軽量・深い指摘）。
