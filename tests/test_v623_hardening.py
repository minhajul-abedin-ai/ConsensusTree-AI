"""Targeted regressions for trust-boundary and evaluation correctness.

These are INTERNAL tests, not a penetration-test certification.
"""
from __future__ import annotations

import os
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from consensustree import scanner
from consensustree.gitdiff import diff_snapshot
from consensustree.providers import (ProviderError, _extract_openai, _extract_anthropic,
                                    _extract_gemini, _extract_ollama, _post_json)
from consensustree.validation import parse_verdict


class ScannerRaceTests(unittest.TestCase):
    def test_ordinary_regular_file_still_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'app.py'
            p.write_text('x = 42\n', encoding='utf-8')
            self.assertEqual(scanner._read_bounded_regular_file(p), b'x = 42\n')

    def test_multiple_chunk_read_preserves_full_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'large.py'
            content = b'a' * 110_000
            path.write_bytes(content)
            self.assertEqual(scanner._read_bounded_regular_file(path), content)

    def test_beyond_file_size_limit_is_not_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'oversize.py'
            path.write_bytes(b'a' * (scanner.MAX_FILE_BYTES + 1))
            self.assertIsNone(scanner._read_bounded_regular_file(path))

    def test_non_regular_file_not_read(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(scanner._read_bounded_regular_file(Path(folder)))

    @unittest.skipUnless(hasattr(os, 'symlink') and os.name == 'posix', 'Requires POSIX symlinks')
    def test_symlink_swap_before_descriptor_open_cannot_expose_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'project'
            root.mkdir()
            target = root/'a.py'
            target.write_text('harmless = 1\n')
            (root/'b.py').write_text('still = 2\n')
            outside = Path(folder)/'outside.key'
            outside.write_text('HIGHLY_PRIVATE_TEXT\n')
            original_open = scanner.os.open
            triggered = False
            def swap_then_open(path, flags, *a, **kw):
                nonlocal triggered
                if Path(path) == target and not triggered:
                    triggered = True
                    target.unlink()
                    target.symlink_to(outside)
                return original_open(path, flags, *a, **kw)
            with patch.object(scanner.os, 'open', side_effect=swap_then_open):
                snapshot = scanner.scan(root)
            self.assertTrue(triggered)
            self.assertEqual(snapshot.files, ['b.py'])
            self.assertNotIn('HIGHLY_PRIVATE_TEXT', snapshot.text)

    @unittest.skipUnless(os.name == 'posix', 'Invalid UTF-8 filesystem names need POSIX')
    def test_non_utf8_filename_is_skipped_not_a_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'ok.py').write_text('ok = True\n')
            raw = os.fsencode(folder) + b'/invalid_\xff.py'
            fd = os.open(raw, os.O_CREAT | os.O_WRONLY, 0o600)
            os.write(fd, b'not_ok = 1\n')
            os.close(fd)
            result = scanner.scan(folder)
            self.assertEqual(result.files, ['ok.py'])


class GitDiffPrivacyTests(unittest.TestCase):
    @unittest.skipUnless(bool(__import__('shutil').which('git')), 'Requires Git executable')
    def test_git_diff_excludes_sensitive_directories_and_newline_filenames(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            def git(*args):
                subprocess.run(['git', '-C', folder, *args], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git('init', '-q')
            git('config', 'user.email', 'ci@example.invalid')
            git('config', 'user.name', 'CI')
            (repo/'src').mkdir(); (repo/'secrets').mkdir()
            (repo/'src'/'app.py').write_text('safe = 1\n')
            (repo/'secrets'/'config.py').write_text('HIDDEN = 1\n')
            weird=repo/'src'/'bad\nname.py'
            weird.write_text('weird = 1\n')
            git('add', '.');git('commit', '-qm', 'initial')
            (repo/'src'/'app.py').write_text('safe = 2\n')
            (repo/'secrets'/'config.py').write_text('HIDDEN = 2\n')
            weird.write_text('weird = 2\n')
            git('add', '.');git('commit', '-qm', 'changes')
            result = diff_snapshot(repo)
            self.assertEqual(result.files, ['src/app.py'])
            self.assertNotIn('HIDDEN = 2', result.text)
            self.assertNotIn('bad\\nname', result.text)


class ProviderDefensiveParsingTests(unittest.TestCase):
    def test_openai_mixed_content_accepts_only_string_text(self):
        payload = {'choices': [{'message': {'content': [{'text': 3}, {'text': 'Fine'}]}}]}
        self.assertEqual(_extract_openai(payload), 'Fine')

    def test_anthropic_nonstring_text_not_fatal_if_valid_exists(self):
        self.assertEqual(_extract_anthropic({'content': [{'type':'text','text': None},
                                                         {'type':'text','text':'Fine'}]}), 'Fine')

    def test_gemini_bad_part_text_skipped(self):
        data = {'candidates':[{'content':{'parts':[{'text': {'wrong':'type'}}, {'text':'Fine'}]}}]}
        self.assertEqual(_extract_gemini(data), 'Fine')

    def test_ollama_malformed_message_is_provider_error(self):
        with self.assertRaises(ProviderError):
            _extract_ollama({'message': 'not an object'})

    def test_oversized_provider_response_fails_explicitly(self):
        class FakeOpener:
            def open(self, *args, **kwargs):
                return io.BytesIO(b'a' * 4_000_001)
        with patch('consensustree.providers.urllib.request.build_opener', return_value=FakeOpener()):
            with self.assertRaisesRegex(ProviderError, '4 MB'):
                _post_json('https://example.invalid/api', {}, {'test': 'request'}, 1)


class VerdictIntegrityTests(unittest.TestCase):
    def test_duplicate_verdict_abstains_even_if_identical(self):
        self.assertIsNone(parse_verdict('VERDICT: ISSUE\nVERDICT: ISSUE'))

    def test_post_verdict_explanation_abstains(self):
        self.assertIsNone(parse_verdict('VERDICT: ISSUE\nBut maybe not.'))

    def test_verdict_must_be_standalone(self):
        self.assertIsNone(parse_verdict('```VERDICT: ISSUE```'))
        self.assertIsNone(parse_verdict('> VERDICT: ISSUE'))

    def test_final_line_and_trailing_whitespace(self):
        self.assertTrue(parse_verdict('Reason.\nVERDICT: ISSUE  \n\n'))
        self.assertFalse(parse_verdict('VERDICT: NO_ISSUE\n'))


if __name__ == '__main__':
    unittest.main()
