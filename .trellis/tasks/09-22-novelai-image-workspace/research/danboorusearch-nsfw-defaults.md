# DanbooruSearch NSFW defaults

Checked 2026-09-23 against the public provider's own files:

- The REST `SearchIn` schema defaults `show_nsfw` to `True`:
  https://huggingface.co/spaces/SAkizuki/DanbooruSearch/blob/main/api_fastapi.py
- The provider's README describes its own web UI as hiding NSFW tags by
  default, while its REST example explicitly sets `show_nsfw: true`:
  https://huggingface.co/spaces/SAkizuki/DanbooruSearch/blob/main/README.md

An app with no NSFW switch still needs to choose which result behavior it
implements. Do not infer the workspace's product policy from the provider's
different UI and API defaults; request a product decision first.

Product decision (2026-09-23): the workspace includes NSFW candidates by
default and provides no filter or toggle. Set `show_nsfw: true` explicitly in
the backend search adapter so this behavior does not depend on provider defaults.
