# Character Workflow Capability Map

Source research on 2026-11-13. No application database, reference/generated
image, caption, export or runtime provider response was inspected.

## Existing Building Blocks

| Capability | Source evidence | Reuse / boundary |
| --- | --- | --- |
| Dataset form | `apps/web/src/DatasetRun.tsx:197` | Existing character libraries, selection and automatic canvases. |
| Character configuration | `apps/web/src/CharacterDataset.tsx:27`, `:260` | Private uploads/history references and per-mode styles; no saved workflow aggregate. |
| Editable image trait advice | `apps/api/src/novelai_api/app.py:1413`, `apps/api/src/novelai_api/advice.py:54` | English identity tags plus Chinese translations; explicit request/application. Advice configuration is separate from GPT image configuration. |
| GPT image edits | `apps/api/src/novelai_api/gpt_images.py:37`, `:86` | Multipart edits and request recording exist; the current dataset wrapper prohibits turnaround sheets and panels. |
| Reference allocation | `apps/api/src/novelai_api/dataset_plan.py:108` | GPT uses all references; Precise rotates one reference per item. View-specific matching would be new. |
| Frozen definitions | `apps/api/src/novelai_api/dataset_plan.py:263` | Existing items/styles/traits and pinned reference digests can retain immutable dataset inputs. |
| Durable scheduler | `apps/api/src/novelai_api/style_experiments.py:262`, `:783` | Owner-scoped queues, max ten unfinished runs, separate GPT/NovelAI lanes, configurable GPT concurrency. No paired workflow launch. |
| Result promotion | `apps/api/src/novelai_api/app.py:1295` | Existing authenticated result-to-reference operation; sheet splitting would need a new operation. |
| Review and export | `apps/web/src/ReviewGrid.tsx:187`, `apps/web/src/dataset-export.ts:151`, `:188` | Reuse review, captions and discard/purge filtering; preparation revisions are a separate concern. |

## Gaps to Design After Product Decisions

1. A dedicated source-style-preserving preparation purpose and explicit revision
   instructions without changing historical dataset prompt behavior.
2. The user chose three independent front/side/back images. Define per-view
   generation, correction and confirmation; no sheet or splitting operation.
3. The user confirmed full owner-scoped workflow persistence, per-view version
   history/selection and recovery after reload/reentry. New persistence is
   required; current component state cannot provide that guarantee.
4. Provenance between selected references, advice and launched datasets; reject
   stale completions after reference/trait changes.
5. Stable identities and truthful two-branch launch outcomes when a provider is
   unavailable, the queue is full or a response is lost. Never resubmit accepted
   paid work while reconciling state.
6. Stage capability checks: `/api/capabilities` advertises GPT images, while
   trait advice uses its separately configured image-capable advice runner.
7. Preserve each provider's existing independent content/parameter controls.
   Paired launch must validate both branches before accepting either, enqueue
   them consistently, and reconcile the same launch identity after uncertain
   responses. Provider execution still proceeds independently after acceptance.
8. Full revision retention must not consume a new general-reference quota slot
   for every historical preparation image. Design workflow-owned media/version
   retention and selected-reference pinning deliberately, without weakening the
   existing general reference quota or cleanup protections.

## Compatibility and Verification

- Use disposable synthetic SQLite/files and fake provider/advice transports.
- Update OpenAPI and TypeScript consumers deliberately for new API contracts.
- Preserve owner isolation, Origin checks, bounded images and private storage.
- Preserve existing standalone creation and frozen historical execution,
  including legacy Vibe/img2img definitions.
- Keep unrelated recipe-editor and recipe-spec changes outside this task.
