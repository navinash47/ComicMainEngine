"""Recurring cast for the Phase 0.5 CJP test episode."""

from __future__ import annotations

from comicengine.episode_schema import Character

# Cockroach Janta Party (CJP) student-movement test cast — NOT Citizens for Justice and Peace.
CHARACTERS: list[Character] = [
    Character(
        id="dad",
        display_name="Dad",
        role="narrator parent",
        look="kind Indian father, soft sweater, warm smile, Korean manhwa character design",
        notes="Frames the story gently for his daughter.",
    ),
    Character(
        id="daughter",
        display_name="Daughter",
        role="curious child listener",
        look="young Indian girl in pajamas, expressive manhwa eyes, holding a picture book",
        notes="Asks simple questions; keeps tone age-appropriate.",
    ),
    Character(
        id="abhijeet_dipke",
        display_name="Abhijeet Dipke",
        role="youth organizer / CJP founder",
        look="young Indian man, simple kurta or jacket, earnest face, manhwa webtoon protagonist styling",
        notes="Public figure in news reports about CJP student protests.",
    ),
    Character(
        id="students",
        display_name="Students",
        role="crowd of exam aspirants",
        look="diverse Indian college students with backpacks, placards about fair exams",
        notes="Represent many real students; keep sympathetic and non-violent in art.",
    ),
    Character(
        id="modiji",
        display_name="Prime Minister Modi",
        role="India's prime minister (background institutional figure)",
        look="recognizable white-beard elder statesman, formal attire, dignified Korean manhwa portrait",
        notes="Show respectfully as a national leader hearing about public issues — no mockery.",
    ),
    Character(
        id="amit_shah",
        display_name="Amit Shah",
        role="senior government minister (background)",
        look="senior Indian politician in formal attire, composed manhwa character design, distant government hall",
        notes="Institutional figure only; no invented private dialogue claiming malice.",
    ),
    Character(
        id="education_minister",
        display_name="Education Minister",
        role="union education minister (institutional)",
        look="Indian cabinet minister in formal clothes at a Delhi office",
        notes="Generic/office role in the bedtime retelling; avoid cartoonish villainy.",
    ),
]

CHARACTER_LOOKUP = {c.id: c for c in CHARACTERS}

TOPIC_CJP_ORIGIN = """
How the Cockroach Janta Party (CJP) student protest movement started in India (public news summary for a bedtime comic):

- Many students across India prepare for huge entrance exams like NEET-UG.
- News of paper leaks and exam irregularities made families feel the system was unfair.
- Abhijeet Dipke returned from the US (around June) and helped lead youth gatherings asking for fair exams and accountability.
- Crowds of students gathered in Delhi, notably at Jantar Mantar, with placards and speeches.
- The movement used the satirical name Cockroach Janta Party (CJP) and framed itself as a youth pressure group, not (at first) a traditional election party.
- Protesters asked leaders and institutions to fix exam integrity; reports also mentioned calls involving the education ministry.
- Later news said CJP described itself as a pressure group and also talked about supporting student protests elsewhere (e.g. Jharkhand recruitment exam concerns).

Rules for the comic:
- Bedtime dad→daughter voice: calm, kind, hopeful, age 7–10 appropriate.
- Do NOT invent crimes, secret plots, or cruel private dialogue by named leaders.
- Political figures appear as respectful background characters who hear about public worries.
- Emphasize fairness in exams, courage of students speaking up, and listening institutions.
- Label dramatization; keep violence / police crackdowns soft or off-panel for bedtime.
""".strip()
