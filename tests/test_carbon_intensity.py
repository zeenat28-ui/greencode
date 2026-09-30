"""Tests for the provider-agnostic carbon intensity layer.

Every assertion corresponds to a property an enterprise buyer needs for the
number to be defensible: the fallback order holds, a static value is never
dressed up as live, provenance always travels with the figure, and a provider
that was never reached never claims to be verified.

No network access: every fetch is patched.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import carbon_intensity as ci

# Captured before any patching. The factory helpers below call this rather than
# ci._providers(), because ci._providers is what the tests replace - calling it
# through the patched name recurses until the stack overflows.
_REAL_PROVIDERS = ci._providers


def _offline_all():
    """Every provider present but unable to answer.

    The fetcher accepts the optional key_override second argument that
    resolve_carbon_intensity always passes, so these stubs must too.
    """
    providers = _REAL_PROVIDERS()
    for p in providers:
        p.fetch = lambda z, k=None: None
    return providers


class _CacheIsolation(unittest.TestCase):
    """Base class that empties the module cache around every test.

    Without this, a reading cached by one test is served to the next, so a test
    that patches a provider sees a stale value and fails for the wrong reason.
    """

    def setUp(self):
        ci._CACHE.clear()
        self.addCleanup(ci._CACHE.clear)


class TestProvenanceVocabulary(_CacheIsolation):
    """The tier names are a published contract, not internal constants."""

    def test_chain_is_ordered_best_first(self):
        self.assertEqual(
            ci.FALLBACK_CHAIN,
            (
                ci.TIER_PRIMARY_OFFICIAL,
                ci.TIER_CUSTOMER_KEY,
                ci.TIER_FREE_DATASET,
                ci.TIER_STATIC_MATRIX,
            ),
        )

    def test_every_audit_field_is_present_on_every_result(self):
        required = {
            "zone", "carbon_intensity", "intensity_source", "intensity_source_tier",
            "source_label", "is_live", "freshness", "observed_at", "age_seconds",
            "resolution", "fallback_chain", "tried", "caveats", "citation",
        }
        payload = ci.resolve_carbon_intensity("ZZ", use_cache=False).to_dict()
        self.assertTrue(required.issubset(set(payload)))

    def test_result_is_json_serialisable(self):
        import json
        json.dumps(ci.resolve_carbon_intensity("ZZ", use_cache=False).to_dict())


class TestProviderStatus(_CacheIsolation):
    """Operators must be able to see what is actually usable."""

    def test_status_lists_every_provider(self):
        ids = {p["provider_id"] for p in ci.provider_status()["providers"]}
        self.assertTrue({"uk_eso", "entsoe", "electricity_maps", "watttime"} <= ids)

    def test_keyless_official_provider_is_reported_as_free(self):
        self.assertIn("uk_eso", ci.provider_status()["free_tier1_no_key"])

    def test_provider_without_key_is_not_usable_now(self):
        with patch.dict(os.environ, {}, clear=True):
            by_id = {p["provider_id"]: p for p in ci.provider_status()["providers"]}
        self.assertFalse(by_id["electricity_maps"]["usable_now"])
        self.assertFalse(by_id["entsoe"]["usable_now"])
        # UK ESO needs no key, so it must be usable with an empty environment.
        self.assertTrue(by_id["uk_eso"]["usable_now"])

    def test_unverified_provider_never_claims_verification(self):
        # The honesty property: nothing may assert verified_live before a
        # request has actually succeeded from this host.
        by_id = {p["provider_id"]: p for p in ci.provider_status()["providers"]}
        for pid in ("entsoe", "electricity_maps", "watttime"):
            self.assertFalse(by_id[pid]["verified_live"], pid)



class TestFallbackOrder(_CacheIsolation):
    """Authority order must hold, and must not depend on key presence."""

    @staticmethod
    def _factory(primary_value, customer_value):
        def factory():
            providers = _REAL_PROVIDERS()
            for p in providers:
                p.requires_key = False          # both tiers usable
                if p.provider_id == "uk_eso":
                    p.fetch = lambda z, k=None: {"carbon_intensity": primary_value}
                elif p.provider_id == "electricity_maps":
                    p.fetch = lambda z, k=None: {"carbon_intensity": customer_value}
                else:
                    p.fetch = lambda z, k=None: None
            return providers
        return factory

    def test_official_provider_beats_customer_key(self):
        factory = self._factory(50.0, 900.0)
        with patch.object(ci, "_providers", factory):
            r = ci.resolve_carbon_intensity("GB", use_cache=False)
        self.assertEqual(r.intensity_source, "uk_eso")
        self.assertEqual(r.intensity_source_tier, ci.TIER_PRIMARY_OFFICIAL)
        self.assertEqual(r.carbon_intensity, 50.0)

    def test_customer_key_used_when_official_is_unavailable(self):
        factory = self._factory(None, 321.0)
        with patch.object(ci, "_providers", factory):
            r = ci.resolve_carbon_intensity("ZZ", use_cache=False)
        self.assertEqual(r.intensity_source, "electricity_maps")
        self.assertEqual(r.intensity_source_tier, ci.TIER_CUSTOMER_KEY)

    def test_customer_key_result_warns_about_licence(self):
        factory = self._factory(None, 321.0)
        with patch.object(ci, "_providers", factory):
            r = ci.resolve_carbon_intensity("ZZ", use_cache=False)
        self.assertTrue(any("licence" in c for c in r.caveats))


class TestStaticFallbackIsNeverDressedUp(_CacheIsolation):
    """The single most important property: no lying about provenance."""

    STATIC = {"US-CAL-CISO": {"carbon_intensity": 215.0, "source": "reference"}}

    def test_static_result_is_not_live(self):
        with patch.object(ci, "_providers", _offline_all):
            r = ci.resolve_carbon_intensity(
                "US-CAL-CISO", static_lookup=self.STATIC.get, use_cache=False
            )
        self.assertFalse(r.is_live)
        self.assertEqual(r.intensity_source_tier, ci.TIER_STATIC_MATRIX)
        self.assertEqual(r.freshness, ci.FRESHNESS_STATIC)
        self.assertIsNone(r.age_seconds)

    def test_static_result_carries_an_explicit_caveat(self):
        with patch.object(ci, "_providers", _offline_all):
            r = ci.resolve_carbon_intensity(
                "US-CAL-CISO", static_lookup=self.STATIC.get, use_cache=False
            )
        self.assertIn("not a live grid", " ".join(r.caveats))

    def test_static_result_records_every_provider_it_passed_over(self):
        with patch.object(ci, "_providers", _offline_all):
            r = ci.resolve_carbon_intensity(
                "US-CAL-CISO", static_lookup=self.STATIC.get, use_cache=False
            )
        tried = {t["provider"] for t in r.tried}
        self.assertTrue({"entsoe", "electricity_maps", "static_matrix"} <= tried)

    def test_nothing_available_reports_zero_with_a_caveat(self):
        with patch.object(ci, "_providers", _offline_all):
            r = ci.resolve_carbon_intensity(
                "ZZ", static_lookup=lambda z: None, use_cache=False
            )
        self.assertEqual(r.carbon_intensity, 0.0)
        self.assertEqual(r.intensity_source, "none")
        self.assertFalse(r.provider_verified)
        self.assertTrue(r.caveats)



class TestFreshnessHandling(_CacheIsolation):
    """A stale reading must be flagged, not passed off as current."""

    @staticmethod
    def _payload(intensity, stamp):
        return ({"data": [{"from": stamp, "to": stamp,
                           "intensity": intensity}]}, None)

    def test_age_is_computed_from_the_provider_timestamp(self):
        payload = self._payload({"actual": 100}, "2020-01-01T00:00Z")
        with patch.object(ci, "_get_json", return_value=payload):
            r = ci.resolve_carbon_intensity("GB", use_cache=False)
        self.assertGreater(r.age_seconds, 3600)
        self.assertTrue(any("h old" in c for c in r.caveats))

    def test_malformed_timestamp_does_not_raise(self):
        payload = self._payload({"actual": 100}, "not-a-date")
        with patch.object(ci, "_get_json", return_value=payload):
            r = ci.resolve_carbon_intensity("GB", use_cache=False)
        self.assertIsNone(r.age_seconds)
        self.assertEqual(r.carbon_intensity, 100.0)

    def test_actual_value_is_preferred_over_forecast(self):
        payload = self._payload({"actual": 82, "forecast": 400}, "2026-01-01T00:00Z")
        with patch.object(ci, "_get_json", return_value=payload):
            r = ci.resolve_carbon_intensity("GB", use_cache=False)
        self.assertEqual(r.carbon_intensity, 82.0)

    def test_forecast_is_used_when_actual_is_absent(self):
        payload = self._payload({"forecast": 137}, "2026-01-01T00:00Z")
        with patch.object(ci, "_get_json", return_value=payload):
            r = ci.resolve_carbon_intensity("GB", use_cache=False)
        self.assertEqual(r.carbon_intensity, 137.0)

    def test_empty_data_array_returns_none(self):
        with patch.object(ci, "_get_json", return_value=({"data": []}, None)):
            self.assertIsNone(ci._fetch_uk_eso("GB"))

    def test_uk_provider_declines_non_gb_zones(self):
        self.assertIsNone(ci._fetch_uk_eso("US-CAL-CISO"))

    def test_transport_error_falls_through_to_static(self):
        with patch.object(ci, "_get_json", return_value=(None, "HTTP 503")):
            with patch.object(ci, "_providers", _offline_all):
                r = ci.resolve_carbon_intensity(
                    "GB", static_lookup=lambda z: {"carbon_intensity": 1.0},
                    use_cache=False,
                )
        self.assertEqual(r.intensity_source, "static_matrix")



class TestEntsoeConversion(_CacheIsolation):
    """Fuel-weighted conversion is easy to get subtly wrong."""

    @staticmethod
    def _payload():
        return ({"TimeSeries": [
            {"in_Domain.mRID": "Nuclear", "Interval": [{"quantity": {"value": 100}}]},
            {"in_Domain.mRID": "Fossil", "Interval": [{"quantity": {"value": 100}}]},
        ]}, None)

    def test_weighted_average_of_two_fuels(self):
        # (100 MWh nuclear at 12 + 100 MWh fossil at 900) / 200 MWh = 456
        with patch.dict(os.environ, {"ENTSOE_API_TOKEN": "tok"}, clear=False):
            with patch.object(ci, "_get_json", return_value=self._payload()):
                datum = ci._fetch_entsoe("DE")
        self.assertIsNotNone(datum)
        self.assertAlmostEqual(datum["carbon_intensity"], 456.0, places=1)
        self.assertEqual(datum["resolution"], "PT15M")

    def test_returns_none_without_a_token(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(ci._fetch_entsoe("DE"))

    def test_unknown_country_returns_none(self):
        with patch.dict(os.environ, {"ENTSOE_API_TOKEN": "tok"}, clear=False):
            self.assertIsNone(ci._fetch_entsoe("US-CAL-CISO"))

    def test_zero_generation_returns_none_not_a_division_error(self):
        empty = ({"TimeSeries": []}, None)
        with patch.dict(os.environ, {"ENTSOE_API_TOKEN": "tok"}, clear=False):
            with patch.object(ci, "_get_json", return_value=empty):
                self.assertIsNone(ci._fetch_entsoe("DE"))


class TestCustomerKeyProvidersRequireCredentials(_CacheIsolation):
    """A provider must never be attempted without its key."""

    def test_electricity_maps_without_key_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(ci._fetch_electricity_maps("US-CAL-CISO"))

    def test_watttime_without_token_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(ci._fetch_watttime("US-CAL-CISO"))



class TestOptimizerIntegration(_CacheIsolation):
    """get_zone_carbon_intensity must expose provenance on every path."""

    PROVENANCE_KEYS = (
        "intensity_source", "intensity_source_tier", "resolution",
        "freshness", "age_seconds", "fallback_chain", "providers_tried",
        "intensity_caveats", "intensity_citation",
    )

    def test_provenance_keys_present_for_a_static_zone(self):
        from app.optimizer import get_zone_carbon_intensity

        with patch.object(ci, "_providers", _offline_all):
            payload = get_zone_carbon_intensity("US-CAL-CISO")
        for key in self.PROVENANCE_KEYS:
            self.assertIn(key, payload, key)

    def test_is_live_is_false_when_only_static_is_available(self):
        from app.optimizer import get_zone_carbon_intensity

        with patch.object(ci, "_providers", _offline_all):
            payload = get_zone_carbon_intensity("US-CAL-CISO")
        self.assertFalse(payload["is_live"])

    def test_official_source_is_labelled_live_end_to_end(self):
        from app.optimizer import get_zone_carbon_intensity

        def factory():
            providers = _REAL_PROVIDERS()
            for p in providers:
                p.requires_key = False
                if p.provider_id == "uk_eso":
                    p.fetch = lambda z, k=None: {
                        "carbon_intensity": 42.0,
                        "observed_at": "2026-01-01T00:00Z",
                    }
                else:
                    p.fetch = lambda z, k=None: None
            return providers

        with patch.object(ci, "_providers", factory):
            payload = get_zone_carbon_intensity("GB")
        self.assertTrue(payload["is_live"])
        self.assertEqual(payload["intensity_source"], "uk_eso")
        self.assertEqual(payload["intensity_source_tier"], ci.TIER_PRIMARY_OFFICIAL)
        self.assertEqual(payload["carbon_intensity"], 42.0)


class TestExplicitKeyOverride(_CacheIsolation):
    """A caller-supplied credential must actually reach the provider chain.

    Regression guard. An earlier refactor accepted api_key=... on
    get_zone_carbon_intensity and then dropped it, so the request silently fell
    through to the static matrix. Nothing failed loudly, which is the worst
    outcome for a carbon figure.
    """

    def test_key_for_prefers_the_explicit_override_over_the_environment(self):
        with patch.dict(os.environ, {"ELECTRICITY_MAPS_API_KEY": "from-env"}):
            self.assertEqual(
                ci._key_for("ELECTRICITY_MAPS_API_KEY", {"ELECTRICITY_MAPS_API_KEY": "explicit"}),
                "explicit",
            )

    def test_key_for_falls_back_to_the_environment(self):
        with patch.dict(os.environ, {"ELECTRICITY_MAPS_API_KEY": "from-env"}):
            self.assertEqual(ci._key_for("ELECTRICITY_MAPS_API_KEY", None), "from-env")

    def test_key_for_returns_empty_when_neither_is_present(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(ci._key_for("ELECTRICITY_MAPS_API_KEY", None), "")

    def test_provider_without_a_key_is_skipped_when_no_override_given(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(ci, "_providers", _offline_all):
                r = ci.resolve_carbon_intensity("ZZ", use_cache=False)
        results = {t["provider"]: t["result"] for t in r.tried}
        self.assertEqual(results.get("electricity_maps"), "no_key")

    def test_provider_is_attempted_when_an_override_is_given(self):
        attempted = {}

        def factory():
            providers = _REAL_PROVIDERS()
            for p in providers:
                p.requires_key = True
                p.key_env = "ELECTRICITY_MAPS_API_KEY"
                if p.provider_id == "electricity_maps":
                    def fetch(zone, key_override=None, _sink=attempted):
                        _sink["saw_key"] = (key_override or {}).get(
                            "ELECTRICITY_MAPS_API_KEY"
                        )
                        return None
                    p.fetch = fetch
                else:
                    p.fetch = lambda z, k=None: None
            return providers

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(ci, "_providers", factory):
                ci.resolve_carbon_intensity(
                    "ZZ",
                    use_cache=False,
                    key_override={"ELECTRICITY_MAPS_API_KEY": "explicit-key"},
                )
        self.assertEqual(attempted.get("saw_key"), "explicit-key")

    def test_optimizer_passes_api_key_through_to_the_chain(self):
        from app.optimizer import get_zone_carbon_intensity

        seen = {}

        def factory():
            providers = _REAL_PROVIDERS()
            for p in providers:
                p.requires_key = True
                p.key_env = "ELECTRICITY_MAPS_API_KEY"
                if p.provider_id == "electricity_maps":
                    def fetch(zone, key_override=None):
                        seen["key"] = (key_override or {}).get("ELECTRICITY_MAPS_API_KEY")
                        return {"carbon_intensity": 210.0, "observed_at": None}
                    p.fetch = fetch
                else:
                    p.fetch = lambda z, k=None: None
            return providers

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(ci, "_providers", factory):
                payload = get_zone_carbon_intensity("US-CAL-CISO", api_key="caller-key")

        self.assertEqual(seen.get("key"), "caller-key")
        self.assertEqual(payload["carbon_intensity"], 210.0)
        self.assertTrue(payload["is_live"])
        self.assertEqual(payload["intensity_source"], "electricity_maps")

    def test_provider_status_reflects_an_override(self):
        with patch.dict(os.environ, {}, clear=True):
            status = ci.provider_status(
                key_override={"ELECTRICITY_MAPS_API_KEY": "explicit"}
            )
        by_id = {p["provider_id"]: p for p in status["providers"]}
        self.assertTrue(by_id["electricity_maps"]["usable_now"])


if __name__ == "__main__":
    unittest.main()
