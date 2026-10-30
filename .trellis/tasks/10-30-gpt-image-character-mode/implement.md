# Implementation plan

0. Operator: add `NAI_GPT_IMAGE_API_KEY` to `/etc/novelai/api.env`
   (sudoedit; never in chat). Agent never prints it.
1. Paid probe (approved budget): one `/v1/images/edits` call with one
   reference to confirm fields, sizes, response format and timing. Record
   findings in `research/gpt-image-probe.md`.
2. Backend: settings; `gpt_images.py` provider; `ReferenceUse`/`CharacterRequest`
   mode `gpt`; manager dispatch; availability flag; 503 when unconfigured;
   OpenAPI snapshot. Fake-transport tests. Gate: ruff + pytest.
3. Frontend: mode option, GPT settings panel, prompt preview, availability
   notice; viewer/summary labels. Gate: lint + env-free build.
4. Specs: extend `character-dataset-contract.md`, deployment notes (new
   secret), README.
5. Commit; deploy API then web when idle (operator approval); operator runs
   a small real batch.
