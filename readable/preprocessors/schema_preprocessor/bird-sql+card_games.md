```sql
-- Database: card_games

-- Table: cards (56822 rows)
CREATE TABLE cards (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for each card (primary key of the cards table).</description>
        -- <example>41138</example>
    artist TEXT NULL,
        -- <description>Artist credited for a card's illustration — the credited illustrator's name (most cards have a value; 3 missing out of 56,822, ~991 distinct artists).</description>
        -- <example>'Pete Venters'</example>
    asciiName TEXT NULL,
        -- <description>ASCII-normalized card name (Basic-128); the card's name with non‑ASCII / special Unicode characters removed or replaced.</description>
        -- <example>'El-Hajjaj'</example>
    availability TEXT NULL,
        -- <description>Card printing availability — a comma-separated list of product platforms/formats where this specific printing is available (which channels carry that printing). NULL when availability is not specified.</description>
        -- <values>{'arena', 'arena,mtgo', 'arena,mtgo,paper', 'arena,paper', 'dreamcast', 'mtgo', 'mtgo,paper', 'paper', 'shandalar'}</values>
    borderColor TEXT NULL,
        -- <description>card border color — the printed border treatment of the card; a visual/stylistic attribute (not a gameplay property).</description>
        -- <values>{'black', 'borderless', 'gold', 'silver', 'white'}</values>
    cardKingdomFoilId TEXT NULL,
        -- <description>Card Kingdom foil product identifier — the external Card Kingdom ID for this card's foil printing; useful for linking/matching to Card Kingdom product pages (most non-null values are unique and it complements cardKingdomId).</description>
        -- <example>'123094'</example>
    cardKingdomId TEXT NULL,
        -- <description>Card Kingdom product identifier for this specific printing — an external Card Kingdom ID used to link the card printing to Card Kingdom product pages. Values are largely unique per non-null row and are commonly paired with cardKingdomFoilId to distinguish foil vs. non‑foil listings.</description>
        -- <example>'122719'</example>
    colorIdentity TEXT NULL,
        -- <description>Card color identity — the set of colors a card is associated with (derived from its mana cost, color indicators, and rules text), recorded as a comma-separated list of color initials (W, U, B, R, G). Empty/NULL indicates a colorless card or no color identity.</description>
        -- <example>'W'</example>
    colorIndicator TEXT NULL,
        -- <description>Color indicator list — the colors shown by a card’s color-indicator symbols (the colored pips that can appear next to the type line); sparsely populated (167 non-null values out of 56,822 rows).</description>
        -- <values>{'B', 'B,G', 'B,R,U', 'G', 'G,R', 'G,R,W', 'R', 'U', 'W'}</values>
    colors TEXT NULL,
        -- <description>Card colors — a comma-separated list of color letters (W, U, B, R, G) indicating the colors present on the card (derived from manaCost and colorIndicator); NULL for colorless cards (including cards with “Devoid”).</description>
        -- <example>'W'</example>
    convertedManaCost REAL NULL,
        -- <description>Converted mana cost (mana value) of the card's printing — the total mana required to cast the card. Contains no NULLs; occasional extreme outliers (e.g., 1,000,000) appear and may be placeholders for variable or special costs. For the canonical MTGJSON name, prefer the 'manaValue' property.</description>
        -- <example>7.000</example>
    duelDeck TEXT NULL,
        -- <description>Duel Deck membership indicator — identifies which Duel Deck product printing the card belongs to; typically NULL (only a small number of cards are assigned to a Duel Deck).</description>
        -- <values>{'a', 'b'}</values>
    edhrecRank INTEGER NULL,
        -- <description>EDHRec popularity rank for the card (lower = more popular). Missing for some cards; observed range 1–20,900 with 52,061 non-null values out of 56,822 rows.</description>
        -- <example>15650</example>
    faceConvertedManaCost REAL NULL,
        -- <description>Mana value (converted mana cost) for an individual card face — used when a card has multiple faces or parts (e.g., split, double-faced, meld).</description>
        -- <example>4.000</example>
    faceName TEXT NULL,
        -- <description>Printed name on a card face — the name shown on an individual face (used for multi‑faced, split, melded, or transformed cards).</description>
        -- <example>'Dusk'</example>
    flavorName TEXT NULL,
        -- <description>Promotional display name printed above a card’s actual name — decorative text used on special promo cards and not part of gameplay. (Mostly empty: present on 21 of 56,822 rows.)</description>
        -- <example>'Godzilla, King of the Monsters'</example>
    flavorText TEXT NULL,
        -- <description>Flavor text — the italicized, non‑mechanical text printed below a card's rules text that provides lore, quotes, or ambiance and does not affect gameplay; present on roughly 54% of cards.</description>
        -- <example>'Every tear shed is a drop of immortality.'</example>
    frameEffects TEXT NULL,
        -- <description>Visual frame effects for the printing — a comma-separated list of decorative or frame-style modifications applied to this card printing (for example: "legendary", "fullart", "inverted", "extendedart", "nyxtouched"). Often empty for standard printings.</description>
        -- <example>'legendary'</example>
    frameVersion TEXT NULL,
        -- <description>Card frame style version — identifies which visual frame update a card printing uses (distinguishes older and modern frame treatments).</description>
        -- <values>{'1993', '1997', '2003', '2015', 'future'}</values>
    hand TEXT NULL,
        -- <description>Starting hand-size modifier — a small signed integer value that adjusts a card’s starting maximum hand size (examples: -1, 0, 2). This field is rarely populated (about 118 non-null rows; ~56,704 NULLs).</description>
        -- <values>{'-1', '-2', '-3', '-4', '0', '1', '2', '3'}</values>
    hasAlternativeDeckLimit INTEGER NOT NULL,
        -- <description>Alternate deck-limit indicator — marks cards that allow a nonstandard deck limit (1 = allows a deck-size other than four copies; 0 = follows the standard four-copy limit).</description>
        -- <example>0</example>
    hasContentWarning INTEGER NOT NULL,
        -- <description>Content-warning flag indicating whether a card is marked by Wizards of the Coast as containing sensitive or potentially objectionable content (1 = marked, 0 = not marked). Marked cards may have degraded or missing properties. Very rare in this dataset (29 of 56,822 rows).</description>
        -- <example>0</example>
    hasFoil INTEGER NOT NULL,
        -- <description>Foil availability indicator — whether a foil printing exists for this card.</description>
        -- <example>0</example>
    hasNonFoil INTEGER NOT NULL,
        -- <description>Non-foil availability flag for the printing — indicates whether this card printing is available in non-foil (1 = available, 0 = not available).</description>
        -- <example>1</example>
    isAlternative INTEGER NOT NULL,
        -- <description>Alternate-printing indicator — 1 if this card is an alternate variation of an original printing, 0 otherwise.</description>
        -- <example>0</example>
    isFullArt INTEGER NOT NULL,
        -- <description>Full‑art printing indicator — whether this card printing is a full‑art variant (uses expanded artwork/altered layout rather than standard framed art).</description>
        -- <example>0</example>
    isOnlineOnly INTEGER NOT NULL,
        -- <description>Online-only availability flag indicating the card printing is exclusive to digital platforms (e.g., MTG Arena/MTGO).</description>
        -- <example>0</example>
    isOversized INTEGER NOT NULL,
        -- <description>Oversized card indicator — marks printings that are physically larger than standard (used for oversized promotional or special-format cards).</description>
        -- <example>0</example>
    isPromo INTEGER NOT NULL,
        -- <description>Promotional-printing indicator for this card printing — marks whether the printing is a promotional release (1 = promotional, 0 = not).</description>
        -- <example>0</example>
    isReprint INTEGER NOT NULL,
        -- <description>reprint indicator for the card printing — 1 = this printing is a reprint, 0 = original printing</description>
        -- <example>1</example>
    isReserved INTEGER NOT NULL,
        -- <description>Reserved-list indicator — whether the card is on Magic: The Gathering's Reserved List (cards Wizards of the Coast has pledged not to reprint).</description>
        -- <example>0</example>
    isStarter INTEGER NOT NULL,
        -- <description>Starter-deck indicator — marks whether this card printing appears in starter products (for example, Planeswalker or other starter/beginner decks).</description>
        -- <example>0</example>
    isStorySpotlight INTEGER NOT NULL,
        -- <description>Story Spotlight flag marking cards designated as a Story Spotlight — cards highlighted for narrative or storyline significance within the dataset.</description>
        -- <example>0</example>
    isTextless INTEGER NOT NULL,
        -- <description>Text-box presence indicator for the card — marks cards that have no rules text box (value 1) or that do have a text box (value 0).</description>
        -- <example>0</example>
    isTimeshifted INTEGER NOT NULL,
        -- <description>Timeshifted printing indicator — marks cards printed as a "timeshifted" variant (a special alternate-frame printing used in certain sets). Value 1 = timeshifted, 0 = normal. Rare (215 of 56,822 rows).</description>
        -- <example>0</example>
    keywords TEXT NULL,
        -- <description>Card keyword abilities and mechanics (comma-separated list of ability names). Includes keyword abilities and short mechanics that appear on the card (e.g., Flying, Haste, Deathtouch, Delve, Myriad). Many rows are empty — a large portion of cards have no keywords.</description>
        -- <example>'First strike'</example>
    layout TEXT NULL,
        -- <description>Card layout — indicates the card’s physical/functional layout (how faces or parts are arranged), e.g., normal, split, transform/modal double-faced, saga, meld, adventure, etc. Useful for distinguishing multi‑face and special-format cards from standard single‑face cards.</description>
        -- <values>{'adventure', 'aftermath', 'augment', 'flip', 'host', 'leveler', 'meld', 'modal_dfc', 'normal', 'planar', 'saga', 'scheme', 'split', 'transform', 'vanguard'}</values>
    leadershipSkills TEXT NULL,
        -- <description>Leadership-format eligibility flags indicating whether the card may serve as a deck leader in formats such as commander, brawl, and oathbreaker (stored as a textified mapping like {'brawl': False, 'commander': True, 'oathbreaker': False}).</description>
        -- <values>{'{'brawl': False, 'commander': False, 'oathbreaker': True}', '{'brawl': False, 'commander': True, 'oathbreaker': False}', '{'brawl': False, 'commander': True, 'oathbreaker': True}', '{'brawl': True, 'commander': False, 'oathbreaker': True}', '{'brawl': True, 'commander': True, 'oathbreaker': False}'}</values>
    life TEXT NULL,
        -- <description>Starting life-total modifier — a signed integer (preceded by + or −) that indicates how the card adjusts a player’s starting life total (e.g., -5, 7). Very sparsely populated in this dataset (118 non-null values out of 56,822).</description>
        -- <example>'-5'</example>
    loyalty TEXT NULL,
        -- <description>Starting loyalty printed on a planeswalker card — the card's initial loyalty as printed (empty when unknown). Values may be numeric or variable expressions (e.g., '5', '4', 'X', '*', '1d4+1').</description>
        -- <values>{'*', '0', '1d4+1', '2', '20', '3', '4', '5', '6', '7', 'X'}</values>
    manaCost TEXT NULL,
        -- <description>Mana cost — the card's original printed cost expressed as a sequence of mana symbols in curly braces (e.g. {1}{W}, {X}{R}{R}).</description>
        -- <example>'{5}{W}{W}'</example>
    name TEXT NULL,
        -- <description>Card name — the card's printed/display name; for cards with multiple faces (split, meld, transform, etc.) the face names are joined together using a delimiter.</description>
        -- <example>'Ancestor's Chosen'</example>
    number TEXT NULL,
        -- <description>collector/printed card number for the specific set printing — the card's collector or identification number as it appears on the physical card; typically numeric but often alphanumeric (e.g., '196', 'ap100', '141s'). Values are not unique across different set printings.</description>
        -- <example>'1'</example>
    originalReleaseDate TEXT NULL,
        -- <description>Original release date for promotional or out-of-cycle printings (ISO‑8601-style string, e.g., YYYY/MM/DD). Used for cards released outside a set's normal window (for example, Secret Lair drops).</description>
        -- <example>'2012/12/1'</example>
    originalText TEXT NULL,
        -- <description>Original printed rules text — the card's rules-box wording as it first appeared on the printed card (preserves historical wording and may differ from the current "text" after errata or reprints).</description>
        -- <example>'First strike (This creature deals combat damage be..., you gain 1 life for each card in your graveyard.'</example>
    originalType TEXT NULL,
        -- <description>Original printed type line — the card’s type line as it appeared on its original printing, including any supertypes and subtypes (may be null for ~26% of rows).</description>
        -- <example>'Creature - Human Cleric'</example>
    otherFaceIds TEXT NULL,
        -- <description>UUIDs of this card's other face(s) — one or more MTGJSON card UUIDs referencing counterpart faces (e.g., transformed, melded, split, or alternate faces). Values are presented as comma-separated UUID strings that link to other rows' uuid.</description>
        -- <example>'87f0062a-8321-5c16-960e-a12ce1df5839'</example>
    power TEXT NULL,
        -- <description>Printed power value for the card — the card's power as printed on creature/creature-like faces; may be numeric or a special symbol/expression.</description>
        -- <example>'4'</example>
    printings TEXT NULL,
        -- <description>Comma-separated set printing codes for the card — a list of uppercase set codes indicating every set this card was printed in.</description>
        -- <example>'10E,JUD,UMA'</example>
    promoTypes TEXT NULL,
        -- <description>Promotional-type tag list for the printing — comma-separated promo tags describing special promotional printings (e.g., setpromo, prerelease, datestamped, mediainsert). Many rows are empty: promoTypes is NULL for ~50,685 of 56,822 cards (≈6,137 cards populated). Common entries include 'mediainsert' and 'setpromo,prerelease,datestamped'.</description>
        -- <example>'boxtopper,boosterfun'</example>
    purchaseUrls TEXT NULL,
        -- <description>Vendor purchase links mapping — a text-serialized dictionary of vendor identifiers to purchase URLs (often mtgjson redirect links). Common keys include 'tcgplayer', 'cardmarket', 'cardKingdom' and occasionally 'cardKingdomFoil'; keys and presence vary by card.</description>
        -- <example>'{'cardKingdom': 'https://mtgjson.com/links/9fb51af...er': 'https://mtgjson.com/links/4843cea124a0d515'}'</example>
    rarity TEXT NULL,
        -- <description>Card printing rarity — denotes the printing’s rarity tier, indicating how scarce the printing is and informing collector value and pack distribution.</description>
        -- <values>{'common', 'mythic', 'rare', 'uncommon'}</values>
    setCode TEXT NULL,
        -- <description>Set printing code identifying which set a card printing comes from (e.g., 'GRN', 'M11'). Populated for all rows in this dataset.</description>
        -- <example>'10E'</example>
        -- <fk> -> sets.code</fk>
    side TEXT NULL,
        -- <description>Card side identifier used to mark which face of a multi-faced card this row represents; blank/null indicates a single-faced printing.</description>
        -- <values>{'a', 'b', 'c', 'd', 'e'}</values>
    subtypes TEXT NULL,
        -- <description>Card subtypes — the terms that appear after the em dash in a card’s type line, recorded as a comma-separated list when a card has multiple subtypes (e.g., "Human,Cleric", "Elf,Shaman").</description>
        -- <example>'Human,Cleric'</example>
    supertypes TEXT NULL,
        -- <description>Card supertypes — comma-separated list of supertypes that appear before the em dash on a card’s type line (e.g., Legendary, Basic, Snow, World).</description>
        -- <values>{'Basic', 'Basic,Snow', 'Host', 'Legendary', 'Legendary,Snow', 'Ongoing', 'Snow', 'World'}</values>
    tcgplayerProductId TEXT NULL,
        -- <description>TCGplayer product identifier for this card — the external product ID used to link the card to its TCGplayer listing. Populated in most rows (50,222 of 56,822) and nearly unique (49,470 distinct values).</description>
        -- <example>'15032'</example>
    text TEXT NULL,
        -- <description>Card rules text (oracle) describing a card’s abilities, effects, keywords and reminder/templating text — may differ from the original printed text and is empty for some cards.</description>
        -- <example>'First strike (This creature deals combat damage be..., you gain 1 life for each card in your graveyard.'</example>
    toughness TEXT NULL,
        -- <description>Card toughness (printed defensive value) — the printed toughness shown on a card’s creature/stat line; usually a whole number but may be '*', a range or expression (e.g., '7-*', '*+1'), or null for non‑creature cards.</description>
        -- <example>'4'</example>
    type TEXT NULL,
        -- <description>Card type line — the full visible type line printed on the card, including any supertypes, types, and subtypes (e.g., "Legendary Creature — Elf Warrior").</description>
        -- <example>'Creature — Human Cleric'</example>
    types TEXT NULL,
        -- <description>Comma-separated list of all gameplay types for the card (e.g., Creature, Instant, Land), including variant/Un‑set types.</description>
        -- <example>'Creature'</example>
    uuid TEXT NOT NULL,
        -- <description>MTGJSON v5 UUID for the card — a stable, record-level unique identifier generated by MTGJSON and used to link this card to related tables (e.g., legalities, rulings, foreign_data).</description>
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
    variations TEXT NULL,
        -- <description>Comma-separated MTGJSON UUIDs identifying alternate printings/variations of this card (when present).</description>
        -- <example>'b7c19924-b4bf-56fc-aa73-f586e940bd42'</example>
    watermark TEXT NULL,
        -- <description>Card watermark name — the emblem or watermark printed on a card (e.g., mirran, azorius, dromoka). Present for 4,449 of 56,822 rows (mostly null); used to indicate set/faction identity when printed.</description>
        -- <example>'set (HOU)'</example>
    FOREIGN KEY (setCode) REFERENCES sets(code)
);

-- Table: foreign_data (229186 rows)
CREATE TABLE foreign_data (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Row identifier (primary key) for foreign_data — a unique integer surrogate id assigned to each foreign_data row.</description>
        -- <example>1</example>
    flavorText TEXT NULL,
        -- <description>Foreign flavor text — the card’s non-rules (flavor) text as printed on non-English card versions; may include quotations, attributions, line breaks and language-specific characters/punctuation.</description>
        -- <example>'„Es ist der Wille aller, und meine Hand, die ihn ausführt."'</example>
    language TEXT NULL,
        -- <description>Foreign card language, indicating the language used for the localized fields (name, text, flavorText, type) in this foreign_data row and linked to cards via uuid.</description>
        -- <values>{'Ancient Greek', 'Arabic', 'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Hebrew', 'Italian', 'Japanese', 'Korean', 'Latin', 'Phyrexian', 'Portuguese (Brazil)', 'Russian', 'Sanskrit', 'Spanish'}</values>
    multiverseid INTEGER NULL,
        -- <description>Foreign-printing multiverse identifier — the Wizards multiverse ID for this card's foreign-language printing, used to cross-reference a specific printing with external services.</description>
        -- <example>148411</example>
    name TEXT NULL,
        -- <description>Foreign-language (localized) card name — the card’s printed/official name translated into the language given by foreign_data.language and associated with the card identified by foreign_data.uuid.</description>
        -- <example>'Ausgewählter der Ahnfrau'</example>
    text TEXT NULL,
        -- <description>Foreign-language rules text — the card's rules/oracle text (rulings) translated into the row's language.</description>
        -- <example>'Erstschlag (Diese Kreatur fügt Kampfschaden vor Kr...ebenspunkt für jede Karte in deinem Friedhof dazu.'</example>
    type TEXT NULL,
        -- <description>Foreign-language card type line — the card’s printed type line in the target language, including supertypes, main types and subtypes (e.g., “Criatura Lendária — Zumbi Naga”, “Kreatur — Zentaur, Druide”). Many rows are empty or missing for some entries.</description>
        -- <example>'Kreatur — Mensch, Kleriker'</example>
    uuid TEXT NULL,
        -- <description>Card UUID linking this foreign-language row to the canonical card record (cards.uuid).</description>
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
        -- <fk> -> cards.uuid</fk>
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

-- Table: legalities (427907 rows)
CREATE TABLE legalities (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>row identifier for a legality record (primary key)</description>
        -- <example>1</example>
    format TEXT NULL,
        -- <description>Play format — identifies the organized-play format that the legality status applies to.</description>
        -- <values>{'brawl', 'commander', 'duel', 'future', 'gladiator', 'historic', 'legacy', 'modern', 'oldschool', 'pauper', 'penny', 'pioneer', 'premodern', 'standard', 'vintage'}</values>
    status TEXT NULL,
        -- <description>Format legality status of the card, indicating whether the card is permitted, prohibited, or limited in the specified play format.</description>
        -- <values>{'Banned', 'Legal', 'Restricted'}</values>
    uuid TEXT NULL,
        -- <description>Card UUID referencing cards.uuid — the MTGJSON v5 identifier that links each legality record to its card (used to join legalities → cards). Typically populated for all rows; a very small number of UUIDs do not match any card in cards.</description>
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
        -- <fk> -> cards.uuid</fk>
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

-- Table: rulings (87769 rows)
CREATE TABLE rulings (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for a ruling record.</description>
        -- <example>1</example>
    date DATE NULL,
        -- <description>Ruling date — the calendar date on which the ruling was issued.</description>
        -- <example>'2007-07-15'</example>
    text TEXT NULL,
        -- <description>Ruling text — the official explanatory text for a card ruling, providing rules clarifications, timing details and interaction guidance for that card.</description>
        -- <example>'You draw the card when Bandage resolves, not when the damage is actually prevented.'</example>
    uuid TEXT NULL,
        -- <description>Card UUID referencing the card this ruling applies to — links a ruling to its card entry (multiple rulings may share the same card UUID).</description>
        -- <example>'6d268c95-c176-5766-9a46-c14f739aba1c'</example>
        -- <fk> -> cards.uuid</fk>
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

-- Table: set_translations (1210 rows)
CREATE TABLE set_translations (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique row identifier for a set translation entry.</description>
        -- <example>1</example>
    language TEXT NULL,
        -- <description>Set translation language — the language that the translated set name/metadata is written in.</description>
        -- <values>{'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Italian', 'Japanese', 'Korean', 'Portuguese (Brazil)', 'Russian', 'Spanish'}</values>
    setCode TEXT NULL,
        -- <description>Set code (foreign key to sets.code) identifying the set this translation applies to.</description>
        -- <example>'10E'</example>
        -- <fk> -> sets.code</fk>
    translation TEXT NULL,
        -- <description>Translated set name in the target language (localized title of the card set).</description>
        -- <example>'核心系列第十版'</example>
    FOREIGN KEY (setCode) REFERENCES sets(code)
);

-- Table: sets (551 rows)
CREATE TABLE sets (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique set identifier — internal primary key for the sets table (values observed: 1–551).</description>
        -- <example>1</example>
    baseSetSize INTEGER NULL,
        -- <description>Base set card count — the number of cards in the set's base printing (the set's primary card count; excludes promotional/supplemental cards).</description>
        -- <example>383</example>
    block TEXT NULL,
        -- <description>Set block name — the name of the block (grouping) a set belongs to; used historically to group related releases. Nullable: many sets have no block and remain NULL.</description>
        -- <example>'Core Set'</example>
    booster TEXT NULL,
        -- <description>booster pack configuration (MTGJSON JSON structure) describing booster contents, slot counts, special slots, sheet/print weights and variant probabilities used to model booster composition.</description>
        -- <example>'{'default': {'boosters': [{'contents': {'basic': 1... 318987}, {'contents': {'basic': 1, 'common': 10, '</example>
    code TEXT NOT NULL,
        -- <description>Set code — the canonical short identifier used to reference a card set and its printings across tables and external sources.</description>
        -- <example>'10E'</example>
    isFoilOnly INTEGER NOT NULL,
        -- <description>Foil-only indicator for a set — marks sets that are released only in foil (1 = foil-only, 0 = not foil-only).</description>
        -- <example>0</example>
    isForeignOnly INTEGER NOT NULL,
        -- <description>Indicator for sets released only outside the United States (marks set as foreign‑market only).</description>
        -- <example>0</example>
    isNonFoilOnly INTEGER NOT NULL,
        -- <description>Indicator for whether a set is distributed only in non‑foil printings (1 = yes, 0 = no).</description>
        -- <example>0</example>
    isOnlineOnly INTEGER NOT NULL,
        -- <description>Online-only flag for the set (1 = set released only on online platforms; 0 = set has physical printings or is not online-only).</description>
        -- <example>0</example>
    isPartialPreview INTEGER NOT NULL,
        -- <description>Partial-preview indicator for a set — marks sets that are still in spoiler/preview state (their data may be incomplete).</description>
        -- <example>0</example>
    keyruneCode TEXT NULL,
        -- <description>Keyrune code used to select the set’s small Keyrune icon (the set image/badge shown in UIs). Most rows are populated (551/551) and there are 249 distinct Keyrune codes.</description>
        -- <example>'10E'</example>
    mcmId INTEGER NULL,
        -- <description>MagicCardMarket / Cardmarket set identifier linking this set to its Cardmarket listing (nullable).</description>
        -- <example>74</example>
    mcmIdExtras INTEGER NULL,
        -- <description>Secondary MagicCardMarket (MCM) set identifier used when a set is printed in two parts — identifies the second MCM set for split/paired printings.</description>
        -- <example>3209</example>
    mcmName TEXT NULL,
        -- <description>Magic Card Market (MCM) set name — the set's display name as listed on MagicCardMarket, used to map or match this set to its MCM listing; may be null.</description>
        -- <example>'Tenth Edition'</example>
    mtgoCode TEXT NULL,
        -- <description>MTGO set code — the set's official code as used on Magic: The Gathering Online; null means the set is not listed on MTGO.</description>
        -- <example>'10E'</example>
    name TEXT NULL,
        -- <description>Set name — the human-readable title of the expansion or product (the display name printed for the set), e.g., "Tenth Edition". Each row in the sets table has a non-null, unique value.</description>
        -- <example>'Tenth Edition'</example>
    parentCode TEXT NULL,
        -- <description>Parent set code for set variations — the set code of the base/parent set for this printing (used for promotions, guild kits, alternate printings and other set variants); references the parent set in sets.code. Many sets have no parent (154 of 551 rows are populated).</description>
        -- <example>'JMP'</example>
        -- <fk> -> sets.code</fk>
    releaseDate DATE NULL,
        -- <description>set release date (ISO 8601) — the official release date of the set, recorded in ISO 8601 format. All 551 rows have values (earliest: 1993-08-05; latest: 2021-03-19).</description>
        -- <example>'2007-07-13'</example>
    tcgplayerGroupId INTEGER NULL,
        -- <description>TCGplayer group identifier for the set (external mapping to TCGplayer's set group).</description>
        -- <example>1</example>
    totalSetSize INTEGER NULL,
        -- <description>Total set size — the total number of cards in the set, counting promotional and related supplemental products; excludes Alchemy-only modifications.</description>
        -- <example>508</example>
    type TEXT NULL,
        -- <description>Set expansion type — categorizes the set by product/role (how and why it was released), e.g., core or expansion releases, promotional or supplemental products like commander or masters, token/box products, etc.</description>
        -- <example>'core'</example>
    FOREIGN KEY (parentCode) REFERENCES sets(code)
);
```