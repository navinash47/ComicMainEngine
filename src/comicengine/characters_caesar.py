"""Julius Caesar / Et tu, Brute? — character bible for Phase 4 (teen didactic)."""

from __future__ import annotations

from comicengine.episode_schema import Character

STORY_ID = "episode_et_tu_brutus"
FILE_STEM = "episode_et_tu_brutus"

CHARACTERS: list[Character] = [
    Character(
        id="dad",
        display_name="Dad",
        role="narrator parent / modern guide",
        look="kind Indian father in soft sweater, Korean manhwa design, thoughtful bedtime expression",
        notes=(
            "Frames Rome for a curious teen daughter. Connects Senate, crowd, and power "
            "to fragile democracy today without lecturing."
        ),
    ),
    Character(
        id="daughter",
        display_name="Daughter",
        role="teen listener who asks hard questions",
        look="Indian teen girl in pajamas with a history book, sharp curious manhwa eyes",
        notes="Pushes Dad: Was Brutus a hero or a traitor? Does killing a strongman save freedom?",
    ),
    Character(
        id="julius_caesar",
        display_name="Julius Caesar",
        role="general → dictator, charisma and ambition",
        look=(
            "Middle-aged Roman statesman-general, laurel crown optional, crimson-edged toga, "
            "assured gaze, manhwa historical portrait — dignified not cartoonish"
        ),
        notes=(
            "THINKING/IDEOLOGY: Believes Rome needs decisive personal command after civil war; "
            "presents victory and reforms as 'for the people' while accumulating lifelong power. "
            "Sees opposition as envy and delay. Pride; clemency used as political tool. "
            "Does not think of himself as 'villain' — thinks history will thank the strong hand."
        ),
    ),
    Character(
        id="marcus_brutus",
        display_name="Marcus Junius Brutus",
        role="senator / idealist republican / assassin",
        look=(
            "Younger Roman noble, pale serious face, simple toga, restless eyes — manhwa tragic hero look"
        ),
        notes=(
            "THINKING/IDEOLOGY: Worships the idea of Res Publica (public thing / shared rule). "
            "Fears one-man rule more than chaos. Persuaded that killing Caesar is civic duty, "
            "not personal hate — yet wounded by friendship with Caesar. Blind spot: assumes "
            "Romans will cheer republic restoration after the dagger."
        ),
    ),
    Character(
        id="cassius",
        display_name="Gaius Cassius Longinus",
        role="conspirator / hard realist",
        look="Lean sharp-featured Roman senator, darker toga edges, calculating manhwa expression",
        notes=(
            "THINKING: Distrusts Caesar's megalomania; mixes republican language with personal "
            "resentment. Recruits Brutus as the 'noble face' the public will accept."
        ),
    ),
    Character(
        id="mark_antony",
        display_name="Mark Antony",
        role="Caesar's ally / master of public emotion",
        look="Athletic Roman commander, vivid red cloak, charismatic intense eyes, manhwa orator pose",
        notes=(
            "THINKING: Loyal to Caesar's person and faction. After the murder, uses grief and "
            "rhetoric (funeral speech tradition) to turn the crowd against the conspirators — "
            "proves narrative + emotion can outrun 'constitutional' arguments."
        ),
    ),
    Character(
        id="calpurnia",
        display_name="Calpurnia",
        role="Caesar's wife / private conscience",
        look="Roman noblewoman in draped stola, worried eyes, elegant manhwa historical design",
        notes="Voices fear and omens; humanizes the cost of power games in the household.",
    ),
    Character(
        id="roman_people",
        display_name="Roman People (Plebs)",
        role="crowd — cheers today, chants tomorrow",
        look="Diverse Roman crowd in Forum: workers, veterans, women, children with banners",
        notes=(
            "THINKING: Want bread, games, glory, stability. Love a winner who pays them attention. "
            "Can be steered by spectacle and speeches. Analog for modern publics under propaganda."
        ),
    ),
    Character(
        id="senate",
        display_name="Roman Senators",
        role="elite institutional chorus",
        look="Cluster of togaed senators in Curia / Theatre of Pompey, marble columns, tense faces",
        notes="Some defend aristocratic privilege; some fear tyranny; many protect their own status.",
    ),
]

CHARACTER_LOOKUP = {c.id: c for c in CHARACTERS}

TOPIC_ET_TU_BRUTUS = """
STORY: "Et tu, Brute?" — Julius Caesar, the late Roman Republic, and how a republic dies.

HISTORICAL ARC (educational teen comic — dramatized, not exhaustive):
1. Republic under stress: civil wars, strong generals (Marius, Sulla, Pompey, Caesar).
2. Caesar's victories (Gaul), crossing Rubicon (49 BCE) — personal army vs Senate order.
3. Civil war → dictatorship / perpetual honors; many Romans adore him; others see monarchy returning.
4. Ides of March 44 BCE: Brutus, Cassius, and conspirators stab Caesar in the Theatre of Pompey.
5. Famous beat: Caesar's shock at Brutus ("You too, Brutus?" — legendary phrasing from later tradition / Shakespeare; label dramatized).
6. Aftermath: Brutus assumes Romans wanted the Republic back — instead Mark Antony's funeral rhetoric and later wars bury the conspirators' hope; Octavian (Augustus) will finish the transition to Empire.

CHARACTER LENSES (MUST write dialogue/caption from shifting POV — not flat textbook):
- Caesar panels: pride, reformer self-image, contempt for 'obstruction'.
- Brutus panels: duty vs friendship; Republican purity.
- Cassius: cold urgency to act.
- Antony: grief weaponized into politics.
- Roman People: hunger for order + susceptibility to oratory.
- Dad/Daughter: modern readers arguing what 'freedom' means when institutions rot.

MODERN ANALOGIES (explicit, teen-direct, not partisan slogans):
- Fragile democracy / republic: elections and senates can hollow out while a popular strongman accumulates permanence.
- Personality cult: banners, triumphs, celebrity replace shared rules.
- Political violence is not a reset button: murdering Caesar did not restore liberty; it opened more civil war.
- Crowds and virality: Antony's speech ≈ how emotional narrative can flip public opinion overnight.
- Elites claiming to save the republic while also protecting their caste.
- 'For the people' language used by both tyrants-in-waiting and oligarchs.

RULES:
- Teen / young-adult didactic (ages ~13–17): denser ideas, honest about power and bloodless daggers shown non-graphically.
- No gore close-ups; stabbing can be silhouette / off-panel / sharp shock beat.
- Label legendary/Shakespearean lines as dramatized in fact_checks.
- End with Dad and Daughter: freedom needs institutions + citizens who stay awake — not only heroes and knives.
- Korean manhwa webtoon art_prompt, short 1–2 sentences.
""".strip()

SYSTEM_CAESAR = """You write TEEN/young-adult educational comics for a Dad reading history with his Daughter.
Tone: didactic, sharp, emotionally honest — not cute preschool.
Let Julius Caesar, Brutus, Cassius, Antony, Calpurnia, Senators, and the Roman People speak in FIRST-PERSON flavor inside dialogue/captions when their panel.
Dad translates analogies to today's fragile democracies, crowds, and strongmen — without naming living politicians as villains.
Never glorify assassination as a cure. Never invent private crimes for modern leaders.
Call submit_episode exactly once."""
