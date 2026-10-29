# Plan for real adoption rather than star inflation

## Unique promise to test

**"More useful, verifiable code-review findings with explicit disagreement and predictable cost."**

This is a hypothesis. Do not claim it until tests establish better results than a simpler baseline.

## Measurement plan

- **Correctness**: Compare confirmed real issues discovered against single-model and multi-model alternatives on human-labelled repositories. Track precision, recall, actionable findings, false positives, and hallucination rate.
- **Efficiency**: Record wall-clock time and actual provider usage/billing from receipts or provider dashboards; compare per correctly identified issue, not solely per request.
- **Usability**: Measure time to first useful result and task completion for new external users.
- **Trust**: Track disclosure of assumptions, uncertainty, and reproducible verification commands.
- **Open-source adoption**: Track GitHub stars, issues from independent users, forks, recurring contributors, PyPI downloads if published, and sustained usage if voluntarily measured.

## Release/adoption phases (not guaranteed timeframes or forecasts)

1. Polish the five-minute quickstart, screenshots and a two-minute demo; make known limitations prominent.
2. Validate provider compatibility and release real comparative benchmark data on a held-out corpus.
3. Publish a clearly scoped beta, respond constructively to issues and invite reproducible test cases.
4. Build integrations requested by users (e.g. code-review artifacts, languages, CI) rather than only expanding the number of agents.
5. Review adoption and bug accuracy monthly. Prioritize fixes that save developer time or reduce incorrect advice. Reject artificial engagement and star purchasing.

## Explicit decision gate

If 10+ outside users cannot get a useful result quickly, fix the product experience before adding new advanced features. If a multi-agent council does not beat a simple baseline on an agreed objective, simplify or change the approach. The target of 10,000 stars cannot be promised by an engineering team or automated by software.
