"""
Tool: generate_complaint
=========================
Generates a formal complaint letter or court filing template that
the citizen can use to take legal action.

Filing info is grounded in actual Nigerian law from the knowledge base:
    - Labour Act, 1974 (Sections 80-85 — jurisdiction, complaints, court powers)
    - Lagos Tenancy Law, 2011 (Sections 24-27 — proceedings to recover possession,
      Section 30 — arbitration, Section 32 — mediation via Citizens Mediation Centre)
    - Federal Competition and Consumer Protection Act, 2018 (Part III — FCCPC functions,
      Part VI — enforcement warrants)

Presentation example:
    User:  "I want to file a complaint against my landlord for illegal eviction."
    Agent: calls generate_complaint(complaint_type="illegal eviction", ...)
    Tool returns a ready-to-use letter with real filing procedures.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Filing info derived from actual Nigerian statutes in the knowledge base
# ---------------------------------------------------------------------------

FILING_INFO: dict[str, dict] = {
    "labor": {
        "agency": (
            "Ministry of Labor & Employment (administrative complaint) or "
            "National Industrial Court (court action). Per Labour Act Section 80, "
            "civil proceedings for recovery of wages or damages may be commenced "
            "before a Magistrate's Court or District Court."
        ),
        "filing_fee": "FREE (Ministry) or court filing fee per Magistrate Court schedule",
        "documents_needed": [
            "ID card",
            "Written statement of employment terms (Labour Act Section 7 requires employers to provide this)",
            "Payslips or evidence of wages paid",
            "Evidence of violation (messages, letters, witness statements)",
        ],
        "timeline": "Labour Act Section 81-83: complaint investigation and court hearing, typically 4-8 weeks",
        "legal_basis": "Labour Act, 1974 — Sections 80-85 (Settlement of disputes)",
    },
    "tenancy": {
        "agency": (
            "Magistrate Court or High Court of Lagos State (per Tenancy Law Section 2). "
            "Proceedings at High Court where rental value exceeds Magistrate Court jurisdiction. "
            "Court may also refer to mediation at Citizens Mediation Centre or Lagos Multi-Door "
            "Court House (Tenancy Law Section 32)."
        ),
        "filing_fee": "Court filing fee per Magistrate/High Court schedule",
        "documents_needed": [
            "ID card",
            "Tenancy agreement (Tenancy Law Section 3 — can be oral or written)",
            "Rent payment receipts (Tenancy Law Section 5 — landlord must issue these)",
            "Notice to quit received (Forms TL2/TL3 per Tenancy Law Section 13)",
            "Evidence of violation (photos, messages, witness statements)",
        ],
        "timeline": (
            "7 days notice of intention to recover possession (Tenancy Law Section 16), "
            "then court proceedings. Court may order possession within 6 months (Section 27(5))."
        ),
        "legal_basis": "Lagos Tenancy Law, 2011 — Sections 13, 16, 24-27, 32",
    },
    "consumer": {
        "agency": (
            "Federal Competition and Consumer Protection Commission (FCCPC). "
            "Established under FCCPA 2018, Part II (Section 3). The Commission has "
            "power to receive complaints and investigate (Part III, Section 17-18)."
        ),
        "filing_fee": "FREE — FCCPC handles consumer complaints at no cost",
        "documents_needed": [
            "ID card",
            "Receipt of purchase",
            "Product photos / evidence of defect",
            "Communication with seller (demanding refund/replacement)",
            "Description of goods and purpose communicated to seller (for FCCPA Section 122 claims)",
        ],
        "timeline": "FCCPC investigation per Part VI enforcement powers, typically 4-8 weeks",
        "legal_basis": "Federal Competition and Consumer Protection Act, 2018 — Sections 17, 18, 122, 136",
    },
    "constitution": {
        "agency": (
            "Federal High Court or State High Court for fundamental rights enforcement. "
            "Per Constitution 1999, Chapter IV (Fundamental Rights)."
        ),
        "filing_fee": "Court filing fee per Federal/State High Court schedule",
        "documents_needed": [
            "ID card",
            "Evidence of rights violation",
            "Witness statements",
            "Any relevant correspondence or official documents",
        ],
        "timeline": "Varies by court — fundamental rights cases may be expedited",
        "legal_basis": "Constitution of the Federal Republic of Nigeria, 1999 — Chapter IV",
    },
}


def generate_complaint(
    complaint_type: str,
    user_name: str = "[YOUR NAME]",
    opponent_name: str = "[OPPONENT NAME]",
    facts: str = "",
    topic: str = "",
) -> dict:
    """Generate a formal complaint letter and filing guide based on Nigerian law.

    Use this tool when the user wants to take action — file a complaint,
    write a demand letter, or submit a case to a court or agency.

    Args:
        complaint_type: What happened (e.g. "illegal eviction", "unpaid wages",
                        "defective product", "salary deduction").
        user_name:      Complainant's name (or placeholder).
        opponent_name:  Name of the person/company being complained about.
        facts:          Brief description of what happened.
        topic:          Legal topic for filing info lookup (labor, tenancy, consumer, constitution).

    Returns:
        A dict with the complaint letter text, filing instructions, and required documents.
    """
    if not complaint_type:
        return {"error": "Please specify what you are complaining about."}

    # --- Determine topic if not provided ---
    if not topic:
        type_lower = complaint_type.lower()
        if any(kw in type_lower for kw in ["salary", "wage", "fired", "dismiss", "employer", "work", "deduction", "overtime"]):
            topic = "labor"
        elif any(kw in type_lower for kw in ["rent", "evict", "landlord", "tenant", "lease", "premises"]):
            topic = "tenancy"
        elif any(kw in type_lower for kw in ["product", "defective", "refund", "purchase", "goods", "consumer"]):
            topic = "consumer"
        elif any(kw in type_lower for kw in ["rights", "constitution", "arrest", "detention", "freedom"]):
            topic = "constitution"
        else:
            topic = "labor"  # default

    # --- Get filing info ---
    filing = FILING_INFO.get(topic, {
        "agency": "Relevant authority — consult a lawyer for the appropriate jurisdiction",
        "filing_fee": "Contact the agency for current fees",
        "documents_needed": ["ID card", "Evidence of violation", "Communication records"],
        "timeline": "Varies — contact agency for estimate",
        "legal_basis": "Consult relevant Nigerian statute",
    })

    # --- Generate the complaint letter ---
    facts_section = facts if facts else f"[Describe the details of the {complaint_type} here]"

    letter = f"""
FORMAL COMPLAINT LETTER
========================

Date: [INSERT DATE]
To: {filing['agency']}

FROM: {user_name}
AGAINST: {opponent_name}

SUBJECT: Formal Complaint — {complaint_type.title()}

Dear Sir/Madam,

I, {user_name}, respectfully submit this formal complaint against
{opponent_name} for the following violation:

COMPLAINT TYPE: {complaint_type.title()}

LEGAL BASIS: {filing['legal_basis']}

FACTS OF THE CASE:
{facts_section}

RELIEF SOUGHT:
I respectfully request that the appropriate authority:
1. Investigate this matter promptly
2. Order {opponent_name} to cease the unlawful conduct
3. Award appropriate compensation for damages suffered
4. Take any other action deemed fit under the law

I attach all supporting documents as listed below and am available
for further questioning at your convenience.

Respectfully submitted,

____________________________
{user_name}
[Phone number]
[Address]
""".strip()

    return {
        "complaint_letter": letter,
        "filing_info": {
            "where_to_file": filing["agency"],
            "filing_fee": filing["filing_fee"],
            "documents_needed": filing["documents_needed"],
            "estimated_timeline": filing["timeline"],
            "legal_basis": filing["legal_basis"],
        },
        "next_steps": [
            "Fill in your personal details and the date",
            "Attach all supporting documents (receipts, photos, contracts, messages)",
            "Make 3 copies of everything (1 for court/agency, 1 for opponent, 1 for yourself)",
            f"Submit at: {filing['agency'].split('.')[0]}",
            "Keep your filing receipt — it is proof you submitted",
            "Follow up after 2 weeks if you haven't heard back",
        ],
        "topic": topic,
        "source": "Filing procedures derived from actual Nigerian statutes in rag/knowledge-base/",
    }
