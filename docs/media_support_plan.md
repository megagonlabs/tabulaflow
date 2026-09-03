# Multimodal media support — implementation plan

## Status

Phases 1–4B are implemented; Phases 4C–7 are proposed. This plan covers
model-visible media supplied by the user or discovered through TabulaFlow's
existing filesystem, browser, database, and bulk-processing workflows. Existing
media rendering in the browser output pane remains intact.

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
  detection and extraction of raw bytes from base64/data URIs and common values
  such as Hugging Face media structs. It must not depend on pandas, Pydantic AI,
  or the app.
- `tabulaflow/agents/media.py`: media validation, optional format conversion,
  PDF page selection, and conversion into Pydantic AI media types.
- `tabulaflow/agents/chat/input.py`: the public alias for Pydantic AI's ordered
  text-plus-media input and safe descriptor rendering.
- `tabulaflow/app`: clipboard integration, `[Image #N]` presentation, and
  existing output rendering.

The generic logic previously in `tabulaflow/app/media.py` and
`tabulaflow/app/pane/tables.py` has moved down rather than being duplicated. The
app consumes the shared detector while retaining browser-specific payload and
asset-spill behavior.

## Media normalization rules

Resolve a value in this order:

1. Actual byte signature, when bytes are available.
2. Trusted explicit MIME metadata, when present.
3. A structured dataset declaration, such as a Hugging Face Image/Audio value.
4. A filename or URL extension as a fallback.
5. Generic binary when the type remains unknown; do not guess.

When explicit metadata and the byte signature disagree, the verified signature
wins. Plain strings must not be treated as base64, paths, or URLs without a
strong signal: accept data URIs, explicitly selected media columns, and values
whose role is supplied by the caller.

Pydantic AI already handles provider serialization, supported URL download
paths, SSRF protection for its own downloads, and a 50 MiB URL ceiling. It does
not inspect database cells, magic-sniff local bytes, enforce TabulaFlow's allowed
filesystem roots, impose an aggregate attachment budget, transcode formats, or
manage TabulaFlow's histories and trajectories.

## Phase 1 — Shared media foundation

Create the shared core and agents media modules.

- Move and extend the existing tested media-signature and base64 helpers.
- Represent detected formats with a small immutable MIME type and suffix value;
  use Pydantic AI's own content classes rather than duplicating them.
- Normalize raw bytes, `bytearray`, `memoryview`, Hugging Face
  `{"bytes": ..., "path": ...}` values, and explicit data URIs.
- Use Pydantic AI types as the final model-facing representation.
- Use Pillow for image validation and only the conversions concretely needed by
  supported models. Avoid a native `libmagic` dependency; consider a pure-Python
  signature library later only if the maintained signature table becomes
  burdensome.

**Exit criteria:** existing output-pane media tests pass through the shared
normalizer, and unit tests cover valid, malformed, spoofed, decompression-bomb,
and unknown media values.

## Phase 2 — Multimodal chat contract and history

Expose `ChatInput` as `str | Sequence[str | BinaryContent]`, retaining plain
strings as the convenient common case and accepting only the bytes-backed media
contract TabulaFlow currently uses.

Update `ChatSession.run_stream`, `ChatSession.run`, and the internal turn path to
pass plain text or Pydantic AI `BinaryContent` directly to the model boundary.
Propagate the same contract through `AppSession`.

Lifecycle behavior:

- Store only prompt text and attachment descriptors in `_internal.messages`.
- Keep raw content only in native in-memory model history.
- Record descriptors and sizes in trajectories, never raw bytes or base64.
- Preserve media in the active and configured recent turns during compaction;
  replace older media with descriptors after checkpointing.
- Estimate history from safe descriptors rather than serialized base64; actual
  provider usage remains the anchor after each completed request.
- Preserve content ordering and native media objects.

**Exit criteria:** a library caller can submit each supported modality, continue
the conversation, trigger compaction, switch models, and save a trajectory
without losing history validity or leaking bytes.

## Phase 3 — Minimal TUI image paste

Pasted images are the initial attachment UX.

- Read image clipboard data through Pillow's cross-platform `ImageGrab` support.
- Insert `[Image #1]`, `[Image #2]`, and so on at the input position.
- Keep the image payload out of the visible text while retaining ordered backing
  media state.
- Highlight active image references with the inline-code color; markers recalled
  from history remain unstyled plain text.
- Keep cursor and selection endpoints outside active references, and treat the
  references atomically for backspace and delete.
- Preserve markers, but never payloads, in command history and never reuse their
  displayed ids.
- Clear pending images after a completed submission while retaining them when a
  submission is interrupted and restored.
- Show a concise error for an image that cannot be normalized.
- Preserve ordinary text paste and existing paste-token behavior.

Pillow handles macOS and Windows directly and uses `wl-paste` or `xclip` on
Linux. Unsupported environments leave text paste unaffected. No permanent
attach button or attachment pane is added.

**Exit criteria:** pasting one or several images produces placeholders, submits
text and images in order, supports removal, and degrades cleanly where binary
clipboard access is unavailable.

## Phase 4 — Media on disk and the web

### Phase 4A — Images

Implemented:

- `file_editor view` returns recognized local images as native model content.
- `browser_screenshot(tab, ref=None)` captures the current viewport or one
  referenced element.
- `browser_navigate` returns direct image responses as native model content.
- Each acquisition path enforces its own byte limit and returns a concise text
  descriptor alongside the image.

### Phase 4B — Native PDFs

Implemented:

- `file_editor view` returns PDFs as native model content without local text
  extraction or message-store offloading.
- `view_range` selects an inclusive, 1-indexed physical page range and returns
  a new native PDF containing those pages.
- `browser_navigate` returns direct PDF responses as native model content.
- PDFs are validated and page-counted with `pypdf`; pages are not rendered
  locally and extracted text is not duplicated alongside the document.
- Local and browser acquisition paths enforce their own media byte limits and
  return concise descriptors.

### Phase 4C — Audio and video

### `file_editor`

Extend only `view`:

- Continue returning text for text files.
- Return recognized audio and video as native model content where the active
  provider supports them.
- Keep `write_file` and `str_replace` text-only.
- Return a concise descriptor as the ordinary tool result so trajectories and
  progress output remain readable.

### Browser

- Use screenshot inspection explicitly for canvases, maps, charts, visual-only
  layouts, and images without useful accessibility text.
- Keep accessibility snapshots as the default and never attach screenshots
  automatically.

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
