# Paired evaluation integrity preflight

Before comparing ConsensusTree's council with a single-model baseline, check that both arms are associated with the **same recorded case digest**. This optional, standard-library-only preflight checks structural pairing; it does not execute models, score accuracy, verify SHA-256 against source files, or establish assessor independence.

Create a JSON object with a nonempty `records` array. Each row needs `case_id` (nonempty string), `arm` (`baseline` or `council`) and `case_sha256` (lowercase 64-character hex digest of the same canonical case bytes). Each case must occur exactly once in each arm, with identical digests.

Example:

```json
{"records":[
  {"case_id":"synthetic-001","arm":"baseline","case_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
  {"case_id":"synthetic-001","arm":"council","case_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
]}
```

The example digest is a **placeholder**, not a real content hash. For real cases, compute the SHA-256 from identical canonical input bytes *before* either arm is run, then record that digest for both arms.

```bash
python scripts/validate_pairs.py paired-records.json
python -m unittest discover -s scripts -p 'test_validate_paired_evaluation.py'
```

Exit codes: 0 for valid structure, 1 for invalid records, 2 for unreadable or malformed JSON. Do not put secrets, proprietary code, or private participant data in published manifests. Preserve case-source revisions and independently reviewed labels separately. See [independent accuracy protocol](assessment/INDEPENDENT_ACCURACY_PROTOCOL.md). This tool does not replace that protocol and is not integrated into the existing benchmark CLI.

## Adapter for existing production benchmark output

The shipped `python -m consensustree.production_benchmark run --execute ...` command (implemented in [`src/consensustree/production_benchmark.py`](../src/consensustree/production_benchmark.py)) writes a **single row per case** with `id`, `source_sha256`, `baseline`, and `council`. To check the resulting structure without making any additional model calls:

```bash
python scripts/production_pairs_manifest.py production-benchmark-results.json paired-records.json
python scripts/validate_pairs.py paired-records.json
python -m unittest discover -s scripts -p 'test_production_pairs_manifest.py' -v
python -m unittest discover -s scripts -p 'test_validate_paired_evaluation.py' -v
```

Both scripts require only Python's standard library. Run both test commands: the adapter test filename and paired-validator test filename do not share the `test_*pairs*.py` glob, so that glob silently skips validator tests. The adapter accepts nonempty string, list, or object outputs, rejecting missing, empty, and scalar (Boolean/number) outputs. Synthetic regression tests cover multi-case ordering and pairing. It rejects duplicate case identifiers, malformed hashes, wrong benchmark types, and cases whose top-level `completion` is not exactly `complete`. The producer sets this field from `council.execution["completion"]["status"]`. This checks reported execution completeness, not factual correctness. Older output lacking this field is rejected. It copies the **same recorded source digest** into both arms, because the production benchmark stores one source digest per case. Therefore this adapter cannot independently prove that both models received identical prompts or verify the digest against source bytes; it only provides a structural compatibility check. Preserve the original benchmark JSON and input case revision for independent audit. No synthetic fixture is evidence of real provider performance.

## Production-schema audit (26 November 2026)

Source inspection confirms `run_production_cases` emits `benchmark_type`, `cases`, and per-case `id`, `source_sha256`, `baseline`, and `council` fields, matching the adapter's expected shape. Its `source_sha256` is computed from the UTF-8 **source string alone**, not the filename, numbered snapshot, system instructions, model specification, or any prompt sent to a provider. Consequently, even a successful preflight does **not** establish prompt equality or full case identity across arms. The adapter requires the producer-reported `completion` value `complete`; this does **not** independently establish model correctness, prompt parity, provider authenticity, or independent scoring. Inspect original council execution metadata before scoring. Preserve the input `--cases` JSON and benchmark output together, under appropriate access controls. These are source-code observations, not evidence of any real-model run.
