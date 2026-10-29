# Contributing

Thanks for helping make AI reviews more useful and trustworthy. This repository emphasizes **testable behavior and reproducible evidence**, not claims that an agent council is invariably correct.

1. Open an issue describing a concrete user problem, expected behavior and reproduction if relevant.
2. Fork the repository, create a scoped branch, add tests and documentation for changed behavior.
3. Run `python -m unittest discover -s tests -v` and `python -m compileall -q src tests`.
4. Submit a pull request explaining the outcome and known limitations.

Do not commit API keys, personal data, private source repositories or confidential examples. Any real-model benchmark contribution should disclose the exact model, date, evaluation cases, pricing and judge methodology; label all synthetic fixtures.

Security concerns should use private reporting (see `SECURITY.md`). The project is experimental; no production guarantees are made.
