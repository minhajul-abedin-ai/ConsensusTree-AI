# Offline reviewer agreement diagnostics

This research-to-software utility reports deterministic agreement statistics from reviewer labels without calling any model or API. It is **not** a measure of factual correctness, security-review accuracy, independence, or model calibration. It does not replace independently labelled benchmarks.

Run after `python -m pip install -e .`:

```python
from consensustree.consensus_diagnostics import summarize_votes
print(summarize_votes(["approve", "approve", None]))
```

Output includes reviewer count, response count, abstentions, sorted label counts, a unique plurality winner (or `None` on a tie), and a winner share whose denominator includes abstentions. `unanimous_among_responses` is false if all abstain. This helper intentionally does **not** normalize synonyms, judge answer quality, aggregate free-form LLM outputs, or modify the production council.

Verification: `python -m unittest tests.test_consensus_diagnostics -v` or `python -m unittest discover -s tests -v`. Tests cover ties, abstentions, empty input, malformed votes and generator inputs. No live provider requests or research experiments are performed.
