# Codex prompt for generating media prompt banks

Use this prompt in Codex from the project root.

```text
You are working in a repository for a structured media-generation experiment. Create high-quality prompt banks for text-to-video and text-to-image generation.

Critical execution rule: use 3 parallel subagents. Each subagent must independently draft a diverse subset, then the main agent must merge, deduplicate, normalize IDs, and run quality checks. Do not do this as one monolithic pass.

Repository context:
- The runner reads `prompts/video_prompts.jsonl` and `prompts/image_prompts.jsonl`.
- Each JSONL line must be an object with `id`, `category`, and `prompt`.
- Final target: exactly 7 video prompts and exactly 550 image prompts.
- Prompts should be English, concise, visually specific, safe, original, and suitable for commercial experimentation.
- Avoid near-duplicates, real-person likeness requests, copyrighted character names, logos, explicit sexual content, gore, extremist content, political persuasion, or private data.

Subagent split:
1. Product, architecture, UI/app assets, e-commerce, marketing, editorial design.
2. Nature, travel, food, lifestyle, music, fashion, Taiwan/Asia-inspired urban scenes.
3. Science fiction, fantasy, educational visual scenes, game assets, abstract concepts, high-density scenes.

Video requirements:
- Exactly 7 prompts.
- Include subject, action, scene, camera movement, lighting, and style.
- Target short 5–10 second clips.
- Avoid text-heavy scenes.

Image requirements:
- Exactly 550 prompts.
- Keep category distribution balanced.
- Most prompts should be 20–45 words and remain below 70 words.
- Prefer subject + environment + style + lighting + composition + detail.
- Use “blank area for text” instead of requiring exact typography.

Workflow:
1. Read existing files.
2. Update `prompts/GENERATION_PROGRESS.md`.
3. Draft in parallel under `prompts/drafts/`.
4. Merge and normalize IDs.
5. Validate JSONL, counts, uniqueness, length, empty values, and near-duplicates.
6. Update `prompts/PROMPT_BANK_AUDIT.md`.

IDs:
- Video: `v001` to `v007`.
- Image: `i0001` to `i0550`.

Perform the work rather than stopping after planning.
```
