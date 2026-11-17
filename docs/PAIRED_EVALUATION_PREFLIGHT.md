# Paired evaluation integrity preflight

Before comparing ConsensusTree's council with a single-model baseline, verify that both arms receive the **same immutable case content**. This optional, standard-library-only preflight checks structural pairing; it does not execute models, score accuracy, verify SHA-256 against source files, or establish assessor independence.

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
python scripts/validate_paired_evaluation.py paired-records.json
python -m unittest discover -s scripts -p 'test_validate_paired_evaluation.py'
```

Exit codes: 0 for valid structure, 1 for invalid records, 2 for unreadable or malformed JSON. Do not put secrets, proprietary code, or private participant data in published manifests. Preserve case-source revisions and independently reviewed labels separately. See [independent accuracy protocol](assessment/INDEPENDENT_ACCURACY_PROTOCOL.md). This tool does not replace that protocol and is not integrated into the existing benchmark CLI.
