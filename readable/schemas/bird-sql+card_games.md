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
        -- <example>41138</example>
    artist TEXT NULL,
        -- <example>'Pete Venters'</example>
    asciiName TEXT NULL,
        -- <example>'El-Hajjaj'</example>
    availability TEXT NULL,
        -- <values>{'arena', 'arena,mtgo', 'arena,mtgo,paper', 'arena,paper', 'dreamcast', 'mtgo', 'mtgo,paper', 'paper', 'shandalar'}</values>
    borderColor TEXT NOT NULL,
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
    convertedManaCost REAL NOT NULL,
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
    frameVersion TEXT NOT NULL,
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
    layout TEXT NOT NULL,
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
    mtgjsonV4Id TEXT NOT NULL,
        -- <example>'ad41be73-582f-58ed-abd4-a88c1f616ac3'</example>
    mtgoFoilId TEXT NULL,
        -- <example>'27501'</example>
    mtgoId TEXT NULL,
        -- <example>'27500'</example>
    multiverseId TEXT NULL,
        -- <example>'130550'</example>
    name TEXT NOT NULL,
        -- <example>'Ancestor's Chosen'</example>
    number TEXT NOT NULL,
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
    printings TEXT NOT NULL,
        -- <example>'10E,JUD,UMA'</example>
    promoTypes TEXT NULL,
        -- <example>'boxtopper,boosterfun'</example>
    purchaseUrls TEXT NULL,
        -- <example>'{'cardKingdom': 'https://mtgjson.com/links/9fb51af...er': 'https://mtgjson.com/links/4843cea124a0d515'}'</example>
    rarity TEXT NOT NULL,
        -- <values>{'common', 'mythic', 'rare', 'uncommon'}</values>
    scryfallId TEXT NOT NULL,
        -- <example>'7a5cd03c-4227-4551-aa4b-7d119f0468b5'</example>
    scryfallIllustrationId TEXT NULL,
        -- <example>'be2f7173-c8b7-4172-a388-9b2c6b3c16e5'</example>
    scryfallOracleId TEXT NOT NULL,
        -- <example>'fc2ccab7-cab1-4463-b73d-898070136d74'</example>
    setCode TEXT NOT NULL,
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
    type TEXT NOT NULL,
        -- <example>'Creature — Human Cleric'</example>
    types TEXT NOT NULL,
        -- <example>'Creature'</example>
    uuid TEXT NOT NULL,
        -- <example>'5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c'</example>
    variations TEXT NULL,
        -- <example>'b7c19924-b4bf-56fc-aa73-f586e940bd42'</example>
    watermark TEXT NULL
        -- <example>'set (HOU)'</example>
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
        -- <example>1</example>
    flavorText TEXT NOT NULL,
        -- <example>'„Es ist der Wille aller, und meine Hand, die ihn ausführt."'</example>
    language TEXT NOT NULL,
        -- <values>{'Ancient Greek', 'Arabic', 'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Hebrew', 'Italian', 'Japanese', 'Korean', 'Latin', 'Phyrexian', 'Portuguese (Brazil)', 'Russian', 'Sanskrit', 'Spanish'}</values>
    multiverseid INTEGER NULL,
        -- <example>148411</example>
    name TEXT NOT NULL,
        -- <example>'Ausgewählter der Ahnfrau'</example>
    text TEXT NOT NULL,
        -- <example>'Erstschlag (Diese Kreatur fügt Kampfschaden vor Kr...ebenspunkt für jede Karte in deinem Friedhof dazu.'</example>
    type TEXT NOT NULL,
        -- <example>'Kreatur — Mensch, Kleriker'</example>
    uuid TEXT NOT NULL,
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
        -- <example>1</example>
    format TEXT NOT NULL,
        -- <values>{'brawl', 'commander', 'duel', 'future', 'gladiator', 'historic', 'legacy', 'modern', 'oldschool', 'pauper', 'penny', 'pioneer', 'premodern', 'standard', 'vintage'}</values>
    status TEXT NOT NULL,
        -- <values>{'Banned', 'Legal', 'Restricted'}</values>
    uuid TEXT NOT NULL,
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
        -- <example>1</example>
    date DATE NOT NULL,
        -- <example>'2007-07-15'</example>
    text TEXT NOT NULL,
        -- <example>'You draw the card when Bandage resolves, not when the damage is actually prevented.'</example>
    uuid TEXT NOT NULL,
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
        -- <example>1</example>
    language TEXT NOT NULL,
        -- <values>{'Chinese Simplified', 'Chinese Traditional', 'French', 'German', 'Italian', 'Japanese', 'Korean', 'Portuguese (Brazil)', 'Russian', 'Spanish'}</values>
    setCode TEXT NOT NULL,
        -- <example>'10E'</example>
        -- <fk> -> sets.code</fk>
    translation TEXT NULL,
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
        -- <example>1</example>
    baseSetSize INTEGER NOT NULL,
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
    keyruneCode TEXT NOT NULL,
        -- <example>'10E'</example>
    mcmId INTEGER NULL,
        -- <example>74</example>
    mcmIdExtras INTEGER NULL,
        -- <example>3209</example>
    mcmName TEXT NULL,
        -- <example>'Tenth Edition'</example>
    mtgoCode TEXT NULL,
        -- <example>'10E'</example>
    name TEXT NOT NULL,
        -- <example>'Tenth Edition'</example>
    parentCode TEXT NULL,
        -- <example>'JMP'</example>
    releaseDate DATE NOT NULL,
        -- <example>'2007-07-13'</example>
    tcgplayerGroupId INTEGER NULL,
        -- <example>1</example>
    totalSetSize INTEGER NOT NULL,
        -- <example>508</example>
    type TEXT NOT NULL
        -- <example>'core'</example>
);
```