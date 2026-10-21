#!/usr/bin/env python3
"""run_voice_automated_tests.py

Automated Voice-to-Voice Test Runner for GreenCode Alexa Agent.
- Uses Windows Native SAPI Speech Synthesizer (Built into Windows, zero external deps).
- Tester Bot (David - Male Voice) speaks the question out loud through speakers.
- GreenCode Alexa ASK Webhook processes the query through live AST and Carbon Telemetry.
- Alexa Agent (Zira - Female Voice) speaks the response out loud through speakers.
- Validates keywords and reports real-time PASS/FAIL.
"""

import os
import re
import sys
import time
from datetime import datetime, timezone

# Ensure stdout unbuffered
sys.stdout.reconfigure(line_buffering=True)

import win32com.client
from app.mcp_server import handle_alexa_skill_request

# Initialize Windows SAPI
tts = win32com.client.Dispatch("SAPI.SpVoice")
voices = tts.GetVoices()
TESTER_VOICE = voices.Item(0) if voices.Count > 0 else None
ALEXA_VOICE = voices.Item(1) if voices.Count > 1 else voices.Item(0)

def bot_speak(text: str):
    """Tester Bot speaks the question out loud."""
    if TESTER_VOICE:
        tts.Voice = TESTER_VOICE
    tts.Rate = 1
    tts.Speak(text, 0)

def alexa_speak(text: str):
    """Alexa speaks the response out loud."""
    if ALEXA_VOICE:
        tts.Voice = ALEXA_VOICE
    tts.Rate = 1
    tts.Speak(text, 0)

def strip_ssml(text: str) -> str:
    """Clean SSML markup tags for clean spoken output."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def send_query_to_alexa(query: str) -> str:
    """Send natural language query to GreenCode Alexa ASK Webhook."""
    payload = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": f"automated-voice-session-{int(time.time())}",
            "application": {},
            "attributes": {},
            "user": {"userId": "voice-automated-tester"},
        },
        "context": {
            "System": {
                "application": {},
                "user": {"userId": "voice-automated-tester"},
                "device": {"deviceId": "laptop-speakers"},
            },
        },
        "request": {
            "type": "IntentRequest",
            "requestId": f"req-{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "locale": "en-US",
            "intent": {
                "name": "FreeformGreenCodeQueryIntent",
                "slots": {"query": {"name": "query", "value": query}},
            },
        },
    }

    resp = handle_alexa_skill_request(payload)
    output = resp.get("response", {}).get("outputSpeech", {})
    speech = output.get("text") or output.get("ssml") or "GreenCode processed your request."
    return strip_ssml(speech)

# ── Test Suite ──────────────────────────────────────────────────────────────

TEST_SUITE = [
    {
        "id": "TEST 1",
        "name": "Regional Grid Carbon Comparison",
        "spoken_prompt": "Alexa, compare Ireland and Virginia.",
        "backend_query": "compare ireland and virginia",
        "expected_keywords": ["cleanest", "grams", "co2"],
    },
    {
        "id": "TEST 2",
        "name": "Audit History & Saved Carbon Metrics",
        "spoken_prompt": "Alexa, show my audit history.",
        "backend_query": "show my audit history",
        "expected_keywords": ["audits", "history", "saved"],
    },
    {
        "id": "TEST 3",
        "name": "Energy SLA Quality Gate Evaluation",
        "spoken_prompt": "Alexa, check my energy SLA.",
        "backend_query": "check my energy sla",
        "expected_keywords": ["energy sla", "deployment", "score"],
    },
    {
        "id": "TEST 4",
        "name": "Scope 1, 2, and 3 Carbon Inventory",
        "spoken_prompt": "Alexa, scope one two three inventory.",
        "backend_query": "scope one two three inventory",
        "expected_keywords": ["scope 1", "scope 2", "scope 3"],
    },
]

def run_tests():
    print("=" * 70, flush=True)
    print(" GREENCODE LIVE VOICE-TO-VOICE AUTOMATED TEST SUITE", flush=True)
    print(" Male Voice: Tester Bot (David)", flush=True)
    print(" Female Voice: GreenCode Alexa Agent (Zira)", flush=True)
    print("=" * 70, flush=True)
    print("Audio active! Listen to your computer speakers now...\n", flush=True)

    passed_count = 0
    total_count = len(TEST_SUITE)

    for test in TEST_SUITE:
        print("----------------------------------------------------------------------", flush=True)
        print(f" [{test['id']}] {test['name']}", flush=True)
        print("----------------------------------------------------------------------", flush=True)

        # Step 1: Tester Bot speaks question
        prompt = test["spoken_prompt"]
        print(f" [TESTER BOT (David)]: \"{prompt}\"", flush=True)
        bot_speak(prompt)
        time.sleep(0.5)

        # Step 2: Query live backend
        print(" [BACKEND]: Processing ASK webhook...", flush=True)
        response_text = send_query_to_alexa(test["backend_query"])

        # Step 3: Alexa speaks response
        print(f" [ALEXA (Zira)]: \"{response_text}\"", flush=True)
        alexa_speak(response_text)
        time.sleep(0.5)

        # Step 4: Verification
        lowered = response_text.lower()
        matched = [k for k in test["expected_keywords"] if k.lower() in lowered]
        passed = len(matched) >= len(test["expected_keywords"]) // 2 + 1

        if passed:
            print(f" >>> VERIFICATION: [PASS] (Matched: {', '.join(matched)})\n", flush=True)
            passed_count += 1
        else:
            print(f" >>> VERIFICATION: [FAIL] (Missing required terms)\n", flush=True)

    print("=" * 70, flush=True)
    print(f" ALL TESTS COMPLETE: {passed_count}/{total_count} PASSED", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    run_tests()
