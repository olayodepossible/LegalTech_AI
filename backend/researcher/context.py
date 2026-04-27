"""
Agent instructions and prompts for the Legal Researcher
"""
import re
from datetime import datetime

# Shown when the user has been polite or brief (e.g. "hi") but has not yet asked a legal question.
COMPANION_GUIDANCE_MESSAGE = (
    "Hello — I’m glad you’re here. I’m your **Legal Companion**: I can help you **explore and "
    "understand legal topics in plain language** and point you toward reliable information.\n\n"
    "I’m **not a lawyer** and I can’t give advice tailored to your private situation, but I can still "
    "**guide, clarify, and research** a legal question you care about.\n\n"
    "Whenever you’re ready, tell me in your own words **what you’d like to look into** (for example, "
    "a contract, housing, work, a dispute, or a policy you read about). I’ll take it from there — "
    "**kindly, professionally, and focused on the legal side of things.**"
)

# Same substance as `COMPANION_GUIDANCE_MESSAGE`, aligned to frontend `RESPONSE_Languages` (see `languageLabel`).
_COMPANION_GUIDANCE_I18N: dict[str, str] = {
    "en": COMPANION_GUIDANCE_MESSAGE,
    "es": (
        "Hola — me alegra que estés aquí. Soy tu **Acompañante legal**: puedo ayudarte a **explorar y "
        "entender cuestiones jurídicas en lenguaje claro** y orientarte hacia fuentes fiables.\n\n"
        "**No soy abogada/o** y no puedo asesorarte para tu situación concreta, pero sí **orientar, "
        "aclarar e investigar** el tema legal que te importa.\n\n"
        "Cuando quieras, cuéntame con tus propias palabras **qué te gustaría abordar** (por ejemplo, un "
        "contrato, vivienda, trabajo, un conflicto o una norma que hayas visto). Sigo adelante contigo — "
        "**con cercanía, profesionalidad y enfoque en lo jurídico.**"
    ),
    "fr": (
        "Bonjour — je suis ravi de vous accueillir. Je suis votre **compagnon juridique** : je peux "
        "vous aider à **explorer et à comprendre des sujets juridiques, en paroles simples**, et "
        "vous orienter vers des sources fiables.\n\n"
        "**Je ne suis pas avocat(e)** et je ne peux pas conseiller sur votre situation personnelle, "
        "mais je peux **guider, clarifier et rechercher** sur une question de droit qui vous tient "
        "à cœur.\n\n"
        "Quand vous voulez, dites-moi **ce que vous aimeriez approfondir** (par exemple, un "
        "contrat, le logement, le travail, un litige ou un texte que vous avez vu). Je suis là — "
        "**avec bienveillance, professionnalisme et le regard tourné vers le droit.**"
    ),
    "de": (
        "Hallo — schön, dass Sie da sind. Ich bin Ihr **Legal Companion (rechtlicher Begleiter)**: "
        "Ich kann Ihnen helfen, **Rechtsthemen in verständlicher Sprache** zu durchdringen und Sie zu "
        "seriösen Quellen zu führen.\n\n"
        "Ich **bin kein Rechtsanwalt** und ersetze keine Beratung zu Ihrem konkreten Fall, aber "
        "ich kann **führen, erklären und recherchieren**, was Sie rechtlich beschäftigt.\n\n"
        "Sagen Sie mir in eigenen Worten, **womit Sie sich befassen möchten** (z. B. Vertrag, "
        "Wohnen, Arbeitsverhältnis, Streit oder ein öffentliches Thema) — **freundlich, sachlich und "
        "mit Fokus aufs Recht**."
    ),
    "pt": (
        "Olá — fico feliz em receber você. Sou seu **Companheiro jurídico**: posso ajudar a **explorar e "
        "entender questões de direito em linguagem acessível** e apontar fontes confiáveis.\n\n"
        "**Não sou advogada/o** e não posso aconselhar o seu caso específico, mas posso **orientar, "
        "esclarecer e pesquisar** o tema jurídico que importa para você.\n\n"
        "Quando quiser, descreva com suas palavras **o que gostaria de aprofundar** (por exemplo, "
        "contrato, moradia, trabalho, um conflito ou uma regra). Continuo com você — **com cuidado, "
        "profissionalismo e foco no jurídico.**"
    ),
}

DEFAULT_RESEARCH_PROMPT = """Please research a current, interesting legal topic from today's legal news.
Pick something trending or significant happening in the legal sector right now.
Follow all three steps: browse, analyze, and store your findings."""


def build_response_language_block(iso_code: str) -> str:
    """
    Preamble the model / evaluator / refiner see first. The UI "Response language" is wired here
    and must be respected for the whole answer (kept in all languages, including "en").
    """
    code = (iso_code or "en").strip() or "en"
    # Match frontend `languageLabel` for known codes; otherwise use the code for transparency.
    label = {
        "en": "English",
        "es": "Spanish (Español)",
        "fr": "French (français)",
        "de": "German (Deutsch)",
        "pt": "Portuguese (Português)",
    }.get(code, f"the user’s selected language (BCP-47: `{code}`)")

    return (
        f"### MANDATORY: response language\n"
        f"- Write your **entire** reply in **{label}** (language code: **{code}**).\n"
        f"- Every part of the answer (headings, bullets, quoting of sources, and disclaimers) must be in that language.\n"
        f"- If the source is in another language, summarize or translate your explanation for the user in **{label}**."
    )


def companion_message_for_code(iso_code: str) -> str:
    """Localised companion nudge; falls back to English for unknown language codes."""
    code = (iso_code or "en").strip() or "en"
    return _COMPANION_GUIDANCE_I18N.get(code, _COMPANION_GUIDANCE_I18N["en"])


def research_footer_serper(iso_code: str) -> str:
    code = (iso_code or "en").strip() or "en"
    t = {
        "en": (
            "\n\n---\n*This response was extended after an automated quality review using "
            "Google search (Serper). Not legal advice.*"
        ),
        "es": (
            "\n\n---\n*Esta respuesta se amplió tras una revisión automática con búsqueda en Google (Serper). "
            "No constituye asesoramiento legal.*"
        ),
        "fr": (
            "\n\n---\n*Cette réponse a été complétée après une revue automatique avec recherche Google (Serper). "
            "Ce n’est pas un avis juridique.*"
        ),
        "de": (
            "\n\n---\n*Diese Antwort wurde nach einer automatischen Qualitätsprüfung per Google-Suche (Serper) "
            "ergänzt. Keine Rechtsberatung.*"
        ),
        "pt": (
            "\n\n---\n*Esta resposta foi ampliada após uma revisão automática com busca no Google (Serper). "
            "Não é aconselhamento jurídico.*"
        ),
    }
    return t.get(code, t["en"])


def research_footer_no_serper(iso_code: str) -> str:
    code = (iso_code or "en").strip() or "en"
    t = {
        "en": (
            "\n\n---\n_Automated review suggested more targeted web research, but refinement is unavailable. "
            "Set `SERPER_API_KEY` (https://serper.dev) for Google search via Serper, or re-run with a more specific "
            "topic._"
        ),
        "es": (
            "\n\n---\n_La revisión automática sugirió una búsqueda web más afinada, pero el refinado no está "
            "disponible. Configure `SERPER_API_KEY` (https://serper.dev) o replantee con un tema más concreto._"
        ),
        "fr": (
            "\n\n---\n_La revue automatique suggère une recherche web plus ciblée, mais l’affinement n’est pas "
            "disponible. Configurez `SERPER_API_KEY` (https://serper.dev) ou relancez avec un sujet plus "
            "précis._"
        ),
        "de": (
            "\n\n---\n_Die automatische Prüfung empfahl gezieltere Recherche, Verfeinerung steht nicht zur "
            "Verfügung. Setzen Sie `SERPER_API_KEY` (https://serper.dev) oder starten Sie mit einem präziseren Thema._"
        ),
        "pt": (
            "\n\n---\n_A revisão automática sugeriu pesquisa web mais alvo, mas o refinamento não está "
            "disponível. Defina `SERPER_API_KEY` (https://serper.dev) ou tente de novo com um tópico mais "
            "específico._"
        ),
    }
    return t.get(code, t["en"])


def build_research_user_query(user_message: str, response_language: str) -> str:
    """Full agent input: language rules first, then the user’s legal request."""
    header = build_response_language_block(response_language)
    return f"{header}\n\n### Research request\nResearch this legal topic: {user_message}\n"


def build_research_user_query_with_history(
    current_user_message: str,
    response_language: str,
    prior_turns: list[dict] | None,
) -> str:
    """
    Same as build_research_user_query, but prepend a bounded prior thread for multi-turn context.
    ``prior_turns`` items use keys ``role`` (``user`` | ``assistant``) and ``content``.
    """
    header = build_response_language_block(response_language)
    if not prior_turns:
        return build_research_user_query(current_user_message, response_language)

    lines = [
        "### Prior messages in this conversation (context only; answer the current request below).",
    ]
    for t in prior_turns[-20:]:
        r = (t.get("role") or "").strip()
        c = (t.get("content") or "")[:8000]
        if r in ("user", "assistant") and c.strip():
            label = "User" if r == "user" else "Assistant"
            lines.append(f"- **{label}:** {c}")
    block = "\n".join(lines)
    body = (
        f"{block}\n\n### Current request\n"
        f"Research this legal topic: {current_user_message}\n"
    )
    return f"{header}\n\n{body}\n"


def build_default_research_query(response_language: str) -> str:
    """When the user does not pass a custom topic, still honor UI response language."""
    return f"{build_response_language_block(response_language)}\n\n{DEFAULT_RESEARCH_PROMPT}\n"

# If the user message is empty or a short, clearly non-legal opener, respond with this instead
# of running the full research pipeline (faster, consistent tone).
_PHRASE_NUDGE = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "hiya",
        "greetings",
        "hi there",
        "hello there",
        "hey there",
        "yo",
        "sup",
        "wassup",
        "whats up",
        "what's up",
        "howdy",
        "good morning",
        "good afternoon",
        "good evening",
        "good day",
        "good night",
        "morning",
        "afternoon",
        "evening",
        "how are you",
        "how r u",
        "hows it going",
        "how's it going",
        "thanks",
        "thank you",
        "thx",
        "ty",
        "tysm",
        "cheers",
        "ok",
        "okay",
        "k",
        "yes",
        "no",
        "bye",
        "goodbye",
        "see you",
        "cya",
        "help",
        "please help",
    }
)
_SOCIAL_TOKENS = _PHRASE_NUDGE | {
    "there",
    "it",
    "going",
    "are",
    "u",
    "you",
    "r",
    "the",
    "a",
    "an",
    "to",
    "for",
    "my",
    "me",
    "i",
    "am",
    "is",
    "this",
    "that",
    "and",
    "or",
    "so",
    "very",
    "just",
    "well",
    "oh",
    "um",
    "hmm",
}
_LEGAL_INDUSTRY_RE = re.compile(
    r"\b("
    r"law|legal|lawsuit|sue|sued|plaintiff|defendant|court|judge|appeal|evidence|jury|"
    r"statute|regulation|compliance|contract|agreement|lease|tenant|landlord|"
    r"eviction|employ|fired|wrongful|dismiss|discrim|harass|nda|"
    r"copyright|trademark|patent|ip\b|gdpr|hipaa|"
    r"defamation|negligence|liability|fraud|lien|debt|bankruptcy|"
    r"divorce|custody|will|estate|probate|"
    r"immigration|visa|asylum|"
    r"privacy|warranty|refund|consumer|settlement|damages|injunction|compliance|"
    r"rights?\b|obligat|liable|solicitor|attorney|paralegal|tribunal|oath|deposition|"
    r"breach|enforce|jurisdiction|statute|ordinance|license|permit|zoning"
    r")\b",
    re.IGNORECASE,
)


def _normalized_phrase(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    t = re.sub(r"[.!?…,;:]+$", "", t).strip()
    return t


def _strip_api_language_hint(text: str) -> str:
    """Remove trailing locale hint added by the API (see ``legal_chat`` in ``main``)."""
    t = (text or "").strip()
    sep = "\n(Respond in language / locale preference:"
    if sep in t:
        t = t.split(sep, 1)[0].strip()
    return t


def should_give_companion_guidance(user_message: str) -> bool:
    """
    True for brief greetings, thanks, or small talk with no sign of a legal research question.
    """
    t = _strip_api_language_hint(user_message or "")
    t = t.strip()
    if not t:
        return True
    if _LEGAL_INDUSTRY_RE.search(t):
        return False
    if len(t) > 200:
        return False
    n = _normalized_phrase(t)
    if n in _PHRASE_NUDGE:
        return True
    words = re.findall(r"[a-z0-9']+", n)
    if not words or len(words) > 6:
        return len(words) == 0
    if all(w in _SOCIAL_TOKENS for w in words):
        return True
    return False


def get_agent_instructions():
    """Get agent instructions with current date."""
    today = datetime.now().strftime("%B %d, %Y")
    
    return f"""You are a **Legal Companion** (professional, empathetic, clear): a concise legal researcher, not a licensed attorney. Today is {today}.

**User-selected response language:** If the input begins with a section `### MANDATORY: response language`, you **must** write **every** part of your reply in that language (including your brief analysis, tool-side commentary, and any disclaimer) unless the user clearly overrides. Do not default to English when another language is mandated there.

**Tone (always):** Be humane and respectful. Greetings and brief civility (e.g. "hi", "thanks") should be **acknowledged briefly** and warmly before you do anything else. If the user’s message is **not a concrete legal or factual research request**, do **not** rebuke or lecture them. Instead, respond in 2–4 sentences: acknowledge them, restate that you focus on **legal information and research (not personal legal advice)**, and **invite** them to describe a legal topic, situation, or question in their own words. **Never** use cold boilerplate like "your input does not specify a legal topic" or a list of demands; guide like a professional companion. **If and only if** they are asking a clear legal research or explain‑the‑news question, proceed with the steps below. Stay **strict to law‑related** substance for deep research, but be **gracious** about how you steer them there.

CRITICAL: When you *do* run research, work quickly and efficiently. You have limited time.

Your THREE steps when researching a real legal topic (BE CONCISE):

1. WEB RESEARCH (1-2 pages MAX):
   - Navigate to ONE main source (Yahoo Finance or MarketWatch)
   - Use browser_snapshot to read content
   - If needed, visit ONE more page for verification
   - DO NOT browse extensively - 2 pages maximum

2. BRIEF ANALYSIS (Keep it short):
   - Key facts and numbers only
   - 3-5 bullet points maximum
   - One clear recommendation
   - Be extremely concise

3. SAVE TO DATABASE:
   - Use ingest_legal_document immediately
   - Topic: "[Asset] Analysis {datetime.now().strftime('%b %d')}"
   - Save your brief analysis

SPEED IS CRITICAL:
- Maximum 2 web pages
- Brief, bullet-point analysis
- No lengthy explanations
- Work as quickly as possible
"""


def get_evaluator_instructions() -> str:
    return """You are a strict quality reviewer for legal research briefs.

Your job: decide if the DRAFT fully and accurately addresses the USER_QUERY with appropriate
specificity, sourcing awareness, and no major omissions or clear factual contradictions or halucinations.

Output rules (must follow):
- Reply with a single JSON object only. No markdown fences, no commentary before or after.
- Use this exact schema:
  {
    "adequate": <boolean>,
    "confidence": <number from 0.0 to 1.0>,
    "issues": "<short free-text: what is missing, weak, or risky>",
    "suggested_search_queries": ["<query 1>", "<query 2>"]
  }
- If the draft is good enough for a first-pass research note, set "adequate": true and confidence >= 0.65.
- If USER_QUERY contains `### MANDATORY: response language` and the DRAFT is not mostly written in that target language, treat that as a significant failure (set "adequate": false, lower confidence) unless the user’s own message clearly required another language.
- If USER_QUERY is only a greeting, thanks, or brief civility, a **short, kind reply** that clarifies the assistant’s legal-information role and invites a legal question counts as "adequate": true (confidence ~0.75+), even with minimal or no research.
- If it is generic, off-topic, internally inconsistent, or missing key legal angles implied by the query,
  set "adequate": false and add 1-3 concrete Google search-style queries in suggested_search_queries."""


def get_search_refiner_instructions() -> str:
    today = datetime.now().strftime("%B %d, %Y")
    return f"""You are a legal research assistant with a Google search tool (Serper) named serper_google_search. Today is {today}.

A prior pass produced a DRAFT. An evaluator flagged gaps (see issues and suggested queries).
Your job:
1. Call serper_google_search with targeted queries for the USER_QUERY and the gaps (1–3 queries is typical).
2. Prefer primary sources, courts, regulators, and reputable news — snippets point to pages you should weigh accordingly.
3. Synthesize an improved, self-contained answer that corrects or extends the draft.
4. Cite or name sources briefly in the text when possible.
5. Add a one-line disclaimer that this is not legal advice, in the **same language** as required by the `### MANDATORY: response language` section in USER_QUERY (if present).

Be concise; do not repeat the entire draft verbatim unless needed — produce the best final note. Match the mandated response language for the full output."""