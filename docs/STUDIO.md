# ConsensusTree AI — Local Studio (v6.2 release candidate)

## Launch in three commands

Requires Python **3.10+**. From the extracted project directory:

```bash
python -m pip install -e .
consensustree doctor
consensustree studio --root ./examples --open
```

The local server binds **only** to `127.0.0.1` on port `8765`, and the terminal prints a private URL containing a freshly generated capability token. Copy the URL to the same computer's browser if `--open` does not work. Press Ctrl+C in the terminal to stop the server. Use `--port 8766` if the default port is already in use. The CLI does not automatically publish or expose a service on the Internet.

## Try it without an API key

Click **Explore demo**; the content is an intentionally fictional fixture, not the result of reviewing source code. You can also open the stand-alone `examples/interactive_showcase.html` to explore the workbench design with simulated review interactions. That file does not communicate with the local server or any AI provider.

## Run an actual review

1. Choose the **Code review** objective and specify a relative subfolder or `.`. The project root is fixed by the `--root` option at server startup; browser inputs cannot review outside this root.
2. Click **Preview files** and inspect the filenames, **exact numbered source excerpt**, and size/truncation details. The sampler excludes symlinks and common sensitive/hidden paths, but exclusion and secret detection are **best effort**. Never use confidential code unless permitted.
3. Choose a provider and a model ID. Optionally enable **Assign a different model to each specialist** to select three distinct reviewer models; reviewer #1 also chairs the final synthesis. To use OpenAI, Gemini or Anthropic, set `OPENAI_API_KEY`, `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` in the server's environment *before starting the app*. For Ollama, separately install Ollama, pull the selected model and ensure a localhost service runs. The browser Studio accepts only loopback Ollama endpoints (configured via `OLLAMA_BASE_URL`), never a remote Ollama URL.
4. Select **Standard** (3 specialists + 1 chair, up to 4 requests) or **Hierarchical** (1–2 groups, up to 5–9 requests). Model usage may cost money; these are request counts, not guaranteed billed token estimates.
5. Read and check the consent box, then choose **Run council**. A new source scan is checked against the earlier preview fingerprint. If files changed, repeat the preview before proceeding. The council runs server-side, and progress and results appear in your browser.
6. Inspect specialist reports and the synthesis. Download JSON for reproducibility or standalone HTML for further offline analysis. Browser jobs are stored in temporary server memory (up to eight) and disappear on server restart.

## Ask the council a question

Switch to **Ask council**, enter a question and select a provider. The studio blocks a few obvious credential patterns in questions, but the detector is incomplete. Never paste private data or confidential information. The three specialists change to Pragmatist, Skeptic and Strategist.

## Source-reference checks

Code-review reports contain a **source-reference integrity** summary. This checks whether model-cited `file.py:line` locations were actually present in the excerpt sent to the models. It **does not validate any bug, severity, test result, or factual conclusion.** Claims without line references require human follow-up.

The studio also uses Git ignore rules for valid Git repositories, including nested selected subfolders. This is not a comprehensive secret detector: consent only to transmit code you are allowed to share.

## Safety boundaries

- **Local-only:** The web server is a single-user developer tool, not a hardened multi-user SaaS. Do not reverse-proxy it, change binding to a public interface or deploy it as a remotely reachable service.
- **Bearer token:** Anyone with the printed private URL can access local reports and start model calls while the server runs. Do not paste that URL publicly or include it in screenshots/logs.
- **Cost / privacy:** Hosting providers receive the selected prompt and source excerpts after explicit approval, and their normal data-handling terms apply. Ollama uses the configured local service by default.
- **Limits:** 20 source files, 24,000 source characters, 1 concurrent review, 36KB API request bodies, 8 jobs retained in memory. Browser requests have checks for Host, Origin and token; the interface serves no CDN scripts, fonts or telemetry.
- **No independent verification:** AI consensus is not a security audit, factual certification or test execution. Where separate `verify` evidence is used, it is not cryptographically authenticated. Do not automatically merge proposed changes without review.
- **Plugin system:** Provider plugins are disabled in this web interface. The pre-existing CLI plugin functionality is opt-in and should only load trusted code.

## Testing and deployment

The unittest suite tests the local server over real HTTP with a fake provider, input boundaries, authentication, safety checks, response rendering and Ollama request format against a fake local HTTP endpoint. `python tests/browser_studio_optional.py` requires Playwright and installed Chromium and exercises a separately labelled offline showcase, not a live browser-to-server end-to-end test. Real provider calls, Safari/Firefox, Windows/macOS and public hosting have not been validated.

For local developer release, use `python -m unittest discover -s tests -v` and `python -m pip wheel --no-build-isolation --no-deps -w dist .`.
