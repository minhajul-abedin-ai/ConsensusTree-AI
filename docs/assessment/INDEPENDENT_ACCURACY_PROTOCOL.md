# Independent code-review accuracy evaluation protocol

1. Build a held-out, independently labelled corpus of real bug-fix pairs from projects with suitable licenses. Store bug IDs, commit SHAs, test evidence and source hashes. Remove near-duplicate cases before evaluation and keep labels hidden from model prompts.
2. Have two qualified reviewers, unrelated to the project's model outputs, independently adjudicate each case. Record credentials, conflict disclosures, adjudication criteria and disagreements. Resolve conflicts through a third assessor; preserve all raw judgements.
3. Configure an actual model and cap paid calls. Run `python -m consensustree.production_benchmark run --execute --provider openai --max-cases 2 --cases benchmarks/accuracy_cases.json --output review-records.json` as a technical smoke test. This supplied 50-case fixture is **synthetic, author-labelled and NOT an independent benchmark**.
4. Use real held-out cases and judge each report blind by arm (`baseline` / `council`) for concrete detected defects and invented defects; prepare a JSON file containing `judgments` rows with `{id, arm, assessor, correct, independent}`. The CLI validates that two distinct assessors agree but cannot verify who they are.
5. Run `python -m consensustree.production_benchmark score --records review-records.json --judgments adjudications.json --output scores.json`.
6. Report precision and recall at finding level, hallucination rate, disagreement rate, abstention rate, model, version, input context coverage, tokens, estimated cost and paired statistical uncertainty. The current `score` command only evaluates case-level **correctness according to declared human assessors**; it does **not** compute fine-grained bug finding precision/recall.

**Do not describe these results as externally independently validated until independent assessor identity, provenance and work have been confirmed.**
