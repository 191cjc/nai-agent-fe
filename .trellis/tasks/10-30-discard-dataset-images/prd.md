# Discard dataset images

## Goal

While reviewing a training set, the owner can mark individual images as
discarded; exports never include them. Marks persist on the server and can
be undone.

## Confirmed Decisions (operator, 2026-10-30)

- Granularity: **per image** (one image of a multi-image group).
- Persistence: **server-side** (survives refresh, browser change, re-login);
  schema migration v6 → v7 is acceptable.
- Reversible: discarding only marks; the viewer still shows discarded images
  with a clear badge and a 「恢复」 action, plus a 「只看未弃置」 toggle.

## Requirements

- R1 Owner-scoped marks keyed by (job, image index); idempotent discard and
  restore; foreign/missing jobs or indexes → 404; Origin-checked mutations.
- R2 Every `GenerationView` carries `discarded_images: [index…]` (additive),
  so viewer, history and export see the same state.
- R3 Viewer: 「弃置」/「恢复」 button for the shown image, 「已弃置」 badge, a
  「只看未弃置」 toggle that skips discarded images in left/right navigation,
  and the review count (kept / discarded) for experiment groups.
- R4 Export (dataset runs and selected history) skips discarded images and
  reports them separately from failed/expired ones; numbering stays
  contiguous (`0001…`). The existing per-item export checklist still works.
- R5 Deleting a generation removes its marks; marks never delete image
  files, and expiry behaves as before.

- R6 (operator, 2026-10-30) Multi-select export: in the saved
  experiments/training sets list the owner can tick several training sets and
  export them into one zip (same clean PNG + caption pairs, contiguous
  numbering across sets, discarded images skipped, per-item checklist still
  available for a single set).

## Acceptance Criteria

- [ ] Discard → refresh/re-login → still discarded; restore works; marks are
      invisible to other users.
- [ ] Exported zip omits discarded images; summary shows the discarded count.
- [ ] 「只看未弃置」 navigation never lands on a discarded image; turning it off
      shows them again with the badge.
- [ ] Selecting several training sets exports one zip containing all of
      their kept images.
- [ ] Migration v6→v7 preserves all data; fake-only backend tests; web lint/
      tsc/env-free build; no paid calls.

## Out of Scope

- Deleting image files on discard; bulk discard by rule; per-item notes.
