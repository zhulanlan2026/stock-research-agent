from dataclasses import dataclass, field


@dataclass(frozen=True)
class AbacSubject:
    tenant_id: str
    user_id: str
    roles: frozenset[str]
    mfa_level: str = "none"


@dataclass(frozen=True)
class AbacResource:
    visibility_scope: str = "PUBLIC"
    owner_id: str | None = None
    license_policy_id: str | None = None
    symbol: str | None = None
    document_type: str | None = None


@dataclass(frozen=True)
class AbacEnvironment:
    system_health: str = "HEALTHY"
    ip_risk: str = "LOW"
    device_trust: str = "TRUSTED"


@dataclass(frozen=True)
class AbacModelPolicy:
    external_model_allowed: bool = True
    quote_allowed: bool = True
    export_allowed: bool = False


@dataclass(frozen=True)
class AbacRequest:
    purpose: str
    requested_mode: str = "standard"


@dataclass(frozen=True)
class AbacContext:
    subject: AbacSubject
    resource: AbacResource
    environment: AbacEnvironment = field(default_factory=AbacEnvironment)
    model: AbacModelPolicy = field(default_factory=AbacModelPolicy)
    request: AbacRequest | None = None


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    reasons: tuple[str, ...] = ()


class AbacPolicyEngine:
    def evaluate(self, context: AbacContext) -> PolicyDecision:
        reasons: list[str] = []

        if (
            not context.model.external_model_allowed
            and context.resource.visibility_scope in {"PRIVATE", "LICENSED"}
        ):
            reasons.append("EXTERNAL_MODEL_DENIED")

        if (
            context.resource.visibility_scope == "PRIVATE"
            and context.resource.owner_id != context.subject.user_id
            and "ADMIN" not in context.subject.roles
        ):
            reasons.append("DATA_SCOPE_DENIED")

        if context.environment.system_health == "BLOCK":
            reasons.append("SYSTEM_DEGRADED")

        if reasons:
            return PolicyDecision(decision="DENY", reasons=tuple(reasons))
        return PolicyDecision(decision="ALLOW")
