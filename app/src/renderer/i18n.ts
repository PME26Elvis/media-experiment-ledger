import { createI18n } from 'vue-i18n'

const en = {
  app: { name: 'Media Experiment Ledger Studio', tagline: 'Atlas · Detection · Media Automation' },
  nav: {
    workspace: 'Workspace', import: 'Media Import', samples: 'Sample Corpora', automation: 'Automation',
    atlas: 'Atlas Studio', detection: 'Detection Studio', jobs: 'Job Center', models: 'Models',
    reports: 'Reports', updates: 'Updates', diagnostics: 'Support & Privacy', settings: 'Settings',
  },
  common: {
    browse: 'Browse', reveal: 'Open folder', run: 'Run', save: 'Save', loading: 'Loading…',
    empty: 'Nothing here yet', retry: 'Retry', menu: 'Open navigation', compact: 'Compact', expand: 'Expand navigation',
  },
}
const zhTW = {
  app: { name: 'Media Experiment Ledger Studio', tagline: 'Atlas · Detection · Media Automation' },
  nav: {
    workspace: '工作區', import: '媒體匯入', samples: '範例資料集', automation: '自動化',
    atlas: 'Atlas Studio', detection: 'Detection Studio', jobs: '工作中心', models: '模型管理',
    reports: '報告庫', updates: '更新中心', diagnostics: '支援與隱私', settings: '設定',
  },
  common: {
    browse: '瀏覽', reveal: '打開資料夾', run: '開始執行', save: '儲存', loading: '載入中…',
    empty: '目前沒有內容', retry: '重試', menu: '開啟導覽', compact: '精簡側欄', expand: '展開側欄',
  },
}
const zhCN = {
  ...zhTW,
  nav: { ...zhTW.nav, workspace: '工作区', import: '媒体导入', samples: '示例数据集', jobs: '任务中心', diagnostics: '支持与隐私', settings: '设置', updates: '更新中心' },
  common: { ...zhTW.common, reveal: '打开文件夹', loading: '加载中…', empty: '当前没有内容', menu: '打开导航', compact: '精简侧栏', expand: '展开侧栏' },
}
const ja = {
  ...en,
  nav: { workspace: 'ワークスペース', import: 'メディア取込', samples: 'サンプルコーパス', automation: '自動化', atlas: 'Atlas Studio', detection: 'Detection Studio', jobs: 'ジョブ', models: 'モデル', reports: 'レポート', updates: '更新', diagnostics: 'サポートとプライバシー', settings: '設定' },
  common: { ...en.common, menu: 'ナビゲーションを開く', compact: 'コンパクト表示', expand: 'ナビゲーションを展開' },
}
const ko = {
  ...en,
  nav: { workspace: '작업 공간', import: '미디어 가져오기', samples: '샘플 코퍼스', automation: '자동화', atlas: 'Atlas Studio', detection: 'Detection Studio', jobs: '작업 센터', models: '모델', reports: '보고서', updates: '업데이트', diagnostics: '지원 및 개인정보', settings: '설정' },
  common: { ...en.common, menu: '탐색 열기', compact: '간단히', expand: '탐색 확장' },
}

export const i18n = createI18n({
  legacy: false,
  locale: 'zh-TW',
  fallbackLocale: 'en',
  messages: { 'zh-TW': zhTW, en, 'zh-CN': zhCN, ja, ko },
})
