# NanoDet multi-detector production evidence

- Verified (UTC): `2026-07-21T08:47:47+00:00`
- Analysis batch: `detection-233b11b0368c4b9b98eb6cc148b25fde84ee5e94`
- YOLOX workflow run: `29812888677`
- NanoDet workflow run: `29812888709`
- Publisher workflow run: `29813188073`
- Writeback commit: [`9bef82a565ac25db97708628acfe8f56e1cc3b29`](https://github.com/PME26Elvis/media-experiment-ledger/commit/9bef82a565ac25db97708628acfe8f56e1cc3b29)
- Production Release: [media-detection-all-2026-07-13-v1](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-detection-all-2026-07-13-v1)
- Canonical images compared: **387**
- YOLOX detections: **1,533**
- NanoDet detections: **3,243**
- Matched same-class boxes: **902**
- Mean disagreement: **0.557421**
- Agreement states: `{"both-empty": 13, "both-nonempty": 307, "nanodet-only-nonempty": 61, "yolox-only-nonempty": 6}`
- Release assets: **13 ZIP files**, **812,138,310 bytes**
- Representative repository previews: **20**
- Detector Lab: [https://pme26elvis.github.io/media-experiment-ledger/detector-lab/](https://pme26elvis.github.io/media-experiment-ledger/detector-lab/)
- Deployed JSON: [https://pme26elvis.github.io/media-experiment-ledger/data/detection/latest.json](https://pme26elvis.github.io/media-experiment-ledger/data/detection/latest.json)
- Atlas index SHA unchanged across detector writeback: `3778183686ca7603e3c6d49013ff643182445cec`

This report records agreement/disagreement observations from two COCO-pretrained detectors. The generated corpus has no human-verified COCO ground truth, so this is not an accuracy, precision, recall, false-positive, or mAP benchmark.

The complete machine-readable evidence is stored in `NANODET_PRODUCTION_EVIDENCE.json`.
