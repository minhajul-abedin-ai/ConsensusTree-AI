> Final gates: see [FINAL_RELEASE_CHECKLIST.md](FINAL_RELEASE_CHECKLIST.md).

# Public GitHub beta checklist

Use this only after installing and testing the local app on your own computer.

- [ ] Confirm `consensustree studio --root ./examples --open` opens the private local URL and **Explore demo** works.
- [ ] Configure at least one real provider or local Ollama, run a bounded review on disposable code, inspect actual outputs and costs.
- [ ] Test a fresh installation on your intended operating system and check error messages when no model is available.
- [ ] Review the repository for secrets, private files and personal information before publishing it publicly.
- [ ] Add a real screen recording, the included screenshots, a clear GIF/video demo and a Quickstart section in the GitHub README.
- [ ] Enable GitHub Actions, run tests on Python 3.10–3.13 and resolve any platform-specific failures.
- [ ] Publish a prerelease tag (for example `v6.3.0rc1`) while clearly labeling the tool experimental.
- [ ] Collect independent bug reports and developer feedback. Record failures and review accuracy rather than using agreement as a confidence score.
- [ ] Compare against a single model on held-out code-review cases; publish methodology and negative results.
- [ ] Run an independent security assessment before public hosted deployment. Do not expose the existing localhost-only Studio as an Internet-facing service.

**10,000 stars are a community adoption milestone, not a software test result.** Code completeness does not automatically achieve it. Keep any public star counter grounded in GitHub's actual repository data.
