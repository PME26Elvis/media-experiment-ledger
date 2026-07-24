export const PRODUCT_LOCALES = ['zh-TW', 'en', 'zh-CN', 'ja', 'ko'] as const
export type ProductLocale = typeof PRODUCT_LOCALES[number]

type LocalizedEntry = Record<Exclude<ProductLocale, 'en'>, string>

const entries: Record<string, LocalizedEntry> = {
  'Studio · Atlas · Detection · Automation': { 'zh-TW': 'Studio · Atlas · 偵測 · 自動化', 'zh-CN': 'Studio · Atlas · 检测 · 自动化', ja: 'Studio · Atlas · 検出 · 自動化', ko: 'Studio · Atlas · 탐지 · 자동화' },
  'Local-first creative research': { 'zh-TW': '本機優先的創意研究', 'zh-CN': '本地优先的创意研究', ja: 'ローカル優先のクリエイティブ研究', ko: '로컬 우선 크리에이티브 연구' },
  'Your media intelligence workspace': { 'zh-TW': '你的媒體智慧工作區', 'zh-CN': '你的媒体智能工作区', ja: 'メディアインテリジェンス・ワークスペース', ko: '미디어 인텔리전스 작업 공간' },
  'Import or generate media, build repeatability atlases, compare detectors and publish polished evidence without sending your project to a hosted service.': { 'zh-TW': '匯入或生成媒體、建立可重現性 Atlas、比較偵測器並發布精緻證據，全程不必把專案傳到託管服務。', 'zh-CN': '导入或生成媒体、建立可重复性 Atlas、比较检测器并发布精致证据，全程无需把项目传到托管服务。', ja: 'メディアの取込・生成、再現性Atlasの構築、検出器の比較、洗練された証拠の公開を、プロジェクトをホスト型サービスへ送らずに行えます。', ko: '프로젝트를 호스팅 서비스로 보내지 않고 미디어 가져오기·생성, 반복성 Atlas 구축, 탐지기 비교와 정제된 증거 게시를 수행합니다.' },
  'Active jobs': { 'zh-TW': '進行中的工作', 'zh-CN': '进行中的任务', ja: '実行中のジョブ', ko: '활성 작업' },
  'Durable work survives window changes and can recover after interruption.': { 'zh-TW': '耐久工作不受視窗切換影響，並可在中斷後復原。', 'zh-CN': '持久任务不受窗口切换影响，并可在中断后恢复。', ja: '耐久ジョブはウィンドウ変更に影響されず、中断後に復旧できます。', ko: '내구성 작업은 창 변경 후에도 유지되며 중단 뒤 복구할 수 있습니다.' },
  'Engine': { 'zh-TW': '引擎', 'zh-CN': '引擎', ja: 'エンジン', ko: '엔진' },
  'Python engine protocol is available.': { 'zh-TW': 'Python 引擎協定可用。', 'zh-CN': 'Python 引擎协议可用。', ja: 'Pythonエンジンプロトコルを利用できます。', ko: 'Python 엔진 프로토콜을 사용할 수 있습니다.' },
  'Engine source is not reachable.': { 'zh-TW': '無法連接引擎來源。', 'zh-CN': '无法连接引擎来源。', ja: 'エンジンソースに接続できません。', ko: '엔진 소스에 연결할 수 없습니다.' },
  'Ready': { 'zh-TW': '就緒', 'zh-CN': '就绪', ja: '準備完了', ko: '준비됨' },
  'Check': { 'zh-TW': '檢查', 'zh-CN': '检查', ja: '確認', ko: '확인' },
  'Build deterministic image and video evidence, then design a PDF-ready report.': { 'zh-TW': '建立具決定性的圖片與影片證據，再設計可輸出 PDF 的報告。', 'zh-CN': '建立确定性的图片与视频证据，再设计可输出 PDF 的报告。', ja: '決定論的な画像・動画証拠を構築し、PDF対応レポートを設計します。', ko: '결정적 이미지·영상 증거를 구축한 뒤 PDF 준비 보고서를 설계합니다.' },
  'Run representative YOLOX and NanoDet tiers with checkpoints.': { 'zh-TW': '以檢查點執行代表性的 YOLOX 與 NanoDet 等級。', 'zh-CN': '通过检查点运行代表性的 YOLOX 与 NanoDet 等级。', ja: 'チェックポイント付きで代表的なYOLOX／NanoDet階層を実行します。', ko: '체크포인트와 함께 대표 YOLOX 및 NanoDet 등급을 실행합니다.' },
  'Secure desktop boundary': { 'zh-TW': '安全的桌面邊界', 'zh-CN': '安全的桌面边界', ja: '安全なデスクトップ境界', ko: '안전한 데스크톱 경계' },
  'Renderer sandboxed · typed IPC · SQLite WAL · source media immutable': { 'zh-TW': 'Renderer 沙盒化 · 型別化 IPC · SQLite WAL · 來源媒體不可變', 'zh-CN': 'Renderer 沙箱化 · 类型化 IPC · SQLite WAL · 源媒体不可变', ja: 'Rendererサンドボックス · 型付きIPC · SQLite WAL · 元メディア不変', ko: 'Renderer 샌드박스 · 형식화 IPC · SQLite WAL · 원본 미디어 불변' },

  'Media Import': { 'zh-TW': '媒體匯入', 'zh-CN': '媒体导入', ja: 'メディア取込', ko: '미디어 가져오기' },
  'Bring large corpora under control': { 'zh-TW': '掌控大型媒體資料集', 'zh-CN': '掌控大型媒体数据集', ja: '大規模コーパスを管理下へ', ko: '대규모 코퍼스를 통제' },
  'Choose independent sources, storage policy and a project directory. The engine hashes, deduplicates, generates display-pixel-aware proxies and can materialize portable content-addressed copies.': { 'zh-TW': '選擇獨立來源、儲存策略與專案目錄。引擎會雜湊、去重、建立符合顯示像素的代理，並可具現化可攜式內容定址副本。', 'zh-CN': '选择独立来源、存储策略与项目目录。引擎会哈希、去重、建立符合显示像素的代理，并可实体化便携式内容寻址副本。', ja: '独立したソース、保存方針、プロジェクトディレクトリを選択します。エンジンはハッシュ化、重複排除、表示画素対応プロキシ生成、可搬なコンテンツアドレスコピーの実体化を行います。', ko: '독립 소스, 저장 정책과 프로젝트 디렉터리를 선택합니다. 엔진은 해시, 중복 제거, 표시 픽셀 대응 프록시 생성과 이동 가능한 콘텐츠 주소 복사를 수행합니다.' },
  'Image input directory': { 'zh-TW': '圖片輸入目錄', 'zh-CN': '图片输入目录', ja: '画像入力ディレクトリ', ko: '이미지 입력 디렉터리' },
  'Video input directory': { 'zh-TW': '影片輸入目錄', 'zh-CN': '视频输入目录', ja: '動画入力ディレクトリ', ko: '영상 입력 디렉터리' },
  'Project materialization directory': { 'zh-TW': '專案具現化目錄', 'zh-CN': '项目实体化目录', ja: 'プロジェクト実体化ディレクトリ', ko: '프로젝트 구체화 디렉터리' },
  'Existing references remain untouched.': { 'zh-TW': '既有參照不會被修改。', 'zh-CN': '现有引用不会被修改。', ja: '既存参照は変更されません。', ko: '기존 참조는 변경되지 않습니다.' },
  'Video indexing generates verified poster proxies.': { 'zh-TW': '影片索引會建立經驗證的海報代理。', 'zh-CN': '视频索引会建立已验证的海报代理。', ja: '動画索引は検証済みポスタープロキシを生成します。', ko: '영상 인덱싱은 검증된 포스터 프록시를 생성합니다.' },
  'Stores media-index.json, proxy pyramids and optional managed blobs.': { 'zh-TW': '儲存 media-index.json、代理金字塔與選用的受管 blob。', 'zh-CN': '存储 media-index.json、代理金字塔与可选的托管 blob。', ja: 'media-index.json、プロキシピラミッド、任意の管理blobを保存します。', ko: 'media-index.json, 프록시 피라미드와 선택적 관리 blob을 저장합니다.' },
  'Storage policy': { 'zh-TW': '儲存策略', 'zh-CN': '存储策略', ja: '保存方針', ko: '저장 정책' },
  'Adaptive recommendation': { 'zh-TW': '自適應建議', 'zh-CN': '自适应建议', ja: '適応的な推奨', ko: '적응형 권장' },
  'Managed content-addressed copy': { 'zh-TW': '受管內容定址副本', 'zh-CN': '托管内容寻址副本', ja: '管理対象コンテンツアドレスコピー', ko: '관리형 콘텐츠 주소 복사' },
  'External reference': { 'zh-TW': '外部參照', 'zh-CN': '外部引用', ja: '外部参照', ko: '외부 참조' },
  'Bounded workers': { 'zh-TW': '受限工作執行緒', 'zh-CN': '受限工作线程', ja: '上限付きワーカー', ko: '제한된 워커' },
  'Adaptive mode chooses a managed copy only when the corpus is below the configured threshold and enough free disk remains. Otherwise it preserves external references.': { 'zh-TW': '只有在資料集低於設定門檻且磁碟空間充足時，自適應模式才會選擇受管副本；否則保留外部參照。', 'zh-CN': '只有在数据集低于设定阈值且磁盘空间充足时，自适应模式才会选择托管副本；否则保留外部引用。', ja: '適応モードは、コーパスが設定閾値未満で十分な空き容量がある場合のみ管理コピーを選択し、それ以外は外部参照を維持します。', ko: '적응 모드는 코퍼스가 설정 임계값보다 작고 디스크 여유가 충분할 때만 관리 복사를 선택하며, 그 외에는 외부 참조를 유지합니다.' },
  'Index corpus': { 'zh-TW': '建立資料集索引', 'zh-CN': '建立数据集索引', ja: 'コーパスを索引化', ko: '코퍼스 인덱싱' },
  'Import job created. Progress and recovery controls are available in Job Center.': { 'zh-TW': '匯入工作已建立。進度與復原控制可在工作中心查看。', 'zh-CN': '导入任务已创建。进度与恢复控制可在任务中心查看。', ja: '取込ジョブを作成しました。進捗と復旧操作はジョブセンターで確認できます。', ko: '가져오기 작업이 생성되었습니다. 진행률과 복구 제어는 작업 센터에서 확인할 수 있습니다.' },

  'Sample Corpus Manager': { 'zh-TW': '範例資料集管理器', 'zh-CN': '示例数据集管理器', ja: 'サンプルコーパス管理', ko: '샘플 코퍼스 관리자' },
  'Run the product before supplying your own data': { 'zh-TW': '先用範例資料完整體驗產品', 'zh-CN': '先用示例数据完整体验产品', ja: '自分のデータを用意する前に製品を実行', ko: '자신의 데이터를 제공하기 전에 제품 실행' },
  'Quick Start demonstrates the complete workflow; Full Research preserves the sanitized canonical corpus for scale and repeatability evaluation. Each part is immutable and SHA-256 verified.': { 'zh-TW': 'Quick Start 展示完整流程；Full Research 保存經清理的標準資料集，用於規模與可重現性評估。每個分卷皆不可變並經 SHA-256 驗證。', 'zh-CN': 'Quick Start 展示完整流程；Full Research 保存已清理的标准数据集，用于规模与可重复性评估。每个分卷均不可变并经 SHA-256 验证。', ja: 'Quick Startは完全なワークフローを示し、Full Researchは規模・再現性評価用のサニタイズ済み標準コーパスを保持します。各パートは不変でSHA-256検証済みです。', ko: 'Quick Start는 전체 워크플로를 보여주며 Full Research는 규모와 반복성 평가용 정제 표준 코퍼스를 보존합니다. 각 파트는 불변이며 SHA-256 검증됩니다.' },
  'Discover Releases': { 'zh-TW': '探索 Releases', 'zh-CN': '发现 Releases', ja: 'Releaseを検索', ko: 'Release 찾기' },
  'Import manifest': { 'zh-TW': '匯入 manifest', 'zh-CN': '导入 manifest', ja: 'manifestを取込', ko: 'manifest 가져오기' },
  'Install / Resume': { 'zh-TW': '安裝／繼續', 'zh-CN': '安装／继续', ja: 'インストール／再開', ko: '설치／재개' },
  'Remove files': { 'zh-TW': '移除檔案', 'zh-CN': '移除文件', ja: 'ファイルを削除', ko: '파일 제거' },
  'No corpus manifests installed': { 'zh-TW': '尚未安裝資料集 manifest', 'zh-CN': '尚未安装数据集 manifest', ja: 'コーパスmanifestは未インストールです', ko: '설치된 코퍼스 manifest가 없습니다' },
  'Discover approved GitHub Releases or import a locally reviewed manifest.': { 'zh-TW': '探索已核准的 GitHub Releases，或匯入經本機審核的 manifest。', 'zh-CN': '发现已批准的 GitHub Releases，或导入经本地审核的 manifest。', ja: '承認済みGitHub Releaseを検索するか、ローカルでレビューしたmanifestを取込んでください。', ko: '승인된 GitHub Release를 찾거나 로컬 검토 manifest를 가져오세요.' },

  'Media Automation': { 'zh-TW': '媒體自動化', 'zh-CN': '媒体自动化', ja: 'メディア自動化', ko: '미디어 자동화' },
  'Rate-conscious generation orchestration': { 'zh-TW': '兼顧速率限制的生成編排', 'zh-CN': '兼顾速率限制的生成编排', ja: 'レート制限を考慮した生成オーケストレーション', ko: '속도 제한을 고려한 생성 오케스트레이션' },
  'Durable submission, video polling, verified Generated Media, bounded retries and circuit breakers run outside the renderer.': { 'zh-TW': '耐久提交、影片輪詢、已驗證生成媒體、受限重試與斷路器皆在 renderer 外執行。', 'zh-CN': '持久提交、视频轮询、已验证生成媒体、受限重试与断路器均在 renderer 外执行。', ja: '耐久送信、動画ポーリング、検証済み生成メディア、上限付き再試行、サーキットブレーカーはrenderer外で動作します。', ko: '내구성 제출, 영상 폴링, 검증된 생성 미디어, 제한 재시도와 회로 차단기는 renderer 밖에서 실행됩니다.' },
  'No unlocked Agnes credential': { 'zh-TW': '沒有已解鎖的 Agnes 憑證', 'zh-CN': '没有已解锁的 Agnes 凭证', ja: '解除済みAgnes資格情報がありません', ko: '잠금 해제된 Agnes 자격 증명이 없습니다' },
  'Create or unlock a compatible credential profile in Settings. The API key is injected only into the isolated engine process.': { 'zh-TW': '請在設定中建立或解鎖相容的憑證設定檔。API key 只會注入隔離的引擎程序。', 'zh-CN': '请在设置中创建或解锁兼容的凭证配置。API key 只会注入隔离的引擎进程。', ja: '設定で互換資格情報プロファイルを作成または解除してください。APIキーは隔離されたエンジンプロセスのみに注入されます。', ko: '설정에서 호환 자격 증명 프로필을 만들거나 잠금 해제하세요. API 키는 격리된 엔진 프로세스에만 주입됩니다.' },
  'Provider': { 'zh-TW': '服務商', 'zh-CN': '服务商', ja: 'プロバイダー', ko: '공급자' },
  'Credential profile': { 'zh-TW': '憑證設定檔', 'zh-CN': '凭证配置', ja: '資格情報プロファイル', ko: '자격 증명 프로필' },
  'Media type': { 'zh-TW': '媒體類型', 'zh-CN': '媒体类型', ja: 'メディア種別', ko: '미디어 유형' },
  'Provider model': { 'zh-TW': '服務商模型', 'zh-CN': '服务商模型', ja: 'プロバイダーモデル', ko: '공급자 모델' },
  'Create interval (seconds)': { 'zh-TW': '建立間隔（秒）', 'zh-CN': '创建间隔（秒）', ja: '生成間隔（秒）', ko: '생성 간격(초)' },
  'Concurrent workers': { 'zh-TW': '並行工作數', 'zh-CN': '并行工作数', ja: '並列ワーカー', ko: '동시 워커' },
  'Prompt text or JSONL file': { 'zh-TW': 'Prompt 文字或 JSONL 檔案', 'zh-CN': 'Prompt 文本或 JSONL 文件', ja: 'PromptテキストまたはJSONLファイル', ko: 'Prompt 텍스트 또는 JSONL 파일' },
  'Generated media output': { 'zh-TW': '生成媒體輸出', 'zh-CN': '生成媒体输出', ja: '生成メディア出力', ko: '생성 미디어 출력' },
  'Start durable automation': { 'zh-TW': '開始耐久自動化', 'zh-CN': '开始持久自动化', ja: '耐久自動化を開始', ko: '내구성 자동화 시작' },

  'Evidence first. Presentation second.': { 'zh-TW': '證據優先，呈現其次。', 'zh-CN': '证据优先，呈现其次。', ja: '証拠を先に、表現はその次に。', ko: '증거가 먼저, 표현은 그다음.' },
  'Create resumable immutable image/video evidence, then author a structured or controlled-freeform PDF without changing source media.': { 'zh-TW': '建立可續傳、不可變的圖片／影片證據，再在不修改來源媒體的前提下編寫結構化或受控自由排版 PDF。', 'zh-CN': '建立可续传、不可变的图片／视频证据，再在不修改源媒体的前提下编写结构化或受控自由排版 PDF。', ja: '再開可能で不変な画像・動画証拠を作成し、元メディアを変更せず構造化または制御自由配置PDFを編集します。', ko: '재개 가능한 불변 이미지·영상 증거를 만든 뒤 원본 미디어를 변경하지 않고 구조화 또는 제어형 자유 배치 PDF를 작성합니다.' },
  'Atlas input corpus': { 'zh-TW': 'Atlas 輸入資料集', 'zh-CN': 'Atlas 输入数据集', ja: 'Atlas入力コーパス', ko: 'Atlas 입력 코퍼스' },
  'Atlas output directory': { 'zh-TW': 'Atlas 輸出目錄', 'zh-CN': 'Atlas 输出目录', ja: 'Atlas出力ディレクトリ', ko: 'Atlas 출력 디렉터리' },
  'Report template': { 'zh-TW': '報告模板', 'zh-CN': '报告模板', ja: 'レポートテンプレート', ko: '보고서 템플릿' },
  'Evidence scope': { 'zh-TW': '證據範圍', 'zh-CN': '证据范围', ja: '証拠範囲', ko: '증거 범위' },
  'Full corpus': { 'zh-TW': '完整資料集', 'zh-CN': '完整数据集', ja: '全コーパス', ko: '전체 코퍼스' },
  'Selected collection': { 'zh-TW': '選取的集合', 'zh-CN': '选定集合', ja: '選択コレクション', ko: '선택 컬렉션' },
  'Static video evidence': { 'zh-TW': '靜態影片證據', 'zh-CN': '静态视频证据', ja: '静的動画証拠', ko: '정적 영상 증거' },
  'Poster frame': { 'zh-TW': '海報影格', 'zh-CN': '海报帧', ja: 'ポスターフレーム', ko: '포스터 프레임' },
  'Create lightweight GIF previews': { 'zh-TW': '建立輕量 GIF 預覽', 'zh-CN': '创建轻量 GIF 预览', ja: '軽量GIFプレビューを作成', ko: '경량 GIF 미리보기 생성' },
  'Build resumable Atlas snapshot': { 'zh-TW': '建立可續傳 Atlas 快照', 'zh-CN': '建立可续传 Atlas 快照', ja: '再開可能なAtlasスナップショットを構築', ko: '재개 가능한 Atlas 스냅샷 구축' },
  'Video evidence policy': { 'zh-TW': '影片證據策略', 'zh-CN': '视频证据策略', ja: '動画証拠方針', ko: '영상 증거 정책' },

  'Multi-model inference with durable checkpoints': { 'zh-TW': '具耐久檢查點的多模型推論', 'zh-CN': '具持久检查点的多模型推理', ja: '耐久チェックポイント付きマルチモデル推論', ko: '내구성 체크포인트 기반 다중 모델 추론' },
  'Run built-in registry slots or hash-pinned user-supplied ONNX manifests through the same verified YOLOX and NanoDet decoders.': { 'zh-TW': '透過相同且經驗證的 YOLOX 與 NanoDet decoder，執行內建 registry 槽位或鎖定雜湊的使用者 ONNX manifest。', 'zh-CN': '通过相同且已验证的 YOLOX 与 NanoDet decoder，运行内置 registry 槽位或锁定哈希的用户 ONNX manifest。', ja: '同じ検証済みYOLOX／NanoDetデコーダーで、内蔵レジストリスロットまたはハッシュ固定のユーザーONNX manifestを実行します。', ko: '동일한 검증 YOLOX 및 NanoDet 디코더로 내장 레지스트리 슬롯 또는 해시 고정 사용자 ONNX manifest를 실행합니다.' },
  'Install a model first': { 'zh-TW': '請先安裝模型', 'zh-CN': '请先安装模型', ja: '先にモデルをインストールしてください', ko: '먼저 모델을 설치하세요' },
  'Open Model Manager and import a verified ONNX artifact or declarative user model manifest.': { 'zh-TW': '開啟模型管理器並匯入經驗證的 ONNX 資產或宣告式使用者模型 manifest。', 'zh-CN': '打开模型管理器并导入已验证的 ONNX 资产或声明式用户模型 manifest。', ja: 'モデル管理を開き、検証済みONNXアーティファクトまたは宣言型ユーザーモデルmanifestを取込んでください。', ko: '모델 관리자를 열어 검증된 ONNX 아티팩트 또는 선언형 사용자 모델 manifest를 가져오세요.' },
  'Image corpus': { 'zh-TW': '圖片資料集', 'zh-CN': '图片数据集', ja: '画像コーパス', ko: '이미지 코퍼스' },
  'Detection output directory': { 'zh-TW': '偵測輸出目錄', 'zh-CN': '检测输出目录', ja: '検出出力ディレクトリ', ko: '탐지 출력 디렉터리' },
  'Installed model': { 'zh-TW': '已安裝模型', 'zh-CN': '已安装模型', ja: 'インストール済みモデル', ko: '설치된 모델' },
  'Execution provider': { 'zh-TW': '執行 provider', 'zh-CN': '执行 provider', ja: '実行プロバイダー', ko: '실행 공급자' },
  'Start detection': { 'zh-TW': '開始偵測', 'zh-CN': '开始检测', ja: '検出を開始', ko: '탐지 시작' },

  'Durable jobs': { 'zh-TW': '耐久工作', 'zh-CN': '持久任务', ja: '耐久ジョブ', ko: '내구성 작업' },
  'Job Center': { 'zh-TW': '工作中心', 'zh-CN': '任务中心', ja: 'ジョブセンター', ko: '작업 센터' },
  'Every nontrivial operation has an identity, state machine, item progress, recovery path and final verification stage.': { 'zh-TW': '每個非簡單操作都有識別碼、狀態機、項目進度、復原路徑與最終驗證階段。', 'zh-CN': '每个非简单操作都有标识、状态机、项目进度、恢复路径与最终验证阶段。', ja: 'すべての非自明な操作には識別子、状態機械、項目進捗、復旧経路、最終検証段階があります。', ko: '모든 비단순 작업에는 식별자, 상태 머신, 항목 진행률, 복구 경로와 최종 검증 단계가 있습니다.' },
  'No jobs yet': { 'zh-TW': '尚無工作', 'zh-CN': '尚无任务', ja: 'ジョブはまだありません', ko: '아직 작업이 없습니다' },
  'Create work from Import, Automation, Atlas or Detection Studio.': { 'zh-TW': '可從匯入、自動化、Atlas 或 Detection Studio 建立工作。', 'zh-CN': '可从导入、自动化、Atlas 或 Detection Studio 创建任务。', ja: '取込、自動化、Atlas、Detection Studioからジョブを作成してください。', ko: '가져오기, 자동화, Atlas 또는 Detection Studio에서 작업을 생성하세요.' },
  'Pause': { 'zh-TW': '暫停', 'zh-CN': '暂停', ja: '一時停止', ko: '일시정지' },
  'Resume': { 'zh-TW': '繼續', 'zh-CN': '继续', ja: '再開', ko: '재개' },
  'Cancel': { 'zh-TW': '取消', 'zh-CN': '取消', ja: 'キャンセル', ko: '취소' },
  'queued': { 'zh-TW': '已排入', 'zh-CN': '已排队', ja: '待機中', ko: '대기 중' },
  'running': { 'zh-TW': '執行中', 'zh-CN': '运行中', ja: '実行中', ko: '실행 중' },
  'paused': { 'zh-TW': '已暫停', 'zh-CN': '已暂停', ja: '一時停止', ko: '일시정지됨' },
  'recoverable': { 'zh-TW': '可復原', 'zh-CN': '可恢复', ja: '復旧可能', ko: '복구 가능' },
  'completed': { 'zh-TW': '已完成', 'zh-CN': '已完成', ja: '完了', ko: '완료' },
  'failed': { 'zh-TW': '失敗', 'zh-CN': '失败', ja: '失敗', ko: '실패' },
  'cancelled': { 'zh-TW': '已取消', 'zh-CN': '已取消', ja: 'キャンセル済み', ko: '취소됨' },

  'Model Manager': { 'zh-TW': '模型管理器', 'zh-CN': '模型管理器', ja: 'モデル管理', ko: '모델 관리자' },
  'Verified model registry': { 'zh-TW': '經驗證的模型 registry', 'zh-CN': '已验证的模型 registry', ja: '検証済みモデルレジストリ', ko: '검증된 모델 레지스트리' },
  'Built-in model slots and declarative user-supplied manifests share the same hash, adapter and provenance boundary. No manifest may execute code.': { 'zh-TW': '內建模型槽位與宣告式使用者 manifest 共用相同的雜湊、adapter 與來源邊界；任何 manifest 都不得執行程式碼。', 'zh-CN': '内置模型槽位与声明式用户 manifest 共用相同的哈希、adapter 与来源边界；任何 manifest 都不得执行代码。', ja: '内蔵モデルスロットと宣言型ユーザーmanifestは同じハッシュ、アダプター、来歴境界を共有し、manifestはコードを実行できません。', ko: '내장 모델 슬롯과 선언형 사용자 manifest는 동일한 해시, 어댑터와 출처 경계를 공유하며 어떤 manifest도 코드를 실행할 수 없습니다.' },
  'Import model manifest': { 'zh-TW': '匯入模型 manifest', 'zh-CN': '导入模型 manifest', ja: 'モデルmanifestを取込', ko: '모델 manifest 가져오기' },
  'User supplied': { 'zh-TW': '使用者提供', 'zh-CN': '用户提供', ja: 'ユーザー提供', ko: '사용자 제공' },
  'Installed': { 'zh-TW': '已安裝', 'zh-CN': '已安装', ja: 'インストール済み', ko: '설치됨' },
  'Not installed': { 'zh-TW': '未安裝', 'zh-CN': '未安装', ja: '未インストール', ko: '설치되지 않음' },
  'Import ONNX': { 'zh-TW': '匯入 ONNX', 'zh-CN': '导入 ONNX', ja: 'ONNXを取込', ko: 'ONNX 가져오기' },
  'Reveal': { 'zh-TW': '顯示位置', 'zh-CN': '显示位置', ja: '場所を表示', ko: '위치 표시' },
  'Remove': { 'zh-TW': '移除', 'zh-CN': '移除', ja: '削除', ko: '제거' },

  'Report Library & Document Studio': { 'zh-TW': '報告庫與文件工作室', 'zh-CN': '报告库与文档工作室', ja: 'レポートライブラリ＆文書スタジオ', ko: '보고서 라이브러리 및 문서 스튜디오' },
  'Turn immutable evidence into a polished document': { 'zh-TW': '把不可變證據轉化為精緻文件', 'zh-CN': '把不可变证据转化为精致文档', ja: '不変の証拠を洗練された文書へ', ko: '불변 증거를 정제된 문서로 전환' },
  'Analysis snapshots remain unchanged while structured and controlled-freeform blocks, templates, revisions and PDF exports evolve independently.': { 'zh-TW': '分析快照保持不變，而結構化與受控自由排版區塊、模板、修訂及 PDF 輸出可獨立演進。', 'zh-CN': '分析快照保持不变，而结构化与受控自由排版区块、模板、修订及 PDF 输出可独立演进。', ja: '分析スナップショットは不変のまま、構造化／制御自由配置ブロック、テンプレート、改訂、PDF出力を独立して発展させます。', ko: '분석 스냅샷은 변경하지 않고 구조화·제어형 자유 배치 블록, 템플릿, 리비전과 PDF 출력을 독립적으로 발전시킵니다.' },
  'New report': { 'zh-TW': '新增報告', 'zh-CN': '新建报告', ja: '新規レポート', ko: '새 보고서' },
  'Import Atlas manifest': { 'zh-TW': '匯入 Atlas manifest', 'zh-CN': '导入 Atlas manifest', ja: 'Atlas manifestを取込', ko: 'Atlas manifest 가져오기' },
  'Export PDF': { 'zh-TW': '輸出 PDF', 'zh-CN': '导出 PDF', ja: 'PDFを出力', ko: 'PDF 내보내기' },
  'No report documents yet.': { 'zh-TW': '尚無報告文件。', 'zh-CN': '尚无报告文档。', ja: 'レポート文書はまだありません。', ko: '아직 보고서 문서가 없습니다.' },
  'Checkpoint': { 'zh-TW': '建立檢查點', 'zh-CN': '建立检查点', ja: 'チェックポイント', ko: '체크포인트' },
  'Delete': { 'zh-TW': '刪除', 'zh-CN': '删除', ja: '削除', ko: '삭제' },
  'Editor': { 'zh-TW': '編輯器', 'zh-CN': '编辑器', ja: 'エディター', ko: '편집기' },
  'Paged preview': { 'zh-TW': '分頁預覽', 'zh-CN': '分页预览', ja: 'ページプレビュー', ko: '페이지 미리보기' },
  'Templates': { 'zh-TW': '模板', 'zh-CN': '模板', ja: 'テンプレート', ko: '템플릿' },
  'Revisions': { 'zh-TW': '修訂', 'zh-CN': '修订', ja: '改訂', ko: '리비전' },
  'Document title': { 'zh-TW': '文件標題', 'zh-CN': '文档标题', ja: '文書タイトル', ko: '문서 제목' },
  'Subtitle / summary': { 'zh-TW': '副標題／摘要', 'zh-CN': '副标题／摘要', ja: '副題／要約', ko: '부제／요약' },

  'Update & Recovery Center': { 'zh-TW': '更新與復原中心', 'zh-CN': '更新与恢复中心', ja: '更新＆復旧センター', ko: '업데이트 및 복구 센터' },
  'Verified upgrades with a way back': { 'zh-TW': '可回復的經驗證升級', 'zh-CN': '可回退的已验证升级', ja: '戻れる検証済みアップグレード', ko: '되돌릴 수 있는 검증 업그레이드' },
  'Online and offline update packages are gated by active jobs, platform identity, hashes and recovery checkpoints. Restores run before SQLite opens.': { 'zh-TW': '線上與離線更新套件皆受進行中工作、平台識別、雜湊與復原檢查點把關；還原會在 SQLite 開啟前執行。', 'zh-CN': '在线与离线更新包均受进行中任务、平台标识、哈希与恢复检查点把关；还原会在 SQLite 打开前执行。', ja: 'オンライン／オフライン更新パッケージは実行中ジョブ、プラットフォームID、ハッシュ、復旧チェックポイントで制御され、復元はSQLiteを開く前に実行されます。', ko: '온라인·오프라인 업데이트 패키지는 활성 작업, 플랫폼 식별, 해시와 복구 체크포인트로 제한되며 복원은 SQLite가 열리기 전에 실행됩니다.' },
  'Application update': { 'zh-TW': '應用程式更新', 'zh-CN': '应用程序更新', ja: 'アプリ更新', ko: '애플리케이션 업데이트' },
  'Current version': { 'zh-TW': '目前版本', 'zh-CN': '当前版本', ja: '現在のバージョン', ko: '현재 버전' },
  'Available version': { 'zh-TW': '可用版本', 'zh-CN': '可用版本', ja: '利用可能なバージョン', ko: '사용 가능한 버전' },
  'Channel': { 'zh-TW': '頻道', 'zh-CN': '通道', ja: 'チャンネル', ko: '채널' },
  'Platform mode': { 'zh-TW': '平台模式', 'zh-CN': '平台模式', ja: 'プラットフォームモード', ko: '플랫폼 모드' },
  'None detected': { 'zh-TW': '未偵測到', 'zh-CN': '未检测到', ja: '検出なし', ko: '감지되지 않음' },
  'Automatic updater': { 'zh-TW': '自動更新器', 'zh-CN': '自动更新器', ja: '自動アップデーター', ko: '자동 업데이터' },
  'Signed manual packages': { 'zh-TW': '已簽章手動套件', 'zh-CN': '已签名手动包', ja: '署名済み手動パッケージ', ko: '서명된 수동 패키지' },
  'Download': { 'zh-TW': '下載', 'zh-CN': '下载', ja: 'ダウンロード', ko: '다운로드' },
  'Back up & install': { 'zh-TW': '備份並安裝', 'zh-CN': '备份并安装', ja: 'バックアップしてインストール', ko: '백업 후 설치' },
  'Offline package': { 'zh-TW': '離線套件', 'zh-CN': '离线包', ja: 'オフラインパッケージ', ko: '오프라인 패키지' },
  'Air-gapped update staging': { 'zh-TW': '隔離環境更新暫存', 'zh-CN': '隔离环境更新暂存', ja: 'エアギャップ更新ステージング', ko: '에어갭 업데이트 스테이징' },
  'Offline update manifest': { 'zh-TW': '離線更新 manifest', 'zh-CN': '离线更新 manifest', ja: 'オフライン更新manifest', ko: '오프라인 업데이트 manifest' },
  'Matching installer package': { 'zh-TW': '相符的安裝套件', 'zh-CN': '匹配的安装包', ja: '対応インストーラーパッケージ', ko: '일치하는 설치 패키지' },
  'Verify & stage': { 'zh-TW': '驗證並暫存', 'zh-CN': '验证并暂存', ja: '検証してステージ', ko: '검증 및 스테이징' },
  'Back up & open': { 'zh-TW': '備份並開啟', 'zh-CN': '备份并打开', ja: 'バックアップして開く', ko: '백업 후 열기' },
  'Database health': { 'zh-TW': '資料庫健康狀態', 'zh-CN': '数据库健康状态', ja: 'データベース健全性', ko: '데이터베이스 상태' },
  'Integrity verified': { 'zh-TW': '完整性已驗證', 'zh-CN': '完整性已验证', ja: '整合性を確認済み', ko: '무결성 검증됨' },
  'Attention required': { 'zh-TW': '需要注意', 'zh-CN': '需要注意', ja: '要対応', ko: '주의 필요' },
  'Recovery checkpoints': { 'zh-TW': '復原檢查點', 'zh-CN': '恢复检查点', ja: '復旧チェックポイント', ko: '복구 체크포인트' },
  'Hash-verified application state': { 'zh-TW': '經雜湊驗證的應用程式狀態', 'zh-CN': '经哈希验证的应用程序状态', ja: 'ハッシュ検証済みアプリ状態', ko: '해시 검증 애플리케이션 상태' },
  'Backup reason': { 'zh-TW': '備份原因', 'zh-CN': '备份原因', ja: 'バックアップ理由', ko: '백업 이유' },
  'Create': { 'zh-TW': '建立', 'zh-CN': '创建', ja: '作成', ko: '생성' },
  'No recovery backups yet.': { 'zh-TW': '尚無復原備份。', 'zh-CN': '尚无恢复备份。', ja: '復旧バックアップはまだありません。', ko: '아직 복구 백업이 없습니다.' },

  'Support & Privacy': { 'zh-TW': '支援與隱私', 'zh-CN': '支持与隐私', ja: 'サポートとプライバシー', ko: '지원 및 개인정보' },
  'Preview every byte before it leaves': { 'zh-TW': '每一個位元組離開前都可預覽', 'zh-CN': '每一个字节离开前都可预览', ja: '送信前にすべてのバイトを確認', ko: '모든 바이트를 전송 전에 미리보기' },
  'Diagnostics exclude media, prompts, job configuration, credentials and raw paths. Remote telemetry is disabled until an HTTPS endpoint is explicitly enabled.': { 'zh-TW': '診斷資料排除媒體、prompt、工作設定、憑證與原始路徑；只有明確啟用 HTTPS endpoint 後才允許遠端遙測。', 'zh-CN': '诊断数据排除媒体、prompt、任务配置、凭证与原始路径；只有明确启用 HTTPS endpoint 后才允许远程遥测。', ja: '診断にはメディア、prompt、ジョブ設定、資格情報、生パスを含めません。HTTPSエンドポイントを明示的に有効化するまで遠隔テレメトリは無効です。', ko: '진단은 미디어, prompt, 작업 구성, 자격 증명과 원시 경로를 제외합니다. HTTPS 엔드포인트를 명시적으로 활성화하기 전까지 원격 텔레메트리는 비활성화됩니다.' },
  'Consent': { 'zh-TW': '同意設定', 'zh-CN': '同意设置', ja: '同意', ko: '동의' },
  'Default-off remote diagnostics': { 'zh-TW': '預設關閉的遠端診斷', 'zh-CN': '默认关闭的远程诊断', ja: '既定で無効の遠隔診断', ko: '기본 비활성 원격 진단' },
  'Allow manual remote diagnostics sends': { 'zh-TW': '允許手動傳送遠端診斷', 'zh-CN': '允许手动发送远程诊断', ja: '手動の遠隔診断送信を許可', ko: '수동 원격 진단 전송 허용' },
  'HTTPS diagnostics endpoint': { 'zh-TW': 'HTTPS 診斷 endpoint', 'zh-CN': 'HTTPS 诊断 endpoint', ja: 'HTTPS診断エンドポイント', ko: 'HTTPS 진단 엔드포인트' },
  'Save consent': { 'zh-TW': '儲存同意設定', 'zh-CN': '保存同意设置', ja: '同意を保存', ko: '동의 저장' },
  'Send preview': { 'zh-TW': '傳送預覽內容', 'zh-CN': '发送预览内容', ja: 'プレビューを送信', ko: '미리보기 전송' },
  'Local support bundle': { 'zh-TW': '本機支援套件', 'zh-CN': '本地支持包', ja: 'ローカルサポートバンドル', ko: '로컬 지원 번들' },
  'Compressed JSON + SHA-256 manifest': { 'zh-TW': '壓縮 JSON ＋ SHA-256 manifest', 'zh-CN': '压缩 JSON ＋ SHA-256 manifest', ja: '圧縮JSON＋SHA-256 manifest', ko: '압축 JSON + SHA-256 manifest' },
  'Support bundle output directory': { 'zh-TW': '支援套件輸出目錄', 'zh-CN': '支持包输出目录', ja: 'サポートバンドル出力ディレクトリ', ko: '지원 번들 출력 디렉터리' },
  'Create redacted bundle': { 'zh-TW': '建立已遮蔽套件', 'zh-CN': '创建已脱敏包', ja: '秘匿化バンドルを作成', ko: '비식별 번들 생성' },
  'Payload preview': { 'zh-TW': 'Payload 預覽', 'zh-CN': 'Payload 预览', ja: 'ペイロードプレビュー', ko: '페이로드 미리보기' },
  'Exact redacted structure': { 'zh-TW': '精確的遮蔽後結構', 'zh-CN': '精确的脱敏后结构', ja: '正確な秘匿化構造', ko: '정확한 비식별 구조' },
  'Refresh': { 'zh-TW': '重新整理', 'zh-CN': '刷新', ja: '更新', ko: '새로고침' },

  'Preferences, paths & credentials': { 'zh-TW': '偏好、路徑與憑證', 'zh-CN': '偏好、路径与凭证', ja: '環境設定・パス・資格情報', ko: '환경설정, 경로 및 자격 증명' },
  'Settings': { 'zh-TW': '設定', 'zh-CN': '设置', ja: '設定', ko: '설정' },
  'Project paths remain explicit and browsable. Secrets use dedicated profiles and never enter ordinary project exports.': { 'zh-TW': '專案路徑保持明確且可瀏覽；秘密資料使用專用設定檔，絕不進入一般專案輸出。', 'zh-CN': '项目路径保持明确且可浏览；秘密数据使用专用配置，绝不进入普通项目导出。', ja: 'プロジェクトパスは明示的で参照可能です。秘密情報は専用プロファイルを使い、通常のプロジェクト出力には入りません。', ko: '프로젝트 경로는 명시적이고 탐색 가능합니다. 비밀 정보는 전용 프로필을 사용하며 일반 프로젝트 내보내기에 포함되지 않습니다.' },
  'Language': { 'zh-TW': '語言', 'zh-CN': '语言', ja: '言語', ko: '언어' },
  'Appearance': { 'zh-TW': '外觀', 'zh-CN': '外观', ja: '外観', ko: '모양' },
  'Close behavior': { 'zh-TW': '關閉行為', 'zh-CN': '关闭行为', ja: '閉じる動作', ko: '닫기 동작' },
  'Default image input': { 'zh-TW': '預設圖片輸入', 'zh-CN': '默认图片输入', ja: '既定の画像入力', ko: '기본 이미지 입력' },
  'Default video input': { 'zh-TW': '預設影片輸入', 'zh-CN': '默认视频输入', ja: '既定の動画入力', ko: '기본 영상 입력' },
  'Default Atlas output': { 'zh-TW': '預設 Atlas 輸出', 'zh-CN': '默认 Atlas 输出', ja: '既定のAtlas出力', ko: '기본 Atlas 출력' },
  'Default detection output': { 'zh-TW': '預設偵測輸出', 'zh-CN': '默认检测输出', ja: '既定の検出出力', ko: '기본 탐지 출력' },
  'Default generated media output': { 'zh-TW': '預設生成媒體輸出', 'zh-CN': '默认生成媒体输出', ja: '既定の生成メディア出力', ko: '기본 생성 미디어 출력' },
  'Updates & interaction': { 'zh-TW': '更新與互動', 'zh-CN': '更新与交互', ja: '更新と操作', ko: '업데이트 및 상호작용' },
  'Update channel': { 'zh-TW': '更新頻道', 'zh-CN': '更新通道', ja: '更新チャンネル', ko: '업데이트 채널' },
  'Check updates on launch': { 'zh-TW': '啟動時檢查更新', 'zh-CN': '启动时检查更新', ja: '起動時に更新を確認', ko: '시작 시 업데이트 확인' },
  'Reduce motion': { 'zh-TW': '減少動態效果', 'zh-CN': '减少动态效果', ja: 'モーションを減らす', ko: '모션 줄이기' },
  'Save settings': { 'zh-TW': '儲存設定', 'zh-CN': '保存设置', ja: '設定を保存', ko: '설정 저장' },
  'Settings saved': { 'zh-TW': '設定已儲存', 'zh-CN': '设置已保存', ja: '設定を保存しました', ko: '설정이 저장되었습니다' },

  'Hour': { 'zh-TW': '小時', 'zh-CN': '小时', ja: '時', ko: '시간' },
  'Minute': { 'zh-TW': '分鐘', 'zh-CN': '分钟', ja: '分', ko: '분' },
  'Job config JSON': { 'zh-TW': '工作設定 JSON', 'zh-CN': '任务配置 JSON', ja: 'ジョブ設定JSON', ko: '작업 구성 JSON' },
  'Draft': { 'zh-TW': '草稿', 'zh-CN': '草稿', ja: 'ドラフト', ko: '초안' },
  'Prerelease': { 'zh-TW': '預發布', 'zh-CN': '预发布', ja: 'プレリリース', ko: '프리릴리스' },
  'Pinned SHA-256': { 'zh-TW': '鎖定的 SHA-256', 'zh-CN': '锁定的 SHA-256', ja: '固定SHA-256', ko: '고정 SHA-256' },
  'Input JSON': { 'zh-TW': '輸入 JSON', 'zh-CN': '输入 JSON', ja: '入力JSON', ko: '입력 JSON' },
  'Timeout (ms)': { 'zh-TW': '逾時（毫秒）', 'zh-CN': '超时（毫秒）', ja: 'タイムアウト（ms）', ko: '시간 제한(ms)' },
  'Memory pages': { 'zh-TW': '記憶體頁數', 'zh-CN': '内存页数', ja: 'メモリページ', ko: '메모리 페이지' },
}

const nodeCopy = new WeakMap<Text, { source: string; last: string }>()
const attributeCopy = new WeakMap<Element, Map<string, { source: string; last: string }>>()
const ignoredParents = new Set(['SCRIPT', 'STYLE', 'PRE', 'CODE', 'TEXTAREA'])
const localizableAttributes = ['aria-label', 'title', 'placeholder'] as const

function normalizedLocale(locale: string): ProductLocale {
  return PRODUCT_LOCALES.includes(locale as ProductLocale) ? locale as ProductLocale : 'en'
}

function translateDynamic(locale: ProductLocale, source: string): string | undefined {
  const discovered = /^Discovered (\d+) approved or reviewable manifests\.$/u.exec(source)
  if (discovered) {
    const count = discovered[1]
    if (locale === 'zh-TW') return `已找到 ${count} 份已核准或可審核的 manifest。`
    if (locale === 'zh-CN') return `已找到 ${count} 份已批准或可审核的 manifest。`
    if (locale === 'ja') return `承認済みまたはレビュー可能なmanifestを${count}件検出しました。`
    if (locale === 'ko') return `승인되었거나 검토 가능한 manifest ${count}개를 찾았습니다.`
  }
  const queued = /^Queued (\d+) verified part downloads\.$/u.exec(source)
  if (queued) {
    const count = queued[1]
    if (locale === 'zh-TW') return `已排入 ${count} 個經驗證的分卷下載。`
    if (locale === 'zh-CN') return `已排入 ${count} 个已验证分卷下载。`
    if (locale === 'ja') return `検証済みパートのダウンロードを${count}件キューに追加しました。`
    if (locale === 'ko') return `검증된 파트 다운로드 ${count}개를 대기열에 추가했습니다.`
  }
  const active = /^(\d+) download job\(s\) active or recoverable\.$/u.exec(source)
  if (active) {
    const count = active[1]
    if (locale === 'zh-TW') return `${count} 個下載工作正在執行或可復原。`
    if (locale === 'zh-CN') return `${count} 个下载任务正在运行或可恢复。`
    if (locale === 'ja') return `${count}件のダウンロードジョブが実行中または復旧可能です。`
    if (locale === 'ko') return `${count}개 다운로드 작업이 실행 중이거나 복구 가능합니다.`
  }
  const installed = /^(\d+) \/ (\d+) models installed\./u.exec(source)
  if (installed) {
    const [, current, total] = installed
    if (locale === 'zh-TW') return `${current} / ${total} 個模型已安裝。使用者 manifest 必須參照相鄰且鎖定雜湊的 ONNX 檔案，以及其中一個內建 decoder。`
    if (locale === 'zh-CN') return `${current} / ${total} 个模型已安装。用户 manifest 必须引用相邻且锁定哈希的 ONNX 文件，以及其中一个内置 decoder。`
    if (locale === 'ja') return `${current} / ${total}モデルをインストール済みです。ユーザーmanifestは隣接するハッシュ固定ONNXファイルと内蔵デコーダーのいずれかを参照する必要があります。`
    if (locale === 'ko') return `${current} / ${total}개 모델이 설치되었습니다. 사용자 manifest는 인접한 해시 고정 ONNX 파일과 내장 디코더 중 하나를 참조해야 합니다.`
  }
  return undefined
}

export function translateLiteral(localeValue: string, source: string): string {
  const locale = normalizedLocale(localeValue)
  if (locale === 'en') return source
  return translateDynamic(locale, source) ?? entries[source]?.[locale] ?? source
}

function translatePreservingWhitespace(locale: string, source: string): string {
  const match = /^(\s*)(.*?)(\s*)$/su.exec(source)
  if (!match || !match[2]) return source
  return `${match[1]}${translateLiteral(locale, match[2])}${match[3]}`
}

function shouldIgnore(node: Node): boolean {
  const parent = node.parentElement
  return Boolean(parent?.closest('[data-no-localize], script, style, pre, code, textarea')) || Boolean(parent && ignoredParents.has(parent.tagName))
}

function localizeTextNode(node: Text, locale: string): void {
  if (shouldIgnore(node)) return
  const current = node.data
  const record = nodeCopy.get(node)
  const source = record && current === record.last ? record.source : current
  const next = translatePreservingWhitespace(locale, source)
  nodeCopy.set(node, { source, last: next })
  if (current !== next) node.data = next
}

function localizeAttributes(element: Element, locale: string): void {
  let records = attributeCopy.get(element)
  if (!records) {
    records = new Map()
    attributeCopy.set(element, records)
  }
  for (const name of localizableAttributes) {
    const current = element.getAttribute(name)
    if (!current) continue
    const record = records.get(name)
    const source = record && current === record.last ? record.source : current
    const next = translateLiteral(locale, source)
    records.set(name, { source, last: next })
    if (current !== next) element.setAttribute(name, next)
  }
}

export function localizeTree(root: ParentNode, locale: string): void {
  if (root instanceof Element) localizeAttributes(root, locale)
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT)
  let node = walker.nextNode()
  while (node) {
    if (node instanceof Text) localizeTextNode(node, locale)
    else if (node instanceof Element && !node.closest('[data-no-localize]')) localizeAttributes(node, locale)
    node = walker.nextNode()
  }
}

export function observeLiteralLocalization(root: HTMLElement, getLocale: () => string): () => void {
  let scheduled = false
  const apply = () => {
    if (scheduled) return
    scheduled = true
    queueMicrotask(() => {
      scheduled = false
      localizeTree(root, getLocale())
    })
  }
  localizeTree(root, getLocale())
  const observer = new MutationObserver(apply)
  observer.observe(root, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: [...localizableAttributes] })
  return () => observer.disconnect()
}

const routeTitles: Record<string, string> = {
  '/workspace': 'Your media intelligence workspace',
  '/import': 'Bring large corpora under control',
  '/samples': 'Run the product before supplying your own data',
  '/automation': 'Rate-conscious generation orchestration',
  '/atlas': 'Evidence first. Presentation second.',
  '/detection': 'Multi-model inference with durable checkpoints',
  '/jobs': 'Job Center',
  '/models': 'Verified model registry',
  '/reports': 'Turn immutable evidence into a polished document',
  '/integrations': 'Integration Center',
  '/updates': 'Verified upgrades with a way back',
  '/diagnostics': 'Preview every byte before it leaves',
  '/settings': 'Settings',
}

export function localizedRouteMarker(route: string, locale: string): string {
  const source = routeTitles[route]
  return source ? translateLiteral(locale, source) : ''
}

export function catalogEntries(): Readonly<Record<string, LocalizedEntry>> {
  return entries
}
