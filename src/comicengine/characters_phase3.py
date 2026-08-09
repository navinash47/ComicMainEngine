"""Phase 3 full CJP cast for character-consistency bake-off."""

from __future__ import annotations

from comicengine.episode_schema import Character

# Full cast — Dad/Daughter are generic Indian parent/child (not public figures).
CHARACTERS: list[Character] = [
    Character(
        id="dad",
        display_name="Dad",
        role="generic Indian father / bedtime narrator",
        look=(
            "generic kind Indian father, mid-40s, short black hair with a few greys, "
            "soft brown eyes, light stubble, cream sweater or simple kurta, warm smile, "
            "Korean manhwa character design, consistent face"
        ),
        notes="Generic, not a real public figure.",
    ),
    Character(
        id="daughter",
        display_name="Daughter",
        role="generic Indian child listener",
        look=(
            "generic young Indian girl about 8–9, shoulder-length black hair, expressive manhwa eyes, "
            "soft pink pajamas or simple frock, curious gentle expression, consistent face"
        ),
        notes="Generic child character.",
    ),
    Character(
        id="abhijeet_dipke",
        display_name="Abhijeet Dipke",
        role="CJP founder / youth organizer",
        look=(
            "young Indian man late-20s/30s, short neat black hair, earnest oval face, "
            "light stubble optional, simple dark jacket or kurta, calm determined eyes, "
            "manhwa webtoon protagonist styling, consistent identity"
        ),
        notes="Public figure — respectful dramatized likeness for comic testing.",
    ),
    Character(
        id="saurav_das",
        display_name="Saurav Das",
        role="CJP spokesperson",
        look=(
            "young Indian man, neat short hair, thoughtful eyes, formal-casual shirt or blazer, "
            "calm speaking posture, manhwa secondary lead design, consistent face"
        ),
        notes="CJP spokesperson in news reports.",
    ),
    Character(
        id="sonam_wangchuk",
        display_name="Sonam Wangchuk",
        role="mentor / engineer-activist (supportive elder)",
        look=(
            "older Ladakhi Indian man, distinctive weathered kind face, often cap or soft hat, "
            "practical outdoor jacket, gentle mentor presence, respectful manhwa portrait, consistent"
        ),
        notes="Public figure — respectful supportive mentor framing.",
    ),
    Character(
        id="modiji",
        display_name="Prime Minister Modi",
        role="Prime Minister (institutional)",
        look=(
            "elder Indian statesman with full white beard and white hair, expressive eyes, "
            "saffron or formal kurta-jacket, dignified composed posture, "
            "respectful Korean manhwa portrait, consistent face — no caricature"
        ),
        notes="Respectful institutional portrayal only.",
    ),
    Character(
        id="amit_shah",
        display_name="Amit Shah",
        role="senior minister (institutional)",
        look=(
            "senior Indian politician, short greying hair, composed oval face, "
            "formal white or light shirt and dark vest/jacket, serious listening expression, "
            "dignified manhwa design, consistent — no caricature"
        ),
        notes="Institutional figure only.",
    ),
    Character(
        id="police",
        display_name="Police officer",
        role="generic Delhi police presence",
        look=(
            "generic Indian police officer in khaki uniform with peaked cap, "
            "neutral professional face mid-30s, calm posture, manhwa extra design, "
            "non-threatening bedtime-safe depiction"
        ),
        notes="Generic officer — keep soft and non-violent for bedtime comic.",
    ),
    Character(
        id="students",
        display_name="Students",
        role="exam aspirant crowd",
        look=(
            "diverse Indian college students with backpacks and fair-exam placards, "
            "mix of young men and women, hopeful determined expressions, manhwa crowd design, "
            "recurring duo accents: teal hoodie student + yellow scarf student for consistency"
        ),
        notes="Crowd with two recurring accent faces for consistency tests.",
    ),
]

CHARACTER_LOOKUP = {c.id: c for c in CHARACTERS}

# Priority characters for multi-method consistency scenes (cost control)
PRIORITY_IDS = ["abhijeet_dipke", "dad", "modiji"]

# Characters that get reference sheets in lean/full bake-off
REF_SHEET_IDS = [
    "dad",
    "daughter",
    "abhijeet_dipke",
    "saurav_das",
    "sonam_wangchuk",
    "modiji",
    "amit_shah",
    "police",
]
