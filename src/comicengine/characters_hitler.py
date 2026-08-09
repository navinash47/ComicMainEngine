"""Hitler-era biography / Holocaust warning — character bible for Phase 4 (teen didactic).

Educational only. Must never romanticize Nazism. Character 'voice' shows ideology
so readers can recognize propaganda patterns; captions and Dad must condemn hatred.
"""

from __future__ import annotations

from comicengine.episode_schema import Character

STORY_ID = "episode_hitler_warning"
FILE_STEM = "episode_hitler_warning"

CHARACTERS: list[Character] = [
    Character(
        id="dad",
        display_name="Dad",
        role="narrator parent / moral guide",
        look="kind Indian father in soft sweater, solemn manhwa expression, holding history book",
        notes=(
            "Explains democracy's collapse and genocide warning clearly for teens. "
            "Always counters Nazi worldview; never leaves hate unchallenged."
        ),
    ),
    Character(
        id="daughter",
        display_name="Daughter",
        role="teen listener / conscience questions",
        look="Indian teen girl in pajamas, worried thoughtful manhwa eyes, notebook open",
        notes=(
            "Asks: How do ordinary people become bystanders? Why blame minorities? "
            "Could this pattern happen again?"
        ),
    ),
    Character(
        id="adolf_hitler",
        display_name="Adolf Hitler",
        role="Nazi dictator / propagandist — antagonist of history",
        look=(
            "Historical likeness restrained: dark suit or brown-era coat, intense eyes, "
            "manhwa documentary style — NEVER heroic lighting, no awe composition"
        ),
        notes=(
            "THINKING/IDEOLOGY (to EXPOSE, not endorse): Racial hierarchy myth; antisemitic "
            "conspiracy fantasies; Führerprinzip (blind obedience); Lebensraum aggression; "
            "scapegoats Jews, Roma, disabled people, political opponents, LGBTQ people, and more "
            "for Germany's crises. Believes democracy is weak and must be destroyed from inside "
            "then crushed. Speaks of 'the people' while stripping rights. "
            "SCRIPT RULE: when he speaks, panels must immediately or next show victims/Dad "
            "naming the lie."
        ),
    ),
    Character(
        id="joseph_goebbels",
        display_name="Joseph Goebbels",
        role="propaganda minister",
        look="Thin bespectacled Nazi official at microphones/posters, cold manhwa documentary styling",
        notes=(
            "THINKING: Repeating a lie makes it feel true; control film, radio, newspapers; "
            "turn neighbors into enemies. Modern analogy: coordinated hate memes and "
            "state-aligned media ecosystems."
        ),
    ),
    Character(
        id="adolf_eichmann",
        display_name="Adolf Eichmann",
        role="bureaucratic organizer of deportations — banality of evil",
        look=(
            "Ordinary-looking mid-level official with briefcase/lists/train schedules, "
            "gray office lighting, unsettlingly normal manhwa face"
        ),
        notes=(
            "THINKING: 'Just following orders / logistics' — turns mass murder into paperwork. "
            "Hannah Arendt later described this pattern as banality of evil. Analogy: "
            "atrocity enabled by clerks, code, and careerism."
        ),
    ),
    Character(
        id="heinrich_himmler",
        display_name="Heinrich Himmler",
        role="SS leader / terror apparatus",
        look="SS officer silhouette in cold office, not glamorous, manhwa historical restraint",
        notes="THINKING: Police state + racial purity cult; terror as policy instrument.",
    ),
    Character(
        id="anne_frank_symbol",
        display_name="Jewish Teen (composite / Anne-like witness)",
        role="persecuted youth voice",
        look=(
            "Composite young Jewish girl with diary notebook in cramped attic light — "
            "inspired by survivor teens / Anne Frank archetype, NOT claimed as photo-real Anne"
        ),
        notes=(
            "Represents millions targeted: hopes, fear, stolen childhood. "
            "Never reduce to statistic only."
        ),
    ),
    Character(
        id="german_neighbor",
        display_name="Ordinary German Neighbor",
        role="bystander / sometimes collaborator public",
        look="1930s Berlin apartment neighbor, plain clothes, looking away from a broken shop window",
        notes=(
            "THINKING: Fear, peer pressure, career, belief in lies, 'not my business'. "
            "Shows how democracy dies when neighbors stop defending neighbors."
        ),
    ),
    Character(
        id="weimar_citizen",
        display_name="Weimar Voter / Worker",
        role="crisis voter who wants order",
        look="1930s German worker with unemployment notice, listening to street rally",
        notes=(
            "THINKING: Inflation, humiliation after WWI, unemployment → craving strong hand. "
            "Analogy: economic pain + humiliation myths make demagogues look like medicine."
        ),
    ),
    Character(
        id="resistance_voice",
        display_name="Resister / White Rose echo",
        role="courage against the regime",
        look="Young students distributing forbidden leaflets at night, tense manhwa shadows",
        notes="THINKING: Truth is worth risk; silence is a choice. Courage is rare and precious.",
    ),
]

CHARACTER_LOOKUP = {c.id: c for c in CHARACTERS}

TOPIC_HITLER_WARNING = """
STORY: Hitler's rise, Nazi dictatorship, propaganda, persecution — a teen warning comic.

IMPORTANT: This is ANTI-fascist education. Never glamorize Nazis. Show ideology to RECOGNIZE
and REFUSE it. Dad must state clearly: racial hatred and genocide are evil and false.

HISTORICAL ARC (selected important beats — dramatized educational summary):
1. Post-WWI Germany: Treaty of Versailles humiliation myths, hyperinflation trauma, Depression.
2. Hitler / Nazis sell scapegoats (especially Jews) and 'national rebirth' / authoritarian order.
3. 1933: appointed Chancellor → Enabling Act → democracy legally dismantled; opposition jailed.
4. Propaganda state (Goebbels): radio, film, schools, rallies; book burnings; Gleichschaltung.
5. Nuremberg Laws, Kristallnacht — stripping rights, public violence against Jews.
6. War + Holocaust: industrial genocide; Eichmann as logistics clerk of deportations; camps.
7. Brief courage (resistance leaflets / 'White Rose' echo) and the cost of bystander silence.
8. Aftermath lesson: never again requires institutions, law, media literacy, defending minorities.

CHARACTER LENSES (rotate POV; expose thinking THEN challenge it):
- Hitler: demagogue self-belief and hate mythology (always undercut by next caption/Dad).
- Goebbels: propaganda craft — big lie, enemy image.
- Eichmann: paperwork atrocity / 'only following orders'.
- Weimar voter / neighbor: how ordinary people enable.
- Jewish teen voice: human target of the machine.
- Resistance: moral clarity under terror.
- Dad/Daughter: map to CURRENT WORLD AFFAIRS patterns (not conspiracy):
  * Fragile democracy — legal paths can kill republics.
  * Propaganda and hate against minorities / immigrants / 'internal enemies'.
  * Strongman promises after economic fear.
  * Bureaucracy making cruelty efficient.
  * Social media / crowd dynamics as modern Forum.
  Do NOT invent crimes about living politicians; speak in patterns and civic warnings.

RULES:
- Teen didactic (~13–17): honest vocabulary — dictatorship, genocide, antisemitism, propaganda.
- NO gore, NO corpses, NO camp torture visuals. Use empty shoes, broken glass, lists, trains silhouette, darkened radio, yellow-star symbolism carefully and respectfully.
- Never jokes about the Holocaust. Never 'both-sides' Nazism.
- fact_sheet must include that six million Jews were murdered (among millions of other victims).
- End with Daughter refusing the bystander role and Dad linking to protecting minorities + free press + votes.
- Korean manhwa webtoon art_prompt, 1–2 sentences, documentary-mood lighting — not epic-hero Nazi aesthetics.
""".strip()

SYSTEM_HITLER = """You write TEEN/young-adult educational comics for a Dad teaching hard history with his Daughter.
This episode is about Hitler, Nazi propaganda, and the Holocaust warning.
Tone: serious, clear, didactic — never cute, never glamorous toward Nazis.
Show character thinking (Hitler, Goebbels, Eichmann, neighbors) so hate/propaganda patterns are recognizable,
THEN immediately challenge them via victims, resistors, or Dad.
Never endorse Nazi ideology. Never invent private modern political crimes.
No graphic violence. Call submit_episode exactly once."""
