```sql
-- Database: card_games

-- Table: cards (56822 rows)
CREATE TABLE cards (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 41138
    artist TEXT,  -- e.g. 'Pete Venters'
    asciiName TEXT,  -- e.g. 'El-Hajjaj'
    availability TEXT,  -- values: {'arena', 'arena,mtgo', 'arena,mtgo,paper', 'arena,paper', 'dreamcast', 'mtgo', 'mtgo,paper', 'paper', 'shandalar'}
    borderColor TEXT,  -- values: {'black', 'borderless', 'gold', 'silver', 'white'}
    cardKingdomFoilId TEXT,  -- e.g. '123094'
    cardKingdomId TEXT,  -- e.g. '122719'
    colorIdentity TEXT,  -- e.g. 'W'
    colorIndicator TEXT,  -- values: {'B', 'B,G', 'B,R,U', 'G', 'G,R', 'G,R,W', 'R', 'U', 'W'}
    colors TEXT,  -- e.g. 'W'
    convertedManaCost REAL,  -- e.g. 7.000
    duelDeck TEXT,  -- values: {'a', 'b'}
    edhrecRank INTEGER,  -- e.g. 15650
    faceConvertedManaCost REAL,  -- e.g. 4.000
    faceName TEXT,  -- e.g. 'Dusk'
    flavorName TEXT,  -- e.g. 'Godzilla, King of the Monsters'
    flavorText TEXT,  -- e.g. 'Every tear shed is a drop of immortality.'
    frameEffects TEXT,  -- e.g. 'legendary'
    frameVersion TEXT,  -- values: {'1993', '1997', '2003', '2015', 'future'}
    hand TEXT,  -- values: {'-1', '-2', '-3', '-4', '0', '1', '2', '3'}
    hasAlternativeDeckLimit INTEGER NOT NULL,  -- e.g. 0
    hasContentWarning INTEGER NOT NULL,  -- e.g. 0
    hasFoil INTEGER NOT NULL,  -- e.g. 0
    hasNonFoil INTEGER NOT NULL,  -- e.g. 1
    isAlternative INTEGER NOT NULL,  -- e.g. 0
    isFullArt INTEGER NOT NULL,  -- e.g. 0
    isOnlineOnly INTEGER NOT NULL,  -- e.g. 0
    isOversized INTEGER NOT NULL,  -- e.g. 0
    isPromo INTEGER NOT NULL,  -- e.g. 0
    isReprint INTEGER NOT NULL,  -- e.g. 1
    isReserved INTEGER NOT NULL,  -- e.g. 0
    isStarter INTEGER NOT NULL,  -- e.g. 0
    isStorySpotlight INTEGER NOT NULL,  -- e.g. 0
    isTextless INTEGER NOT NULL,  -- e.g. 0
    isTimeshifted INTEGER NOT NULL,  -- e.g. 0
    keywords TEXT,  -- e.g. 'First strike'
    layout TEXT,  -- values: {'adventure', 'aftermath', 'augment', 'flip', 'host', 'leveler', 'meld', 'modal_dfc', 'normal', 'planar', 'saga', 'scheme', 'split', 'transform', 'vanguard'}
    leadershipSkills TEXT,  -- values: {'{'brawl': False, 'commander': False, 'oathbreaker': True}', '{'brawl': False, 'commander': True, 'oathbreaker': False}', '{'brawl': False, 'commander': True, 'oathbreaker': True}', '{'brawl': True, 'commander': False, 'oathbreaker': True}', '{'brawl': True, 'commander': True, 'oathbreaker': False}'}
    life TEXT,  -- e.g. '-5'
    loyalty TEXT,  -- values: {'*', '0', '1d4+1', '2', '20', '3', '4', '5', '6', '7', 'X'}
    manaCost TEXT,  -- e.g. '{5}{W}{W}'
    mcmId TEXT,  -- e.g. '16165'
    mcmMetaId TEXT,  -- e.g. '156'
    mtgArenaId TEXT,  -- e.g. '74983'
    mtgjsonV4Id TEXT,  -- e.g. 'ad41be73-582f-58ed-abd4-a88c1f616ac3'
    mtgoFoilId TEXT,  -- e.g. '27501'
    mtgoId TEXT,  -- e.g. '27500'
    multiverseId TEXT,  -- e.g. '130550'
    name TEXT,  -- e.g. 'Ancestor's Chosen'
    number TEXT,  -- e.g. '1'
    originalReleaseDate TEXT,  -- e.g. '2012/12/1'
    originalText TEXT,  -- e.g. 'First strike (This creature deals combat damage be..., you gain 1 life for each card in your graveyard.'
    originalType TEXT,  -- e.g. 'Creature - Human Cleric'
    otherFaceIds TEXT,  -- e.g. '87f0062a-8321-5c16-960e-a12ce1df5839'
    power TEXT,  -- e.g. '4'
    printings TEXT,  -- e.g. '10E,JUD,UMA'
    promoTypes TEXT,  -- e.g. 'boxtopper,boosterfun'
    purchaseUrls TEXT,  -- e.g. '{'cardKingdom': 'https://mtgjson.com/links/9fb51af...er': 'https://mtgjson.com/links/4843cea124a0d515'}'
    rarity TEXT,  -- values: {'common', 'mythic', 'rare', 'uncommon'}
    scryfallId TEXT,  -- e.g. '7a5cd03c-4227-4551-aa4b-7d119f0468b5'
    scryfallIllustrationId TEXT,  -- e.g. 'be2f7173-c8b7-4172-a388-9b2c6b3c16e5'
    scryfallOracleId TEXT,  -- e.g. 'fc2ccab7-cab1-4463-b73d-898070136d74'
    setCode TEXT,  -- e.g. '10E'
    side TEXT,  -- values: {'a', 'b', 'c', 'd', 'e'}
    subtypes TEXT,  -- e.g. 'Human,Cleric'
    supertypes TEXT,  -- values: {'Basic', 'Basic,Snow', 'Host', 'Legendary', 'Legendary,Snow', 'Ongoing', 'Snow', 'World'}
    tcgplayerProductId TEXT,  -- e.g. '15032'
    text TEXT,  -- e.g. 'First strike (This creature deals combat damage be..., you gain 1 life for each card in your graveyard.'
    toughness TEXT,  -- e.g. '4'
    type TEXT,  -- e.g. 'Creature — Human Cleric'
    types TEXT,  -- e.g. 'Creature'
    uuid TEXT NOT NULL,  -- e.g. '5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'
    variations TEXT,  -- e.g. 'b7c19924-b4bf-56fc-aa73-f586e940bd42'
    watermark TEXT  -- e.g. 'set (HOU)'
);

-- Table: foreign_data (229186 rows)
CREATE TABLE foreign_data (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    flavorText TEXT,  -- e.g. '„Es ist der Wille aller, und meine Hand, die ihn ausführt."'
    language TEXT,  -- values: {'Ancient Greek', 'Arabic', 'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Hebrew', 'Italian', 'Japanese', 'Korean', 'Latin', 'Phyrexian', 'Portuguese (Brazil)', 'Russian', 'Sanskrit', 'Spanish'}
    multiverseid INTEGER,  -- e.g. 148411
    name TEXT,  -- e.g. 'Ausgewählter der Ahnfrau'
    text TEXT,  -- e.g. 'Erstschlag (Diese Kreatur fügt Kampfschaden vor Kr...ebenspunkt für jede Karte in deinem Friedhof dazu.'
    type TEXT,  -- e.g. 'Kreatur — Mensch, Kleriker'
    uuid TEXT,  -- e.g. '5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'; FK -> cards.uuid
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

-- Table: legalities (427907 rows)
CREATE TABLE legalities (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    format TEXT,  -- values: {'brawl', 'commander', 'duel', 'future', 'gladiator', 'historic', 'legacy', 'modern', 'oldschool', 'pauper', 'penny', 'pioneer', 'premodern', 'standard', 'vintage'}
    status TEXT,  -- values: {'Banned', 'Legal', 'Restricted'}
    uuid TEXT,  -- e.g. '5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'; FK -> cards.uuid
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

-- Table: rulings (87769 rows)
CREATE TABLE rulings (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    date DATE,  -- e.g. '2007-07-15'
    text TEXT,  -- e.g. 'You draw the card when Bandage resolves, not when the damage is actually prevented.'
    uuid TEXT,  -- e.g. '6d268c95-c176-5766-9a46-c14f739aba1c'; FK -> cards.uuid
    FOREIGN KEY (uuid) REFERENCES cards(uuid)
);

-- Table: set_translations (1210 rows)
CREATE TABLE set_translations (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    language TEXT,  -- values: {'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Italian', 'Japanese', 'Korean', 'Portuguese (Brazil)', 'Russian', 'Spanish'}
    setCode TEXT,  -- e.g. '10E'; FK -> sets.code
    translation TEXT,  -- e.g. '核心系列第十版'
    FOREIGN KEY (setCode) REFERENCES sets(code)
);

-- Table: sets (551 rows)
CREATE TABLE sets (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    baseSetSize INTEGER,  -- e.g. 383
    block TEXT,  -- e.g. 'Core Set'
    booster TEXT,  -- e.g. '{'default': {'boosters': [{'contents': {'basic': 1... 318987}, {'contents': {'basic': 1, 'common': 10, '
    code TEXT NOT NULL,  -- e.g. '10E'
    isFoilOnly INTEGER NOT NULL,  -- e.g. 0
    isForeignOnly INTEGER NOT NULL,  -- e.g. 0
    isNonFoilOnly INTEGER NOT NULL,  -- e.g. 0
    isOnlineOnly INTEGER NOT NULL,  -- e.g. 0
    isPartialPreview INTEGER NOT NULL,  -- e.g. 0
    keyruneCode TEXT,  -- e.g. '10E'
    mcmId INTEGER,  -- e.g. 74
    mcmIdExtras INTEGER,  -- e.g. 3209
    mcmName TEXT,  -- e.g. 'Tenth Edition'
    mtgoCode TEXT,  -- e.g. '10E'
    name TEXT,  -- e.g. 'Tenth Edition'
    parentCode TEXT,  -- e.g. 'JMP'
    releaseDate DATE,  -- e.g. '2007-07-13'
    tcgplayerGroupId INTEGER,  -- e.g. 1
    totalSetSize INTEGER,  -- e.g. 508
    type TEXT  -- e.g. 'core'
);
```