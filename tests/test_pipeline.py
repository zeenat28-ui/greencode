"""Test suite for the GreenCode Reality Verification Pipeline.

Covers the four things the pipeline promises, and the one thing it must refuse
to do:

- Verification: verdicts follow from evidence, not from optimism.
- Honesty: modelled energy can never verify a claim.
- Integrity: the hash chain detects any edit to recorded history.
- Security: unsigned or replayed evidence is rejected at the door.

Everything here runs against the real database, the real verifier and the real
FastAPI app. Only outbound notifications are mocked, because the thing under
test is the decision, not Slack's uptime.
"""

import json
import os
import sys
import time
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.database import init_db
from app.energy_sensors import HARDWARE_METHODS
from app.main import app
from app.pipeline import engine, ledger
from app.pipeline.config import PipelineConfig
from app.pipeline.n8n import build_workflow
from app.pipeline.signing import compute_signature, verify_signature
from app.pipeline.verifier import (
    VERDICT_CONTRADICTED,
    VERDICT_PARTIAL,
    VERDICT_UNVERIFIED,
    VERDICT_VERIFIED,
    Claim,
    ClaimError,
    Evidence,
    verify,
)


def _claim(claim_id: str = "t-claim", pct: float = 50.0, baseline: float = 1000.0) -> Claim:
    return Claim(
        claim_id, "zeenat28-ui/greencode", pct,
        baseline_energy_joules=baseline, source="refactor",
    )


def _samples(claim_id: str, joules: float, n: int = 3, method: str = "rapl"):
    """Build `n` identical measurement runs filed against `claim_id`."""
    return [
        Evidence(f"{claim_id}-run-{i}", claim_id, joules, functional_unit=1.0,
                 measurement_method=method, source="ci-runner")
        for i in range(n)
    ]


def _case(claim_id: str, joules: float, *, pct: float = 50.0,
          baseline: float = 1000.0, n: int = 3, method: str = "rapl"):
    """A claim plus its evidence, correlated on the same id."""
    return _claim(claim_id, pct, baseline), _samples(claim_id, joules, n, method)


class TestVerifierLogic(unittest.TestCase):
    """The decision rules, tested in isolation from HTTP and storage."""

    def test_01_no_evidence_is_unverified_not_optimistic(self):
        verdict = verify(_claim(), [])
        self.assertEqual(verdict.verdict, VERDICT_UNVERIFIED)
        self.assertEqual(verdict.confidence, 0.0)
        self.assertTrue(verdict.gaps, "an unverified claim must say what would close it")

    def test_02_modelled_evidence_cannot_verify_a_claim(self):
        """The central honesty guarantee: a model cannot confirm a model."""
        claim, evidence = _case("m", 500.0, method="model")
        verdict = verify(claim, evidence)
        self.assertEqual(verdict.verdict, VERDICT_UNVERIFIED)
        self.assertFalse(verdict.measurement_is_hardware)
        self.assertIn("model", " ".join(verdict.reasons).lower())

    def test_03_hardware_evidence_matching_the_claim_verifies(self):
        claim, evidence = _case("h", 500.0)
        verdict = verify(claim, evidence)
        self.assertEqual(verdict.verdict, VERDICT_VERIFIED)
        self.assertTrue(verdict.measurement_is_hardware)
        self.assertAlmostEqual(verdict.observed_reduction_pct, 50.0, places=2)
        self.assertGreater(verdict.confidence, 0.5)

    def test_04_energy_increase_contradicts_the_claim(self):
        claim, evidence = _case("r", 1500.0)
        verdict = verify(claim, evidence)
        self.assertEqual(verdict.verdict, VERDICT_CONTRADICTED)
        self.assertEqual(verdict.severity, "HIGH")
        self.assertLess(verdict.observed_reduction_pct, 0)

    def test_04b_every_hardware_backend_can_verify_a_claim(self):
        """A real counter is a real counter, whichever tier delivered it.

        Regression guard. `scaphandre` was missing from the verifier's hardware
        set, so a genuine RAPL reading relayed over the Prometheus sidecar - the
        exact deployment the README recommends for Docker-on-Linux - was silently
        downgraded to UNVERIFIED. The tool could not confirm its own flagship
        measurement path.
        """
        for method in sorted(HARDWARE_METHODS):
            with self.subTest(method=method):
                claim, evidence = _case(f"hw-{method}", 500.0, method=method)
                verdict = verify(claim, evidence)
                self.assertEqual(verdict.verdict, VERDICT_VERIFIED)
                self.assertTrue(verdict.measurement_is_hardware)

    def test_04c_an_unrecognised_method_is_never_treated_as_hardware(self):
        """Forward compatibility must fail closed, not open.

        A backend name this build has never heard of is not evidence of a
        measurement. Treating it as one would let any caller mint a VERIFIED
        verdict by inventing a method string.
        """
        claim, evidence = _case("unknown-tier", 500.0, method="totally_made_up")
        verdict = verify(claim, evidence)
        self.assertNotEqual(verdict.verdict, VERDICT_VERIFIED)
        self.assertFalse(verdict.measurement_is_hardware)

    def test_05_shortfall_is_partial_not_verified(self):
        """A 20% saving against a 50% claim is real, but it is not the claim."""
        claim, evidence = _case("s", 800.0)
        verdict = verify(claim, evidence)
        self.assertEqual(verdict.verdict, VERDICT_PARTIAL)
        self.assertAlmostEqual(verdict.observed_reduction_pct, 20.0, places=2)

    def test_06_single_sample_cannot_verify(self):
        claim, evidence = _case("one", 500.0, n=1)
        self.assertEqual(verify(claim, evidence).verdict, VERDICT_PARTIAL)

    def test_07_claim_without_baseline_stays_unverified(self):
        claim, evidence = _case("nb", 500.0)
        verdict = verify(Claim(claim.claim_id, claim.repo, 50.0), evidence)
        self.assertEqual(verdict.verdict, VERDICT_UNVERIFIED)
        self.assertIn("baseline", " ".join(verdict.reasons).lower())

    def test_08_noisy_workload_is_flagged_not_confirmed(self):
        """Run-to-run variance above the limit blocks verification."""
        noisy = [
            Evidence(f"n-{i}", "n", joules, functional_unit=1.0, measurement_method="rapl")
            for i, joules in enumerate((200.0, 900.0, 500.0, 1500.0, 400.0))
        ]
        verdict = verify(_claim("n"), noisy)
        self.assertEqual(verdict.verdict, VERDICT_PARTIAL)
        self.assertIn("spread", " ".join(verdict.reasons).lower())

    def test_09_evidence_scales_by_functional_unit(self):
        """A 10x larger workload must not look like a 10x energy regression."""
        big = [
            Evidence(f"b-{i}", "b", 5000.0, functional_unit=10.0, measurement_method="rapl")
            for i in range(3)
        ]
        verdict = verify(_claim("b", 50.0, baseline=10_000.0), big)
        self.assertEqual(verdict.verdict, VERDICT_VERIFIED)


    def test_10_invalid_claims_are_rejected_at_construction(self):
        with self.assertRaises(ClaimError):
            Claim("", "o/r", 50.0)
        with self.assertRaises(ClaimError):
            Claim("x", "", 50.0)
        with self.assertRaises(ClaimError):
            Claim("x", "o/r", 150.0)
        with self.assertRaises(ClaimError):
            Evidence("e", "c", -5.0)
        with self.assertRaises(ClaimError):
            Evidence("e", "c", 10.0, functional_unit=0)


class TestSigning(unittest.TestCase):
    """Authentication of machine-to-machine evidence intake."""

    SECRET = "test-secret-do-not-use-in-production"

    def test_01_valid_signature_is_accepted(self):
        body = b'{"claim_id":"c1"}'
        sig, ts = compute_signature(self.SECRET, body)
        result = verify_signature(self.SECRET, body, sig, str(ts))
        self.assertTrue(result.ok, result.reason)

    def test_02_tampered_body_is_rejected(self):
        body = b'{"claim_id":"c1"}'
        sig, ts = compute_signature(self.SECRET, body)
        result = verify_signature(self.SECRET, b'{"claim_id":"c2"}', sig, str(ts))
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "signature_mismatch")

    def test_03_replayed_stale_timestamp_is_rejected(self):
        body = b"{}"
        sig, ts = compute_signature(self.SECRET, body, timestamp=int(time.time()) - 4000)
        result = verify_signature(self.SECRET, body, sig, str(ts), max_skew_seconds=300)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "stale_timestamp")

    def test_04_timestamp_cannot_be_shifted_across_the_body_boundary(self):
        """A dot separator stops `123`+`456` colliding with `12`+`3456`."""
        body = b"456"
        sig, ts = compute_signature(self.SECRET, b"123" + b"456", timestamp=12)
        # Same total bytes, different split: the digest must differ.
        other = verify_signature(self.SECRET, body, sig, "3456")
        self.assertFalse(other.ok)

    def test_05_missing_and_malformed_fields_are_distinguished(self):
        body = b"{}"
        sig, _ = compute_signature(self.SECRET, body)
        self.assertEqual(verify_signature(self.SECRET, body, None, None).reason, "missing_timestamp")
        self.assertEqual(verify_signature(self.SECRET, body, sig, "abc").reason, "malformed_timestamp")
        self.assertEqual(verify_signature(self.SECRET, body, None, str(int(time.time()))).reason,
                         "missing_signature")
        self.assertEqual(verify_signature(self.SECRET, body, "sha256=xyz", str(int(time.time()))).reason,
                         "malformed_signature")

    def test_06_no_secret_configured_never_verifies(self):
        result = verify_signature("", b"{}", "sha256=" + "0" * 64, str(int(time.time())))
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "no_secret_configured")


class TestLedgerIntegrity(unittest.TestCase):
    """The chain must make post-hoc edits to history detectable.

    These tests deliberately corrupt ledger rows, so each one restores the
    original value in a `finally`. Without that, the shared development database
    would be left with a permanently broken chain and every later run - including
    the CI suite - would fail for a reason unrelated to the code under test.
    """

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        # A chain already broken by an interrupted earlier run must not be
        # mistaken for a regression introduced by this test.
        self.assertTrue(
            ledger.verify_chain().ok,
            "ledger was already broken before this test ran; "
            "reset the pipeline_ledger table to recover",
        )

    def _mutate(self, seq, **changes):
        """Apply changes to a row and return a callable that undoes them."""
        from app.database import SessionLocal
        from app.pipeline.ledger import PipelineLedgerEntry

        db = SessionLocal()
        try:
            row = db.query(PipelineLedgerEntry).filter(
                PipelineLedgerEntry.seq == seq
            ).first()
            original = {k: getattr(row, k) for k in changes}
            for k, v in changes.items():
                setattr(row, k, v)
            db.commit()
        finally:
            db.close()

        def restore():
            db = SessionLocal()
            try:
                row = db.query(PipelineLedgerEntry).filter(
                    PipelineLedgerEntry.seq == seq
                ).first()
                if row is not None:
                    for k, v in original.items():
                        setattr(row, k, v)
                    db.commit()
            finally:
                db.close()

        return restore

    def test_01_chain_verifies_after_normal_appends(self):
        engine.clear()
        for i in range(3):
            engine.file_claim(_claim(f"chain-{i}"))
        report = ledger.verify_chain()
        self.assertTrue(report.ok, report.reason)
        self.assertGreaterEqual(report.checked, 3)

    def test_02_editing_a_recorded_verdict_breaks_the_chain(self):
        """The whole point: a rewritten history must not verify."""
        engine.clear()
        engine.file_claim(_claim("tamper-1"))
        entry = ledger.append(
            event_id=f"tamper-evt-{uuid.uuid4().hex}",
            event_type="evidence_filed",
            severity="INFO",
            repo="o/r",
            claim_id="tamper-1",
            verdict="VERIFIED",
            confidence=0.99,
            summary="original text",
            evidence={"n": 1},
        )
        self.assertTrue(ledger.verify_chain().ok)

        # Simulate an operator quietly improving history.
        restore = self._mutate(entry["seq"], verdict="PARTIALLY_VERIFIED",
                               summary="quietly rewritten")
        try:
            report = ledger.verify_chain()
            self.assertFalse(report.ok)
            self.assertEqual(report.broken_at_seq, entry["seq"])
            self.assertIn(report.reason, ("entry_hash_mismatch", "prev_hash_mismatch"))
        finally:
            restore()
        self.assertTrue(ledger.verify_chain().ok, "chain must recover after restore")

    def test_03_deleting_an_entry_breaks_the_chain(self):
        """A removed record is detectable: the next entry no longer links up."""
        from app.database import SessionLocal
        from app.pipeline.ledger import PipelineLedgerEntry

        engine.clear()
        first = engine.file_claim(_claim("del-1"))["ledger_entry"]
        engine.file_claim(_claim("del-2"))
        # Mutate the tail so the deletion lands mid-chain rather than at the end.
        restore_tail = self._mutate(
            ledger.append(
                event_id=f"del-evt-{uuid.uuid4().hex}",
                event_type="evidence_filed", repo="o/r", claim_id="del-1",
                verdict="VERIFIED", summary="tail", evidence={},
            )["seq"],
            summary="tail",
        )

        db = SessionLocal()
        try:
            row = db.query(PipelineLedgerEntry).filter(
                PipelineLedgerEntry.seq == first["seq"]
            ).one()
            # Capture every column so the row can be put back byte-identical.
            snapshot = {c.name: getattr(row, c.name) for c in row.__table__.columns}
            db.delete(row)
            db.commit()
            self.assertFalse(ledger.verify_chain().ok)
        finally:
            db.close()
            restore_tail()

        # Put the deleted record back exactly as it was.
        db = SessionLocal()
        try:
            restored = PipelineLedgerEntry(**snapshot)
            restored.id = None
            db.add(restored)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        self.assertTrue(ledger.verify_chain().ok, "chain must recover after restore")

    def test_04_duplicate_event_id_is_refused(self):
        engine.clear()
        eid = f"dupe-{uuid.uuid4().hex}"
        engine.file_claim(_claim("dupe-claim"), record=False)
        engine.file_evidence(_samples("dupe-claim", 500.0)[0], event_id=eid, should_notify=False)
        with self.assertRaises(ValueError):
            ledger.append(event_id=eid, event_type="evidence_filed", summary="second try")


class TestPipelineEndpoints(unittest.TestCase):
    """End-to-end HTTP behaviour of the pipeline API."""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        engine.clear()

    def _auth(self) -> dict:
        """Mint a valid access token for the first user in the database."""
        import jwt as pyjwt
        from app.main import JWT_SECRET
        from app.database import SessionLocal, User

        db = SessionLocal()
        try:
            user = db.query(User).first()
        finally:
            db.close()
        if user is None:
            self.skipTest("no user in the database to authenticate as")
        token = pyjwt.encode(
            {"sub": str(user.id), "username": user.username,
             "exp": int(time.time()) + 900},
            JWT_SECRET, algorithm="HS256",
        )
        return {"Authorization": f"Bearer {token}"}

    def _file_claim(self, claim_id: str) -> None:
        resp = self.client.post("/api/pipeline/claim", headers=self._auth(), json={
            "claim_id": claim_id,
            "repo": "zeenat28-ui/greencode",
            "predicted_reduction_pct": 50.0,
            "baseline_energy_joules": 1000.0,
            "source": "refactor",
        })
        self.assertEqual(resp.status_code, 200, resp.text)

    def test_01_status_endpoint_is_public_and_secret_free(self):
        resp = self.client.get("/api/pipeline/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("configuration", body)
        self.assertIn("ledger", body)
        self.assertNotIn("test-secret", json.dumps(body))
        # Only booleans about secrets, never their values.
        self.assertIn("webhook_secret_configured", body["configuration"])

    def test_02_claim_requires_authentication(self):
        resp = self.client.post("/api/pipeline/claim", json={
            "claim_id": "unauth-claim", "repo": "o/r",
            "predicted_reduction_pct": 50.0, "baseline_energy_joules": 1000.0,
        })
        self.assertEqual(resp.status_code, 401)

    def test_03_claim_and_evidence_flow_reaches_a_verdict(self):
        claim_id = f"api-{uuid.uuid4().hex[:8]}"
        self._file_claim(claim_id)

        last = None
        for i in range(3):
            last = self.client.post("/api/pipeline/evidence", json={
                "claim_id": claim_id, "energy_joules": 500.0, "functional_unit": 1.0,
                "measurement_method": "rapl", "source": "ci-runner",
                "evidence_id": f"{claim_id}-run-{i}",
            })
        self.assertEqual(last.status_code, 200, last.text)
        self.assertEqual(last.json()["verdict"], VERDICT_VERIFIED)

        check = self.client.get(f"/api/pipeline/claim/{claim_id}")
        self.assertEqual(check.status_code, 200)
        self.assertEqual(check.json()["verdict"]["verdict"], VERDICT_VERIFIED)

    def test_04_replayed_event_id_does_not_create_a_second_record(self):
        claim_id = f"replay-{uuid.uuid4().hex[:8]}"
        self._file_claim(claim_id)
        event_id = f"replay-evt-{uuid.uuid4().hex[:8]}"
        payload = {
            "claim_id": claim_id, "energy_joules": 500.0, "functional_unit": 1.0,
            "measurement_method": "rapl", "event_id": event_id,
        }
        first = self.client.post("/api/pipeline/evidence", json=payload)
        second = self.client.post("/api/pipeline/evidence", json=payload)

        self.assertEqual(first.status_code, 200)
        # A retry must not look like a failure, or every queue retries forever.
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["duplicate"])
        self.assertEqual(first.json()["ledger_entry"]["seq"], second.json()["ledger_entry"]["seq"])

    def test_05_evidence_for_unknown_claim_is_recorded_but_reported(self):
        resp = self.client.post("/api/pipeline/evidence", json={
            "claim_id": f"ghost-{uuid.uuid4().hex[:8]}",
            "energy_joules": 10.0, "functional_unit": 1.0,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["verdict"], "INVALID_EVIDENCE")
        self.assertEqual(resp.json()["error"], "unknown_claim")

    def test_06_invalid_claim_payload_is_rejected(self):
        resp = self.client.post("/api/pipeline/claim", headers=self._auth(), json={
            "claim_id": "bad", "repo": "o/r", "predicted_reduction_pct": 500.0,
        })
        self.assertEqual(resp.status_code, 422)

    def test_07_ledger_and_chain_verification_endpoints(self):
        body = self.client.get("/api/pipeline/ledger?limit=5").json()
        self.assertIn("entries", body)
        self.assertIn("chain", body)
        self.assertTrue(self.client.get("/api/pipeline/ledger/verify").json()["ok"])

    def test_08_broken_chain_is_reported_as_409_with_the_sequence(self):
        from app.database import SessionLocal
        from app.pipeline.ledger import PipelineLedgerEntry

        entry = self.client.get("/api/pipeline/ledger?limit=1").json()["entries"][0]
        db = SessionLocal()
        try:
            row = db.query(PipelineLedgerEntry).filter(
                PipelineLedgerEntry.seq == entry["seq"]
            ).first()
            original = row.summary
            row.summary = "tampered via test"
            db.commit()
        finally:
            db.close()

        try:
            resp = self.client.get("/api/pipeline/ledger/verify")
            self.assertEqual(resp.status_code, 409)
            self.assertEqual(resp.json()["error"], "ledger_integrity_failure")
            self.assertEqual(resp.json()["broken_at_seq"], entry["seq"])
        finally:
            # Restore, or every subsequent run inherits a broken chain.
            db = SessionLocal()
            try:
                row = db.query(PipelineLedgerEntry).filter(
                    PipelineLedgerEntry.seq == entry["seq"]
                ).first()
                row.summary = original
                db.commit()
            finally:
                db.close()
        self.assertEqual(self.client.get("/api/pipeline/ledger/verify").status_code, 200)

    def test_09_n8n_workflow_export_is_well_formed(self):
        wf = self.client.get("/api/pipeline/n8n-workflow").json()
        self.assertEqual(len(wf["nodes"]), 8)
        types = [n["type"] for n in wf["nodes"]]
        self.assertIn("n8n-nodes-base.webhook", types)
        self.assertIn("n8n-nodes-base.code", types)
        self.assertIn("n8n-nodes-base.httpRequest", types)
        self.assertEqual(types.count("n8n-nodes-base.if"), 2)
        self.assertEqual(types.count("n8n-nodes-base.slack"), 3)
        # Every connection target must be a node that actually exists.
        names = {n["name"] for n in wf["nodes"]}
        for source, outputs in wf["connections"].items():
            self.assertIn(source, names)
            for branch in outputs["main"]:
                for target in branch:
                    self.assertIn(target["node"], names)


class TestSignedIntake(unittest.TestCase):
    """When a secret is configured, unsigned evidence must be refused."""

    SECRET = "test-secret-do-not-use-in-production"

    def setUp(self):
        init_db()
        engine.clear()
        self.client = TestClient(app)

    def test_01_unsigned_evidence_is_rejected_when_a_secret_is_set(self):
        with patch.dict(os.environ, {
            "GREENCODE_PIPELINE_WEBHOOK_SECRET": self.SECRET,
            "GREENCODE_PIPELINE_ALLOW_UNSIGNED": "false",
        }):
            resp = self.client.post("/api/pipeline/evidence", json={
                "claim_id": "signed-test", "energy_joules": 10.0, "functional_unit": 1.0,
            })
        self.assertEqual(resp.status_code, 401)
        # The reason is reported precisely, not as a generic 403, so an operator
        # can tell a missing header from a genuinely forged signature.
        self.assertIn("missing_timestamp", resp.json()["detail"])

    def test_01b_forged_signature_is_rejected_with_a_distinct_reason(self):
        with patch.dict(os.environ, {
            "GREENCODE_PIPELINE_WEBHOOK_SECRET": self.SECRET,
            "GREENCODE_PIPELINE_ALLOW_UNSIGNED": "false",
        }):
            resp = self.client.post(
                "/api/pipeline/evidence",
                content=json.dumps({
                    "claim_id": "signed-bad", "energy_joules": 10.0, "functional_unit": 1.0,
                }).encode(),
                headers={
                    "Content-Type": "application/json",
                    "X-GreenCode-Signature": "sha256=" + "0" * 64,
                    "X-GreenCode-Timestamp": str(int(time.time())),
                },
            )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("signature_mismatch", resp.json()["detail"])

    def test_02_correctly_signed_evidence_is_accepted(self):
        payload = {"claim_id": "signed-ok", "energy_joules": 10.0, "functional_unit": 1.0}
        body = json.dumps(payload).encode("utf-8")
        sig, ts = compute_signature(self.SECRET, body)

        with patch.dict(os.environ, {
            "GREENCODE_PIPELINE_WEBHOOK_SECRET": self.SECRET,
            "GREENCODE_PIPELINE_ALLOW_UNSIGNED": "false",
        }):
            resp = self.client.post(
                "/api/pipeline/evidence",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GreenCode-Signature": sig,
                    "X-GreenCode-Timestamp": str(ts),
                },
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.json()["ledger_entry"]["signature_verified"])

    def test_03_production_without_a_secret_is_reported_as_blocked(self):
        cfg = PipelineConfig(
            webhook_secret="", allow_unsigned=True, environment="production",
        )
        blockers = " ".join(cfg.production_blockers()).lower()
        self.assertIn("webhook_secret", blockers)

    def test_04_production_allow_unsigned_is_reported_as_blocked(self):
        cfg = PipelineConfig(
            webhook_secret=self.SECRET, allow_unsigned=True, environment="production",
        )
        self.assertIn("allow_unsigned", " ".join(cfg.production_blockers()).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
