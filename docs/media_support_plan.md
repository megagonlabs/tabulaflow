# Multimodal media support — implementation plan

## Status

Proposed. This plan covers model-visible media supplied by the user or discovered
through TabulaFlow's existing filesystem, browser, database, and bulk-processing
workflows. Existing media rendering in the browser output pane remains intact.

## Goals

- Let library callers send text plus images, audio, video, or documents in one
  `ChatSession` turn.
- Let TUI users paste an image into the chat input and see a minimal `[Image #N]`
  placeholder before submission.
- Let the agent inspect supported media on disk, on the web, and in database
  result cells.
- Let row-wise subagents and document extraction process media in bulk without
  loading unbounded payloads into one model request.
- Use Pydantic AI's native multimodal and provider-conversion support rather than
  introducing a parallel message protocol.
- Preserve TabulaFlow's provider and DBMS independence.

## Non-goals

- A persistent attachment button, gallery, or attachment-management panel.
- Automatically sending screenshots after every browser action.
- Automatically sending every binary value returned by a query to the model.
- Database-specific commands that export BLOBs to a server filesystem.
- Storing raw binary data in `_internal.messages`, Markdown trajectories, or
  ordinary text logs.
- Making schema, visualization, transfer, shell, or patch tools interpret media.

## Settled design decisions

1. **Pydantic AI owns the model-facing representation.** Use its
   `BinaryContent`, `ImageUrl`, `AudioUrl`, `VideoUrl`, `DocumentUrl`, and
   `UploadedFile` types, plus its provider adapters and URL-download protections.
2. **TabulaFlow owns source normalization and policy.** It must recognize media
   in files and database cells, verify MIME information, enforce safe roots and
   size limits, convert unsupported image formats where appropriate, and keep
   binary data out of logs.
3. **The TUI stays minimalist.** Pasting an image creates an inline
   `[Image #N]` placeholder that can be removed before submission. No permanent
   attachment UI is added.
4. **Disk access stays with `file_editor`.** A user can also mention or drag a
   file path into the prompt and let the agent inspect it through `view`.
5. **The browser gets one visual action.** Add `browser_screenshot(tab,
   ref=None)`; do not add a separate `browser_view_image` tool. Direct image URLs
   are handled by `browser_navigate`.
6. **Database media stays within `run_query`.** Add explicit
   `include_media=true` support for narrow queries. Do not add
   `inspect_source_media` initially.
7. **Media handling occurs after connector execution.** `run_query` operates on
   the normalized `ExecResult.df`, so no media-specific SQL or DBMS behavior is
   introduced.
8. **Bulk media is explicit.** Row subagents receive only named media columns;
   document extraction receives an explicit text/media source. Neither tool
   guesses across an entire table.

## Target architecture

```text
user paste / ChatSession API / filesystem / browser / database cell
                              |
                              v
            source extraction and media normalization
                              |
                              v
             MIME verification, limits, access policy
                              |
                              v
          Pydantic AI UserContent or native tool content
                              |
                              v
                    provider model adapter
```

Layer ownership:

- `tabulaflow/core/media.py`: pure, provider-independent helpers for signature
  detection, base64/data-URI decoding, media descriptors, and extraction of raw
  bytes from common values such as Hugging Face media structs. It must not depend
  on pandas, Pydantic AI, or the app.
- `tabulaflow/agents/media.py`: safe local loading, request limits, optional
  format conversion, and conversion into Pydantic AI media types.
- `tabulaflow/agents/chat/input.py`: the public text-plus-media chat-input
  contract.
- `tabulaflow/app`: clipboard integration, `[Image #N]` presentation, and
  existing output rendering.

The generic logic currently in `tabulaflow/app/media.py` and
`tabulaflow/app/pane/tables.py` should move down rather than be duplicated. The
app should consume the shared detector while retaining browser-specific payload
and asset-spill behavior.

## Media normalization rules

Resolve a value in this order:

1. Trusted explicit MIME metadata, when present.
2. Actual byte signature, when bytes are available.
3. A structured dataset declaration, such as a Hugging Face Image/Audio value.
4. A filename or URL extension as a fallback.
5. Generic binary when the type remains unknown; do not guess.

When explicit metadata and the byte signature disagree, reject the value or use
the verified signature with a visible warning. Plain strings must not be treated
as base64, paths, or URLs without a strong signal: accept data URIs, explicitly
selected media columns, and values whose role is supplied by the caller.

Pydantic AI already handles provider serialization, supported URL download
paths, SSRF protection for its own downloads, and a 50 MiB URL ceiling. It does
not inspect database cells, magic-sniff local bytes, enforce TabulaFlow's allowed
filesystem roots, impose an aggregate attachment budget, transcode formats, or
manage TabulaFlow's histories and trajectories.

## Phase 1 — Shared media foundation

Create the shared core and agents media modules.

- Move and extend the existing tested media-signature and base64 helpers.
- Define a small immutable descriptor containing media kind, MIME type,
  identifier, optional filename, and byte size.
- Normalize raw bytes, `bytearray`, `memoryview`, Hugging Face
  `{"bytes": ..., "path": ...}` values, explicit data URIs, and trusted URLs.
- Add central limits for per-item bytes, item count, and aggregate request bytes.
- Enforce the existing project/scratch/data root policy before reading a local
  file.
- Use Pydantic AI types as the final model-facing representation.
- Use Pillow for image validation and only the conversions concretely needed by
  supported models. Avoid a native `libmagic` dependency; consider a pure-Python
  signature library later only if the maintained signature table becomes
  burdensome.

**Exit criteria:** existing output-pane media tests pass through the shared
normalizer, and unit tests cover valid, malformed, spoofed, oversized, and
unknown media values.

## Phase 2 — Multimodal chat contract and history

Add a public `ChatInput` carrying text and ordered media items while retaining
plain `str` as a convenience input.

Update `ChatSession.run_stream`, `ChatSession.run`, and the internal turn path to
pass a Pydantic AI `Sequence[UserContent]` at the model boundary. Propagate the
same contract through `AppSession`.

Update lifecycle behavior:

- Store only prompt text and attachment descriptors in `_internal.messages`.
- Keep raw content in native in-memory history or a session-scoped,
  content-addressed media cache when a durable local reference is required.
- Record descriptors, identifiers, sizes, and hashes in trajectories, never raw
  bytes or base64.
- Preserve media in the active and configured recent turns during compaction;
  replace older media with omission descriptors after checkpointing.
- Estimate pending media separately rather than estimating serialized base64 as
  ordinary text.
- Preserve attachment ordering and include a textual identifier so the model can
  refer to each item unambiguously.

**Exit criteria:** a library caller can submit each supported modality, continue
the conversation, trigger compaction, switch models, and save a trajectory
without losing history validity or leaking bytes.

## Phase 3 — Minimal TUI image paste

Implement pasted images as the only initial attachment UX.

- Read image clipboard data through a platform adapter.
- Insert `[Image #1]`, `[Image #2]`, and so on at the input position.
- Keep the image payload out of the visible text while retaining ordered backing
  media state.
- Allow normal deletion/backspace behavior to remove a pending image.
- Clear pending images only after the submission is accepted.
- Show a concise preflight error for unsupported formats or size limits.
- Preserve ordinary text paste and existing paste-token behavior.

Implement and test adapters independently for macOS, Windows, Wayland, and X11;
unsupported environments should leave text input unaffected and explain that the
user can save or drag the image path instead. Do not add a permanent attach
button or attachment pane.

**Exit criteria:** pasting one or several images produces placeholders, submits
text and images in order, supports removal, and degrades cleanly where binary
clipboard access is unavailable.

## Phase 4 — Media on disk and the web

### `file_editor`

Extend only `view`:

- Continue returning text for text files.
- Return recognized images, audio, video, and documents as native model content.
- For PDFs, retain extracted text when useful and make the original document or
  rendered pages available when the PDF is scanned.
- Keep `write_file` and `str_replace` text-only.
- Return a concise descriptor as the ordinary tool result so trajectories and
  progress output remain readable.

### Browser

- Add `browser_screenshot(tab, ref=None)` to capture the current viewport or one
  referenced element/region.
- Make `browser_navigate` recognize direct image responses and expose them as
  native model content.
- Use screenshot inspection explicitly for canvases, maps, charts, visual-only
  layouts, and images without useful accessibility text.
- Keep accessibility snapshots as the default and never attach screenshots
  automatically.
- Handle scanned PDFs through document input or bounded rendered pages.

**Exit criteria:** the agent can inspect a local image, a scanned local PDF, a
direct image URL, an embedded page image, and a canvas-rendered visualization.

## Phase 5 — Media in database query results

Add `include_media: bool = false` to the model-facing `run_query` variants.
Normal query execution and output storage remain unchanged.

With `include_media=true`:

- Examine only values already returned in `ExecResult.df`.
- Require a deliberately narrow result and enforce strict cell-count and byte
  limits.
- Recognize actual binary values, declared media structs, and explicit data URIs.
- Return normal textual rows plus native media content for accepted cells.
- Describe omitted, unknown, oversized, or unsupported cells without including
  their raw representation.
- Do not automatically dereference path or URL strings; paths belong to
  `file_editor`, and URLs belong to browser/media URL handling.
- Do not execute extra SQL, write temporary files through the DBMS, or use
  database-specific export syntax.

The expected agent workflow is to identify a row using an ordinary query, then
issue a narrow query selecting the desired media value with
`include_media=true`.

Add a separate result-cell inspection tool only if real workflows require
inspecting expensive, volatile, or non-reproducible stored results without
rerunning their query.

**Exit criteria:** the same host-side behavior works for BLOB/BYTEA/BINARY values
from representative SQL connectors and for Hugging Face media structs, without
connector-specific branches.

## Phase 6 — Bulk multimodal processing

### `run_subagent_for_each_row`

- Add explicit media-column selection.
- Build each row prompt from rendered text plus normalized native media.
- Bound media items and bytes per row and across concurrent workers.
- Sample and verify a subset before large media fan-outs, consistent with the
  existing large-task policy.
- Write only descriptors to row trajectories and exception metadata.

### `extract_rows_from_documents`

Generalize its source contract beyond a string-only `content` column while
keeping modality handling explicit:

- Text, HTML, and Markdown use the current structure-aware splitter.
- Text PDFs use extraction; scanned PDFs use bounded page images.
- Images run as one task or bounded tiles when necessary.
- Audio uses provider-native input or bounded time segments.
- Video uses provider-native input where supported; otherwise a later fallback
  may use sampled frames and an audio transcript.

Ship image and PDF extraction before audio and video bulk processing. The latter
have greater provider variance, memory pressure, and cost.

**Exit criteria:** media-bearing rows can be classified or expanded concurrently
with deterministic limits, cancellation, progress reporting, and typed scalar
write-back.

## Phase 7 — Provider compatibility and hardening

- Test OpenAI Responses, Anthropic, and Google request conversion for every
  supported modality.
- Use provider/model capability metadata when available; otherwise normalize the
  provider's rejection into a clear user-facing error rather than maintaining a
  broad model-name heuristic table.
- Verify multimodal tool returns as well as direct user prompts for each provider.
- Test malformed media, MIME spoofing, decompression bombs, excessive dimensions
  or duration, unsafe paths, SSRF, redirects, cancellation, and concurrent memory
  pressure.
- Add per-modality usage and failure metrics without recording payloads.
- Document provider-specific limitations and deterministic fallbacks.
- Revisit provider file uploads only when repeated large-media turns demonstrate
  a need; `UploadedFile` is provider-bound and should not be the initial storage
  abstraction.

**Exit criteria:** unsupported combinations fail before or at the provider
boundary with actionable errors; no raw media appears in logs, workspace message
text, or Markdown trajectories.

## Tools intentionally unchanged

The following may preserve, reference, or present media but should not interpret
it for the model:

- `connect_data_source`
- `transfer_source_table`
- `create_parameterized_source`
- `get_db_document`
- `get_table_schema`
- `get_column_json_schema`
- `get_schema`
- `add_canonical_name`
- `render_chart`
- `render_map`
- `render_graph`
- `show_artifacts`
- `execute_bash`
- `apply_patch`

Schema tools should describe binary/media-bearing columns. Transfer and connect
paths should preserve supported binary values. Rendering and `show_artifacts`
remain user-presentation paths; generated visuals do not need to be fed back to
the model by default.

## Recommended delivery order

Deliver Phases 1–3 together as the first user-visible milestone: shared media,
correct chat history, and paste-image support. Phase 4 then gives the autonomous
agent access to disk and web media. Phase 5 adds narrow DB media inspection
without a new tool. Phase 6 is a separate bulk-processing milestone. Phase 7
hardening runs throughout, with its final provider matrix gating general release.
