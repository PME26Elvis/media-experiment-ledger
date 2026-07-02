# Codex prompt for generating Agnes media prompt banks

Use this prompt in Codex from the project root.

```text
You are working in a repository for an Agnes AI media-harvesting experiment. Your job is to create high-quality prompt banks for text-to-video and text-to-image generation.

Critical execution rule: use 3 parallel subagents. Each subagent must independently draft a diverse subset, then the main agent must merge, deduplicate, normalize IDs, and run quality checks. Do not do this as one monolithic pass.

Repository context:
- The harvester reads `prompts/video_prompts.jsonl` and `prompts/image_prompts.jsonl`.
- Each JSONL line must be a JSON object with fields: `id`, `category`, `prompt`.
- Final target: exactly 7 video prompts and exactly 550 image prompts.
- Prompts should be English, concise, visually specific, and not overly long.
- Do not include disallowed content, real-person likeness requests, copyrighted character names, logos, explicit sexual content, gore, extremist content, weapons fetish content, political persuasion, or private/personal data.
- Prefer original, safe, commercially usable concepts.
- Avoid near-duplicates. Similar topic is okay only if composition, subject, style, and use case differ clearly.
- Make the prompts varied across domains, scenes, camera/composition, lighting, and style.

Subagent split:
1. Subagent A: product, architecture, UI/app assets, e-commerce, marketing, editorial design.
2. Subagent B: nature, travel, food, lifestyle, music, fashion, Taiwan/Asia-inspired urban scenes.
3. Subagent C: sci-fi, fantasy, educational diagrams as visual scenes, game assets, abstract concept art, high-density scenes.

Video prompts:
- Exactly 7 prompts total.
- Each should describe subject + action + scene + camera movement + lighting + style.
- Make them suitable for 5–10 second text-to-video clips.
- Avoid text-heavy scenes because video models often render text poorly.

Image prompts:
- Exactly 550 prompts total.
- Use category-balanced distribution; no single category should dominate excessively.
- Each prompt should generally follow:
  `[subject] + [scene/environment] + [visual style] + [lighting] + [composition] + [quality/detail]`
- Keep most prompts around 20–45 words.
- Include enough detail for high-quality 2K image generation.
- Avoid requiring exact typography; if a poster or UI asset needs text space, say “blank area for text” rather than specifying text.

Progress and quality workflow:
1. Read existing files first if present.
2. Create or update `prompts/GENERATION_PROGRESS.md` with current counts, category counts, and remaining work.
3. Generate in batches. Each subagent writes a temporary draft file under `prompts/drafts/`.
4. Main agent merges drafts into final JSONL files.
5. Validate:
   - valid JSONL
   - unique ids
   - exactly 7 video prompts
   - exactly 550 image prompts
   - no empty prompts
   - no prompt over 70 words
   - no obvious near-duplicates
6. Write `prompts/PROMPT_BANK_AUDIT.md` explaining category distribution and any quality filters applied.

ID format:
- Video: `v001` to `v007`
- Image: `i0001` to `i0550`

Now perform the task. Do not stop after planning; actually create/modify the files.
```
