<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface Props {
  eyebrow: string
  title: string
  subtitle: string
  icon: string
  color?: string
}

const props = defineProps<Props>()
const { locale } = useI18n()
const detectionSubtitles: Record<string, string> = {
  en: 'Multi-model inference with durable checkpoints. Run verified image and video detection, export structured evidence, compare providers, and review crops without repeating completed inference.',
  'zh-TW': '具耐久檢查點的多模型推論。執行經驗證的影像與影片偵測、匯出結構化證據、比較執行環境，並在不重複已完成推論的情況下檢視裁切結果。',
  'zh-CN': '具持久检查点的多模型推理。运行已验证的图像与视频检测、导出结构化证据、比较运行环境，并在不重复已完成推理的情况下查看裁剪结果。',
  ja: '耐久チェックポイント付きマルチモデル推論。検証済みの画像・動画検出、構造化証拠の書き出し、実行環境の比較、完了済み推論を繰り返さないクロップ確認を行います。',
  ko: '내구성 체크포인트 기반 다중 모델 추론. 검증된 이미지·비디오 감지, 구조화 증거 내보내기, 실행 환경 비교, 완료된 추론을 반복하지 않는 크롭 검토를 제공합니다.',
}
const effectiveSubtitle = computed(() => props.eyebrow === 'Detection Studio'
  ? detectionSubtitles[String(locale.value)] ?? detectionSubtitles.en
  : props.subtitle)
</script>
<template><div class="mb-8"><v-chip :color="color ?? 'primary'" variant="tonal" :prepend-icon="icon" class="mb-4">{{ eyebrow }}</v-chip><h1 class="page-title">{{ title }}</h1><p class="page-subtitle mt-4">{{ effectiveSubtitle }}</p><slot /></div></template>
