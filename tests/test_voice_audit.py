"""Automated Tests for Forensic Voice Audio Recording & Cryptographic Audit Ledger."""

import base64
import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app, VOICE_RECORDINGS_DIR, VOICE_AUDIT_LEDGER


class TestVoiceAudioLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_voice_audit_log_without_audio(self):
        """Verify voice command audit log without audio payload creates valid SHA-256 record."""
        payload = {
            "query": "Hey Alexa, check green score for bottlepy/bottle",
            "wake_word": "hey alexa",
            "action_type": "SCAN_REPO",
            "mcp_tool": "audit_repository",
            "spoken_response": "Auditing repository bottlepy/bottle with GreenCode AST engine.",
            "status": "VERIFIED",
        }
        res = self.client.post("/api/voice/audit-log", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        entry = data.get("entry", {})
        self.assertEqual(entry.get("query"), payload["query"])
        self.assertTrue(len(entry.get("record_hash", "")) == 64)

    def test_02_voice_audit_log_with_base64_audio_and_playback(self):
        """Verify raw voice audio is safely decoded, stored on disk, and streamed back via recording endpoint."""
        fake_audio_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00" + b"\x00" * 32
        fake_audio_b64 = "data:audio/webm;base64," + base64.b64encode(fake_audio_bytes).decode("ascii")

        payload = {
            "query": "Hey Alexa, refactor with Bedrock",
            "wake_word": "hey alexa",
            "action_type": "BEDROCK_REFACTOR",
            "mcp_tool": "refactor_code",
            "spoken_response": "Refactored code with Bedrock.",
            "status": "VERIFIED",
            "audio_base64": fake_audio_b64,
            "audio_mime": "audio/webm",
            "speaker_label": "DevOps Engineer / John Doe",
        }
        res = self.client.post("/api/voice/audit-log", json=payload)
        self.assertEqual(res.status_code, 200)
        entry = res.json().get("entry", {})

        self.assertTrue(entry.get("has_audio"))
        self.assertIsNotNone(entry.get("audio_file"))
        self.assertIsNotNone(entry.get("audio_sha256"))
        self.assertEqual(entry.get("speaker_label"), "DevOps Engineer / John Doe")

        record_id = entry.get("id")
        self.assertIsNotNone(record_id)

        # Verify raw file exists on disk
        stored_file = VOICE_RECORDINGS_DIR / entry["audio_file"]
        self.assertTrue(stored_file.exists())
        self.assertEqual(stored_file.stat().st_size, len(fake_audio_bytes))

        # Test streaming playback endpoint
        rec_res = self.client.get(f"/api/voice/recording/{record_id}")
        self.assertEqual(rec_res.status_code, 200)
        self.assertIn("audio", rec_res.headers.get("content-type", ""))
        self.assertEqual(rec_res.content, fake_audio_bytes)

    def test_03_tamper_evident_hash_chain(self):
        """Verify that sequential records are cryptographically chained via prev_hash."""
        logs_res = self.client.get("/api/voice/audit-log?limit=10")
        self.assertEqual(logs_res.status_code, 200)
        items = logs_res.json().get("items", [])
        self.assertGreaterEqual(len(items), 2)
        # Verify chronological chaining
        first = items[-1]
        second = items[-2]
        self.assertEqual(second.get("prev_hash"), first.get("record_hash"))


if __name__ == "__main__":
    unittest.main()

