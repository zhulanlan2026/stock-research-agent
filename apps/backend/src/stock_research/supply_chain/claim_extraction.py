from __future__ import annotations

import re
from dataclasses import dataclass

RELATION_PATTERNS = (
    (re.compile(r"(.+?)与(.+?)签订(?:合同|订单)"), "signed_contract_with"),
    (re.compile(r"(.+?)向(.+?)采购"), "procured_from"),
    (re.compile(r"(.+?)向(.+?)销售"), "sold_to"),
)


@dataclass(frozen=True)
class ExtractedClaim:
    subject: str
    predicate: str
    object: str
    evidence_text: str


class RuleBasedClaimExtractor:
    """确定性规则抽取供应链关系，后续可替换为模型抽取。"""

    def extract(self, text: str) -> list[ExtractedClaim]:
        claims: list[ExtractedClaim] = []
        for pattern, predicate in RELATION_PATTERNS:
            for match in pattern.finditer(text):
                claims.append(
                    ExtractedClaim(
                        subject=match.group(1).strip(),
                        predicate=predicate,
                        object=match.group(2).strip(),
                        evidence_text=match.group(0),
                    )
                )
        return claims
