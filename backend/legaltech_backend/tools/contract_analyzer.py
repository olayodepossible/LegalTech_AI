"""
Tool: analyze_contract
=======================
Extracts key terms from contract text and flags risky / non-standard clauses.

References real Nigerian law from the knowledge base:
    - Federal Competition and Consumer Protection Act, 2018 (Section 122 — right to return goods,
      Section 123 — marketing standards, Section 136 — liability for defective goods)
    - Labour Act, 1974 (Section 5 — prohibited deductions, Section 9 — contract restrictions)
    - Lagos Tenancy Law, 2011 (Section 6 — tenant rights, Section 44 — offences)

Presentation example:
    User:  "I'm buying ₦2M of fabric. Supplier sent me this contract."
    Agent: calls analyze_contract(contract_text="...", country="Nigeria")
    Tool returns flagged clauses → agent warns the user before they sign.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Risky-clause patterns with references to actual Nigerian law
# ---------------------------------------------------------------------------

RISKY_PATTERNS: list[dict] = [
    {
        "pattern": "buyer liable for all",
        "risk": "HIGH",
        "reason": (
            "Shifts ALL liability to buyer — non-standard. Under the Federal Competition "
            "and Consumer Protection Act, 2018 (Section 136), liability for defective goods "
            "rests with the producer/supplier, not the buyer."
        ),
        "suggestion": "Replace with: 'Each party shall be liable only for losses directly caused by its own breach.'",
    },
    {
        "pattern": "no refund",
        "risk": "HIGH",
        "reason": (
            "Eliminates refund rights. This may violate the Federal Competition and Consumer "
            "Protection Act, 2018 (Section 122), which grants consumers the right to return "
            "goods and receive a full refund if goods are unsuitable for the communicated "
            "purpose or do not match description/sample."
        ),
        "suggestion": "Add: 'Buyer is entitled to a full refund if goods are defective or not as described, per FCCPA Section 122.'",
    },
    {
        "pattern": "waive all rights",
        "risk": "HIGH",
        "reason": (
            "Blanket waiver of rights. The FCCPA, 2018 explicitly prohibits contract terms "
            "that 'waive or deprive a consumer of a right to return defective goods or any "
            "right set out in this Act.' Such clauses are void."
        ),
        "suggestion": "Remove clause entirely — it is unenforceable under Nigerian consumer protection law.",
    },
    {
        "pattern": "non-compete",
        "risk": "MEDIUM",
        "reason": (
            "Non-compete clauses can restrict future livelihood. Under the Labour Act, 1974 "
            "(Section 9(6)), no contract shall make it a condition that a worker shall or "
            "shall not join a trade union or relinquish membership — the same principle of "
            "freedom to work applies to overly broad non-competes."
        ),
        "suggestion": "Limit scope: restrict to specific industry, geography, and max 6-12 months.",
    },
    {
        "pattern": "automatic renewal",
        "risk": "MEDIUM",
        "reason": (
            "Contract renews without explicit consent — could trap party in unwanted obligations. "
            "Best practice under Nigerian contract law requires mutual written consent for renewal."
        ),
        "suggestion": "Change to: 'Renewal requires written agreement from both parties at least 30 days before expiry.'",
    },
    {
        "pattern": "penalty",
        "risk": "MEDIUM",
        "reason": "Penalty clauses may be unenforceable if disproportionate to actual loss under Nigerian common law.",
        "suggestion": "Replace 'penalty' with 'liquidated damages' and tie amount to estimated actual loss.",
    },
    {
        "pattern": "sole discretion",
        "risk": "MEDIUM",
        "reason": "Gives one party unchecked power to make decisions affecting both parties.",
        "suggestion": "Add: 'Such discretion shall be exercised reasonably and in good faith.'",
    },
    {
        "pattern": "deduction",
        "risk": "MEDIUM",
        "reason": (
            "Wage deduction clauses must comply with the Labour Act, 1974 (Section 5). "
            "Deductions for fines are prohibited. Only deductions for taxes, provident/pension "
            "funds, union dues, and overpayment (within 3 months) are permitted. Total "
            "deductions must not exceed one-third of monthly wages (Section 5(7))."
        ),
        "suggestion": "Ensure any deduction clause lists only permitted categories per Labour Act Section 5.",
    },
    {
        "pattern": "indemnify",
        "risk": "LOW",
        "reason": "Indemnification is standard but should be mutual — check if only one party indemnifies.",
        "suggestion": "Ensure indemnification is mutual or limited to each party's own negligence.",
    },
]

# Standard contract sections that should be present
EXPECTED_SECTIONS = [
    "payment terms",
    "delivery",
    "cancellation",
    "dispute resolution",
    "liability",
    "governing law",
]


def analyze_contract(contract_text: str, country: str = "Nigeria") -> dict:
    """Analyze contract text for risky or non-standard clauses.

    Use this tool when a user shares contract text and wants to know
    if it is fair, what risks exist, or what to negotiate before signing.
    Flags are grounded in actual Nigerian statutes from the knowledge base.

    Args:
        contract_text: The full text of the contract to analyze.
        country:       Country whose law applies (currently supports Nigeria).

    Returns:
        A dict with flagged clauses, missing sections, and an overall risk score.
    """
    if not contract_text or not contract_text.strip():
        return {"error": "No contract text provided. Please paste the contract text."}

    text_lower = contract_text.lower()

    # --- Flag risky clauses ---
    flagged_clauses = []
    for pattern in RISKY_PATTERNS:
        if pattern["pattern"] in text_lower:
            flagged_clauses.append({
                "clause_trigger": pattern["pattern"],
                "risk_level": pattern["risk"],
                "reason": pattern["reason"],
                "suggestion": pattern["suggestion"],
            })

    # --- Check for missing standard sections ---
    missing_sections = [
        section for section in EXPECTED_SECTIONS
        if section not in text_lower
    ]

    # --- Overall risk assessment ---
    high_count = sum(1 for c in flagged_clauses if c["risk_level"] == "HIGH")
    medium_count = sum(1 for c in flagged_clauses if c["risk_level"] == "MEDIUM")

    if high_count >= 2:
        overall_risk = "HIGH — Do NOT sign without legal review"
    elif high_count == 1 or medium_count >= 2:
        overall_risk = "MEDIUM — Negotiate flagged clauses before signing"
    elif flagged_clauses:
        overall_risk = "LOW — Minor issues, generally acceptable"
    else:
        overall_risk = "LOW — No obvious risky clauses detected"

    return {
        "country": country,
        "overall_risk": overall_risk,
        "flagged_clauses": flagged_clauses,
        "flagged_count": len(flagged_clauses),
        "missing_sections": missing_sections,
        "missing_count": len(missing_sections),
        "legal_references": [
            "Federal Competition and Consumer Protection Act, 2018 (Sections 122, 123, 136)",
            "Labour Act, 1974 (Sections 5, 9)",
            "Source: rag/knowledge-base/Federal Consumer Act.md, Labour Act.md",
        ],
        "recommendation": (
            f"Review this contract under {country} law. "
            f"{len(flagged_clauses)} clause(s) flagged, "
            f"{len(missing_sections)} standard section(s) missing."
        ),
    }
