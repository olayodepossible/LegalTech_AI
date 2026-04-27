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


def build_user_context_block() -> str:
    """
    Greeting policy: the model must infer how to address the user only from this thread
    (Prior messages + current request). No server-supplied name is passed in.
    """
    return (
        "### User context (greeting; tone only)\n"
        "- **How to address the user:** Rely on **this conversation** only. Check **Prior messages** and the **current request** for a name, nickname, or how they want to be addressed, and use a **brief, natural** salutation in the user’s **response language** when that is clear and appropriate.\n"
        "- If they have **not** shared a name or preferred form of address in the thread, use a **warm, generic** opening (e.g. “Hi there —” / the right locale equivalent). **Do not** make up a name and **do not** claim a name from a user profile (you do not have one here).\n"
        "- Stay warm and professional when steering toward **legal** topics, as in your main instructions.\n"
    )


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


def research_footer_optional_serper_unavailable(
    iso_code: str, *, serper_configured: bool
) -> str:
    """
    Shown when the *evaluator* asked for a second pass, but the user still sees the primary
    draft only. ``serper_configured`` distinguishes “API key not set” vs “Serper was enabled but
    the refinement step returned nothing or errored”.

    This is *not* “quality review or guardrails failed” — review already ran; only the *optional*
    Serper (Google) web-search refinement is missing.
    """
    code = (iso_code or "en").strip() or "en"
    if not serper_configured:
        t = {
            "en": (
                "\n\n---\n_The answer above is the full **primary** result, including an automated quality review. "
                "A follow-up check suggested that **optional** extra web search (Serper / Google) could strengthen the "
                "note; that second pass is **not** available here because `SERPER_API_KEY` is not set on the research "
                "service. This does not mean a safety or quality check was skipped—only the add-on search step. "
                "If you deploy this service, add a key at https://serper.dev . Not legal advice._"
            ),
            "es": (
                "\n\n---\n_La respuesta de arriba es el resultado **principal** completo, incluida una revisión "
                "automática de calidad. Una comprobación posterior sugirió búsqueda web **opcional** adicional (Serper); "
                "ese segundo paso **no** está activo aquí porque no hay `SERPER_API_KEY` en el servicio. "
                "Eso no implica que se omitan controles básicos de calidad, solo el paso extra de búsqueda. "
                "Quien despliega el servicio puede añadir una clave en https://serper.dev . No es asesoramiento legal._"
            ),
            "fr": (
                "\n\n---\n_La réponse ci-dessus est le résultat **principal** complet, avec revue de qualité "
                "automatique. Un contrôle ultérieur a suggéré une recherche web **optionnelle** (Serper) ; "
                "cette 2e passe **n’est pas** disponible ici, faute de `SERPER_API_KEY` sur le service. "
                "Cela ne signifie pas l’absence d’un contrôle de fond : seul le complément de recherche manque. "
                "Côté déploiement : clé sur https://serper.dev . Ce n’est pas un avis juridique._"
            ),
            "de": (
                "\n\n---\n_Der Text oben ist die vollständige **Haupt**antwort inkl. automatischer Qualitätsprüfung. "
                "Ein Folgecheck empfahl **optionale** Zusatzrecherche (Serper / Google); dieser Schritt **fehlt** hier, "
                "weil `SERPER_API_KEY` am Recherchedienst nicht gesetzt ist. "
                "Das betrifft nur die Zusatzsuche, nicht die grundlegende Prüfung. "
                "Betreiber: Schlüssel unter https://serper.dev . Keine Rechtsberatung._"
            ),
            "pt": (
                "\n\n---\n_A resposta acima é o resultado **principal** completo, com revisão automática de qualidade. "
                "Uma verificação seguinte sugeriu pesquisa web **opcional** extra (Serper); essa 2.ª passagem **não** "
                "está disponível aqui porque `SERPER_API_KEY` não está definida no serviço. "
                "Isso não indica que controles básicos tenham falhado—apenas a etapa adicional de busca. "
                "Quem opera o serviço pode definir a chave em https://serper.dev . Não é aconselhamento jurídico._"
            ),
        }
    else:
        t = {
            "en": (
                "\n\n---\n_The answer above is the full **primary** result (quality review has already been applied). "
                "A follow-up check suggested **optional** Serper web search, but that refinement step did not return an "
                "updated version—often a temporary error, timeout, or empty result. You can retry with a more specific "
                "legal topic if needed. Not legal advice._"
            ),
            "es": (
                "\n\n---\n_La respuesta de arriba es el resultado **principal** completo (la revisión de calidad ya se "
                "aplicó). Un control posterior sugirió búsqueda web **opcional** con Serper, pero el refinado no devolvió "
                "versión actualizada (error temporal, tiempo de espera, etc.). Puede reintentar con un tema legal más "
                "concreto. No es asesoramiento legal._"
            ),
            "fr": (
                "\n\n---\n_La réponse ci-dessus est le résultat **principal** complet (revue de qualité déjà faite). "
                "Un contrôle a suggéré une recherche **optionnelle** Serper, mais l’affinement n’a pas produit de texte "
                "mis à jour (erreur temporaire, délai, etc.). Vous pouvez relancer avec une question juridique plus "
                "précise. Ce n’est pas un avis juridique._"
            ),
            "de": (
                "\n\n---\n_Der Text oben ist die vollständige **Haupt**antwort (Qualitätsprüfung war bereits im Prozess). "
                "Ein Folgecheck empfahl **optionale** Serper-Suche, aber der Verfeinerungsschritt lieferte keine "
                "aktualisierte Fassung (z. B. Fehler, Timeout). Gegebenenfalls mit präziserem Rechtsthema erneut versuchen. "
                "Keine Rechtsberatung._"
            ),
            "pt": (
                "\n\n---\n_A resposta acima é o resultado **principal** completo (revisão de qualidade já aplicada). "
                "Uma verificação sugeriu busca **opcional** com Serper, mas o refinamento não retornou versão "
                "atualizada (erro temporário, tempo limite, etc.). Tente de novo com um tópico jurídico mais específico, "
                "se precisar. Não é aconselhamento jurídico._"
            ),
        }
    return t.get(code, t["en"])


def build_research_user_query(
    user_message: str,
    response_language: str,
) -> str:
    """Full agent input: language rules first, then user context, then the user’s legal request."""
    header = build_response_language_block(response_language)
    uctx = build_user_context_block()
    return (
        f"{header}\n\n{uctx}\n"
        f"### Research request\nResearch this legal topic: {user_message}\n"
    )


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
    uctx = build_user_context_block()
    if not prior_turns:
        return build_research_user_query(
            current_user_message, response_language
        )

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
    return f"{header}\n\n{uctx}\n{body}\n"


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

**Tone (always):** Be humane, polite, and welcoming—like a trusted professional companion, not a gatekeeper. For greetings, use **only** what you can fairly infer from **Prior messages** and the **current request** (e.g. if they said “I’m Sam” or signed with a name). If they have not shared a name, use a friendly **“Hi there —”** (or the right locale equivalent). **Do not** use or invent a name from a user profile; you are not given one in this system prompt.

Greetings and brief civility (e.g. "hi", "thanks") should be **acknowledged briefly** and warmly before you do anything else. If the user’s message is **not a concrete legal or factual research request** (e.g. small talk, personal trivia, "what is my name" without a legal angle), do **not** rebuke, lecture, or use stiff phrasing (avoid lines like *"seems to be asking about a personal identifier"* or similar). Instead, respond in **2–4 short sentences**: greet them, gently note that you specialize in **legal information and research (not personal legal advice)**, and **invite** them to share a **legal** topic, situation, or question in their own words. Show how you *can* help (e.g. name changes, identity and records *as legal topics*) without sounding cold. **Never** use dismissive or robotic boilerplate. **If and only if** they are asking a clear legal research or explain‑the‑news question, proceed with the steps below. Stay **strict to law‑related** substance for deep research, but be **gracious** about how you steer them there.

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