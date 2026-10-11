"""Enterprise Single Sign-On (SSO), SCIM 2.0 Provisioning, and Data Residency Engine.

Implements Fortune 500 Procurement Security Standards:
1. SAML 2.0 / OIDC Identity Provider Integration (Okta, Azure AD / Microsoft Entra ID).
2. SCIM 2.0 User Provisioning and Deprovisioning standard (/api/scim/v2/Users).
3. Data Residency & Sovereign Cloud Enforcement (Strict EU GDPR / US / FedRAMP boundaries).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("greencode.enterprise.auth")


class DataResidencyZone:
    GLOBAL = "GLOBAL"
    EU_STRICT = "EU_STRICT"       # GDPR Data sovereignty (Germany / France / Ireland)
    US_STRICT = "US_STRICT"       # US FedRAMP / HIPAA sovereign boundary
    APAC_STRICT = "APAC_STRICT"   # Singapore / Tokyo regional enclave


@dataclass
class EnterpriseSSOConfig:
    """SAML 2.0 / OIDC Identity Provider Configuration for an Organization."""
    org_id: int
    idp_entity_id: str
    sso_url: str
    certificate_x509: str
    issuer: str
    enabled: bool = True
    enforce_sso_only: bool = False
    allowed_domains: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SCIMUser:
    """RFC 7643 SCIM 2.0 Core User Schema Representation."""
    id: str
    user_name: str
    display_name: str
    email: str
    active: bool = True
    roles: List[str] = field(default_factory=lambda: ["engineer"])
    external_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EnterpriseGovernanceManager:
    """Manages identity federation, SCIM sync, and data residency boundary compliance with SQLite persistence."""

    def __init__(self):
        self._sso_configs: Dict[int, EnterpriseSSOConfig] = {}
        self._scim_users: Dict[str, SCIMUser] = {}
        self._org_data_residency: Dict[int, str] = {}
        self._ensure_persistence_table()

    @staticmethod
    def _ensure_persistence_table() -> None:
        """Ensure the SQLite persistence table for governance state exists."""
        try:
            from sqlalchemy import text
            from app.database import sync_engine, init_db
            init_db()
            with sync_engine.begin() as conn:
                conn.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS enterprise_governance_kv ("
                        "namespace VARCHAR(64) NOT NULL, "
                        "item_key VARCHAR(128) NOT NULL, "
                        "payload_json TEXT NOT NULL, "
                        "updated_at VARCHAR(64) NOT NULL, "
                        "PRIMARY KEY (namespace, item_key))"
                    )
                )
        except Exception:
            pass  # no-op

    @classmethod
    def _kv_put(cls, namespace: str, key: str, payload: Dict[str, Any]) -> None:
        try:
            from sqlalchemy import text
            from app.database import sync_engine
            cls._ensure_persistence_table()
            now_iso = datetime.now(timezone.utc).isoformat()
            payload_str = json.dumps(payload)
            with sync_engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT OR REPLACE INTO enterprise_governance_kv "
                        "(namespace, item_key, payload_json, updated_at) "
                        "VALUES (:ns, :k, :p, :u)"
                    ),
                    {"ns": namespace, "k": str(key), "p": payload_str, "u": now_iso},
                )
        except Exception:
            pass  # no-op

    @classmethod
    def _kv_get(cls, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        try:
            from sqlalchemy import text
            from app.database import sync_engine
            cls._ensure_persistence_table()
            with sync_engine.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT payload_json FROM enterprise_governance_kv "
                        "WHERE namespace = :ns AND item_key = :k"
                    ),
                    {"ns": namespace, "k": str(key)},
                ).fetchone()
                if row and row[0]:
                    return json.loads(row[0])
        except Exception:
            pass  # no-op
        return None

    def set_data_residency_policy(self, org_id: int, policy: str) -> None:
        """Enforce strict geographic boundary for carbon grid and AI refactor calls."""
        valid_policies = {
            DataResidencyZone.GLOBAL,
            DataResidencyZone.EU_STRICT,
            DataResidencyZone.US_STRICT,
            DataResidencyZone.APAC_STRICT,
        }
        if policy not in valid_policies:
            raise ValueError(f"Invalid data residency policy: {policy}. Must be one of {valid_policies}")
        self._org_data_residency[org_id] = policy
        self._kv_put("residency", str(org_id), {"org_id": org_id, "policy": policy})
        logger.info(f"Organization {org_id} configured with Data Residency policy: {policy}")

    def get_data_residency_policy(self, org_id: Optional[int]) -> str:
        """Retrieve active data residency policy."""
        if org_id is None:
            return DataResidencyZone.GLOBAL
        if org_id in self._org_data_residency:
            return self._org_data_residency[org_id]
        stored = self._kv_get("residency", str(org_id))
        if stored and "policy" in stored:
            self._org_data_residency[org_id] = str(stored["policy"])
            return self._org_data_residency[org_id]
        return DataResidencyZone.GLOBAL

    def validate_outbound_data_transfer(
        self,
        org_id: Optional[int],
        destination_service: str,
        destination_region: str,
    ) -> Dict[str, Any]:
        """Validate if an outbound API call violates the tenant's data residency rule."""
        policy = self.get_data_residency_policy(org_id)
        if policy == DataResidencyZone.GLOBAL:
            return {"allowed": True, "reason": "Global routing permitted"}

        region_upper = (destination_region or "").upper()
        if policy == DataResidencyZone.EU_STRICT:
            eu_allowed_regions = {
                "DE", "FR", "IE", "SE", "NL", "EU", "NO-NO1", "CH",
                "EU-WEST-1", "EU-WEST-2", "EU-WEST-3", "EU-CENTRAL-1", "EU-NORTH-1",
            }
            if region_upper not in eu_allowed_regions:
                return {
                    "allowed": False,
                    "reason": f"GDPR Breach Prevented: Outbound call to {destination_service} in {destination_region} blocked by EU_STRICT policy.",
                }

        if policy == DataResidencyZone.US_STRICT:
            us_allowed_regions = {
                "US", "US-CAL-CISO", "US-MIDW-MISO", "US-MIDA-PJM", "US-TEX-ERCO", "US-NE-ISNE", "US-NW-PACW",
                "US-EAST-1", "US-EAST-2", "US-WEST-1", "US-WEST-2",
            }
            if region_upper not in us_allowed_regions:
                return {
                    "allowed": False,
                    "reason": f"Sovereignty Policy Violation: Outbound call to {destination_service} in {destination_region} blocked by US_STRICT policy.",
                }

        if policy == DataResidencyZone.APAC_STRICT:
            apac_allowed_regions = {
                "SG", "JP-TK", "AU-NSW", "IN-WE", "KR", "AP-SOUTHEAST-1", "AP-NORTHEAST-1", "AP-SOUTH-1",
            }
            if region_upper not in apac_allowed_regions:
                return {
                    "allowed": False,
                    "reason": f"Sovereignty Policy Violation: Outbound call to {destination_service} in {destination_region} blocked by APAC_STRICT policy.",
                }

        return {"allowed": True, "reason": f"Call within {policy} boundary"}

    def configure_sso(
        self,
        org_id: int,
        idp_entity_id: str,
        sso_url: str,
        certificate_x509: str,
        issuer: str,
        allowed_domains: List[str],
        enforce_sso_only: bool = False,
    ) -> EnterpriseSSOConfig:
        """Register or update an Enterprise SAML/OIDC Identity Provider with URL & certificate validation."""
        if not sso_url or not (sso_url.startswith("https://") or sso_url.startswith("http://")):
            raise ValueError("sso_url must be a valid HTTP/HTTPS endpoint URL.")
        if not certificate_x509 or len(certificate_x509.strip()) < 8:
            raise ValueError("certificate_x509 must be a non-empty X.509 certificate or PEM block.")

        cfg = EnterpriseSSOConfig(
            org_id=org_id,
            idp_entity_id=idp_entity_id,
            sso_url=sso_url,
            certificate_x509=certificate_x509,
            issuer=issuer,
            allowed_domains=allowed_domains,
            enforce_sso_only=enforce_sso_only,
        )
        self._sso_configs[org_id] = cfg
        self._kv_put("sso_config", str(org_id), asdict(cfg))
        return cfg

    def get_sso_config(self, org_id: int) -> Optional[EnterpriseSSOConfig]:
        """Retrieve SSO configuration for an organization."""
        if org_id in self._sso_configs:
            return self._sso_configs[org_id]
        stored = self._kv_get("sso_config", str(org_id))
        if stored:
            cfg = EnterpriseSSOConfig(**stored)
            self._sso_configs[org_id] = cfg
            return cfg
        return None

    @staticmethod
    def _normalize_cert_body(pem_or_b64: str) -> str:
        """Strip PEM headers/footers and whitespace to compare canonical base64 X.509 bodies."""
        lines = [
            ln.strip()
            for ln in (pem_or_b64 or "").splitlines()
            if ln.strip() and not ln.strip().startswith("-----")
        ]
        return "".join(lines)

    def verify_saml_response(self, org_id: int, saml_response_b64: str) -> Dict[str, Any]:
        """Parse and validate a SAML 2.0 XML Response/Assertion against the organization's IdP configuration.

        Enforces:
        - XXE / DTD entity expansion defense (`<!DOCTYPE` / `<!ENTITY` rejection)
        - Issuer / IdP EntityID match against registered `EnterpriseSSOConfig`
        - `<Conditions NotBefore="..." NotOnOrAfter="...">` UTC clock window validation
        - Embedded `<ds:X509Certificate>` match against tenant's pinned X.509 certificate
        - Subject `<NameID>` email domain enforcement against `allowed_domains`
        """
        import base64
        import hashlib
        import xml.etree.ElementTree as ET

        cfg = self.get_sso_config(org_id)
        if not cfg or not cfg.enabled:
            return {"verified": False, "reason": f"SSO is not configured or not enabled for organization {org_id}."}

        raw_input = (saml_response_b64 or "").strip()
        if not raw_input:
            return {"verified": False, "reason": "Empty SAMLResponse payload."}

        if raw_input.startswith("<"):
            xml_text = raw_input
        else:
            try:
                xml_text = base64.b64decode(raw_input, validate=False).decode("utf-8", errors="strict")
            except Exception as exc:
                return {"verified": False, "reason": f"Invalid base64 SAMLResponse encoding: {exc}"}

        # Security: block XML External Entity (XXE) & billion-laughs DTD declarations
        upper_xml = xml_text.upper()
        if "<!DOCTYPE" in upper_xml or "<!ENTITY" in upper_xml:
            return {"verified": False, "reason": "Security Violation: DTD/ENTITY declarations are forbidden in SAML XML."}

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            return {"verified": False, "reason": f"Malformed SAML XML document: {exc}"}

        def _local_name(tag: str) -> str:
            return tag.split("}", 1)[-1] if "}" in tag else tag

        issuer_val: Optional[str] = None
        name_id_val: Optional[str] = None
        not_before_str: Optional[str] = None
        not_on_or_after_str: Optional[str] = None
        embedded_cert: Optional[str] = None

        for elem in root.iter():
            lname = _local_name(elem.tag)
            if lname == "Issuer" and elem.text and not issuer_val:
                issuer_val = elem.text.strip()
            elif lname == "NameID" and elem.text and not name_id_val:
                name_id_val = elem.text.strip()
            elif lname == "Conditions":
                not_before_str = elem.attrib.get("NotBefore") or not_before_str
                not_on_or_after_str = elem.attrib.get("NotOnOrAfter") or not_on_or_after_str
            elif lname == "X509Certificate" and elem.text and not embedded_cert:
                embedded_cert = elem.text.strip()

        expected_issuers = {cfg.issuer.strip(), cfg.idp_entity_id.strip()}
        if not issuer_val or issuer_val not in expected_issuers:
            return {
                "verified": False,
                "reason": f"SAML Issuer mismatch: got '{issuer_val}', expected one of {sorted(expected_issuers)}.",
            }

        now_utc = datetime.now(timezone.utc)
        if not_before_str:
            try:
                nb_dt = datetime.fromisoformat(not_before_str.replace("Z", "+00:00"))
                if now_utc < nb_dt:
                    return {"verified": False, "reason": f"SAML Assertion is not yet valid (NotBefore={not_before_str})."}
            except ValueError:
                return {"verified": False, "reason": f"Unparseable NotBefore timestamp: {not_before_str}"}

        if not_on_or_after_str:
            try:
                noa_dt = datetime.fromisoformat(not_on_or_after_str.replace("Z", "+00:00"))
                if now_utc >= noa_dt:
                    return {"verified": False, "reason": f"SAML Assertion has expired (NotOnOrAfter={not_on_or_after_str})."}
            except ValueError:
                return {"verified": False, "reason": f"Unparseable NotOnOrAfter timestamp: {not_on_or_after_str}"}

        expected_cert_body = self._normalize_cert_body(cfg.certificate_x509)
        actual_cert_body = self._normalize_cert_body(embedded_cert or "")
        if not actual_cert_body or actual_cert_body != expected_cert_body:
            return {
                "verified": False,
                "reason": "SAML X.509 signing certificate missing or does not match organization's pinned IdP certificate.",
            }

        if not name_id_val:
            return {"verified": False, "reason": "SAML Assertion is missing a Subject <NameID>."}

        if cfg.allowed_domains and "@" in name_id_val:
            user_domain = name_id_val.rsplit("@", 1)[-1].lower()
            allowed_set = {d.lower().lstrip("@") for d in cfg.allowed_domains}
            if user_domain not in allowed_set:
                return {
                    "verified": False,
                    "reason": f"Subject email domain '{user_domain}' is not permitted by organization SSO allowed_domains.",
                }

        cert_fingerprint = hashlib.sha256(actual_cert_body.encode("utf-8")).hexdigest()
        return {
            "verified": True,
            "org_id": org_id,
            "subject_name_id": name_id_val,
            "issuer": issuer_val,
            "not_before": not_before_str,
            "not_on_or_after": not_on_or_after_str,
            "cert_sha256_fingerprint": cert_fingerprint,
            "reason": "SAML 2.0 XML Assertion verified against pinned IdP entity, X.509 certificate, and validity window.",
        }

    # -----------------------------------------------------------------------
    # SCIM 2.0 PROTOCOL IMPLEMENTATION (RFC 7644)
    # -----------------------------------------------------------------------
    def scim_create_user(self, payload: Dict[str, Any], org_id: int) -> Dict[str, Any]:
        """Process RFC 7644 SCIM 2.0 User Creation (e.g. from Okta / Azure AD sync)."""
        scim_id = str(uuid.uuid4())
        user_name = payload.get("userName") or payload.get("email", "")
        display_name = payload.get("displayName") or user_name
        emails = payload.get("emails", [])
        email = emails[0].get("value") if emails else user_name
        external_id = payload.get("externalId")

        roles = [r.get("value", "engineer") for r in payload.get("roles", [])]
        if not roles:
            roles = ["engineer"]

        scim_user = SCIMUser(
            id=scim_id,
            user_name=user_name,
            display_name=display_name,
            email=email,
            roles=roles,
            external_id=external_id,
        )
        self._scim_users[scim_id] = scim_user
        self._kv_put("scim_user", scim_id, asdict(scim_user))

        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": scim_user.id,
            "externalId": scim_user.external_id,
            "userName": scim_user.user_name,
            "displayName": scim_user.display_name,
            "active": scim_user.active,
            "emails": [{"value": scim_user.email, "primary": True}],
            "roles": [{"value": r} for r in scim_user.roles],
            "meta": {
                "resourceType": "User",
                "created": scim_user.created_at,
                "location": f"/api/scim/v2/Users/{scim_user.id}",
            },
        }

    def scim_get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch SCIM user representation."""
        u = self._scim_users.get(user_id)
        if not u:
            stored = self._kv_get("scim_user", user_id)
            if stored:
                u = SCIMUser(**stored)
                self._scim_users[user_id] = u
        if not u:
            return None
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": u.id,
            "userName": u.user_name,
            "displayName": u.display_name,
            "active": u.active,
            "emails": [{"value": u.email, "primary": True}],
            "roles": [{"value": r} for r in u.roles],
        }

    def scim_deprovision_user(self, user_id: str) -> bool:
        """Handle SCIM user de-provisioning on employee offboarding."""
        u = self._scim_users.get(user_id)
        if not u:
            stored = self._kv_get("scim_user", user_id)
            if stored:
                u = SCIMUser(**stored)
                self._scim_users[user_id] = u
        if u:
            u.active = False
            self._kv_put("scim_user", user_id, asdict(u))
            return True
        return False


# Global singleton instance
governance_manager = EnterpriseGovernanceManager()

