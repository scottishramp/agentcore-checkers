---
title: Burning Altar tags
type: playbook
status: active
created: 2026-08-30
updated: 2026-08-30
confidence: high
related:
  - ../projects/burningaltar-blog.md
---

# Playbook: Burning Altar tags

Closed vocabulary for https://burningaltar.com/. Assign tags when publishing a post to `scottishramp/burningaltar`. Do not invent ad-hoc tags in frontmatter.

## Vocabulary

| Slug | Name | Use when the post is about |
| --- | --- | --- |
| `ai` | AI | Tools, models, agents, and the work of building with them |
| `family` | Family | Household, marriage, parenting, and home life |
| `health` | Health | Body, medicine, food, fitness, sleep, and mental health |
| `philosophy` | Philosophy | Meaning, ethics, first principles, and how to think. Not primarily faith |
| `theology` | Theology | God, scripture, church, and the practice of faith |

Frontmatter uses lowercase slugs: `tags = ["ai", "philosophy"]`. The site displays `#AI`, `#Family`, and so on.

## Assignment rules

1. Every published post gets at least one tag. Usual range is 1–3.
2. Tag the subject, not a passing mention or a single link.
3. If the post is about God, scripture, church, or faith practice, use `theology`. Use `philosophy` for meaning/ethics/first-principles that are not primarily faith.
4. A post may carry both `ai` and `philosophy` (or `theology`) when both are real subjects.
5. If Brian writes tags in [Blog thoughts](https://docs.google.com/document/d/1qkV4rFFANZ8ybZl3dKRsfyOtTFIC_hyyLlYTJuAA_JQ/edit), use those. Otherwise infer from the rules above.
6. Do not reuse a tag slug as a post slug. `/blog/ai/` is the AI filter, not a post.

## Adding a tag

Only when Brian names one, or a ready post has no fit in the current set:

1. Add `[[params.tagVocab]]` in `burningaltar/hugo.toml`.
2. Create `content/tags/<slug>/_index.md` with `title` set to the display name and a one-line description.
3. Update this playbook, the delivery-repo README, and `knowledge/projects/burningaltar-blog.md`.

## Surfaces

- Home and `/blog/` show the full vocabulary, including unused tags.
- `/blog/<slug>/` is the filtered title list.
- Each post (home scroll and permalink) shows only the tags on that post.
