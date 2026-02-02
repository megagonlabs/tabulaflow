```sql
-- Database: card_games

-- Table: cards (56822 rows)
CREATE TABLE cards (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>41138</example>
    artist TEXT NULL,
        -- <example>'Pete Venters'</example>
    asciiName TEXT NULL,
        -- <example>'El-Hajjaj'</example>
    availability TEXT NULL,
        -- <values>{'arena', 'arena,mtgo', 'arena,mtgo,paper', 'arena,paper', 'dreamcast', 'mtgo', 'mtgo,paper', 'paper', 'shandalar'}</values>
    borderColor TEXT NULL,
        -- <values>{'black', 'borderless', 'gold', 'silver', 'white'}</values>
    cardKingdomFoilId TEXT NULL,
        -- <example>'123094'</example>
    cardKingdomId TEXT NULL,
        -- <example>'122719'</example>
    colorIdentity TEXT NULL,
        -- <example>'W'</example>
    colorIndicator TEXT NULL,
        -- <values>{'B', 'B,G', 'B,R,U', 'G', 'G,R', 'G,R,W', 'R', 'U', 'W'}</values>
    colors TEXT NULL,
        -- <example>'W'</example>
    convertedManaCost REAL NULL,
        -- <example>7.000</example>
    duelDeck TEXT NULL,
        -- <values>{'a', 'b'}</values>
    edhrecRank INTEGER NULL,
        -- <example>15650</example>
    faceConvertedManaCost REAL NULL,
        -- <example>4.000</example>
    faceName TEXT NULL,
        -- <example>'Dusk'</example>
    flavorName TEXT NULL,
        -- <example>'Godzilla, King of the Monsters'</example>
    flavorText TEXT NULL,
        -- <example>'Every tear shed is a drop of immortality.'</example>
    frameEffects TEXT NULL,
        -- <example>'legendary'</example>
    frameVersion TEXT NULL,
        -- <values>{'1993', '1997', '2003', '2015', 'future'}</values>
    hand TEXT NULL,
        -- <values>{'-1', '-2', '-3', '-4', '0', '1', '2', '3'}</values>
    hasAlternativeDeckLimit INTEGER NOT NULL,
        -- <example>0</example>
    hasContentWarning INTEGER NOT NULL,
        -- <example>0</example>
    hasFoil INTEGER NOT NULL,
        -- <example>0</example>
    hasNonFoil INTEGER NOT NULL,
        -- <example>1</example>
    isAlternative INTEGER NOT NULL,
        -- <example>0</example>
    isFullArt INTEGER NOT NULL,
        -- <example>0</example>
    isOnlineOnly INTEGER NOT NULL,
        -- <example>0</example>
    isOversized INTEGER NOT NULL,
        -- <example>0</example>
    isPromo INTEGER NOT NULL,
        -- <example>0</example>
    isReprint INTEGER NOT NULL,
        -- <example>1</example>
    isReserved INTEGER NOT NULL,
        -- <example>0</example>
    isStarter INTEGER NOT NULL,
        -- <example>0</example>
    isStorySpotlight INTEGER NOT NULL,
        -- <example>0</example>
    isTextless INTEGER NOT NULL,
        -- <example>0</example>
    isTimeshifted INTEGER NOT NULL,
        -- <example>0</example>
    keywords TEXT NULL,
        -- <example>'First strike'</example>
    layout TEXT NULL,
        -- <values>{'adventure', 'aftermath', 'augment', 'flip', 'host', 'leveler', 'meld', 'modal_dfc', 'normal', 'planar', 'saga', 'scheme', 'split', 'transform', 'vanguard'}</values>
    leadershipSkills TEXT NULL,
        -- <values>{'{'brawl': False, 'commander': False, 'oathbreaker': True}', '{'brawl': False, 'commander': True, 'oathbreaker': False}', '{'brawl': False, 'commander': True, 'oathbreaker': True}', '{'brawl': True, 'commander': False, 'oathbreaker': True}', '{'brawl': True, 'commander': True, 'oathbreaker': False}'}</values>
    life TEXT NULL,
        -- <example>'-5'</example>
    loyalty TEXT NULL,
        -- <values>{'*', '0', '1d4+1', '2', '20', '3', '4', '5', '6', '7', 'X'}</values>
    manaCost TEXT NULL,
        -- <example>'{5}{W}{W}'</example>
    mcmId TEXT NULL,
        -- <example>'16165'</example>
    mcmMetaId TEXT NULL,
        -- <example>'156'</example>
    mtgArenaId TEXT NULL,
        -- <example>'74983'</example>
    mtgjsonV4Id TEXT NULL,
        -- <example>'ad41be73-582f-58ed-abd4-a88c1f616ac3'</example>
    mtgoFoilId TEXT NULL,
        -- <example>'27501'</example>
    mtgoId TEXT NULL,
        -- <example>'27500'</example>
    multiverseId TEXT NULL,
        -- <example>'130550'</example>
    name TEXT NULL,
        -- <example>'Ancestor's Chosen'</example>
    number TEXT NULL,
        -- <example>'1'</example>
    originalReleaseDate TEXT NULL,
        -- <example>'2012/12/1'</example>
    originalText TEXT NULL,
        -- <example>'First strike (This creature deals combat damage be..., you gain 1 life for each card in your graveyard.'</example>
    originalType TEXT NULL,
        -- <example>'Creature - Human Cleric'</example>
    otherFaceIds TEXT NULL,
        -- <example>'87f0062a-8321-5c16-960e-a12ce1df5839'</example>
    power TEXT NULL,
        -- <example>'4'</example>
    printings TEXT NULL,
        -- <example>'10E,JUD,UMA'</example>
    promoTypes TEXT NULL,
        -- <example>'boxtopper,boosterfun'</example>
    purchaseUrls TEXT NULL,
        -- <example>'{'cardKingdom': 'https://mtgjson.com/links/9fb51af...er': 'https://mtgjson.com/links/4843cea124a0d515'}'</example>
    rarity TEXT NULL,
        -- <values>{'common', 'mythic', 'rare', 'uncommon'}</values>
    scryfallId TEXT NULL,
        -- <example>'7a5cd03c-4227-4551-aa4b-7d119f0468b5'</example>
    scryfallIllustrationId TEXT NULL,
        -- <example>'be2f7173-c8b7-4172-a388-9b2c6b3c16e5'</example>
    scryfallOracleId TEXT NULL,
        -- <example>'fc2ccab7-cab1-4463-b73d-898070136d74'</example>
    setCode TEXT NULL,
        -- <example>'10E'</example>
    side TEXT NULL,
        -- <values>{'a', 'b', 'c', 'd', 'e'}</values>
    subtypes TEXT NULL,
        -- <example>'Human,Cleric'</example>
    supertypes TEXT NULL,
        -- <values>{'Basic', 'Basic,Snow', 'Host', 'Legendary', 'Legendary,Snow', 'Ongoing', 'Snow', 'World'}</values>
    tcgplayerProductId TEXT NULL,
        -- <example>'15032'</example>
    text TEXT NULL,
        -- <example>'First strike (This creature deals combat damage be..., you gain 1 life for each card in your graveyard.'</example>
    toughness TEXT NULL,
        -- <example>'4'</example>
    type TEXT NULL,
        -- <example>'Creature — Human Cleric'</example>
    types TEXT NULL,
        -- <example>'Creature'</example>
    uuid TEXT NOT NULL,
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
    variations TEXT NULL,
        -- <example>'b7c19924-b4bf-56fc-aa73-f586e940bd42'</example>
    watermark TEXT NULL
        -- <example>'set (HOU)'</example>
);

-- Table: foreign_data (229186 rows)
CREATE TABLE foreign_data (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    flavorText TEXT NULL,
        -- <example>'„Es ist der Wille aller, und meine Hand, die ihn ausführt."'</example>
    language TEXT NULL,
        -- <values>{'Ancient Greek', 'Arabic', 'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Hebrew', 'Italian', 'Japanese', 'Korean', 'Latin', 'Phyrexian', 'Portuguese (Brazil)', 'Russian', 'Sanskrit', 'Spanish'}</values>
    multiverseid INTEGER NULL,
        -- <example>148411</example>
    name TEXT NULL,
        -- <example>'Ausgewählter der Ahnfrau'</example>
    text TEXT NULL,
        -- <example>'Erstschlag (Diese Kreatur fügt Kampfschaden vor Kr...ebenspunkt für jede Karte in deinem Friedhof dazu.'</example>
    type TEXT NULL,
        -- <example>'Kreatur — Mensch, Kleriker'</example>
    uuid TEXT NULL,
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
        -- <fk> -> cards.uuid</fk>
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

-- Table: legalities (427907 rows)
CREATE TABLE legalities (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    format TEXT NULL,
        -- <values>{'brawl', 'commander', 'duel', 'future', 'gladiator', 'historic', 'legacy', 'modern', 'oldschool', 'pauper', 'penny', 'pioneer', 'premodern', 'standard', 'vintage'}</values>
    status TEXT NULL,
        -- <values>{'Banned', 'Legal', 'Restricted'}</values>
    uuid TEXT NULL,
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
        -- <fk> -> cards.uuid</fk>
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

-- Table: rulings (87769 rows)
CREATE TABLE rulings (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    date DATE NULL,
        -- <example>'2007-07-15'</example>
    text TEXT NULL,
        -- <example>'You draw the card when Bandage resolves, not when the damage is actually prevented.'</example>
    uuid TEXT NULL,
        -- <example>'6d268c95-c176-5766-9a46-c14f739aba1c'</example>
        -- <fk> -> cards.uuid</fk>
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

-- Table: set_translations (1210 rows)
CREATE TABLE set_translations (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    language TEXT NULL,
        -- <values>{'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Italian', 'Japanese', 'Korean', 'Portuguese (Brazil)', 'Russian', 'Spanish'}</values>
    setCode TEXT NULL,
        -- <example>'10E'</example>
        -- <fk> -> sets.code</fk>
    translation TEXT NULL,
        -- <example>'核心系列第十版'</example>
    FOREIGN KEY (setCode) REFERENCES sets(code)
);

-- Table: sets (551 rows)
CREATE TABLE sets (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    baseSetSize INTEGER NULL,
        -- <example>383</example>
    block TEXT NULL,
        -- <example>'Core Set'</example>
    booster TEXT NULL,
        -- <example>'{'default': {'boosters': [{'contents': {'basic': 1... 318987}, {'contents': {'basic': 1, 'common': 10, '</example>
    code TEXT NOT NULL,
        -- <example>'10E'</example>
    isFoilOnly INTEGER NOT NULL,
        -- <example>0</example>
    isForeignOnly INTEGER NOT NULL,
        -- <example>0</example>
    isNonFoilOnly INTEGER NOT NULL,
        -- <example>0</example>
    isOnlineOnly INTEGER NOT NULL,
        -- <example>0</example>
    isPartialPreview INTEGER NOT NULL,
        -- <example>0</example>
    keyruneCode TEXT NULL,
        -- <example>'10E'</example>
    mcmId INTEGER NULL,
        -- <example>74</example>
    mcmIdExtras INTEGER NULL,
        -- <example>3209</example>
    mcmName TEXT NULL,
        -- <example>'Tenth Edition'</example>
    mtgoCode TEXT NULL,
        -- <example>'10E'</example>
    name TEXT NULL,
        -- <example>'Tenth Edition'</example>
    parentCode TEXT NULL,
        -- <example>'JMP'</example>
    releaseDate DATE NULL,
        -- <example>'2007-07-13'</example>
    tcgplayerGroupId INTEGER NULL,
        -- <example>1</example>
    totalSetSize INTEGER NULL,
        -- <example>508</example>
    type TEXT NULL
        -- <example>'core'</example>
);
```