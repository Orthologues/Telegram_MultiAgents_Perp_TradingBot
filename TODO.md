# TODO List

Date: 22.07.2026
Implementation progress: <b>0/2</b> priority tasks complete

This is a human-reviewed scaffold, not live-trading software.

## 1. Telethon Image Hydrator

- Use the authorized Telegram user session to retrieve media by `chat_id` and
  message ID.
- Validate, hash, and archive images in private S3; attach provenance to the
  envelope before metadata, reply-tree, QWEN, and cursor processing.
- Send current and chronological parent images to QWEN as multimodal inputs.
- Add network-free tests for success, failures, limits, duplicate hashes, and
  parent-image prompts.

**Complete when:** every available current and parent image reaches QWEN with
an ID, hash, and private S3 provenance before the cursor advances.

## 2. Authentic Serial RAG Examples

- Add authorized chronological text/image sequences for every owner and
  channel, including multi-level replies.
- Label `new_signal`, `continuation`, `duplicate`, and `ambiguous` cases.
- Preserve omitted TP/SL updates, intended orders, media provenance, and
  correct or incorrect outcomes; redact unnecessary personal data.
- Version the JSON profiles and add replay fixtures and evaluation metrics.

**Complete when:** every owner QWEN agent has a small, human-reviewed,
replayable serial RAG set with authentic text/image patterns.

## Further Priorities

- Replace in-memory test storage with production S3 and DynamoDB adapters.
- Implement model-specific Bedrock QWEN and Ministral multimodal adapters.
- Rebuild owner reply-tree indexes safely after worker restarts without DynamoDB
  reads for live prompt context.
- Add end-to-end replay tests before any live execution experiment.
