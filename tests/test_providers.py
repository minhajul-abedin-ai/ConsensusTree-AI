import os
import unittest
from unittest.mock import patch

from consensustree import providers


class ProvidersTests(unittest.TestCase):
    def test_model_spec(self):
        self.assertEqual(str(providers.ModelSpec.parse("gemini:gemini-2.5-flash")), "gemini:gemini-2.5-flash")
        with self.assertRaises(ValueError):
            providers.ModelSpec.parse("unknown:model")
        with self.assertRaises(ValueError):
            providers.ModelSpec.parse("openai")

    def test_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(providers.ProviderError, "OPENAI_API_KEY"):
                providers.LLMClient().complete(providers.ModelSpec("openai", "gpt-4.1-mini"), "S", "U")

    def test_openai_wire_format(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret"}):
            with patch.object(providers, "_post_json", return_value={"choices": [{"message": {"content": "OK"}}]}) as mocked:
                output = providers.LLMClient().complete(providers.ModelSpec("openai", "gpt-4.1-mini"), "SYS", "PROMPT")
                self.assertEqual(output, "OK")
                args = mocked.call_args.args
                self.assertEqual(args[0], "https://api.openai.com/v1/chat/completions")
                self.assertEqual(args[1]["Authorization"], "Bearer test-secret")
                self.assertEqual(args[2]["messages"][0]["role"], "system")

    def test_anthropic_wire_format(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-secret"}):
            with patch.object(providers, "_post_json", return_value={"content": [{"type": "text", "text": "OK"}]}) as mocked:
                output = providers.LLMClient().complete(providers.ModelSpec("anthropic", "claude-sonnet-4-5"), "SYS", "PROMPT")
                self.assertEqual(output, "OK")
                self.assertEqual(mocked.call_args.args[2]["system"], "SYS")
                self.assertEqual(mocked.call_args.args[1]["anthropic-version"], "2023-06-01")

    def test_gemini_wire_format(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-secret"}):
            with patch.object(providers, "_post_json", return_value={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}) as mocked:
                output = providers.LLMClient().complete(providers.ModelSpec("gemini", "gemini-2.5-flash"), "SYS", "PROMPT")
                self.assertEqual(output, "OK")
                self.assertIn("gemini-2.5-flash:generateContent", mocked.call_args.args[0])
                self.assertEqual(mocked.call_args.args[1]["x-goog-api-key"], "test-secret")

    def test_ollama_wire_format(self):
        with patch.object(providers, "_post_json", return_value={"message": {"content": "OK"}}) as mocked:
            self.assertEqual(providers.LLMClient().complete(providers.ModelSpec("ollama", "llama3.2"), "SYS", "PROMPT"), "OK")
            self.assertEqual(mocked.call_args.args[0], "http://localhost:11434/api/chat")
            self.assertFalse(mocked.call_args.args[2]["stream"])

    def test_empty_responses_raise(self):
        for extractor in (providers._extract_openai, providers._extract_anthropic,
                          providers._extract_gemini, providers._extract_ollama):
            with self.assertRaises(providers.ProviderError):
                extractor({})


if __name__ == "__main__":
    unittest.main()
