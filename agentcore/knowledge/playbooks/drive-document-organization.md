# Drive Document Organization

## Purpose

Use AgentCore Google Drive for source files and this repository for metadata. This keeps sensitive documents out of git while preserving enough structure for search, follow-up, and administrative continuity.

## Default Storage Split

- Store source documents, scans, photos, PDFs, and copied shared files in AgentCore Google Drive.
- Store document metadata, indexes, action notes, and workflow decisions in `agentcore/`.
- Store only minimal sensitive details in Markdown unless Brian explicitly asks for richer summaries.
- Treat Brian-shared Google resources as read surfaces unless Brian explicitly grants edit authority. Use AgentCore's own Google Drive/Docs/Sheets/Tasks space for writable working files, indexes, exports, and organized copies.

## Proposed Drive Folders

- `Inbox`
- `Family`
- `Kids`
- `Home`
- `Finance`
- `Health`
- `School`
- `Legal`
- `Vehicles`
- `Travel`
- `Work`
- `Archive`

Adjust this taxonomy after Brian answers the setup questions.

## Metadata Schema

Capture these fields when available:

- Title
- Document date
- Received or scanned date
- People
- Category
- Source
- Google Drive link
- Status
- Due date
- Renewal date
- Sensitivity
- Tags
- Notes
- Action required
- Next follow-up

## Intake Workflow

1. Receive or discover a document through email, Drive share, Android photo upload, or manual file drop.
2. Prefer discovering new materials through Drive `sharedWithMe`; fixed intake folders are optional for future high-volume workflows.
3. Put new files in the Drive `Inbox` unless they are already organized.
4. Extract metadata and create or update the relevant Markdown index.
5. Identify whether the item is reference-only or action-required.
6. Move or copy the file to the target Drive folder if AgentCore has authority.
7. Email Brian only when the item needs a decision, has an urgent deadline, or completes a batch that Brian asked to review.

## Naming Convention

Default file name:

```text
YYYY-MM-DD - Person - Category - Short Title
```

Use the document date when known; otherwise use the scan or received date.

## Safety Rules

- Do not commit source documents, scans, photos, or credentials.
- For medical, legal, identity, finance, or children-related documents, prefer metadata plus Drive links over detailed content copied into Markdown.
- When authority is unclear, preserve a pointer and ask Brian before moving, copying, deleting, or sharing files.
- Treat `briandherbert@gmail.com` as the trusted client channel for clarification.
