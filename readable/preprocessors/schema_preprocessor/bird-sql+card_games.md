```sql
-- Database: card_games

/*
Schema: NULLTable: cards
Rows: 56822
Sample rows:
| id   | artist            | asciiName   | availability   | borderColor   | cardKingdomFoilId   | cardKingdomId   | colorIdentity   | colorIndicator   | colors   | convertedManaCost   | duelDeck   | edhrecRank   | faceConvertedManaCost   | faceName   | flavorName   | flavorText                                                                      | frameEffects   | frameVersion   | hand   | hasAlternativeDeckLimit   | hasContentWarning   | hasFoil   | hasNonFoil   | isAlternative   | isFullArt   | isOnlineOnly   | isOversized   | isPromo   | isReprint   | isReserved   | isStarter   | isStorySpotlight   | isTextless   | isTimeshifted   | keywords     | layout   | leadershipSkills   | life   | loyalty   | manaCost   | mcmId   | mcmMetaId   | mtgArenaId   | mtgjsonV4Id                          | mtgoFoilId   | mtgoId   | multiverseId   | name              | number   | originalReleaseDate   | originalText                                                                         | originalType            | otherFaceIds   | power   | printings                                             | promoTypes   | purchaseUrls                                                                                                                                                                                                | rarity   | scryfallId                           | scryfallIllustrationId               | scryfallOracleId                     | setCode   | side   | subtypes     | supertypes   | tcgplayerProductId   | text                                                                                 | toughness   | type                    | types    | uuid                                 | variations                           | watermark   |
|------|-------------------|-------------|----------------|---------------|---------------------|-----------------|-----------------|------------------|----------|---------------------|------------|--------------|-------------------------|------------|--------------|---------------------------------------------------------------------------------|----------------|----------------|--------|---------------------------|---------------------|-----------|--------------|-----------------|-------------|----------------|---------------|-----------|-------------|--------------|-------------|--------------------|--------------|-----------------|--------------|----------|--------------------|--------|-----------|------------|---------|-------------|--------------|--------------------------------------|--------------|----------|----------------|-------------------|----------|-----------------------|--------------------------------------------------------------------------------------|-------------------------|----------------|---------|-------------------------------------------------------|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|--------------------------------------|--------------------------------------|--------------------------------------|-----------|--------|--------------|--------------|----------------------|--------------------------------------------------------------------------------------|-------------|-------------------------|----------|--------------------------------------|--------------------------------------|-------------|
| 1    | Pete Venters      | [NULL]      | mtgo,paper     | black         | [NULL]              | 122719          | W               | [NULL]           | W        | 7.0                 | [NULL]     | 15650        | [NULL]                  | [NULL]     | [NULL]       | [NULL]                                                                          | [NULL]         | 2003           | [NULL] | 0                         | 0                   | 0         | 1            | 0               | 0           | 0              | 0             | 0         | 1           | 0            | 0           | 0                  | 0            | 0               | First strike | normal   | [NULL]             | [NULL] | [NULL]    | {5}{W}{W}  | 16165   | 156         | [NULL]       | ad41be73-582f-58ed-abd4-a88c1f616ac3 | 27501        | 27500    | 130550         | Ancestor's Chosen | 1        | [NULL]                | First strike (This creature deals combat damage before creatures without first strike.)
When Ancestor's Chosen comes into play, you gain 1 life for each card in your graveyard.                                                                                      | Creature - Human Cleric | [NULL]         | 4       | 10E,JUD,UMA                                           | [NULL]       | {'cardKingdom': 'https://mtgjson.com/links/9fb51af0ad6f0736', 'cardmarket': 'https://mtgjson.com/links/ace8861194ee0b6a', 'tcgplayer': 'https://mtgjson.com/links/4843cea124a0d515'}                        | uncommon | 7a5cd03c-4227-4551-aa4b-7d119f0468b5 | be2f7173-c8b7-4172-a388-9b2c6b3c16e5 | fc2ccab7-cab1-4463-b73d-898070136d74 | 10E       | [NULL] | Human,Cleric | [NULL]       | 15032                | First strike (This creature deals combat damage before creatures without first strike.)
When Ancestor's Chosen enters the battlefield, you gain 1 life for each card in your graveyard.                                                                                      | 4           | Creature — Human Cleric | Creature | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c | b7c19924-b4bf-56fc-aa73-f586e940bd42 | [NULL]      |
| 2    | Volkan Baǵa       | [NULL]      | mtgo,paper     | black         | [NULL]              | 122720          | W               | [NULL]           | W        | 5.0                 | [NULL]     | 12702        | [NULL]                  | [NULL]     | [NULL]       | Every tear shed is a drop of immortality.                                       | [NULL]         | 2003           | [NULL] | 0                         | 0                   | 0         | 1            | 0               | 0           | 0              | 0             | 0         | 1           | 0            | 0           | 0                  | 0            | 0               | Flying       | normal   | [NULL]             | [NULL] | [NULL]    | {4}{W}     | 16166   | 176         | [NULL]       | 9eb2e54c-a12b-5e88-a9c0-d8c84c52d59c | 26993        | 26992    | 129465         | Angel of Mercy    | 2        | [NULL]                | Flying (This creature can't be blocked except by creatures with flying or reach.)
When Angel of Mercy comes into play, you gain 3 life.                                                                                      | Creature - Angel        | [NULL]         | 3       | 10E,8ED,9ED,DDC,DVD,IMA,INV,JMP,MB1,P02,PS11,PSAL,S99 | [NULL]       | {'cardKingdom': 'https://mtgjson.com/links/027095d094e58f5b', 'cardmarket': 'https://mtgjson.com/links/f6fb5098e1cd1b1e', 'tcgplayer': 'https://mtgjson.com/links/56c4b57293f350ef'}                        | uncommon | 8f7980d4-da43-4d6d-ad16-14b8a34ae91d | e4d6c53f-e936-4be8-8b70-47c2be863b20 | a2daaf32-dbfe-4618-892e-0da24f63a44a | 10E       | [NULL] | Angel        | [NULL]       | 15033                | Flying
When Angel of Mercy enters the battlefield, you gain 3 life.                                                                                      | 3           | Creature — Angel        | Creature | 57aaebc1-850c-503d-9f6e-bb8d00d8bf7c | 8fd4e2eb-3eb4-50ea-856b-ef638fa47f8a | [NULL]      |
| 3    | Justin Sweet      | [NULL]      | mtgo,paper     | black         | [NULL]              | 122725          | W               | [NULL]           | W        | 4.0                 | [NULL]     | 11081        | [NULL]                  | [NULL]     | [NULL]       | [NULL]                                                                          | [NULL]         | 2003           | [NULL] | 0                         | 0                   | 0         | 1            | 0               | 0           | 0              | 0             | 0         | 1           | 0            | 0           | 0                  | 0            | 0               | Flying       | normal   | [NULL]             | [NULL] | [NULL]    | {3}{W}     | 16171   | 368         | [NULL]       | c0de6fd8-367a-50fb-b2f4-2b8fa5aeb7d9 | 27473        | 27472    | 129470         | Aven Cloudchaser  | 7        | [NULL]                | Flying (This creature can't be blocked except by creatures with flying or reach.)
When Aven Cloudchaser comes into play, destroy target enchantment.                                                                                      | Creature - Bird Soldier | [NULL]         | 2       | 10E,8ED,9ED,ODY                                       | [NULL]       | {'cardKingdom': 'https://mtgjson.com/links/9246105d88032a9f', 'cardmarket': 'https://mtgjson.com/links/dcdfe48e6a8f9e1e', 'tcgplayer': 'https://mtgjson.com/links/3ce595aabe276f80'}                        | common   | 407110e9-19af-4ff5-97b2-c03225031a73 | 2eb663cd-020a-46d8-a6d9-bb63d4b5c848 | 48bda7dd-d023-41e8-8c28-e0cfda0d07ca | 10E       | [NULL] | Bird,Soldier | [NULL]       | 15045                | Flying (This creature can't be blocked except by creatures with flying or reach.)
When Aven Cloudchaser enters the battlefield, destroy target enchantment.                                                                                      | 2           | Creature — Bird Soldier | Creature | 8ac972b5-9f6e-5cc8-91c3-b9a40a98232e | 6adaf14d-43e3-521a-adf1-960c808e5b1a | [NULL]      |
| 4    | Matthew D. Wilson | [NULL]      | mtgo,paper     | black         | 123094              | 122726          | W               | [NULL]           | W        | 4.0                 | [NULL]     | 12901        | [NULL]                  | [NULL]     | [NULL]       | The perfect antidote for a tightly packed formation.                            | [NULL]         | 2003           | [NULL] | 0                         | 0                   | 1         | 1            | 0               | 0           | 0              | 0             | 0         | 1           | 0            | 0           | 0                  | 0            | 0               | [NULL]       | normal   | [NULL]             | [NULL] | [NULL]    | {3}{W}     | 16172   | 423         | [NULL]       | bfbb65b1-f1bb-5355-9495-fb094f9b0782 | 27327        | 27326    | 129477         | Ballista Squad    | 8        | [NULL]                | {X}{W}, {T}: Ballista Squad deals X damage to target attacking or blocking creature. | Creature - Human Rebel  | [NULL]         | 2       | 10E,9ED,MMQ                                           | [NULL]       | {'cardKingdom': 'https://mtgjson.com/links/d702da7661073a13', 'cardKingdomFoil': 'https://mtgjson.co...ps://mtgjson.com/links/f04d4a0c97f986fe', 'tcgplayer': 'https://mtgjson.com/links/1e6874adc6cbd28f'} | uncommon | a4d17394-b9c4-43f6-9a6d-2c7c7ecb1d74 | 8464353d-099c-47ba-a0eb-e08b7b76b464 | 5973725c-6e1f-4d7e-bcef-3d867ea4c244 | 10E       | [NULL] | Human,Rebel  | [NULL]       | 15048                | {X}{W}, {T}: Ballista Squad deals X damage to target attacking or blocking creature. | 2           | Creature — Human Rebel  | Creature | a69b404f-144a-5317-b10e-7d9dce135b24 | [NULL]                               | [NULL]      |
| 5    | Rebecca Guay      | [NULL]      | mtgo,paper     | black         | 123095              | 122727          | W               | [NULL]           | W        | 1.0                 | [NULL]     | 3988         | [NULL]                  | [NULL]     | [NULL]       | Life is measured in inches. To a healer, every one of those inches is precious. | [NULL]         | 2003           | [NULL] | 0                         | 0                   | 1         | 1            | 0               | 0           | 0              | 0             | 0         | 1           | 0            | 0           | 0                  | 0            | 0               | [NULL]       | normal   | [NULL]             | [NULL] | [NULL]    | {W}        | 16173   | 432         | [NULL]       | a634f6df-fd74-54d9-a56c-3fdd2ad3e9bf | 27095        | 27094    | 132106         | Bandage           | 9        | [NULL]                | Prevent the next 1 damage that would be dealt to target creature or player this turn.
Draw a card.                                                                                      | Instant                 | [NULL]         | [NULL]  | 10E,STH,TPR                                           | [NULL]       | {'cardKingdom': 'https://mtgjson.com/links/a072a876146b29bc', 'cardKingdomFoil': 'https://mtgjson.co...ps://mtgjson.com/links/35a66170a09a59c7', 'tcgplayer': 'https://mtgjson.com/links/d091fd8b400df945'} | common   | c9c17e3b-4d7f-4472-afe1-8e9358b82f2c | af3d1d9e-8a04-4ba5-aa96-9ea678daaa2b | c664df64-0103-462b-a0f8-c483b152974a | 10E       | [NULL] | [NULL]       | [NULL]       | 15049                | Prevent the next 1 damage that would be dealt to any target this turn.
Draw a card.                                                                                      | [NULL]      | Instant                 | Instant  | 6d268c95-c176-5766-9a46-c14f739aba1c | [NULL]                               | [NULL]      |
| ...  | ...               | ...         | ...            | ...           | ...                 | ...             | ...             | ...              | ...      | ...                 | ...        | ...          | ...                     | ...        | ...          | ...                                                                             | ...            | ...            | ...    | ...                       | ...                 | ...       | ...          | ...             | ...         | ...            | ...           | ...       | ...         | ...          | ...         | ...                | ...          | ...             | ...          | ...      | ...                | ...    | ...       | ...        | ...     | ...         | ...          | ...                                  | ...          | ...      | ...            | ...               | ...      | ...                   | ...                                                                                  | ...                     | ...            | ...     | ...                                                   | ...          | ...                                                                                                                                                                                                         | ...      | ...                                  | ...                                  | ...                                  | ...       | ...    | ...          | ...          | ...                  | ...                                                                                  | ...         | ...                     | ...      | ...                                  | ...                                  | ...         |
*/
CREATE TABLE cards (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Card row identifier — unique primary key for each card in the cards table.</description>
        -- <example>41138</example>
    artist TEXT NULL,
        -- <description>Artist credited for the card’s illustration.</description>
        -- <example>'Pete Venters'</example>
    asciiName TEXT NULL,
        -- <description>ASCII card name — the card’s printed name normalized to basic‑128 ASCII by removing or replacing special Unicode characters.</description>
        -- <example>'El-Hajjaj'</example>
    availability TEXT NULL,
        -- <description>Card availability — a comma-separated list of platforms or distribution channels where this card printing appears (e.g., mtgo, paper, arena).</description>
        -- <values>{'arena', 'arena,mtgo', 'arena,mtgo,paper', 'arena,paper', 'dreamcast', 'mtgo', 'mtgo,paper', 'paper', 'shandalar'}</values>
    borderColor TEXT NOT NULL,
        -- <description>Card border color — the printed border style for this card printing (visual attribute, not a gameplay property).</description>
        -- <values>{'black', 'borderless', 'gold', 'silver', 'white'}</values>
    cardKingdomFoilId TEXT NULL,
        -- <description>Card Kingdom foil product identifier — the Card Kingdom retailer ID for this card’s foil printing; useful when joined with cardKingdomId to locate Card Kingdom listings.</description>
        -- <example>'123094'</example>
    cardKingdomId TEXT NULL,
        -- <description>Card Kingdom product identifier for this printing — a numeric ID used to link the card to its Card Kingdom product page (may be null).</description>
        -- <example>'122719'</example>
    colorIdentity TEXT NULL,
        -- <description>Card color identity — comma-separated single-letter color codes (W, U, B, R, G) representing all colors present on the card as derived from its mana cost, color indicator, and rules text; used for deck-building and format rules (for example, Commander).</description>
        -- <example>'W'</example>
    colorIndicator TEXT NULL,
        -- <description>Color indicator — the color(s) shown by the color‑indicator symbol printed next to the card’s type line (used when a card’s color is expressed by an indicator rather than its mana cost).</description>
        -- <values>{'B', 'B,G', 'B,R,U', 'G', 'G,R', 'G,R,W', 'R', 'U', 'W'}</values>
    colors TEXT NULL,
        -- <description>Card colors (the set of colors present on the card, inferred from its mana cost and color indicators).</description>
        -- <example>'W'</example>
    convertedManaCost REAL NOT NULL,
        -- <description>Converted mana cost (mana value) — the total amount of mana required to cast the card; larger values indicate a higher casting cost. Prefer the 'manaValue' property when available.</description>
        -- <example>7.000</example>
    duelDeck TEXT NULL,
        -- <description>Duel Deck membership indicator identifying which side/pack of a Duel Deck printing the card belongs to.</description>
        -- <values>{'a', 'b'}</values>
    edhrecRank INTEGER NULL,
        -- <description>EDHRec popularity rank for the card (rank on EDHRec; lower numbers indicate higher popularity).</description>
        -- <example>15650</example>
    faceConvertedManaCost REAL NULL,
        -- <description>Face converted mana value — the converted mana cost (mana value) of this card’s individual face (used for multi‑face cards such as split, transform, meld or modal faces).</description>
        -- <example>4.000</example>
    faceName TEXT NULL,
        -- <description>Face name — the printed name on a specific face of a multi‑faced card (used for transform, modal double‑faced, split, meld, etc.); typically null for single‑face printings.</description>
        -- <example>'Dusk'</example>
    flavorName TEXT NULL,
        -- <description>Promotional title printed above a card’s main name on special printings; decorative only (no gameplay effect).</description>
        -- <example>'Godzilla, King of the Monsters'</example>
    flavorText TEXT NULL,
        -- <description>Card flavor text — the italicized narrative or lore text printed below a card’s rules text; cosmetic only and has no effect on gameplay.</description>
        -- <example>'Every tear shed is a drop of immortality.'</example>
    frameEffects TEXT NULL,
        -- <description>Card frame visual-effect tag(s) indicating one or more special frame treatments applied to the printing (stored as comma‑separated tokens).</description>
        -- <example>'legendary'</example>
    frameVersion TEXT NOT NULL,
        -- <description>Card frame version — identifies the visual frame style used by that printing (the era or special frame variant).</description>
        -- <values>{'1993', '1997', '2003', '2015', 'future'}</values>
    hand TEXT NULL,
        -- <description>Starting hand size modifier — a signed integer adjustment to a player’s starting maximum hand size (written with an optional '+' or '-' prefix, e.g. +1 or -2).</description>
        -- <values>{'-1', '-2', '-3', '-4', '0', '1', '2', '3'}</values>
    hasAlternativeDeckLimit INTEGER NOT NULL,
        -- <description>Alternate deck-limit flag — indicates the card may be included in a deck at a quantity other than the default four copies (true when the card allows a nonstandard deck limit).</description>
        -- <example>0</example>
    hasContentWarning INTEGER NOT NULL,
        -- <description>Sensitive-content indicator for a card — 1 if Wizards of the Coast has flagged the card for sensitive content, 0 if not. Flagged cards may have missing or degraded properties or values.</description>
        -- <example>0</example>
    hasFoil INTEGER NOT NULL,
        -- <description>Foil availability flag indicating whether this card printing is available in foil (1 = available, 0 = not available).</description>
        -- <example>0</example>
    hasNonFoil INTEGER NOT NULL,
        -- <description>Non-foil availability flag for the card printing — indicates whether this printing is available in non-foil form.</description>
        -- <example>1</example>
    isAlternative INTEGER NOT NULL,
        -- <description>Alternate-printing indicator — marks whether the card is an alternate variation of an original printing (1 = alternate variation, 0 = standard printing).</description>
        -- <example>0</example>
    isFullArt INTEGER NOT NULL,
        -- <description>Full-art indicator for the card printing — marks printings where the artwork extends across or replaces the normal frame (full-art variants).</description>
        -- <example>0</example>
    isOnlineOnly INTEGER NOT NULL,
        -- <description>Online-only availability flag indicating whether this card printing is exclusive to digital platforms (e.g., MTG Arena).</description>
        -- <example>0</example>
    isOversized INTEGER NOT NULL,
        -- <description>Oversized-card flag indicating whether the card printing is physically larger than a standard Magic card (used for oversized tokens, promotional or novelty printings).</description>
        -- <example>0</example>
    isPromo INTEGER NOT NULL,
        -- <description>Promotional-printing indicator — whether this card printing is a promotional release.</description>
        -- <example>0</example>
    isReprint INTEGER NOT NULL,
        -- <description>Reprint indicator showing whether this printing is a reprint (1) or the original printing (0).</description>
        -- <example>1</example>
    isReserved INTEGER NOT NULL,
        -- <description>Reserved List flag indicating whether the card is on Magic: The Gathering’s Reserved List (cards Wizards has pledged not to reprint).</description>
        -- <example>0</example>
    isStarter INTEGER NOT NULL,
        -- <description>Starter-deck inclusion indicator — whether the card printing appears in starter products (for example, Planeswalker/Brawl starter decks).</description>
        -- <example>0</example>
    isStorySpotlight INTEGER NOT NULL,
        -- <description>Story Spotlight indicator for the card, marking printings that depict a key moment in Magic’s official storyline.</description>
        -- <example>0</example>
    isTextless INTEGER NOT NULL,
        -- <description>Textless flag indicating whether the card has no rules text — 1 means the card has no text box (textless), 0 means the card has a text box.</description>
        -- <example>0</example>
    isTimeshifted INTEGER NOT NULL,
        -- <description>Timeshifted indicator — marks cards printed as timeshifted (special printings that use an alternate frame version on certain sets).</description>
        -- <example>0</example>
    keywords TEXT NULL,
        -- <description>Comma-separated list of keyword abilities present on the card (extracted from its rules text), with multiple keywords combined in one string — e.g. 'Flying,Myriad,Vigilance'.</description>
        -- <example>'First strike'</example>
    layout TEXT NOT NULL,
        -- <description>Card layout — the card's structural/print layout, identifying how the card is presented (single-faced, token, split, transform/modal double-faced, saga, meld, etc.; e.g., 'token' for token cards).</description>
        -- <values>{'adventure', 'aftermath', 'augment', 'flip', 'host', 'leveler', 'meld', 'modal_dfc', 'normal', 'planar', 'saga', 'scheme', 'split', 'transform', 'vanguard'}</values>
    leadershipSkills TEXT NULL,
        -- <description>Format-specific commander eligibility flags — a mapping of play formats to boolean values indicating whether a card may be used as a commander in that format.</description>
        -- <values>{'{'brawl': False, 'commander': False, 'oathbreaker': True}', '{'brawl': False, 'commander': True, 'oathbreaker': False}', '{'brawl': False, 'commander': True, 'oathbreaker': True}', '{'brawl': True, 'commander': False, 'oathbreaker': True}', '{'brawl': True, 'commander': True, 'oathbreaker': False}'}</values>
    life TEXT NULL,
        -- <description>Starting life total modifier — a signed integer string (leading '+' or '−') indicating how many life to add or subtract from a player's starting life for cards that alter starting life (examples: '-5', '+7').</description>
        -- <example>'-5'</example>
    loyalty TEXT NULL,
        -- <description>Starting loyalty value for a planeswalker card — the loyalty printed on the card (empty if unknown); values can be numeric or variable (for example '*', '0', or expressions like '1d4+1').</description>
        -- <values>{'*', '0', '1d4+1', '2', '20', '3', '4', '5', '6', '7', 'X'}</values>
    manaCost TEXT NULL,
        -- <description>Printed mana cost — the card’s cost as shown on the card using bracketed mana symbols (e.g. {X}, numeric generic like {3}, colored symbols like {W},{U},{B},{R},{G}, hybrid or other special symbols).</description>
        -- <example>'{5}{W}{W}'</example>
    name TEXT NOT NULL,
        -- <description>Card name — the printed name shown on the card; multi‑face cards have their face names joined with a delimiter (e.g., split/meld/transform cards).</description>
        -- <example>'Ancestor's Chosen'</example>
    number TEXT NOT NULL,
        -- <description>Printed collector number within the card’s set — the set-specific identifier shown on the physical/card image; may be numeric or alphanumeric and can include prefixes/suffixes for promos or special printings (e.g., '196', 'ap100').</description>
        -- <example>'1'</example>
    originalReleaseDate TEXT NULL,
        -- <description>Original release date for promotional or out-of-cycle printings (e.g., Secret Lair drops); recorded in ISO 8601 date format (YYYY/MM/DD).</description>
        -- <example>'2012/12/1'</example>
    originalText TEXT NULL,
        -- <description>Original printed rules and flavor text of the card as it appeared on its first printing, preserved for historical/reference comparisons with the current "text" field.</description>
        -- <example>'First strike (This creature deals combat damage be..., you gain 1 life for each card in your graveyard.'</example>
    originalType TEXT NULL,
        -- <description>Original printed type line of the card, preserving any supertypes and subtypes as they appeared on the card’s original printing.</description>
        -- <example>'Creature - Human Cleric'</example>
    otherFaceIds TEXT NULL,
        -- <description>UUIDs of this card's other face(s) — one or more card UUIDs referencing the card’s counterpart face(s) (for transformed, melded, double-faced, or otherwise linked faces).</description>
        -- <example>'87f0062a-8321-5c16-960e-a12ce1df5839'</example>
    power TEXT NULL,
        -- <description>Card power — the printed power of a creature; numeric values (e.g., 4, 7), with '*' for variable/unknown, '∞' for infinite, and null for non‑creature or unspecified.</description>
        -- <example>'4'</example>
    printings TEXT NOT NULL,
        -- <description>List of set printing codes where the card has been printed, expressed as a comma-separated sequence of set codes (for example: '10E,JUD,UMA').</description>
        -- <example>'10E,JUD,UMA'</example>
    promoTypes TEXT NULL,
        -- <description>Promotional type tags for a card printing — comma-separated labels identifying special promotional releases or distribution programs (for example: setpromo, prerelease, boxtopper, judgegift).</description>
        -- <example>'boxtopper,boosterfun'</example>
    purchaseUrls TEXT NULL,
        -- <description>Marketplace purchase links — a JSON/text mapping of marketplace identifiers (for example 'cardKingdom', 'cardmarket', 'tcgplayer') to URLs where this card can be purchased.</description>
        -- <example>'{'cardKingdom': 'https://mtgjson.com/links/9fb51af...er': 'https://mtgjson.com/links/4843cea124a0d515'}'</example>
    rarity TEXT NOT NULL,
        -- <description>Card printing rarity for this specific printing of the card (classification such as common/rare).</description>
        -- <values>{'common', 'mythic', 'rare', 'uncommon'}</values>
    setCode TEXT NOT NULL,
        -- <description>Set code for the card printing — identifies the set or edition a specific card printing belongs to (foreign key referencing sets.code).</description>
        -- <example>'10E'</example>
        -- <fk> -> sets.code</fk>
    side TEXT NULL,
        -- <description>Card side identifier for multi-faced cards; null when the card has only a single face.</description>
        -- <values>{'a', 'b', 'c', 'd', 'e'}</values>
    subtypes TEXT NULL,
        -- <description>Card subtypes — a comma-separated list of the subtype names that appear after the em dash on a card’s type line (e.g., 'Human,Cleric').</description>
        -- <example>'Human,Cleric'</example>
    supertypes TEXT NULL,
        -- <description>Card supertypes as a comma-separated list — the supertypes that appear before the em dash in a card’s type line (e.g., Legendary, Basic, Snow, World).</description>
        -- <values>{'Basic', 'Basic,Snow', 'Host', 'Legendary', 'Legendary,Snow', 'Ongoing', 'Snow', 'World'}</values>
    tcgplayerProductId TEXT NULL,
        -- <description>TCGplayer product identifier — the external marketplace ID used to look up this card’s product page, listings, and pricing on TCGplayer.</description>
        -- <example>'15032'</example>
    text TEXT NULL,
        -- <description>Card rules text — the card’s gameplay instructions and ability wording as printed (may include reminder text, keywords, and multiline formatting). For multi‑face cards this field contains the rules text for that specific face.</description>
        -- <example>'First strike (This creature deals combat damage be..., you gain 1 life for each card in your graveyard.'</example>
    toughness TEXT NULL,
        -- <description>Card toughness value — the printed defensive (toughness) value for a creature face; may be a numeric value, a range, or a variable/special symbol (for example: 4, 7-*, or *).</description>
        -- <example>'4'</example>
    type TEXT NOT NULL,
        -- <description>Card type line including any supertypes, main types, and subtypes as printed on the card (e.g., "Legendary Creature — Elf Warrior").</description>
        -- <example>'Creature — Human Cleric'</example>
    types TEXT NOT NULL,
        -- <description>Card types — the card’s primary type classifications as a comma-separated list (for example: Creature, Artifact, Enchantment); includes Un‑set and gameplay-variant types when applicable.</description>
        -- <example>'Creature'</example>
    uuid TEXT NOT NULL,
        -- <description>MTGJSON v5 UUID for the card — a global unique identifier used to link this printing to MTGJSON records and to join related tables (foreign_data, legalities, rulings).</description>
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
    variations TEXT NULL,
        -- <description>Comma-separated list of UUIDs identifying this card's print variations (other card UUIDs).</description>
        -- <example>'b7c19924-b4bf-56fc-aa73-f586e940bd42'</example>
    watermark TEXT NULL,
        -- <description>Card watermark name identifying the emblem or faction mark printed on a card’s art (for example: mirran, azorius, dromoka).</description>
        -- <example>'set (HOU)'</example>
    FOREIGN KEY (setCode) REFERENCES sets(code)
);

/*
Schema: NULLTable: foreign_data
Rows: 229186
Sample rows:
| id   | flavorText                                                  | language   | multiverseid   | name                     | text                                                                                                                                                                                                        | type                            | uuid                                 |
|------|-------------------------------------------------------------|------------|----------------|--------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------|--------------------------------------|
| 1    | „Es ist der Wille aller, und meine Hand, die ihn ausführt." | German     | 148411         | Ausgewählter der Ahnfrau | Erstschlag (Diese Kreatur fügt Kampfschaden vor Kreaturen ohne Erstschlag zu.)
Wenn der Ausgewählte der Ahnfrau ins Spiel kommt, erhältst du 1 Lebenspunkt für jede Karte in deinem Friedhof dazu.                                                                                                                                                                                                             | Kreatur — Mensch, Kleriker      | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| 2    | "La voluntad de todos, realizada por mi mano."              | Spanish    | 150317         | Elegido de la Antepasada | Daña primero. (Esta criatura hace daño de combate antes que las criaturas sin la habilidad de dañar ...o.)
Cuando el Elegido de la Antepasada entre en juego, ganas 1 vida por cada carta en tu cementerio.                                                                                                                                                                                                             | Criatura — Clérigo humano       | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| 3    | « La volonté de tous passe par ma main. »                   | French     | 149934         | Élu de l'Ancêtre         | Initiative (Cette créature inflige des blessures de combat avant les créatures sans l'initiative.)
Q...l'Élu de l'Ancêtre arrive en jeu, vous gagnez 1 point de vie pour chaque carte dans votre cimetière.                                                                                                                                                                                                             | Créature : humain et clerc      | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| 4    | "La volontà di tutti, eseguita per mano mia."               | Italian    | 148794         | Prescelto dell'Antenata  | Attacco improvviso (Questa creatura infligge danno da combattimento prima delle creature senza attac...do il Prescelto dell'Antenata entra in gioco, guadagni 1 punto vita per ogni carta nel tuo cimitero. | Creatura — Chierico Umano       | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| 5    | すべての意思を、この手で成そう。                            | Japanese   | 148028         | 祖神に選ばれし者         | 先制攻撃 （このクリーチャーは先制攻撃を持たないクリーチャーよりも先に戦闘ダメージを与える。）
祖神に選ばれし者が場に出たとき、あなたはあなたの墓地にあるカード１枚につき１点のライフを得る。                                                                                                                                                                                                             | クリーチャー — 人間・クレリック | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| ...  | ...                                                         | ...        | ...            | ...                      | ...                                                                                                                                                                                                         | ...                             | ...                                  |
*/
CREATE TABLE foreign_data (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for rows in the foreign_data table.</description>
        -- <example>1</example>
    flavorText TEXT NOT NULL,
        -- <description>Foreign-language flavor text — the card’s italicized, non‑rules (flavor) text in the language indicated by foreign_data.language.</description>
        -- <example>'„Es ist der Wille aller, und meine Hand, die ihn ausführt."'</example>
    language TEXT NOT NULL,
        -- <description>Foreign card language — identifies the language of this row's localized card data (name, text and flavorText).</description>
        -- <values>{'Ancient Greek', 'Arabic', 'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Hebrew', 'Italian', 'Japanese', 'Korean', 'Latin', 'Phyrexian', 'Portuguese (Brazil)', 'Russian', 'Sanskrit', 'Spanish'}</values>
    multiverseid INTEGER NULL,
        -- <description>Foreign Multiverse identifier linking this localized (non‑English) record to the card’s Multiverse ID when available.</description>
        -- <example>148411</example>
    name TEXT NOT NULL,
        -- <description>Localized card name — the card’s name translated or localized into the language indicated by this row’s language column (links to the English card via uuid).</description>
        -- <example>'Ausgewählter der Ahnfrau'</example>
    text TEXT NOT NULL,
        -- <description>Foreign rules text — the card’s non‑English rules/ruling text (the card’s effect or ability text written in the row’s language).</description>
        -- <example>'Erstschlag (Diese Kreatur fügt Kampfschaden vor Kr...ebenspunkt für jede Karte in deinem Friedhof dazu.'</example>
    type TEXT NOT NULL,
        -- <description>Localized card type line — the card’s printed type line in a non‑English language, including any supertypes and subtypes (for example: "Criatura Lendária — Zumbi Naga").</description>
        -- <example>'Kreatur — Mensch, Kleriker'</example>
    uuid TEXT NOT NULL,
        -- <description>Card UUID that links this foreign-language row to the corresponding card in the cards table.</description>
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
        -- <fk> -> cards.uuid</fk>
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

/*
Schema: NULLTable: legalities
Rows: 427907
Sample rows:
| id   | format    | status   | uuid                                 |
|------|-----------|----------|--------------------------------------|
| 1    | commander | Legal    | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| 2    | duel      | Legal    | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| 3    | legacy    | Legal    | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| 4    | modern    | Legal    | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| 5    | penny     | Legal    | 5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c |
| ...  | ...       | ...      | ...                                  |
*/
CREATE TABLE legalities (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for a legality record.</description>
        -- <example>1</example>
    format TEXT NOT NULL,
        -- <description>Play format — the game format whose legality is being recorded; paired with the table's 'status' column to indicate whether the card is legal, banned, or restricted in that format.</description>
        -- <values>{'brawl', 'commander', 'duel', 'future', 'gladiator', 'historic', 'legacy', 'modern', 'oldschool', 'pauper', 'penny', 'pioneer', 'premodern', 'standard', 'vintage'}</values>
    status TEXT NOT NULL,
        -- <description>Card legality status — indicates whether a card is allowed in the referenced play format (i.e., legal, banned, or restricted).</description>
        -- <values>{'Banned', 'Legal', 'Restricted'}</values>
    uuid TEXT NOT NULL,
        -- <description>Card UUID identifying which card this legality applies to; foreign key referencing cards.uuid (MTGJSON v5 identifier).</description>
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
        -- <fk> -> cards.uuid</fk>
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

/*
Schema: NULLTable: rulings
Rows: 87769
Sample rows:
| id   | date       | text                                                                                                                                                               | uuid                                 |
|------|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| 1    | 2007-07-15 | You draw the card when Bandage resolves, not when the damage is actually prevented.                                                                                | 6d268c95-c176-5766-9a46-c14f739aba1c |
| 2    | 2007-02-01 | If you double a negative life total, you do the real math. A life total of -10 becomes -20.                                                                        | 56f4935b-f6c5-59b9-88bf-9bcce20247ce |
| 3    | 2007-07-15 | Beacon of Immortality’s effect counts as life gain (or life loss, if the life total was negative) for effects that trigger on or replace life gain (or life loss). | 56f4935b-f6c5-59b9-88bf-9bcce20247ce |
| 4    | 2007-07-15 | If a Beacon is countered or doesn’t resolve, it’s put into its owner’s graveyard, not shuffled into the library.                                                   | 56f4935b-f6c5-59b9-88bf-9bcce20247ce |
| 5    | 2010-08-15 | The affected creature’s last known existence on the battlefield is checked to determine its toughness.                                                             | 7fef665c-36a1-5f7a-9299-cf8938708710 |
| ...  | ...        | ...                                                                                                                                                                | ...                                  |
*/
CREATE TABLE rulings (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for a ruling.</description>
        -- <example>1</example>
    date DATE NOT NULL,
        -- <description>Ruling publication date — the calendar date when the ruling was issued or recorded.</description>
        -- <example>'2007-07-15'</example>
    text TEXT NOT NULL,
        -- <description>Ruling text for a card — the official rules clarification or explanatory note for a specific card, describing how effects interact, timing, or special application details.</description>
        -- <example>'You draw the card when Bandage resolves, not when the damage is actually prevented.'</example>
    uuid TEXT NOT NULL,
        -- <description>Card UUID identifying the card this ruling applies to (foreign key to cards.uuid).</description>
        -- <example>'6d268c95-c176-5766-9a46-c14f739aba1c'</example>
        -- <fk> -> cards.uuid</fk>
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

/*
Schema: NULLTable: set_translations
Rows: 1210
Sample rows:
| id   | language            | setCode   | translation              |
|------|---------------------|-----------|--------------------------|
| 1    | Chinese Simplified  | 10E       | 核心系列第十版           |
| 2    | Chinese Traditional | 10E       | 核心系列第十版           |
| 3    | French              | 10E       | Dixième édition          |
| 4    | German              | 10E       | Hauptset Zehnte Edition  |
| 5    | Italian             | 10E       | Set Base Decima Edizione |
| ...  | ...                 | ...       | ...                      |
*/
CREATE TABLE set_translations (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Set translation row identifier — unique identifier for each set_translations record.</description>
        -- <example>1</example>
    language TEXT NOT NULL,
        -- <description>Translation language for the set — the human-readable name of the language used for the set's translation.</description>
        -- <values>{'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Italian', 'Japanese', 'Korean', 'Portuguese (Brazil)', 'Russian', 'Spanish'}</values>
    setCode TEXT NOT NULL,
        -- <description>Set code of the set being translated.</description>
        -- <example>'10E'</example>
        -- <fk> -> sets.code</fk>
    translation TEXT NULL,
        -- <description>Translated set name — the set’s name rendered in the language indicated by the language column.</description>
        -- <example>'核心系列第十版'</example>
    FOREIGN KEY (setCode) REFERENCES sets(code)
);

/*
Schema: NULLTable: sets
Rows: 551
Sample rows:
| id   | baseSetSize   | block    | booster                                                                                                                                                                                                     | code   | isFoilOnly   | isForeignOnly   | isNonFoilOnly   | isOnlineOnly   | isPartialPreview   | keyruneCode   | mcmId   | mcmIdExtras   | mcmName        | mtgoCode   | name                                | parentCode   | releaseDate   | tcgplayerGroupId   | totalSetSize   | type    |
|------|---------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|--------------|-----------------|-----------------|----------------|--------------------|---------------|---------|---------------|----------------|------------|-------------------------------------|--------------|---------------|--------------------|----------------|---------|
| 1    | 383           | Core Set | {'default': {'boosters': [{'contents': {'basic': 1, 'common': 10, 'rare': 1, 'uncommon': 3}, 'weight...ilCommon': 1, 'rare': 1, 'uncommon': 3}, 'weight': 318987}, {'contents': {'basic': 1, 'common': 10,  | 10E    | 0            | 0               | 0               | 0              | 0                  | 10E           | 74.0    | [NULL]        | Tenth Edition  | 10E        | Tenth Edition                       | [NULL]       | 2007-07-13    | 1.0                | 508            | core    |
| 2    | 302           | Core Set | {'default': {'boosters': [{'contents': {'common': 11, 'rare': 1, 'uncommon': 3}, 'weight': 1}], 'boo...0ab4e3e6-f9fe-5fdc-9697-fd20690a0e15': 1, '0b326a61-0389-54e2-ac58-7bb47ca88202': 1, '0f099574-e9f7- | 2ED    | 0            | 0               | 1               | 0              | 0                  | 2ED           | [NULL]  | [NULL]        | [NULL]         | [NULL]     | Unlimited Edition                   | [NULL]       | 1993-12-01    | 115.0              | 302            | core    |
| 3    | 332           | [NULL]   | {'default': {'boosters': [{'contents': {'common': 8, 'dedicatedFoil2xm': 2, 'rareMythic': 2, 'uncomm...ts': {'common': {'balanceColors': True, 'cards': {'01df4e32-7fe4-5b8d-9460-0f08fa29153e': 1, '032c60 | 2XM    | 0            | 0               | 0               | 0              | 0                  | 2XM           | 3204.0  | 3209.0        | Double Masters | 2XM        | Double Masters                      | [NULL]       | 2020-08-07    | 2655.0             | 384            | masters |
| 4    | 306           | Core Set | {'default': {'boosters': [{'contents': {'common': 11, 'rare': 1, 'uncommon': 3}, 'weight': 1}], 'boo...06ab1cc7-cc5e-55aa-a1d6-0c174ef0af7d': 1, '08313acd-3e35-59b0-b018-c197d67bb74b': 1, '08c502ff-65f8- | 3ED    | 0            | 0               | 1               | 0              | 0                  | 3ED           | [NULL]  | [NULL]        | [NULL]         | [NULL]     | Revised Edition                     | [NULL]       | 1994-04-01    | 97.0               | 306            | core    |
| 5    | 378           | [NULL]   | [NULL]                                                                                                                                                                                                      | 4BB    | 0            | 1               | 0               | 0              | 0                  | 4ED           | [NULL]  | [NULL]        | [NULL]         | [NULL]     | Fourth Edition Foreign Black Border | [NULL]       | 1995-04-01    | [NULL]             | 378            | core    |
| ...  | ...           | ...      | ...                                                                                                                                                                                                         | ...    | ...          | ...             | ...             | ...            | ...                | ...           | ...     | ...           | ...            | ...        | ...                                 | ...          | ...           | ...                | ...            | ...     |
*/
CREATE TABLE sets (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>unique set identifier</description>
        -- <example>1</example>
    baseSetSize INTEGER NOT NULL,
        -- <description>Base set size — number of distinct cards in the set’s core print run (the set’s core card count; typically excludes promotional and supplemental printings).</description>
        -- <example>383</example>
    block TEXT NULL,
        -- <description>Set block name — the block or product group that the set belongs to (used to group related expansions), e.g. 'Battle for Zendikar', 'Shadowmoor'.</description>
        -- <example>'Core Set'</example>
    booster TEXT NULL,
        -- <description>Booster pack configuration (JSON) — a structured description of a set’s booster variants that lists booster “recipes” (slot contents) and their relative weights/frequencies.</description>
        -- <example>'{'default': {'boosters': [{'contents': {'basic': 1... 318987}, {'contents': {'basic': 1, 'common': 10, '</example>
    code TEXT NOT NULL,
        -- <description>Set code — short uppercase identifier for a card set used to link set records across tables.</description>
        -- <example>'10E'</example>
    isFoilOnly INTEGER NOT NULL,
        -- <description>Foil-only set indicator — marks sets whose printings are available exclusively as foil.</description>
        -- <example>0</example>
    isForeignOnly INTEGER NOT NULL,
        -- <description>Flag indicating the set was released only for foreign (non‑U.S.) markets.</description>
        -- <example>0</example>
    isNonFoilOnly INTEGER NOT NULL,
        -- <description>Non-foil-only flag for a set indicating the set is released only in non-foil printings.</description>
        -- <example>0</example>
    isOnlineOnly INTEGER NOT NULL,
        -- <description>Online-only indicator for the set — whether the set is available only through digital/online platforms (1 = online-only, 0 = not online-only).</description>
        -- <example>0</example>
    isPartialPreview INTEGER NOT NULL,
        -- <description>Set preview flag indicating the set is still being previewed (spoiled); preview sets may have incomplete or provisional data.</description>
        -- <example>0</example>
    keyruneCode TEXT NOT NULL,
        -- <description>Keyrune code mapping the set to its Keyrune icon — used to select the small emblem/image representing the set in UIs and artwork assets.</description>
        -- <example>'10E'</example>
    mcmId INTEGER NULL,
        -- <description>MagicCardMarket (MCM) set identifier used to link this set to its MagicCardMarket listing.</description>
        -- <example>74</example>
    mcmIdExtras INTEGER NULL,
        -- <description>Secondary Magic Card Market (MCM) set identifier — the second MCM ID used when a set is printed in two parts (i.e., the split/set-supplement identifier).</description>
        -- <example>3209</example>
    mcmName TEXT NULL,
        -- <description>Magic Card Market set name — the set's display name as used on MagicCardMarket (e.g., 'Tenth Edition'); may be null.</description>
        -- <example>'Tenth Edition'</example>
    mtgoCode TEXT NULL,
        -- <description>MTGO set code — the code used to identify this set on Magic: The Gathering Online; NULL when the set has no MTGO listing.</description>
        -- <example>'10E'</example>
    name TEXT NOT NULL,
        -- <description>Set name — the official display name of the card set as released (for example, 'Tenth Edition').</description>
        -- <example>'Tenth Edition'</example>
    parentCode TEXT NULL,
        -- <description>Parent set code for a set variation (identifies the original/parent set for promos, special releases, guild kits, etc.).</description>
        -- <example>'JMP'</example>
        -- <fk> -> sets.code</fk>
    releaseDate DATE NOT NULL,
        -- <description>Set release date (ISO 8601) — the set's official public release date.</description>
        -- <example>'2007-07-13'</example>
    tcgplayerGroupId INTEGER NULL,
        -- <description>TCGplayer group identifier linking the set to its TCGplayer group.</description>
        -- <example>1</example>
    totalSetSize INTEGER NOT NULL,
        -- <description>Total card count for the set, counting all printed cards including promotional and supplemental products but excluding Alchemy-only modifications.</description>
        -- <example>508</example>
    type TEXT NOT NULL,
        -- <description>Set expansion type — product-category label that classifies a set’s release (used to distinguish core, expansion, promo, commander, masters, etc.).</description>
        -- <example>'core'</example>
    FOREIGN KEY (parentCode) REFERENCES sets(code)
);
```