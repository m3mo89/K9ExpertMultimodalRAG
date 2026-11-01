from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from k9_expert.infrastructure.sqlite import SecurityRepository


class AdminSecurityService:
    def __init__(
        self,
        repository: SecurityRepository,
        configured_secret: str | None,
        confirmation_ttl_seconds: int = 300,
    ) -> None:
        self.repository = repository
        self.configured_secret = configured_secret
        self.confirmation_ttl_seconds = confirmation_ttl_seconds

    def authenticate(self, supplied_secret: str | None, actor_id: str) -> bool:
        valid = bool(
            self.configured_secret
            and supplied_secret
            and hmac.compare_digest(self.configured_secret, supplied_secret)
        )
        self.repository.audit(
            uuid4(), actor_id if valid else None, "admin_authenticated" if valid else "admin_denied"
        )
        return valid

    def issue_confirmation(
        self, actor_id: str, resource_id: str, operation: str, resource_version: str
    ) -> tuple[str, str]:
        expires = datetime.now(UTC) + timedelta(seconds=self.confirmation_ttl_seconds)
        token = self.repository.issue_confirmation(
            actor_id, resource_id, operation, resource_version, expires.isoformat()
        )
        self.repository.audit(uuid4(), actor_id, "confirmation_issued", resource_id)
        return token, expires.isoformat()

    def consume_confirmation(
        self,
        token: str,
        actor_id: str,
        resource_id: str,
        operation: str,
        resource_version: str,
    ) -> bool:
        valid = self.repository.consume_confirmation(
            token,
            actor_id,
            resource_id,
            operation,
            resource_version,
            datetime.now(UTC).isoformat(),
        )
        self.repository.audit(
            uuid4(),
            actor_id,
            "confirmation_consumed" if valid else "confirmation_denied",
            resource_id,
        )
        return valid
