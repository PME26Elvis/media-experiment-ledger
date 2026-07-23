import { createI18n } from 'vue-i18n'

const en = {
  app: { name: 'Media Experiment Ledger Studio', tagline: 'Atlas · Detection · Media Automation' },
  nav: {
    workspace: 'Workspace', import: 'Media Import', samples: 'Sample Corpora', automation: 'Automation',
    atlas: 'Atlas Studio', detection: 'Detection Studio', jobs: 'Job Center', models: 'Models',
    reports: 'Reports', integrations: 'Integrations', updates: 'Updates', diagnostics: 'Support & Privacy', settings: 'Settings',
  },
  common: {
    browse: 'Browse', reveal: 'Open folder', run: 'Run', save: 'Save', loading: 'Loading…',
    empty: 'Nothing here yet', retry: 'Retry', menu: 'Open navigation', compact: 'Compact', expand: 'Expand navigation',
  },
  integrations: {
    eyebrow: 'Scheduling, synchronization & publishing', title: 'Integration Center',
    subtitle: 'Connect local projects to per-user OS scheduling, conflict-safe folders, immutable GitHub Releases and constrained WASM adapters.',
    scheduler: 'OS scheduler', schedulerTitle: 'Scheduled Studio jobs', name: 'Schedule name', enabled: 'Enabled', cadence: 'Cadence',
    intervalHours: 'Interval hours', weekdays: 'Weekdays', jobKind: 'Job kind', jobTitle: 'Job title', installSchedule: 'Install schedule',
    noSchedules: 'No schedules are installed.', scheduleSaved: 'Schedule installed.', scheduleQueued: 'Scheduled job queued.',
    sync: 'Cloud folder sync', syncTitle: 'Conflict-safe project synchronization', projectRoot: 'Local project root', syncRoot: 'Cloud-synced folder',
    dryRun: 'Preview without changing files', runSync: 'Synchronize', syncComplete: 'Synchronization completed.',
    githubTitle: 'Immutable GitHub Release publisher', releaseName: 'Release name', releaseBody: 'Release notes',
    assetPaths: 'Asset paths, one per line', credential: 'Unlocked GitHub credential',
    immutableWarning: 'Existing tags are never modified. A private draft is created first and is published only after every asset upload succeeds.',
    publish: 'Create Release', releaseCreated: 'GitHub Release created.',
    wasmTitle: 'Sandboxed WASM postprocessor', modulePath: 'WASM module',
    wasmPolicy: 'Modules must be SHA-pinned, import-free and use the JSON alloc/postprocess ABI. Execution is isolated in a time- and memory-bounded worker.',
    runWasm: 'Run postprocessor', wasmComplete: 'WASM postprocessor completed.',
  },
}

const zhTW = {
  app: { name: 'Media Experiment Ledger Studio', tagline: 'Atlas · Detection · Media Automation' },
  nav: {
    workspace: '工作區', import: '媒體匯入', samples: '範例資料集', automation: '自動化',
    atlas: 'Atlas Studio', detection: 'Detection Studio', jobs: '工作中心', models: '模型管理',
    reports: '報告庫', integrations: '整合中心', updates: '更新中心', diagnostics: '支援與隱私', settings: '設定',
  },
  common: {
    browse: '瀏覽', reveal: '打開資料夾', run: '開始執行', save: '儲存', loading: '載入中…',
    empty: '目前沒有內容', retry: '重試', menu: '開啟導覽', compact: '精簡側欄', expand: '展開側欄',
  },
  integrations: {
    eyebrow: '排程、同步與發布', title: '整合中心',
    subtitle: '將本機專案連接至使用者層級的系統排程、衝突安全資料夾、不可變 GitHub Release，以及受限 WASM adapter。',
    scheduler: '系統排程', schedulerTitle: 'Studio 排程工作', name: '排程名稱', enabled: '啟用', cadence: '週期',
    intervalHours: '間隔小時', weekdays: '星期', jobKind: '工作類型', jobTitle: '工作標題', installSchedule: '安裝排程',
    noSchedules: '尚未安裝排程。', scheduleSaved: '排程已安裝。', scheduleQueued: '排程工作已加入佇列。',
    sync: '雲端資料夾同步', syncTitle: '衝突安全的專案同步', projectRoot: '本機專案根目錄', syncRoot: '雲端同步資料夾',
    dryRun: '只預覽，不變更檔案', runSync: '開始同步', syncComplete: '同步已完成。',
    githubTitle: '不可變 GitHub Release 發布器', releaseName: 'Release 名稱', releaseBody: 'Release 說明',
    assetPaths: '資產路徑，每行一個', credential: '已解鎖的 GitHub 憑證',
    immutableWarning: '既有 tag 永遠不會被修改。系統會先建立私人草稿，所有資產成功上傳後才依設定公開。',
    publish: '建立 Release', releaseCreated: 'GitHub Release 已建立。',
    wasmTitle: '沙盒化 WASM 後處理器', modulePath: 'WASM 模組',
    wasmPolicy: '模組必須鎖定 SHA、不得匯入 host API，並使用 JSON alloc/postprocess ABI；執行受 worker、逾時與記憶體上限隔離。',
    runWasm: '執行後處理器', wasmComplete: 'WASM 後處理已完成。',
  },
}

const zhCN = {
  app: zhTW.app,
  nav: { ...zhTW.nav, workspace: '工作区', import: '媒体导入', samples: '示例数据集', jobs: '任务中心', models: '模型管理', reports: '报告库', integrations: '集成中心', diagnostics: '支持与隐私', settings: '设置' },
  common: { ...zhTW.common, reveal: '打开文件夹', loading: '加载中…', empty: '当前没有内容', menu: '打开导航', compact: '精简侧栏', expand: '展开侧栏' },
  integrations: {
    ...zhTW.integrations,
    eyebrow: '计划、同步与发布', title: '集成中心', subtitle: '将本地项目连接到用户级系统计划、冲突安全文件夹、不可变 GitHub Release 和受限 WASM 适配器。',
    scheduler: '系统计划', schedulerTitle: 'Studio 计划任务', name: '计划名称', enabled: '启用', cadence: '周期', intervalHours: '间隔小时', weekdays: '星期',
    jobKind: '任务类型', jobTitle: '任务标题', installSchedule: '安装计划', noSchedules: '尚未安装计划。', scheduleSaved: '计划已安装。', scheduleQueued: '计划任务已加入队列。',
    sync: '云文件夹同步', syncTitle: '冲突安全的项目同步', projectRoot: '本地项目根目录', syncRoot: '云同步文件夹', dryRun: '仅预览，不更改文件', runSync: '开始同步', syncComplete: '同步已完成。',
    githubTitle: '不可变 GitHub Release 发布器', releaseName: 'Release 名称', releaseBody: 'Release 说明', assetPaths: '资产路径，每行一个', credential: '已解锁的 GitHub 凭证',
    immutableWarning: '现有 tag 永远不会被修改。系统先建立私有草稿，所有资产成功上传后才按设置发布。', publish: '创建 Release', releaseCreated: 'GitHub Release 已创建。',
    wasmTitle: '沙盒化 WASM 后处理器', modulePath: 'WASM 模块', wasmPolicy: '模块必须锁定 SHA、禁止导入 host API，并使用 JSON alloc/postprocess ABI；执行受 worker、超时和内存上限隔离。', runWasm: '运行后处理器', wasmComplete: 'WASM 后处理已完成。',
  },
}

const ja = {
  app: en.app,
  nav: { workspace: 'ワークスペース', import: 'メディア取込', samples: 'サンプルコーパス', automation: '自動化', atlas: 'Atlas Studio', detection: 'Detection Studio', jobs: 'ジョブ', models: 'モデル', reports: 'レポート', integrations: '連携センター', updates: '更新', diagnostics: 'サポートとプライバシー', settings: '設定' },
  common: { ...en.common, browse: '参照', reveal: 'フォルダーを開く', run: '実行', save: '保存', loading: '読み込み中…', empty: 'まだ項目がありません', retry: '再試行', menu: 'ナビゲーションを開く', compact: 'コンパクト表示', expand: 'ナビゲーションを展開' },
  integrations: {
    eyebrow: 'スケジュール・同期・公開', title: '連携センター', subtitle: 'ローカルプロジェクトをユーザー単位のOSスケジュール、競合安全なフォルダー、変更禁止のGitHub Release、制限付きWASMアダプターへ接続します。',
    scheduler: 'OSスケジューラー', schedulerTitle: 'Studioの予約ジョブ', name: 'スケジュール名', enabled: '有効', cadence: '周期', intervalHours: '間隔（時間）', weekdays: '曜日', jobKind: 'ジョブ種別', jobTitle: 'ジョブ名', installSchedule: 'スケジュールを登録', noSchedules: '登録済みスケジュールはありません。', scheduleSaved: 'スケジュールを登録しました。', scheduleQueued: 'ジョブをキューに追加しました。',
    sync: 'クラウドフォルダー同期', syncTitle: '競合安全なプロジェクト同期', projectRoot: 'ローカルプロジェクト', syncRoot: 'クラウド同期フォルダー', dryRun: '変更せずにプレビュー', runSync: '同期', syncComplete: '同期が完了しました。',
    githubTitle: '変更禁止のGitHub Release公開', releaseName: 'Release名', releaseBody: 'Releaseノート', assetPaths: 'アセットのパス（1行1件）', credential: '解除済みGitHub資格情報', immutableWarning: '既存タグは変更しません。最初に非公開ドラフトを作成し、全アセットのアップロード成功後のみ公開します。', publish: 'Releaseを作成', releaseCreated: 'GitHub Releaseを作成しました。',
    wasmTitle: 'サンドボックスWASM後処理', modulePath: 'WASMモジュール', wasmPolicy: 'SHA固定・import禁止・JSON alloc/postprocess ABIが必須です。ワーカー、タイムアウト、メモリ上限で隔離します。', runWasm: '後処理を実行', wasmComplete: 'WASM後処理が完了しました。',
  },
}

const ko = {
  app: en.app,
  nav: { workspace: '작업 공간', import: '미디어 가져오기', samples: '샘플 코퍼스', automation: '자동화', atlas: 'Atlas Studio', detection: 'Detection Studio', jobs: '작업 센터', models: '모델', reports: '보고서', integrations: '통합 센터', updates: '업데이트', diagnostics: '지원 및 개인정보', settings: '설정' },
  common: { ...en.common, browse: '찾아보기', reveal: '폴더 열기', run: '실행', save: '저장', loading: '불러오는 중…', empty: '아직 항목이 없습니다', retry: '다시 시도', menu: '탐색 열기', compact: '간단히', expand: '탐색 확장' },
  integrations: {
    eyebrow: '예약, 동기화 및 게시', title: '통합 센터', subtitle: '로컬 프로젝트를 사용자 단위 OS 예약, 충돌 안전 폴더, 변경 불가 GitHub Release 및 제한된 WASM 어댑터에 연결합니다.',
    scheduler: 'OS 스케줄러', schedulerTitle: '예약된 Studio 작업', name: '예약 이름', enabled: '사용', cadence: '주기', intervalHours: '간격 시간', weekdays: '요일', jobKind: '작업 종류', jobTitle: '작업 제목', installSchedule: '예약 설치', noSchedules: '설치된 예약이 없습니다.', scheduleSaved: '예약을 설치했습니다.', scheduleQueued: '예약 작업을 대기열에 추가했습니다.',
    sync: '클라우드 폴더 동기화', syncTitle: '충돌 안전 프로젝트 동기화', projectRoot: '로컬 프로젝트 루트', syncRoot: '클라우드 동기화 폴더', dryRun: '파일을 바꾸지 않고 미리보기', runSync: '동기화', syncComplete: '동기화가 완료되었습니다.',
    githubTitle: '변경 불가 GitHub Release 게시', releaseName: 'Release 이름', releaseBody: 'Release 노트', assetPaths: '에셋 경로, 한 줄에 하나', credential: '잠금 해제된 GitHub 자격 증명', immutableWarning: '기존 태그는 수정하지 않습니다. 비공개 초안을 먼저 만들고 모든 에셋 업로드가 성공한 뒤에만 게시합니다.', publish: 'Release 만들기', releaseCreated: 'GitHub Release를 만들었습니다.',
    wasmTitle: '샌드박스 WASM 후처리기', modulePath: 'WASM 모듈', wasmPolicy: 'SHA 고정, import 금지, JSON alloc/postprocess ABI가 필요합니다. 워커, 시간 제한 및 메모리 한도로 격리합니다.', runWasm: '후처리 실행', wasmComplete: 'WASM 후처리가 완료되었습니다.',
  },
}

export const i18n = createI18n({
  legacy: false,
  locale: 'zh-TW',
  fallbackLocale: 'en',
  messages: { 'zh-TW': zhTW, en, 'zh-CN': zhCN, ja, ko },
})
