以下は「C++プロジェクト向けにGitHub Actionsでワークフローを設計・運用する際のベストプラクティス（10項目）」です。各項目に実践例・よくある失敗・ツールの使い分け・YAML構造の推奨・セキュリティ/保守観点を含めて説明します。ツールは前提せず、使う場合の条件や代替案を明示しています。

1) ワークフロー構造とジョブ分割（推奨YAMLの骨組み）
- 推奨構造：checkout → deps install → build → unit tests → static analysis/linters → sanitizers/coverage → package/artifact upload。各フェーズを別ジョブに分け、必要なら依存関係を jobs.<job>.needs で指定。
- YAMLの基本例（骨組み）：
  - name, on: [push, pull_request], concurrency（同一ブランチの同時実行抑制）
  - jobs:
    - build: runs-on, strategy.matrix（os/compiler/build_type）
      steps: actions/checkout@v3 → cache → deps install → configure → build → upload build artifact（必要時）
    - test: needs: build（または並列で独立に実行）
    - lint/static-analysis: 独立ジョブで早い段階で失敗させる
- 理由と注意：分割すると並列化が効き、失敗箇所の特定が容易。長時間ジョブを1つにまとめるとデバッグしづらく、キャッシュ再利用の機会も減る。

2) マトリックス戦略（複数OS/コンパイラ/設定の網羅）
- マトリックスで主要組み合わせ（例：ubuntu-latest/windows-latest/macos-latest × gcc/clang/msvc × Debug/Release）を定義。exclude/includeで組合せ爆発を制御。
- 推奨：最低限 Linux+GCC、Linux+Clang、Windows+MSVC、macOS+Clang をカバー。PRでは最小セット、mainブランチではフルセットにするなど条件分け。
- よくある失敗：無条件で全マトリックスをすべてのpushに回しコストを浪費すること。strategy.matrix.fail-fast を活用。

3) 依存管理（選択肢と使い分け）
- 代表ツールの比較：
  - Conan：バイナリパッケージとバージョン管理に強い。CIでのキャッシュを活かすことで再ビルドを削減。CMakeとの統合が良好。大規模/複雑依存に向く。lockfileが利用可能で再現性向上。
  - vcpkg：Visual Studio/Windowsとの親和性が高く、CMake toolchain ファイルで簡単に組込める。Microsoft公式のポート多数。CIで同一vcpkg.jsonを使えば再現性が高い。
  - FetchContent（CMake）：簡単に埋め込めるが、依存が増えると管理が煩雑。外部プロジェクトを少数しか使わないか、ソースレベルで取り込みたい場合に有効。
  - システムパッケージ（apt/brew/choco）：軽量だがバージョンが固定されておらず再現性が低い。簡単なユーティリティ依存なら可。
- 選び方の指針：
  - マルチOSでバイナリ依存が多い → Conan
  - Windows主軸でVisual Studio互換性重視 → vcpkg
  - 単純で少数の依存 → FetchContentやサブモジュール
- CI上の注意：依存のlockfile（conan.lock、vcpkg.json + manifest mode）を使い、キャッシュキーにlockfileのハッシュを含める。apt等はなるべくバージョン固定や再現用のコンテナを使う。

4) ビルドツール／ジェネレータ（CMake中心だが選択肢の説明）
- 主流：CMake（最も一般的でIDE連携・ツールチェインが豊富）。CMakeを基準に話を進めるのが無難。
- 代替：Meson（高速なビルドと依存管理の簡潔さ）、Bazel（大規模リポジトリ向けで強いインクリメンタル）、Ninja（ジェネレータとして高速）
- CIの実践：CMakeを使う場合は -S . -B build で明示的ビルドディレクトリを作り、cmake --build build -- -j$(nproc) で並列化。Windowsでは -A x64 や Ninjaジェネレータを指定する。ビルドツールを切り替える場合はjobごとに明示的に設定。
- よくある失敗：cmake configureとbuildを同一ディレクトリで行わない、Visual Studioのジェネレータを指定せず期待と違う成果物が出る、Ninjaを使わずに遅いMSBuildで無駄に時間をかける。

5) テスト（フレームワーク・並列化・カバレッジ）
- フレームワーク比較：
  - GoogleTest：機能豊富で慣例的。フィクスチャやパラメタライズドテストが使える。
  - Catch2：ヘッダオンリーで導入が簡単。小～中規模に向く。
  - doctest：非常に軽量で高速。
- CIでの実践：
  - ctest --output-on-failure を用いて出力を得る。JUnitやXML出力を有効にすると GitHub Actions のテストレポート（actions/upload-artifact or junit-report）に統合可能。
  - 並列実行：ctest -j を用いる。大規模テストは分割ジョブにして PR ではスモークテスト、mainでフルテストにすること。
  - カバレッジ：GCC→gcov/lcov、Clang→llvm-cov。出力を lcov/ cobertura に変換し codecov/coveralls にアップロード（APIトークン不要なサービスやトークンの扱いに注意）。
- よくある失敗：テストの実行結果をアーティファクトやレポートに残さない、長いテストをPRで毎回回してレビュー待ちを遅らせる。

6) 静的解析・フォーマット・サニタイザ（品質ゲート）
- ツール例：clang-tidy, cppcheck, clang-format, include-what-you-use（IWYU）。ASan/UBSan/TSanはランタイム検出に有効。
- 実行方法：
  - 早期にlintジョブを回す。clang-formatはPR内の差分だけチェックして自動修正するアクションを用意すると良い。
  - サニタイザは専用のDebugビルド（最適化OFF、-fsanitize=address,undefined など）で実行。CIでは別ジョブで限定的に回すのが現実的（ランタイムとメモリの制約）。
- 注意：clang-tidyのチェックは閾値やベースラインを決めないと既存コードで大量の警告が発生する。段階的に導入する（まず重大度の高いチェックだけ）。

7) キャッシュとアーティファクト（効率化とデバッグ）
- キャッシュ対象：ビルド出力（CMakeの外部ビルドキャッシュは注意）、依存マネージャーのキャッシュ（Conan/vcpkg/aptのパッケージ）、CMakeのCMakeFilesは除外して確実に再生成できるようにする。
- キャッシュキー例：platform-compiler-<hash of lockfile or manifest>-cmake-libs-<version>。lockfileのハッシュをキーに含めることで依存変更時に自動無効化。
- アーティファクト：ビルド成果物、テストログ、カバレッジデータ、静的解析レポートは必ず upload-artifact で保存。失敗時のデバッグに必須。
- 注意点：cacheはサイズ制限があるため無意味に大きくしない。CIキャッシュの壊れによるビルド不整合に備え、キャッシュ復元失敗時にフルビルドを行えるようにする。

8) セキュリティと権限管理
- 最小権限：workflow-levelで permissions を明示し、GITHUB_TOKEN の権限は必要最小限にする。外部サービスのトークンは GitHub Secrets に格納。
- fork PR の扱い：pull_request と pull_request_target の違いを理解する。pull_request_target は base のコンテキストで実行されるため secrets へアクセスする可能性がある。外部コントリビュータからのPRでは secrets を使わないか明確に制限する。
- サードパーティActionの取り扱い：actions/* 以外のアクションはバージョンタグ（@v1）で固定し、信頼性の低いアクションは透過的に確認する。可能なら内部で持つ共通アクションを使う。
- self-hosted runner：便利だがランナーにアクセスできるユーザーが増えると危険。隔離・ログ監査・承認フローを導入する。コンテナを利用して実行環境を限定するのも有効。

9) 保守性（再利用・テスト・レビュー）
- 再利用：共通の処理は reusable workflows や composite actions に切り出し、複数リポジトリで使える形にする。バージョン管理して互換性を担保。
- ドキュメント：ワークフローの目的・失敗時の確認ポイント・キャッシュのキー定義・依存の更新手順をREADMEに記載する。新しいメンバーがすぐ理解できると保守負荷が下がる。
- バージョン固定：GitHub Action やベースイメージはタグ固定（例 actions/checkout@v3）。"@main" や無タグは避け、重大な変更でCIが壊れるリスクを防ぐ。
- テスト：ワークフロー自体の変更は小さくしてプルリクで検証。重大変更はトグル（feature flags）や段階的ロールアウトで適用。

10) よくある失敗例と回避策（現場の教訓）
- 失敗：PRでコンパイル済バイナリや秘密情報をアーティファクトに残してしまう → 対策：artifactの内容を監査、シークレットのマスキング、アーティファクトのアクセス制御。
- 失敗：pull_request_target を安易に使い secrets を参照 → 対策：外部PRでは secrets に依存する処理を行わない、必要ならmaintainerが手動でワークフローをトリガー。
- 失敗：すべてのチェックを全PRで回してCI枯渇 → 対策：PRはクイックチェック（lint+スモークテスト）、mainブランチでフルチェック。strategy.matrix の条件分け。
- 失敗：依存やツールのバージョンを固定しておらず再現性がない → 対策：lockfile、toolchain file、コンテナイメージ、runner イメージの明示的指定。
- 失敗：サニタイザ／UB検査を常にフルで回してジョブ時間が伸びる → 対策：パイプラインを分割し、PRでは軽いチェック、nightlyやmainビルドでフル検査。

補足：実践的なコマンド例（CMake を使うケース）
- configure（再現性を担保）：
  - cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=/path/to/vcpkg.cmake（vcpkg使用時）
  - cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug -G Ninja
- build：
  - cmake --build build -- -j$(nproc)
- test：
  - ctest --test-dir build --output-on-failure -j$(nproc)
- cache key 例：
  - key: ${{ runner.os }}-conan-${{ hashFiles('conan.lock') }}-cmake-${{ env.CMAKE_VERSION }}

まとめ（選択指針）
- 小～中規模：CMake + FetchContent/Catch2、軽いCI構成（速いフィードバック重視）
- マルチOS/大規模＆サードパーティ多数：CMake + Conan（またはvcpkg） + GoogleTest、厳格なlockfile・キャッシュ戦略
- Windows重視：vcpkg + MSVC を第一候補に
- 高速＆複雑なモノレポ：Bazel や専用のインクリメンタルビルド基盤を検討
