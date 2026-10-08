"""Tests for the Alexa+ compliance surface of the GreenCode MCP server.

Every requirement here is quoted from Amazon's Alexa+ MCP documentation:

* Quickstart, Authentication checklist / Discovery: "Your MCP server returns
  401 Unauthorized (without a WWW-Authenticate header) for unauthenticated
  requests." / "Your server hosts a Protected Resource Metadata (PRM)
  document at the well-known URI according to RFC 9728." / "Your auth server
  metadata is available at /.well-known/oauth-authorization-server.
  code_challenge_methods_supported must be present and must include S256."
* Choose the Proper Integration Approach, MCP Toolkit considerations: "Your
  MCP server must meet a round-trip query response latency of less than
  500 ms."
* Quickstart, addon.json schema reference: the field constraints table.

Nothing here opens a socket to the internet. The HTTP tests drive the Starlette
app in-process; the latency test mocks the two slow I/O edges (host capability
probes and the grid-intensity network lookup) so what is measured is the
pipeline itself - the same code a real round trip executes. The real network
round trip, end to end over a socket, is measured by check_mcp_alexa.py.
"""

import json
import os
import time
import unittest
from pathlib import Path
from unittest import mock

from starlette.testclient import TestClient

from app import energy_sensors, mcp_server

TOKEN = "unit-test-token"
REPO_ROOT = Path(__file__).resolve().parents[1]
LATENCY_BUDGET_SECONDS = 0.5


class TestDiscoveryDocuments(unittest.TestCase):
    """RFC 9728 / RFC 8414 discovery must be public and self-describing."""

    @classmethod
    def setUpClass(cls):
        cls._saved_token = os.environ.get("GREENCODE_MCP_TOKEN")
        os.environ["GREENCODE_MCP_TOKEN"] = TOKEN
        cls.app = mcp_server.create_app()
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        if cls._saved_token is None:
            os.environ.pop("GREENCODE_MCP_TOKEN", None)
        else:
            os.environ["GREENCODE_MCP_TOKEN"] = cls._saved_token

    def test_prm_document_is_served_at_the_well_known_uri(self):
        resp = self.client.get("/.well-known/oauth-protected-resource")
        self.assertEqual(resp.status_code, 200)
        doc = resp.json()
        self.assertTrue(doc["resource"].endswith("/mcp"), doc["resource"])
        self.assertIn("header", doc["bearer_methods_supported"])
        self.assertIsInstance(doc["authorization_servers"], list)

    def test_prm_is_also_served_at_the_resource_specific_path(self):
        # RFC 9728 section 3: clients may discover metadata by appending the
        # resource path to the well-known URI.
        resp = self.client.get("/.well-known/oauth-protected-resource/mcp")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["resource"].endswith("/mcp"))

    def test_prm_is_public_even_when_auth_is_enforced(self):
        # Discovery behind a credential is undiscoverable.
        resp = self.client.get(
            "/.well-known/oauth-protected-resource",
            headers={"Authorization": "Bearer wrong"},
        )
        self.assertEqual(resp.status_code, 200)

    def test_authorization_server_metadata_advertises_pkce_s256(self):
        resp = self.client.get("/.well-known/oauth-authorization-server")
        self.assertEqual(resp.status_code, 200)
        doc = resp.json()
        self.assertIn("S256", doc["code_challenge_methods_supported"])
        self.assertTrue(doc["issuer"].startswith("http"))

    def test_forwarded_proto_is_used_behind_a_tunnel(self):
        # cloudflared terminates TLS and forwards to loopback over HTTP; the
        # document must still describe the public resource as https://.
        resp = self.client.get(
            "/.well-known/oauth-protected-resource",
            headers={"X-Forwarded-Proto": "https", "Host": "mcp.example.com"},
        )
        self.assertEqual(resp.json()["resource"], "https://mcp.example.com/mcp")


class TestFourHundredOneChecklist(unittest.TestCase):
    """401 without WWW-Authenticate; bearer requests pass through."""

    @classmethod
    def setUpClass(cls):
        cls._saved_token = os.environ.get("GREENCODE_MCP_TOKEN")
        os.environ["GREENCODE_MCP_TOKEN"] = TOKEN
        cls.app = mcp_server.create_app()
        # Entering the context runs the app's lifespan, which starts the MCP
        # session manager - without it the transport answers 500, not 401.
        # base_url makes the Host header 127.0.0.1:8080, which the MCP
        # transport's DNS-rebinding protection (allowed_hosts: 127.0.0.1:*)
        # accepts; TestClient's default "testserver" host is rejected with 421.
        cls.client = TestClient(cls.app, base_url="http://127.0.0.1:8080")
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        if cls._saved_token is None:
            os.environ.pop("GREENCODE_MCP_TOKEN", None)
        else:
            os.environ["GREENCODE_MCP_TOKEN"] = cls._saved_token

    def test_unauthenticated_post_gets_401_without_www_authenticate(self):
        resp = self.client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            headers={"Accept": "application/json, text/event-stream"},
        )
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn(
            "www-authenticate",
            {k.lower() for k in resp.headers},
            "The Alexa checklist requires the 401 to carry NO WWW-Authenticate header",
        )

    def test_unauthenticated_get_gets_401(self):
        resp = self.client.get("/mcp", headers={"Accept": "text/event-stream"})
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("www-authenticate", {k.lower() for k in resp.headers})

    def test_wrong_token_gets_401(self):
        resp = self.client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            headers={"Authorization": "Bearer not-the-token"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_valid_token_reaches_the_mcp_transport(self):
        resp = self.client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "unit-test", "version": "0"},
                },
            },
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )
        # Not 401 means the middleware admitted the request; the transport
        # answers 200/202 (JSON or SSE) once its session manager is running.
        self.assertIn(resp.status_code, (200, 202), resp.text[:300])

    def test_middleware_gates_only_when_a_token_is_configured(self):
        # The middleware is exercised against a trivial inner app so the three
        # states (open, wrong/missing token, correct token) are visible without
        # spinning up a second MCP session manager.
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route

        async def inner(request):
            return PlainTextResponse("reached")

        def build(token):
            app = Starlette(routes=[Route("/mcp", inner, methods=["GET", "POST"])])
            app.add_middleware(mcp_server.AlexaAuthMiddleware, token=token)
            return TestClient(app)

        with build(None) as open_client:
            self.assertEqual(open_client.post("/mcp").status_code, 200)
        with build(TOKEN) as client:
            self.assertEqual(client.post("/mcp").status_code, 401)
            self.assertEqual(
                client.post("/mcp", headers={"Authorization": f"Bearer {TOKEN}"}).status_code,
                200,
            )
        # And the env-to-token wiring: no token in the environment => open.
        saved = os.environ.pop("GREENCODE_MCP_TOKEN", None)
        try:
            self.assertIsNone(mcp_server._mcp_token())
        finally:
            if saved is not None:
                os.environ["GREENCODE_MCP_TOKEN"] = saved


class TestTunnelHostAllowlist(unittest.TestCase):
    """GREENCODE_MCP_ALLOWED_HOSTS is what lets the public tunnel Host through."""

    TUNNEL = "greencode-demo.trycloudflare.com"
    INIT = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "unit-test", "version": "0"},
        },
    }

    def setUp(self):
        self._saved_token = os.environ.get("GREENCODE_MCP_TOKEN")
        self._saved_hosts = os.environ.pop("GREENCODE_MCP_ALLOWED_HOSTS", None)
        os.environ["GREENCODE_MCP_TOKEN"] = TOKEN

    def tearDown(self):
        os.environ.pop("GREENCODE_MCP_ALLOWED_HOSTS", None)
        if self._saved_hosts is not None:
            os.environ["GREENCODE_MCP_ALLOWED_HOSTS"] = self._saved_hosts
        if self._saved_token is None:
            os.environ.pop("GREENCODE_MCP_TOKEN", None)
        else:
            os.environ["GREENCODE_MCP_TOKEN"] = self._saved_token

    @property
    def auth_headers(self):
        return {
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }

    def _post(self, base_url):
        with TestClient(mcp_server.create_app(), base_url=base_url) as client:
            return client.post("/mcp", json=self.INIT, headers=self.auth_headers)

    def test_tunnel_host_is_rejected_without_the_env_var(self):
        # The SDK's DNS-rebinding guard answers 421 before the transport runs:
        # this is exactly what would block cloudflared's public URL by default.
        resp = self._post(f"https://{self.TUNNEL}")
        self.assertEqual(resp.status_code, 421, resp.text[:300])

    def test_tunnel_host_passes_when_listed_and_others_stay_rejected(self):
        os.environ["GREENCODE_MCP_ALLOWED_HOSTS"] = self.TUNNEL

        resp = self._post(f"https://{self.TUNNEL}")
        self.assertIn(resp.status_code, (200, 202), resp.text[:300])

        # The env var only ever adds: loopback still works...
        local = self._post("http://127.0.0.1:8080")
        self.assertIn(local.status_code, (200, 202), local.text[:300])

        # ...and a host nobody listed is still rejected.
        evil = self._post("https://evil.example.com")
        self.assertEqual(evil.status_code, 421, evil.text[:300])

    def test_multiple_hosts_comma_separated(self):
        os.environ["GREENCODE_MCP_ALLOWED_HOSTS"] = f" {self.TUNNEL}, other.example.com "
        resp = self._post("https://other.example.com")
        self.assertIn(resp.status_code, (200, 202), resp.text[:300])


class TestAddOnAssetsResolve(unittest.TestCase):
    """Every URL addon.json can reference must be served by the app itself."""

    def setUp(self):
        cls_app = mcp_server.create_app()
        self.client = TestClient(cls_app, base_url="http://127.0.0.1:8080")
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_privacy_and_terms_pages_are_served(self):
        for slug in ("privacy", "terms"):
            resp = self.client.get(f"/{slug}")
            self.assertEqual(resp.status_code, 200, slug)
            self.assertIn("<html", resp.text.lower())

    def test_icon_assets_are_served_with_png_type(self):
        resp = self.client.get("/assets/icon-72x72.png")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.headers["content-type"].startswith("image/png"))


class TestLatencyCaches(unittest.TestCase):
    """The two caches that make the <500 ms budget reachable."""

    def setUp(self):
        mcp_server.clear_intensity_cache()
        self._saved_probe_cache = energy_sensors._PROBE_CACHE
        energy_sensors._PROBE_CACHE = None

    def tearDown(self):
        energy_sensors._PROBE_CACHE = self._saved_probe_cache
        mcp_server.clear_intensity_cache()

    def test_probe_capabilities_is_cached_for_the_ttl_window(self):
        with (
            mock.patch.object(energy_sensors, "discover_rapl_domains", return_value=[]),
            mock.patch.object(energy_sensors, "battery_discharge_watts", return_value=None) as battery,
            mock.patch.object(energy_sensors, "perf_available", return_value=False) as perf,
            mock.patch.object(energy_sensors, "scaphandre_available", return_value=False) as scaph,
        ):
            first = energy_sensors.probe_capabilities()
            second = energy_sensors.probe_capabilities()

        for heavy_probe in (battery, perf, scaph):
            self.assertEqual(
                heavy_probe.call_count, 1,
                "second probe must be served from cache, not re-run",
            )
        self.assertEqual(first, second)

    def test_force_flag_bypasses_the_probe_cache(self):
        with (
            mock.patch.object(energy_sensors, "discover_rapl_domains", return_value=[]),
            mock.patch.object(energy_sensors, "battery_discharge_watts", return_value=None) as battery,
            mock.patch.object(energy_sensors, "perf_available", return_value=False),
            mock.patch.object(energy_sensors, "scaphandre_available", return_value=False),
        ):
            energy_sensors.probe_capabilities()
            energy_sensors.probe_capabilities(force=True)
        self.assertEqual(battery.call_count, 2)

    def test_probe_cache_returns_a_private_copy(self):
        with (
            mock.patch.object(energy_sensors, "discover_rapl_domains", return_value=[]),
            mock.patch.object(energy_sensors, "battery_discharge_watts", return_value=None),
            mock.patch.object(energy_sensors, "perf_available", return_value=False),
            mock.patch.object(energy_sensors, "scaphandre_available", return_value=False),
        ):
            first = energy_sensors.probe_capabilities()
            first["best_available"] = "tampered"
            second = energy_sensors.probe_capabilities()
        self.assertNotEqual(second["best_available"], "tampered")

    def test_intensity_lookup_hits_the_provider_once_per_ttl(self):
        reading = {
            "zone": "IE",
            "carbon_intensity": 100.0,
            "intensity_source": "test",
            "intensity_source_tier": "customer_key",
        }
        with mock.patch.object(
            mcp_server.optimizer,
            "get_zone_carbon_intensity",
            side_effect=lambda zone, **_: dict(reading, zone=zone),
        ) as provider:
            a = mcp_server._resolve_intensity("IE")
            b = mcp_server._resolve_intensity("IE")
            c = mcp_server._resolve_intensity("ie")  # key is case-insensitive
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(a["carbon_intensity"], 100.0)
        self.assertEqual(b["carbon_intensity"], 100.0)
        self.assertEqual(c["zone"], "IE")

    def test_zero_ttl_disables_the_intensity_cache(self):
        saved = mcp_server.INTENSITY_CACHE_TTL
        mcp_server.INTENSITY_CACHE_TTL = 0.0
        try:
            with mock.patch.object(
                mcp_server.optimizer,
                "get_zone_carbon_intensity",
                side_effect=lambda zone, **_: {
                    "zone": zone, "carbon_intensity": 1.0,
                    "intensity_source": "test",
                },
            ) as provider:
                mcp_server._resolve_intensity("IE")
                mcp_server._resolve_intensity("IE")
            self.assertEqual(provider.call_count, 2)
        finally:
            mcp_server.INTENSITY_CACHE_TTL = saved

    def test_cached_reading_is_shallow_copied_so_callers_cannot_poison_it(self):
        with mock.patch.object(
            mcp_server.optimizer,
            "get_zone_carbon_intensity",
            return_value={"zone": "FR", "carbon_intensity": 50.0},
        ):
            first = mcp_server._resolve_intensity("FR")
            first["carbon_intensity"] = 999.0
            second = mcp_server._resolve_intensity("FR")
        self.assertEqual(second["carbon_intensity"], 50.0)


class TestLatencyBudget(unittest.TestCase):
    """Tool calls must compute their answer in well under 500 ms.

    The two slow edges - the host capability probe and the grid-intensity
    network lookup - are replaced with instant fakes here, exactly as the
    caches serve them once warm. What remains is the pipeline work a round
    trip performs per call, and that is what is measured against the
    official budget.
    """

    FAKE_CAPS = {
        "platform": "test",
        "rapl": {"supported": False, "domains": []},
        "scaphandre": {"supported": False, "url": ""},
        "perf": {"supported": False},
        "battery": {"supported": False, "watts": None},
        "modelled_fallback": True,
        "best_available": "model",
    }

    @classmethod
    def setUpClass(cls):
        cls.intensity_patch = mock.patch.object(
            mcp_server.optimizer,
            "get_zone_carbon_intensity",
            side_effect=lambda zone, **_: {
                "zone": zone,
                "carbon_intensity": 100.0,
                "intensity_source": "test",
                "intensity_source_tier": "customer_key",
                "is_live": True,
            },
        )
        cls.probe_patch = mock.patch.object(
            energy_sensors, "probe_capabilities", return_value=dict(cls.FAKE_CAPS)
        )
        cls.intensity_patch.start()
        cls.probe_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.probe_patch.stop()
        cls.intensity_patch.stop()

    def setUp(self):
        mcp_server.clear_intensity_cache()

    def _timed(self, fn, *args, **kwargs):
        # First call warms the caches; the second is what the budget governs.
        fn(*args, **kwargs)
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        return time.perf_counter() - start, result

    def _assert_within_budget(self, seconds, label):
        self.assertLess(
            seconds, LATENCY_BUDGET_SECONDS,
            f"{label} took {seconds * 1000:.0f} ms; Alexa+ requires <500 ms "
            f"round-trip query response latency",
        )

    SNIPPET = (
        "def process(rows):\n"
        "    total = 0\n"
        "    for a in rows:\n"
        "        for b in rows:\n"
        "            total += a * b\n"
        "    return total\n"
    )

    def test_audit_and_score_is_within_budget(self):
        elapsed, result = self._timed(
            mcp_server.audit_and_score, self.SNIPPET, language="python"
        )
        self.assertEqual(result["status"], "ok")
        self._assert_within_budget(elapsed, "audit_and_score")

    def test_audit_code_is_within_budget(self):
        elapsed, result = self._timed(mcp_server.audit_code, self.SNIPPET)
        self.assertEqual(result["status"], "ok")
        self._assert_within_budget(elapsed, "audit_code")

    def test_calculate_sci_is_within_budget(self):
        elapsed, result = self._timed(
            mcp_server.calculate_sci,
            energy_joules=1500.0,
            duration_seconds=30.0,
            functional_unit=10000.0,
        )
        self.assertEqual(result["status"], "ok")
        self._assert_within_budget(elapsed, "calculate_sci")

    def test_compare_regions_is_within_budget(self):
        elapsed, result = self._timed(
            mcp_server.compare_regions, ["IE", "US-VA", "FR"]
        )
        self.assertEqual(result["status"], "ok")
        self._assert_within_budget(elapsed, "compare_regions")

    def test_measure_energy_is_within_budget(self):
        elapsed, result = self._timed(mcp_server.measure_energy)
        self.assertEqual(result["status"], "ok")
        self._assert_within_budget(elapsed, "measure_energy")

    def test_get_grid_intensity_is_within_budget(self):
        elapsed, result = self._timed(mcp_server.get_grid_intensity, "IE")
        self.assertEqual(result["status"], "ok")
        self._assert_within_budget(elapsed, "get_grid_intensity")


class TestAddonManifest(unittest.TestCase):
    """addon.json must satisfy every published schema constraint."""

    REQUIRED_ICON_SIZES = ["72x72", "64x64", "88x88", "126x126", "180x180", "241x241"]

    @classmethod
    def setUpClass(cls):
        path = REPO_ROOT / "alexa" / "addon.json"
        cls.manifest = json.loads(path.read_text(encoding="utf-8"))

    def test_manifest_version_is_1(self):
        self.assertEqual(self.manifest["manifestVersion"], "1.0")

    def test_distribution_countries_are_iso_codes(self):
        countries = self.manifest["storeListing"]["distributionCountries"]
        self.assertTrue(countries)
        for code in countries:
            self.assertRegex(code, r"^[A-Z]{2}$")

    def test_name_is_at_most_30_characters(self):
        name = self.manifest["storeListing"]["name"]["value"]
        self.assertLessEqual(len(name), 30)

    def test_short_description_is_at_most_123_characters(self):
        self.assertLessEqual(len(self.manifest["storeListing"]["shortDescription"]), 123)

    def test_full_description_is_at_most_4000_characters(self):
        self.assertLessEqual(len(self.manifest["storeListing"]["fullDescription"]), 4000)

    def test_example_phrases_are_three_or_four_and_each_at_most_200(self):
        phrases = self.manifest["storeListing"]["examplePhrases"]
        self.assertIn(len(phrases), (3, 4))
        for phrase in phrases:
            self.assertLessEqual(len(phrase), 200)

    def test_compliance_urls_are_https(self):
        compliance = self.manifest["storeListing"]["privacyAndCompliance"]
        self.assertTrue(compliance["privacyPolicyUrl"].startswith("https://"))
        self.assertTrue(compliance["termsOfUseUrl"].startswith("https://"))

    def test_all_six_light_icon_sizes_are_present(self):
        light = self.manifest["storeListing"]["mediaAssets"]["icons"]["light"]
        sizes = [icon["size"] for icon in light]
        self.assertEqual(sizes, self.REQUIRED_ICON_SIZES)
        for icon in light:
            self.assertTrue(icon["uri"].startswith("https://"))

    def test_carousel_has_at_least_one_600x900_image_with_alt_text(self):
        carousel = self.manifest["storeListing"]["mediaAssets"]["carouselImages"]
        self.assertGreaterEqual(len(carousel), 1)
        for image in carousel:
            self.assertEqual(image["size"], "600x900")
            self.assertLessEqual(len(image["altText"]), 250)
            self.assertTrue(image["uri"].startswith("https://"))

    def test_integration_is_mcp_with_an_https_endpoint(self):
        integration = self.manifest["integrations"][0]
        self.assertEqual(integration["type"], "MCP")
        endpoint = integration["config"]["endpoints"]["default"]
        self.assertEqual(endpoint["type"], "HTTPS")
        self.assertTrue(endpoint["uri"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
