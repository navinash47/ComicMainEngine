"""How I Met Your Mother — Episode 1 Infatuation (dad-to-daughter love story script)."""

from __future__ import annotations

from comicengine.episode_schema import Character, Episode, Panel

MANHWA = (
    "Korean manhwa webtoon, expressive eyes, soft gloss highlights, romantic comedy drama, "
    "clear emotional acting, Bay Area / California setting (English signage only, no Korean text), "
    "warm hotel/city palette, no text letters or logos in art unless specified"
)


def _chars() -> list[Character]:
    return [
        Character(
            id="dad",
            display_name="Dad (Rohan)",
            role="narrator father, present day",
            look=(
                "Indian dad late 30s, soft sweater, curly hair greying at temples, "
                "warm flustered smile, Korean manhwa"
            ),
            notes="Sits beside Maya and tells her how he met Mom.",
        ),
        Character(
            id="daughter",
            display_name="Maya",
            role="teen daughter who teases then softens",
            look=(
                "Indian teen girl ~14, oversized hoodie, pajama pants, sharp curious manhwa eyes, "
                "mischievous grin"
            ),
            notes="Roasts Dad hard, then leans in when story gets tender.",
        ),
        Character(
            id="rohan",
            display_name="Young Rohan",
            role="Dad in the past — shy IT employee on an HQ trip",
            look=(
                "27yo Indian man, curly black hair, company badge hoodie, introvert posture, "
                "manhwa face that shows every feeling"
            ),
            notes="Straight-forward; cannot read flirting; brave with honesty; butterflies literal.",
        ),
        Character(
            id="elena",
            display_name="Elena Brooks",
            role="Mom in the past — tall brunette colleague",
            look=(
                "tall Caucasian woman mid-20s, soft brunette baby-cut bob, pretty kind eyes, "
                "sometimes Meridian Soft tee, manhwa soft glow"
            ),
            notes="Quiet then warm; scared of heartbreak; more interested than she admits early.",
        ),
        Character(
            id="kabir",
            display_name="Kabir Desai",
            role="F1 Indian friend — flat-hunt panic",
            look="Indian guy mid-20s, neat hair, glasses, joking smile, manhwa",
            notes="Rent math comic relief.",
        ),
        Character(
            id="arjun",
            display_name="Arjun Nair",
            role="F2 Indian friend — reads the room",
            look="Indian guy mid-20s, casual tee, easygoing manhwa smile",
            notes="Anti-third-wheel wingman.",
        ),
        Character(
            id="wei",
            display_name="Wei Zhang",
            role="F3 Chinese friend with the car",
            look="Chinese guy mid-20s, sensible jacket, car keys energy, manhwa",
            notes="Drives early week; absence triggers tram meet-cute.",
        ),
        Character(
            id="marcus",
            display_name="Marcus Hale",
            role="kind team manager late 30s",
            look="white man late 30s, office polo, friendly calm manhwa face",
            notes="Invites Rohan to lunch.",
        ),
    ]


def build_episode() -> Episode:
    raw: list[dict] = []

    def add(
        scene: str,
        chars: list[str],
        dialogue: str = "",
        caption: str = "",
        emotion: str = "warm",
        feeling: str = "",
    ) -> None:
        art = (
            f"{MANHWA}. {scene}"
            + (f" Inner feeling visual: {feeling}." if feeling else "")
        )
        raw.append(
            {
                "scene_description": scene,
                "characters": chars,
                "dialogue": dialogue,
                "caption": caption,
                "emotion": emotion,
                "art_prompt": art,
            }
        )

    # ——— Present frame ———
    add(
        "Living-room sofa at night, soft lamp. Dad sits beside Maya — no book — knees almost touching. "
        "Maya grins sideways; Dad already looks doomed.",
        ["dad", "daughter"],
        "Maya: Okay. Spill. How did you actually meet Mom?\n"
        "Dad: ...You sure you want the full version? It's embarrassing.\n"
        "Maya: Perfect. I live for your embarrassment.",
        "PRESENT · Living room · after dinner",
        "playful, warm",
    )
    add(
        "Close two-shot: Dad rubs the back of his neck; Maya leans in sparkling.",
        ["dad", "daughter"],
        "Dad: Fine. Spring, years ago. Company sent me to the Bay Area office for two weeks.\n"
        "Maya: 'Two weeks' is always how these movies start. Continue, tragic hero.",
        "PRESENT · Living room",
        "teasing",
    )
    add(
        "Elegant title card: bay dusk skyline, tiny tram lights, soft feather motif.",
        [],
        "",
        "HOW I MET YOUR MOTHER · Episode 1 — Infatuation",
        "cinematic",
        "title card atmosphere, romantic dusk city",
    )

    # ——— Prologue ———
    add(
        "Young Rohan exits arrivals with suitcase; California light hits curly hair. "
        "Tiny nervous sparkles around his eyes — excited and out of place.",
        ["rohan"],
        "Dad (V.O.): First Saturday I landed — jetlagged, pretending I knew what I was doing.",
        "SATURDAY · March 8 · San Jose Airport · ~9:00 AM",
        "hopeful, overstimulated",
        "stomach flutter of a new city",
    )
    add(
        "Hotel corridor: Rohan, Kabir, Arjun compare apartment listing screens; comic shock at rents.",
        ["rohan", "kabir", "arjun"],
        "Kabir: Bro, this rent can't be real.\n"
        "Arjun: It is. Welcome to California math.\n"
        "Rohan: We need a flat. And also... sleep.",
        "SATURDAY · March 8 · Grand Oriole Hotel corridor · afternoon",
        "comic overload",
    )
    add(
        "Sunday: Rohan alone on hotel bed staring at ceiling; boredom lines; phone idle.",
        ["rohan"],
        "Dad (V.O.): Sunday I was so bored I went downstairs just to walk in circles "
        "like a professional circle-walker.",
        "SUNDAY · March 9 · Hotel room · late morning",
        "restless loneliness",
        "empty-room echo in his chest",
    )
    add(
        "Lobby panorama — time slows. Across the space: Elena in Meridian Soft tee, tall, "
        "baby-cut brunette, pretty — looking at her phone. Rohan freezes mid-step.",
        ["rohan", "elena"],
        "Dad (V.O.): That was the first time I saw her face.\n"
        "Maya (inset): Mom in a company tee? Immediate legend status.",
        "SUNDAY · March 9 · Grand Oriole Lobby · ~11:20 AM",
        "love-at-first-sight jolt",
        "heart skips; soft spotlight only on her",
    )
    add(
        "Extreme close-up of Rohan's eyes reflecting Elena; tiny butterflies hatch around his temples.",
        ["rohan"],
        "Dad (V.O.): Curly-hair IT guy brain: short-circuit. Pretty. Tall. Same company shirt. "
        "Dangerous combination.",
        "SUNDAY · March 9 · Lobby · internal beat",
        "infatuation ignition",
        "first butterflies swarming",
    )
    add(
        "Rohan introduces himself awkwardly; Elena gives a cool reserved glance — could be shy or cold.",
        ["rohan", "elena"],
        "Rohan: Hi— uh— same company? I'm Rohan. Meridian Soft...\n"
        "Elena: Elena.\n"
        "Dad (V.O.): That look. Condescending? Or did I invent it because pretty girls scramble me?",
        "SUNDAY · March 9 · Lobby",
        "awkward crush",
        "dislike and liking tangled in one chest knot",
    )
    add(
        "Present: Maya covers mouth laughing; Dad covers face with both hands.",
        ["dad", "daughter"],
        "Maya: You disliked her AND liked her? Multitasking!\n"
        "Dad: Don't put that on a poster.\n"
        "Maya: Mental billboard. High resolution.",
        "PRESENT · Living room",
        "daughter roast",
    )
    add(
        "Monday curb: Wei's car; Rohan Kabir Arjun pile in; Wei confident at wheel.",
        ["wei", "rohan", "kabir", "arjun"],
        "Wei: Hop in. Office express.\nRohan: Wei, you are the hero of mornings.",
        "MONDAY · March 10 · Hotel curb · ~8:15 AM",
        "grateful energy",
    )

    # ——— Tuesday destiny tram ———
    add(
        "Tuesday transit stop alone: no Wei. Soft wind. Destiny ripple lines around Rohan's shoes.",
        ["rohan"],
        "Dad (V.O.): Tuesday — Wei couldn't drive us. A tiny change. Destiny wears casual clothes.",
        "TUESDAY · March 11 · City light-rail stop · ~8:05 AM",
        "fateful quiet",
        "uneasy empty morning that somehow matters",
    )
    add(
        "Platform: Elena in white-and-blue with a pretty hat — morning light turns cinematic. "
        "Rohan's pupils widen; sparkles.",
        ["rohan", "elena"],
        "Dad (V.O.): And there she was again. White and blue. That hat. I forgot how to be a person.",
        "TUESDAY · March 11 · Light-rail platform",
        "infatuation spike",
        "butterflies return full swarm",
    )
    add(
        "Tram interior: Rohan manages a tiny intro then becomes a statue; silence drawn as comic panels between them.",
        ["rohan", "elena"],
        "Rohan: Hi... again. Rohan.\n"
        "Elena: Morning.\n"
        "Dad (V.O.): Then — silence. Olympic silence. My mouth filed a resignation letter.",
        "TUESDAY · March 11 · Light rail · morning commute",
        "nervous comedy",
        "heartbeat loud in his ears; words stuck behind teeth",
    )
    add(
        "Present: Maya freezes face like statue Rohan; Dad groans.",
        ["dad", "daughter"],
        "Maya: Strategy: exist silently near crush.\n"
        "Dad: It was... presence.\n"
        "Maya: It was cowardice with good hair.",
        "PRESENT",
        "playful roast",
    )
    add(
        "Office day-one montage: Marcus handshake, badge scan, laptop — Rohan sweaty but trying.",
        ["rohan", "marcus"],
        "Marcus: Welcome aboard, Rohan. Lunch later?\n"
        "Rohan: Thank you, sir— I mean Marcus— I mean— okay.",
        "TUESDAY · March 11 · Meridian Soft Bay Campus · daytime",
        "first-day nerves",
        "half his brain still on the tram hat",
    )

    # ——— Wednesday ———
    add(
        "Wednesday lobby: both wait for rideshare; quiet stretches like elastic; Rohan's hands fidget.",
        ["rohan", "elena"],
        "Dad (V.O.): Wednesday. Lobby again. Same quiet. Saying 'hi' felt like climbing a mountain in flip-flops.",
        "WEDNESDAY · March 12 · Hotel lobby · morning",
        "tense quiet",
        "want to speak / terrified to speak",
    )
    add(
        "Cafeteria: Marcus waves; Rohan arrives late with tray; table full — soft panic.",
        ["rohan", "marcus"],
        "Marcus: Rohan! We saved— wait, we filled up.\n"
        "Dad (V.O.): Late again. Destiny... or bad cafeteria timing. Same thing that week.",
        "WEDNESDAY · March 12 · Office cafeteria · lunch",
        "mild panic",
    )
    add(
        "Rohan sits across Elena alone at small table — soft spotlight between trays.",
        ["rohan", "elena"],
        "Rohan: Mind if I sit? We keep... existing near each other in lobbies.\nElena: Sure.",
        "WEDNESDAY · March 12 · Cafeteria · lunch",
        "first real talk",
        "relief and terror equalized",
    )
    add(
        "Talk beat: Rohan animated with hands about California smiling culture; Elena listening, faint smile blooming.",
        ["rohan", "elena"],
        "Rohan: People here smile at strangers like it's a sport.\n"
        "Elena: You're new. Give it a week.\n"
        "Rohan: A week of smiling — or panicking?",
        "WEDNESDAY · March 12 · Cafeteria",
        "warming",
        "crush softens into conversation warmth",
    )
    add(
        "Feeling close-up: Rohan watching her listen more than talk — manhwa soft focus on her lashes.",
        ["rohan", "elena"],
        "Dad (V.O.): She listened more than she spoke. I liked that. Quiet isn't empty — sometimes it's careful.",
        "WEDNESDAY · March 12 · Cafeteria · mid-lunch",
        "tender observation",
        "fondness collecting like rain in a cup",
    )
    add(
        "Evening curb: Elena enters cab alone; Wei's text about flat hunt. Rohan torn silhouette.",
        ["elena", "rohan"],
        "Dad (V.O.): Wei left early for apartments. She rode alone. I told myself it was fine.\n"
        "Maya (inset): Your face is lying to Future You.",
        "WEDNESDAY · March 12 · Office curb · evening",
        "soft regret",
        "wanting to go with her / not daring",
    )

    # ——— Thursday ———
    add(
        "Thursday dinner: Rohan alone at hotel restaurant — introvert fortress with phone.",
        ["rohan"],
        "Dad (V.O.): Thursday I sat alone. Not because I disliked people — because girls, "
        "even platonically, scrambled my confidence.",
        "THURSDAY · March 13 · Hotel dining lobby · ~7:10 PM",
        "lonely introvert",
        "self-conscious walls up",
    )
    add(
        "Elena sits opposite unexpectedly — electric crackle doodles; Rohan jolts; butterflies explode.",
        ["rohan", "elena"],
        "Elena: Hi.\nRohan: —!\nDad (V.O.): She sat across from me. My heart rebooted incorrectly.",
        "THURSDAY · March 13 · Hotel dining · evening",
        "electric crush",
        "jolt of electricity through whole body",
    )
    add(
        "Present: Maya making zap sound effects with fingers; Dad smiling helplessly.",
        ["dad", "daughter"],
        "Maya: BZZT. Crush.exe has crashed.\nDad: It crashed into a better version of me.",
        "PRESENT",
        "tease + soft pride",
    )
    add(
        "Long dinner montage feeling: plates emptier, clocks melt ~2 hours, laughter lines, eyes soft.",
        ["rohan", "elena"],
        "Dad (V.O.): Two hours. Work. Random things. Easy and terrifying — like learning to swim mid-ocean.",
        "THURSDAY · March 13 · Hotel dining · ~7:10–9:10 PM",
        "sparkling connection",
        "time disappearing because she's interesting",
    )
    add(
        "Night street walk under lamps; Elena gestures keep walking; Rohan would walk forever.",
        ["rohan", "elena"],
        "Elena: One more block?\nRohan: Okay.\nElena: ...Okay one more?\n"
        "Dad (V.O.): She kept insisting we walk. I would've walked to Oregon.",
        "THURSDAY · March 13 · Downtown streets · night",
        "romantic stroll",
        "butterflies match streetlamp flicker",
    )
    add(
        "Walk feeling panel: sideways glance — is this friendship? His fingers twitch near hers and retreat.",
        ["rohan", "elena"],
        "Rohan (thought): Don't read too much. Don't read too little. Why is there no manual?\n"
        "Dad (V.O.): I wanted to know how girls think — and somehow the answer was walking beside one.",
        "THURSDAY · March 13 · Night walk",
        "confused longing",
        "hand almost reaches / pulls back",
    )
    add(
        "Hotel hallway: Rohan bursts into friends' room gushing; Kabir Arjun Wei roast him.",
        ["rohan", "kabir", "arjun", "wei"],
        "Rohan: Guys. There's a girl.\nKabir: There are many girls.\n"
        "Rohan: No — a girl girl.\nArjun: Oh no. He's gone.\nWei: Destiny hours.",
        "THURSDAY · March 13 · Friends' hotel room · ~11:20 PM",
        "comic excitement",
        "happiness too big for his chest",
    )
    add(
        "Rohan asleep peaceful; phone lights with Elena's follow request — unseen. Dramatic irony sparkles.",
        ["rohan"],
        "Dad (V.O.): Slept like a baby at midnight. Phone got a follow request... "
        "and I — genius — had deleted the app a year ago.",
        "THURSDAY night → FRIDAY · 12:00 AM · Hotel room",
        "dramatic irony",
    )
    add(
        "Present: Maya facepalms so hard the couch shakes.",
        ["dad", "daughter"],
        "Maya: You DELETED the app?\n"
        "Dad: I was living pure. Offline. Philosophical.\n"
        "Maya: You were living romantic stupid. Cute stupid, but stupid.",
        "PRESENT",
        "max roast",
    )

    # ——— Friday ditch ———
    add(
        "Friday afternoon: Rohan glowing while getting ready; phone shows Elena invite to club Friday eve.",
        ["rohan"],
        "Elena (text): Club tonight? Friends going — come!\n"
        "Rohan (text): Yes!! Excited to meet everyone!\n"
        "Dad (V.O.): I got ready like it was a wedding. Heart doing cartwheels.",
        "FRIDAY · March 14 · Afternoon → evening · Hotel room",
        "excited peak",
        "anticipation butterflies manic",
    )
    add(
        "Phone close-up: later text — too many people, maybe skip. Rohan's face cracks; little dark rain.",
        ["rohan"],
        "Elena (text): Actually... lots of people. Maybe skip tonight?\n"
        "Dad (V.O.): Cancelled. Upset. Almost angry. Thumb hovered over delete contact.",
        "FRIDAY · March 14 · Evening · Hotel room",
        "hurt",
        "butterflies collapse into heavy chest stone",
    )
    add(
        "Present careful: Dad softer; Maya quieter but still herself.",
        ["dad", "daughter"],
        "Dad: Then I criticized myself. Acquaintance — not entitled to her Friday.\n"
        "Maya: Grown-up Dad speaking. Rare form.\n"
        "Dad: I performed grown-up by lying I was 'busy' the next day.",
        "PRESENT",
        "sincere",
    )
    add(
        "Saturday day: Rohan with Arjun walking 'fine'; thought bubbles of Elena cancelled club.",
        ["rohan", "arjun"],
        "Arjun: You okay?\nRohan: Busy. Very busy. Busy with busy-ness.\nArjun: ...You're upset.",
        "SATURDAY · March 15 · Day · city sidewalk",
        "pretend-okay comedy",
        "pride covering bruise",
    )

    # ——— Saturday apology + room movie ———
    add(
        "Saturday hotel dining lobby: Elena approaches Rohan + Arjun; apologetic soft eyes.",
        ["elena", "rohan", "arjun"],
        "Elena: Rohan — I'm sorry about last night. Can I make it up?\n"
        "Rohan: Uh— this is Arjun.\nArjun: Hi. Friendly obstacle. Nice to meet you.",
        "SATURDAY · March 15 · Hotel dining lobby · evening",
        "apology warmth",
        "bruise starts healing against his will",
    )
    add(
        "Movie invite; Rohan asks Arjun; Arjun declines with subtle wink away from Elena.",
        ["elena", "rohan", "arjun"],
        "Elena: Theater nearby — want to watch something?\n"
        "Rohan: Arjun, you in?\n"
        "Arjun: Busy. Deeply busy. Ancient busy. You two go... as friends.",
        "SATURDAY · March 15 · Lobby",
        "wingman comedy",
    )
    add(
        "Rohan scrolling to invite Kabir/Wei; Elena gently places hand on his phone — softness zoom.",
        ["rohan", "elena"],
        "Rohan: Wait I can ping Kabir—\nElena: No need.\n"
        "Dad (V.O.): Hand on my phone. Brain typed FRIENDS. Destiny typed DATE??",
        "SATURDAY · March 15 · Lobby",
        "hint blindness",
        "skin-tingle where her hand nearly brushed his",
    )
    add(
        "Present roast panel — Maya pointing at imaginary whiteboard labeled 'HINTS YOU MISSED'.",
        ["dad", "daughter"],
        "Maya: Mom said 'no need' and you still held a friendship press conference?\n"
        "Dad: Allergic to implications.\nMaya: Get an epipen for romance.",
        "PRESENT",
        "tease",
    )
    add(
        "Hallway: Rohan invents tiredness; Elena reads him; invites movie in her room — just us.",
        ["rohan", "elena"],
        "Rohan: I'm tired. Sleep. Definitely sleep.\n"
        "Elena: What are you actually going to do?\n"
        "Rohan: ...Watch a movie.\n"
        "Elena: Then watch in my room. Just us.",
        "SATURDAY · March 15 · Hotel hallway · ~9:40 PM",
        "shocked yes",
        "fear-and-hope lightning",
    )
    add(
        "Rohan in his room grabbing iPad Pro — freeze-frame terror, sweat drops, butterfly storm.",
        ["rohan"],
        "Dad (V.O.): Best part — I was terrified.\n"
        "Maya (present): Of Mom?\n"
        "Dad: Of accidentally becoming a person who sits on a bed near a crush.",
        "SATURDAY · March 15 · Rohan's room",
        "scared butterflies",
        "maximum butterfly swarm; knees soft",
    )
    add(
        "Elena's room: Rohan plants iPad on desk far away like a professional; Elena points to bed.",
        ["rohan", "elena"],
        "Rohan: Desk is good. Cinema of professionalism.\nElena: Bed's better. Come on.",
        "SATURDAY · March 15 · Elena's hotel room · night",
        "awkward comedy",
        "panic disguised as logistics",
    )
    add(
        "On bed edge plugging charger; Elena scoots closer for the screen — distance collapses; butterflies fill room air.",
        ["rohan", "elena"],
        "Dad (V.O.): She came closer so she could see. I froze. Every butterfly in California moved into my stomach.",
        "SATURDAY night · Elena's room",
        "intense crush",
        "butterflies swarming inside / warm shoulder distance shrinking",
    )
    add(
        "Watching soft-horror Night Watchman: jump scare; Elena jolts closer, almost head on shoulder; "
        "water bottle; comic stomach growl bubbles.",
        ["rohan", "elena"],
        "SFX: JUMP!\nElena: —!\n"
        "Dad (V.O.): Every scare: closer. Almost her head on my shoulder. "
        "She drank water like dinner forgot her. Her stomach growled. Weirdly adorable.",
        "SATURDAY night · ~10:30 PM–1:00 AM · Elena's room · movie: Night Watchman",
        "cozy scare romance",
        "soft almost-touch heaven; crush rebooting hard",
    )
    add(
        "Rohan thought storm overlay: hints? friendship? romance? manhwa question-mark rain.",
        ["rohan"],
        "Rohan (thought): Is she giving hints?\nAm I failing Hint Class?\nIs this friendship with jump scares?\n"
        "Dad (V.O.): Confused. Crushed. Still sitting like a gentleman statue.",
        "SATURDAY night · Elena's room · internal",
        "internal chaos",
        "wanting meaning / fearing wrong meaning",
    )
    add(
        "Present: Maya whispering like gossip show host.",
        ["dad", "daughter"],
        "Maya: Head. Nearly. On. Shoulder.\nDad: I know.\nMaya: And you did... statues?\nDad: Elite statues.",
        "PRESENT",
        "tease",
    )

    # ——— Sunday best day ———
    add(
        "2AM Rohan returns; can't sleep; 4AM text from Elena can't sleep either — soft phone glow.",
        ["rohan"],
        "Elena (text, 4:01 AM): Still awake. That movie ruined me.\n"
        "Dad (V.O.): Woke at seven, saw it, and thought — wait. Maybe...?",
        "SUNDAY · March 16 · 2:00 AM → 4:01 AM → 7:00 AM",
        "hope blooming",
        "maybe she feels it too — fragile hope",
    )
    add(
        "Flat hunting till 1PM with friends; Elena excited movie texts overlay between rental disasters.",
        ["rohan", "kabir", "arjun", "wei"],
        "Kabir: This closet is pretending to be a bedroom.\n"
        "Elena (text): Still on for movie later??\nRohan (text): YES.",
        "SUNDAY · March 16 · Morning–1:00 PM · apartment search",
        "busy joy",
        "anticipation under chores",
    )
    add(
        "Walking to Silverleaf Mall theater in sun — side by side; soft cinematic widen.",
        ["rohan", "elena"],
        "Dad (V.O.): Walked to the theater. The whole afternoon felt like a scene someone wrote for me.",
        "SUNDAY · March 16 · ~3:00 PM · Silverleaf Mall approach",
        "movie-date glow",
        "every action feels romantic through his filter",
    )
    add(
        "Starbucks: tissue falls; both dive; forehead bump; shared smile — spark line through Rohan's stomach.",
        ["rohan", "elena"],
        "SFX: bonk\nElena: Ow—\nRohan: Sorry—!\nBoth: ...\n"
        "Dad (V.O.): That smile went straight through my stomach.",
        "SUNDAY · March 16 · Starbucks · pre-movie",
        "sweet collide",
        "forehead-bonk electricity; butterflies explode again",
    )
    add(
        "Present: Maya softens, hand over heart dramatically.",
        ["dad", "daughter"],
        "Maya: Okay that was illegally cute.\nDad: Right? I still replay the head-bonk in 4K.",
        "PRESENT",
        "warm",
    )
    add(
        "Dark theater: sitting close; Rohan's hand hovers near hers — almost — retreats.",
        ["rohan", "elena"],
        "Dad (V.O.): In the dark: Do I put my hand on hers?\n"
        "Maya (present): Dad. The answer was yes.\nDad: I know that NOW.",
        "SUNDAY · March 16 · Cinema · afternoon showing",
        "almost-touch tension",
        "hand hovering / courage missing by inches",
    )
    add(
        "Outside theater: Rohan asks for social; Elena already sent; gentle roast energy.",
        ["rohan", "elena"],
        "Rohan: Can I get your... social?\n"
        "Elena: I already sent it. Days ago.\n"
        "Rohan: I deleted the app. Philosophically.\n"
        "Elena: Reinstall philosophy, Rohan.",
        "SUNDAY · March 16 · Theater plaza · late afternoon",
        "cute comedy",
        "happy embarrassment",
    )
    add(
        "Evening montage: dinner, walk, second movie in her room — 'best day' stamp glowing.",
        ["rohan", "elena"],
        "Dad (V.O.): Dinner. Walk. Another movie in her room. Best day of the trip. "
        "Felt like a date... even while I refused the word.",
        "SUNDAY · March 16 · Evening → night",
        "peak happiness",
        "full soft glow; crush undisputed inside him",
    )

    # ——— Monday ———
    add(
        "Monday campus: lunch together, hallway waves between breaks — unlabeled couple energy.",
        ["rohan", "elena"],
        "Dad (V.O.): Monday — breaks, lunch, leave together, dinner, walk. A ritual was forming.",
        "MONDAY · March 17 · Campus + hotel · day–evening",
        "comfortable closeness",
        "belonging sneaking in",
    )
    add(
        "Hotel room: watching Rohan's pick — soft Indian romantic Roja vibes (tasteful); "
        "warm scenes → they glance at each other then look away.",
        ["rohan", "elena"],
        "Dad (V.O.): Alternate-day rule. My choice: Roja. When warm scenes came... we looked. "
        "Silently. Then pretended the wall was fascinating.",
        "MONDAY · March 17 · Night · Elena's room",
        "charged silence",
        "mutual awareness crackling without words",
    )
    add(
        "Graphic: hotel checkout countdown as a ticking heart calendar.",
        [],
        "",
        "COUNTDOWN · Rohan checks out Thu morning (Mar 20) · Elena Fri (Mar 21)",
        "ticking dread",
        "time pressure under romance",
    )
    add(
        "Present: Maya counting on fingers.",
        ["dad", "daughter"],
        "Maya: So your brain: movies good / labeling feelings bad.\n"
        "Dad: Accurate. Painfully accurate.",
        "PRESENT",
        "tease",
    )

    # ——— Tuesday confession ———
    add(
        "Tuesday: Rohan can't work; friends huddle advice — ask her clear.",
        ["rohan", "kabir", "arjun", "wei"],
        "Kabir: Ask. Friend or more.\nWei: Clear is kind.\n"
        "Arjun: Or die of confusion — also popular.\n"
        "Rohan: If I ask, it might get awkward forever.",
        "TUESDAY · March 18 · Office break area · daytime",
        "anxious counsel",
        "fear of losing the soft thing by naming it",
    )
    add(
        "Rohan at desk staring at code he cannot see — Elena silhouette in thoughts.",
        ["rohan"],
        "Dad (V.O.): Whole day unproductive. Heart louder than keyboard.",
        "TUESDAY · March 18 · Desk · daytime",
        "distracted longing",
        "crush crowding out work",
    )
    add(
        "Tuesday night Forrest Gump glow; comfortable until phone rings.",
        ["rohan", "elena"],
        "Dad (V.O.): Night. Her movie — Forrest Gump. Beautiful. Then her brother called.",
        "TUESDAY · March 18 · ~9:30 PM · Elena's room",
        "calm before storm",
    )
    add(
        "Elena on phone lies 'lots of friends' while Rohan alone beside her — hurt then courage rising.",
        ["rohan", "elena"],
        "Elena (on phone): Yeah, just hanging out with a bunch of friends.\n"
        "Dad (V.O.): I was the only bunch. That lie opened a door. Honesty walked through.",
        "TUESDAY · March 18 · During call",
        "soft sting → resolve",
        "hurt that clarifies he wants truth not limbo forever",
    )
    add(
        "After call: Rohan gentle confrontation — last movie as friends vs long future of movies.",
        ["rohan", "elena"],
        "Rohan: Why did you lie?\nElena: ...\n"
        "Rohan: Hey — this might be our last movie as friends... "
        "or the start of movies together for a long, long future.",
        "TUESDAY · March 18 · After call",
        "heart-on-sleeve",
        "voice shaky but true",
    )
    add(
        "Elena shocked: wasn't interested at first; Rohan sad awkward; gut still whispers she cares.",
        ["rohan", "elena"],
        "Elena: I wasn't interested in you at first.\nRohan: ...Oh.\n"
        "Dad (V.O.): Sad. Awkward. Gut still whispered she cared.",
        "TUESDAY · March 18 · Elena's room",
        "shock / hurt",
        "chest drop; refuse to believe zero",
    )
    add(
        "She says get out; he stays, takes her hand, kneels sincerely — earnest not wedding parody.",
        ["rohan", "elena"],
        "Elena: Get out first.\nRohan: I won't. Please hear me.\n"
        "Dad (V.O.): I took her hand. Knelt — not for theater. For truth.",
        "TUESDAY · March 18 · Elena's room",
        "vulnerable courage",
        "terror and sincerity fused",
    )
    add(
        "Elena: scared of dating after friends' heartbreaks; Rohan: we pull each other up when we fight.",
        ["rohan", "elena"],
        "Elena: I'm scared. I've watched friends shatter.\n"
        "Rohan: Breakups happen when people stop pulling each other up. "
        "If we fight, we pull. We learn each other. Accept me — for dating.",
        "TUESDAY · March 18 · Elena's room",
        "sincere negotiation",
        "protectiveness without pressure theater",
    )
    add(
        "Close-up: Rohan names LIMBO DATE — manhwa title-card energy on the phrase.",
        ["rohan", "elena"],
        "Rohan: Call it a Limbo Date. Not nothing. Not everything. "
        "The honest middle — tell me how you really feel.\nElena: ...Limbo Date?",
        "TUESDAY · March 18 · Elena's room",
        "thesis moment",
        "invented phrase landing like a soft bomb",
    )
    add(
        "Elena admits little interest but too early; Rohan: better early than late; answer by tomorrow dinner.",
        ["rohan", "elena"],
        "Elena: I had a little interest... but it felt too early.\n"
        "Rohan: Better early than late. Bad at flirting. Good at honesty. "
        "Think tonight. Tell me at tomorrow's dinner.",
        "TUESDAY · March 18 · Late",
        "hopeful honesty",
        "relief that interest exists at all",
    )
    add(
        "Awkward hallway exit; Elena alone conflicted on bed; Rohan's silhouette walking away small.",
        ["rohan", "elena"],
        "Dad (V.O.): Left awkwardly — like a man who put his heart on the carpet and hoped nobody stepped on it.",
        "TUESDAY · March 18 · Hallway / her room · late",
        "aftermath hush",
        "adrenaline crash; hope still glowing faint",
    )
    add(
        "Present: Maya wiped-eyed still roasting.",
        ["dad", "daughter"],
        "Maya: You KNEELED?\nDad: Respectfully!\n"
        "Maya: Mom must've thought you were proposing to the carpet.\nDad: ...Possibly.",
        "PRESENT",
        "soft tease",
    )

    # ——— Wednesday feather ———
    add(
        "Wednesday: Elena WFH; empty office chair; Rohan restless pacing thoughts.",
        ["rohan"],
        "Dad (V.O.): She didn't come to campus. Worked from hotel. I respected space. My stomach did not.",
        "WEDNESDAY · March 19 · Office daytime",
        "anxious waiting",
        "stomach in knots all day",
    )
    add(
        "Dinner: Elena careful — stay in contact, don't talk about yesterday; Rohan happy but senses uneven footing.",
        ["rohan", "elena"],
        "Elena: Let's stay in contact. But please — not last night's talk. Not tonight.\n"
        "Rohan: Okay. I can do that.\n"
        "Dad (V.O.): Happy. She looked careful. Something unfinished.",
        "WEDNESDAY · March 19 · Hotel dining · evening",
        "bittersweet relief",
        "joy with a hairline crack",
    )
    add(
        "Night walk: Forrest Gump feather / opportunity speech; Elena soft-shocked.",
        ["rohan", "elena"],
        "Rohan: Forrest Gump — that feather. Great relationships are like opportunity. "
        "They float by. I didn't want to waste it. That's why I asked early.\n"
        "Elena: ...You remembered that?\n"
        "Dad (V.O.): Soft-shocked. The good kind.",
        "WEDNESDAY · March 19 · Night walk near hotel",
        "tender breakthrough",
        "connection deepening past crush into meaning",
    )
    add(
        "Movie night different energy — knowing glances; truth in the room; quiet victory smiles.",
        ["rohan", "elena"],
        "Dad (V.O.): Movie as usual. Different. The truth sat between us. "
        "Phase one — honesty — somehow worked. I was solitary... but willing to understand.",
        "WEDNESDAY · March 19 · Night · Elena's room",
        "quiet victory",
        "crush becoming mutual knowing",
    )
    add(
        "Present close: Maya leans head on Dad's shoulder; both soft lamp-lit.",
        ["dad", "daughter"],
        "Dad: Lots happened after that...\n"
        "Maya: Part Two. Tomorrow. Non-negotiable. Bring snacks for my emotional damage.\n"
        "Dad: Deal.",
        "PRESENT · Living room · late",
        "warm cliffhanger",
    )
    add(
        "End card: white feather drifting through warm hotel hallway; To Be Continued.",
        [],
        "",
        "END OF EPISODE 1 — INFATUATION · TO BE CONTINUED IN PART 2",
        "cinematic",
        "feather = opportunity floating onward",
    )

    panels = [Panel(index=i + 1, **p) for i, p in enumerate(raw)]
    return Episode(
        title="How I Met Your Mother — Episode 1: Infatuation",
        topic=(
            "Dad tells Maya how he met Mom — Rohan and Elena, a Meridian Soft trip to the Bay Area, "
            "nights around the Grand Oriole Hotel."
        ),
        season=1,
        episode_no=1,
        voice="dad_to_daughter_love_story",
        disclaimer="A dad-to-daughter love story comic. Soft romance, non-explicit.",
        characters=_chars(),
        fact_sheet=[
            "Dad tells Maya the story of how he met Mom.",
            "Setting: Meridian Soft Bay Area trip, Grand Oriole Hotel, Silverleaf Mall.",
            "Cast: Rohan, Elena, Maya, Kabir, Arjun, Wei, Marcus Hale.",
            "Frame: Dad beside daughter on the sofa — no book.",
        ],
        narrative_summary=(
            "Dad tells Maya how he met Mom: shy IT guy Rohan keeps crossing paths with Elena "
            "on a Bay Area work trip. Silence becomes cafeteria talk, long walks, a cancelled "
            "club night, and a nervously tender hotel-room movie. A Sunday movie day peaks the "
            "crush; he asks for honesty with a Limbo Date. Feelings are known by the end. "
            "To Be Continued."
        ),
        panels=panels,
    )
