# Prompt Bank Audit

Audit date: 2026-06-29

## Source Workflow

The final prompt banks were produced from three independent draft batches:

- Subagent A drafted product, architecture, UI/app assets, e-commerce, marketing, and editorial design prompts.
- Subagent B drafted nature, travel, food, lifestyle, music, fashion, and Taiwan/Asia-inspired urban prompts.
- Subagent C drafted sci-fi, fantasy, educational visual scenes, game assets, abstract concept art, and high-density scene prompts.

The main merge pass normalized final IDs, converted underscore category separators to hyphen separators, applied targeted safety wording cleanup, and wrote the final JSONL banks.

## Final Counts

- `prompts/video_prompts.jsonl`: 7 prompts
- `prompts/image_prompts.jsonl`: 550 prompts

## Video Category Distribution

- educational-video: 1
- fantasy-video: 1
- marketing-video: 1
- nature: 1
- product-video: 1
- sci-fi-video: 1
- taiwan-asia-urban: 1

## Image Category Distribution

- abstract-concept: 30
- architecture: 28
- ecommerce: 30
- editorial-design: 30
- educational-diagram: 31
- fantasy: 31
- fashion: 26
- food: 26
- game-asset: 30
- high-density: 30
- lifestyle: 26
- marketing: 32
- music: 26
- nature: 27
- product: 32
- sci-fi: 31
- taiwan-asia-urban: 26
- travel: 26
- ui-app-assets: 32

No image category exceeds 32 prompts, keeping the largest category below 6% of the 550-prompt bank.

## Quality Filters Applied

- Reassigned final video IDs from `v001` through `v007`.
- Reassigned final image IDs from `i0001` through `i0550`.
- Required every JSONL line to contain exactly `id`, `category`, and `prompt`.
- Rewrote negative exclusion phrasing into positive generic wording.
- Replaced marketing uses of `campaign` with `marketing` wording to avoid political-persuasion ambiguity.
- Removed prompt text that explicitly mentioned excluded terms such as `celebrity`, `brand`, and `gore`, even where the draft used them only as exclusions.
- Preserved concise prompt length; final maximum prompt length is 28 words.

## Validation Results

Final validation passed:

- Valid JSONL syntax.
- Unique IDs.
- Exact target count of 7 video prompts.
- Exact target count of 550 image prompts.
- No empty prompt strings.
- No prompt over 70 words.
- No exact duplicate prompts.
- No obvious near-duplicates found by token-overlap screening.
- No flagged terms from the safety scan remained in final prompt text.
