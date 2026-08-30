# AgentCore Index

This is the content-oriented map of the AgentCore knowledge base. Read this first when looking for relevant pages.

## System Pages

- [README](README.md): overview of the AgentCore knowledge system.
- [Hot Cache](hot-cache.md): compact current-state memory for future sessions.
- [Blockers](blockers.md): major unresolved questions and external blockers.
- [Log](log.md): append-only history of knowledge-base activity.

## Intake

- [Inbox](inbox/README.md): temporary holding area for unprocessed notes and materials.
- [Email Inbox Records](inbox/email/README.md): normalized inbound email records.
- [Telegram Inbox Records](inbox/telegram/README.md): normalized Telegram messages for async triage.
- [Drive Inbox Records](inbox/drive/README.md): normalized inbound Google Drive document records.
- [Photo Inbox Records](inbox/photos/README.md): normalized inbound Android photo upload records.
- [Email Task Queue](inbox/tasks/README.md): queued tasks derived from inbound task intent.
- [Sources](sources/README.md): raw source material and source references.

## Knowledge

- [Projects](knowledge/projects/): active and historical project pages.
- [Brian Personal Operating System](knowledge/projects/personal-operating-system.md): operating hub for diet, scheduling, school logistics, app ideas, and personal management.
- [Family Admin System](knowledge/projects/family-admin-system.md): administrative-assistant system for Brian's documents, family logistics, Drive organization, and action tracking.
- [Checkers Web Game](knowledge/projects/checkers-web-game.md): two-player browser checkers, live at https://scottishramp.github.io/agentcore-checkers/
- [YouVersion Verse of the Day](knowledge/projects/youversion-verse-of-the-day.md): daily Bible verse delivery via YouVersion Platform + Telegram.
- [Domain Management](knowledge/projects/domain-management.md): GoDaddy delegate access and Brian's domain inventory.
- [Burning Altar Blog](knowledge/projects/burningaltar-blog.md): Brian's public writing at https://burningaltar.com/ (Hugo on GitHub Pages).
- [Burning Altar tags](knowledge/playbooks/burningaltar-tags.md): closed tag vocabulary and publish rules for burningaltar.com.
- [Clients](knowledge/clients/): client and sponsor pages.
- [People](knowledge/people/): people and stakeholder pages.
- [Brian Herbert](knowledge/people/brian-herbert.md): trusted client and primary administrative-assistance context.
- [Brian Herbert Food Log](knowledge/people/brian-herbert-food-log.md): rolling meal intake log with rough estimates.
- [Kristin Herbert](knowledge/people/kristin-herbert.md): Brian's spouse and immediate family context.
- [Herbert Children](knowledge/people/herbert-children.md): Brian and Kristin's children for family administration context.
- [Family Facts](knowledge/people/family-facts.md): household facts learned automatically by the email evaluator.
- [Important Contacts](knowledge/people/important-contacts.md): Brian's saved family phone/email favorites.
- [Medical and Drs](knowledge/people/medical-and-drs.md): family providers, insurance, allergies, compact medical history (passwords not stored).
- [Brian Learned Facts](knowledge/people/brian-learned-facts.md): dated facts about Brian learned automatically by the nightly mailbox sweep and calendar ingest.
- [Upcoming Schedule](knowledge/calendar/upcoming.md): near-term calendar view regenerated nightly from Brian's shared Google Calendar.
- [2026-27 School Roster](knowledge/school/2026-27-roster.json): schools, grades, and teacher names for the current year.
- [School digest Google Doc registry](knowledge/school/digest-doc.json): live Doc id and share link.
- [School Communications Digest](knowledge/projects/school-comms-digest.md): daily Telegram digest of kids' school email.
- [Life 2026](knowledge/documents/life-2026.md): Brian's shared life-planning doc index and important dates.
- [Life 2025](knowledge/documents/life-2025.md): 2025 journal index — family dates, work/move timeline, Mom's Royersford address.
- [Stuff We Own](knowledge/household/stuff-we-own.md): house, vehicles, and appliance inventory from Brian's shared Drive doc.
- [Knowledge Content Ingest](knowledge/playbooks/knowledge-content-ingest.md): periodic Gmail/Telegram/shared-Drive content ingest playbook.
- [Organizations](knowledge/organizations/): organizations relevant to projects.
- [Architecture](knowledge/architecture/): current AgentCore system architecture, communication surfaces, workflows, data stores, and operational invariants.
- [AgentCore System Architecture](knowledge/architecture/system-architecture.md): Telegram + email async agent, workflows, secrets, and update requirements.
- [Chatbot Version Registry](knowledge/architecture/chatbot-version.md): fast router semver, context bundle version, changelog, and `version` command.
- [Communications](knowledge/communications/README.md): deterministic communication ingestion summaries, email thread state, and ledgers.
- [Telegram Transcript](knowledge/communications/telegram-transcript.md): durable allowed-message transcript for async Cursor review context.
- [Concepts](knowledge/concepts/): reusable ideas, frameworks, and research themes.
- [UX Message Design](knowledge/concepts/ux-message-design.md): precise failure classification for user-facing status messages.
- [Decisions](knowledge/decisions/): decision records and rationale.
- [Static-first Web Apps](knowledge/decisions/2026-04-24-static-first-web-apps.md): decision to favor dependency-free static apps for small public deliverables.
- [AgentCore Repo Topology](knowledge/decisions/2026-04-25-agentcore-control-repo-topology.md): keep this repository as control repo with separate delivery repos.
- [Playbooks](knowledge/playbooks/): repeatable methods and operating procedures.
- [Telegram Fast Router](knowledge/playbooks/telegram-fast-router.md): instant family 1:1 chat via Telegram bot and Vercel webhook.
- [Public Static Web App](knowledge/playbooks/public-static-web-app.md): fast path for building, verifying, and publishing static web apps.
- [GitHub Pages Deployment](knowledge/playbooks/github-pages-deployment.md): exact steps for deploying to GitHub Pages including auth, repo creation, and build triggering.
- [Burning Altar tags](knowledge/playbooks/burningaltar-tags.md): closed tag vocabulary and publish rules for burningaltar.com.
- [Email Operations](knowledge/playbooks/email-ops.md): operational policy and workflow for async client communication by email.
- [Brian Gmail Mailbox](knowledge/playbooks/brian-gmail-mailbox.md): read, label, archive, and trash access to `briandherbert@gmail.com`.
- [School Communications Digest](knowledge/playbooks/school-comms-digest.md): daily child-grouped school email digest on Telegram.
- [Mailbox and Calendar Learning Loop](knowledge/playbooks/mailbox-learning-loop.md): nightly whole-mailbox sweep, calendar ingest, and the ask-Brian question loop that turns his answers into durable sender policy.
- [Agentic Jobs with Cursor CLI](knowledge/playbooks/agentic-jobs-cursor-cli.md): pattern and recipe for creating scheduled LLM jobs in GitHub Actions.
- [Email to Cursor CLI Bridge](knowledge/playbooks/email-to-cursor-cli-bridge.md): guarded phase-2 design for intent-to-automation handoff.
- [Drive Document Organization](knowledge/playbooks/drive-document-organization.md): Drive-backed source storage with repo metadata for documents, scans, and photo intake.
- [Communication Intake Contracts](knowledge/playbooks/communication-intake-contracts.md): canonical channel contracts, intent classes, and deterministic reply reason codes.
- [GoDaddy Delegate Access](knowledge/playbooks/godaddy-delegate-access.md): sign in as AgentCore and switch into Brian's GoDaddy account.

## Outputs

- [Briefs](outputs/briefs/): concise briefings.
- [Memos](outputs/memos/): written recommendations and internal memos.
- [Analyses](outputs/analyses/): deeper analytical artifacts.
- [Decks](outputs/decks/): slide-style or presentation-ready materials.

## Maintenance

- [Audits](audits/README.md): knowledge-base health checks.
- [Templates](templates/): reusable page templates.
