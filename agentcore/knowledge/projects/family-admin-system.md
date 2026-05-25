# Family Admin System

## Objective

Build an iterative administrative-assistant system for Brian Herbert that can intake documents, photos, emails, and shared materials; organize files in AgentCore Google Drive; and preserve actionable metadata in this repository.

## Status

- Phase: discovery and operating-model setup.
- Trusted client email: `briandherbert@gmail.com`.
- Drive source: `Life 2026` has been shared with viewer access; use its first couple paragraphs for initial context about Brian and his kids when Drive access is available in the working environment.

## Scope

- Document filing and categorization.
- Metadata extraction and indexing.
- Family and children-related administrative context.
- Action identification: deadlines, signatures, payments, renewals, missing information, and follow-up questions.
- Email-based questions, status updates, and digests.
- Android photo intake workflow once Brian decides the capture path.

## System Boundary

- Repository: durable metadata, operating memory, action queues, decisions, and summaries.
- AgentCore Google Drive: actual source documents, scans, photos, organized folders, and copied files where copying is authorized.
- Email: trusted communication channel for questions, setup answers, status digests, and urgent follow-up.

## First Iteration Acceptance Criteria

- Brian answers the setup questions.
- AgentCore has a clear intake path for Android document photos.
- A top-level Drive folder taxonomy is chosen or accepted.
- A metadata schema is defined and tested on a small pilot batch.
- Action items can be distinguished from reference-only documents.

## Open Decisions

- Preferred Drive folder taxonomy.
- Whether AgentCore should copy shared files into its own Drive organization or store pointers only.
- Photo landing zone for Android uploads.
- Digest cadence and urgency thresholds.
- Sensitive-document exclusions or minimal-record rules.
