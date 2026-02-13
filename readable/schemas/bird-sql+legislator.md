```sql
-- Database: legislator

/*
Table: current
Rows: 541
Sample rows:
| ballotpedia_id   | bioguide_id   | birthday_bio   | cspan_id   | fec_id                     | first_name   | gender_bio   | google_entity_id_id   | govtrack_id   | house_history_id   | icpsr_id   | last_name   | lis_id   | maplight_id   | middle_name   | nickname_name   | official_full_name   | opensecrets_id   | religion_bio   | suffix_name   | thomas_id   | votesmart_id   | wikidata_id   | wikipedia_id   |
|------------------|---------------|----------------|------------|----------------------------|--------------|--------------|-----------------------|---------------|--------------------|------------|-------------|----------|---------------|---------------|-----------------|----------------------|------------------|----------------|---------------|-------------|----------------|---------------|----------------|
| Sherrod Brown    | B000944       | 1952-11-09     | 5051.0     | ['H2OH13033', 'S6OH00163'] | Sherrod      | M            | kg:/m/034s80          | 400050        | 9996.0             | 29389.0    | Brown       | S307     | 168.0         | [NULL]        | [NULL]          | Sherrod Brown        | N00003535        | Lutheran       | [NULL]        | 136         | 27018.0        | Q381880       | Sherrod Brown  |
| Maria Cantwell   | C000127       | 1958-10-13     | 26137.0    | ['S8WA00194', 'H2WA01054'] | Maria        | F            | kg:/m/01x68t          | 300018        | 10608.0            | 39310.0    | Cantwell    | S275     | 544.0         | [NULL]        | [NULL]          | Maria Cantwell       | N00007836        | Roman Catholic | [NULL]        | 172         | 27122.0        | Q22250        | Maria Cantwell |
| Ben Cardin       | C000141       | 1943-10-05     | 4004.0     | ['H6MD03177', 'S6MD03177'] | Benjamin     | M            | kg:/m/025k3k          | 400064        | 10629.0            | 15408.0    | Cardin      | S308     | 182.0         | L.            | [NULL]          | Benjamin L. Cardin   | N00001955        | Jewish         | [NULL]        | 174         | 26888.0        | Q723295       | Ben Cardin     |
| Tom Carper       | C000174       | 1947-01-23     | 663.0      | ['S8DE00079']              | Thomas       | M            | kg:/m/01xw7t          | 300019        | 10671.0            | 15015.0    | Carper      | S277     | 545.0         | Richard       | [NULL]          | Thomas R. Carper     | N00012508        | Presbyterian   | [NULL]        | 179         | 22421.0        | Q457432       | Tom Carper     |
| Bob Casey, Jr.   | C001070       | 1960-04-13     | 47036.0    | ['S6PA00217']              | Robert       | M            | kg:/m/047ymw          | 412246        | [NULL]             | 40703.0    | Casey       | S309     | 727.0         | P.            | Bob             | Robert P. Casey, Jr. | N00027503        | [NULL]         | Jr.           | 1828        | 2541.0         | Q887841       | Bob Casey Jr.  |
| ...              | ...           | ...            | ...        | ...                        | ...          | ...          | ...                   | ...           | ...                | ...        | ...         | ...      | ...           | ...           | ...             | ...                  | ...              | ...            | ...           | ...         | ...            | ...           | ...            |
*/
CREATE TABLE current (
    ballotpedia_id TEXT NULL,
        -- <example>'Sherrod Brown'</example>
    bioguide_id TEXT NOT NULL,
        -- <example>'A000055'</example>
    birthday_bio DATE NULL,
        -- <example>'1952-11-09'</example>
    cspan_id REAL NULL,
        -- <example>45516.000</example>
    fec_id TEXT NULL,
        -- <example>'['H2OH13033', 'S6OH00163']'</example>
    first_name TEXT NOT NULL,
        -- <example>'Sherrod'</example>
    gender_bio TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    google_entity_id_id TEXT NULL,
        -- <example>'kg:/m/034s80'</example>
    govtrack_id INTEGER NOT NULL,
        -- <example>400050</example>
    house_history_id REAL NULL,
        -- <example>9996.000</example>
    icpsr_id REAL NULL,
        -- <example>29389.000</example>
    last_name TEXT NOT NULL,
        -- <example>'Brown'</example>
    lis_id TEXT NULL,
        -- <example>'S307'</example>
    maplight_id REAL NULL,
        -- <example>168.000</example>
    middle_name TEXT NULL,
        -- <example>'L.'</example>
    nickname_name TEXT NULL,
        -- <example>'Bob'</example>
    official_full_name TEXT NOT NULL,
        -- <example>'Sherrod Brown'</example>
    opensecrets_id TEXT NULL,
        -- <example>'N00003535'</example>
    religion_bio TEXT NULL,
        -- <example>'Lutheran'</example>
    suffix_name TEXT NULL,
        -- <values>{'II', 'III', 'Jr.'}</values>
    thomas_id INTEGER NULL,
        -- <example>136</example>
    votesmart_id REAL NULL,
        -- <example>27018.000</example>
    wikidata_id TEXT NULL,
        -- <example>'Q381880'</example>
    wikipedia_id TEXT NULL,
        -- <example>'Sherrod Brown'</example>
    PRIMARY KEY (bioguide_id, cspan_id)
);

/*
Table: "current-terms"
Rows: 3078
Sample rows:
| address   | bioguide   | caucus   | chamber   | class   | contact_form   | district   | end        | fax    | last   | name   | office   | party    | party_affiliations   | phone   | relation   | rss_url   | start      | state   | state_rank   | title   | type   | url    |
|-----------|------------|----------|-----------|---------|----------------|------------|------------|--------|--------|--------|----------|----------|----------------------|---------|------------|-----------|------------|---------|--------------|---------|--------|--------|
| [NULL]    | B000944    | [NULL]   | [NULL]    | [NULL]  | [NULL]         | 13.0       | 1995-01-03 | [NULL] | [NULL] | [NULL] | [NULL]   | Democrat | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 1993-01-05 | OH      | [NULL]       | [NULL]  | rep    | [NULL] |
| [NULL]    | B000944    | [NULL]   | [NULL]    | [NULL]  | [NULL]         | 13.0       | 1997-01-03 | [NULL] | [NULL] | [NULL] | [NULL]   | Democrat | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 1995-01-04 | OH      | [NULL]       | [NULL]  | rep    | [NULL] |
| [NULL]    | B000944    | [NULL]   | [NULL]    | [NULL]  | [NULL]         | 13.0       | 1999-01-03 | [NULL] | [NULL] | [NULL] | [NULL]   | Democrat | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 1997-01-07 | OH      | [NULL]       | [NULL]  | rep    | [NULL] |
| [NULL]    | B000944    | [NULL]   | [NULL]    | [NULL]  | [NULL]         | 13.0       | 2001-01-03 | [NULL] | [NULL] | [NULL] | [NULL]   | Democrat | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 1999-01-06 | OH      | [NULL]       | [NULL]  | rep    | [NULL] |
| [NULL]    | B000944    | [NULL]   | [NULL]    | [NULL]  | [NULL]         | 13.0       | 2003-01-03 | [NULL] | [NULL] | [NULL] | [NULL]   | Democrat | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 2001-01-03 | OH      | [NULL]       | [NULL]  | rep    | [NULL] |
| ...       | ...        | ...      | ...       | ...     | ...            | ...        | ...        | ...    | ...    | ...    | ...      | ...      | ...                  | ...     | ...        | ...       | ...        | ...     | ...          | ...     | ...    | ...    |
*/
CREATE TABLE "current-terms" (
    address TEXT NULL,
        -- <example>'713 HART SENATE OFFICE BUILDING WASHINGTON DC 20510'</example>
    bioguide TEXT NOT NULL,
        -- <example>'A000055'</example>
        -- <fk> -> current.bioguide_id</fk>
    caucus TEXT NULL,
        -- <values>{'Democrat'}</values>
    chamber TEXT NULL,
        -- <values>{'house', 'senate'}</values>
    class REAL NULL,
        -- <example>1.000</example>
    contact_form TEXT NULL,
        -- <example>'http://www.brown.senate.gov/contact/'</example>
    district REAL NULL,
        -- <example>13.000</example>
    end TEXT NULL,
        -- <example>'1999-01-03'</example>
    fax TEXT NULL,
        -- <example>'202-228-6321'</example>
    last TEXT NULL,
        -- <values>{'Menendez'}</values>
    name TEXT NULL,
        -- <example>'Stewart Lee Udall'</example>
    office TEXT NULL,
        -- <example>'713 Hart Senate Office Building'</example>
    party TEXT NULL,
        -- <values>{'Democrat', 'Independent', 'Republican'}</values>
    party_affiliations TEXT NULL,
        -- <values>{'{'start': '1993-01-05', 'end': '1994-11-09', 'party': 'Democrat'}', '{'start': '2009-01-06', 'end': '2009-02-23', 'party': 'Independent'}'}</values>
    phone TEXT NULL,
        -- <example>'202-224-2315'</example>
    relation TEXT NULL,
        -- <values>{'brother', 'cousin', 'daughter', 'first cousin once removed', 'grandson', 'great great grandson', 'great great great nephew', 'great nephew', 'nephew', 'relative', 'sister', 'son', 'wife'}</values>
    rss_url TEXT NULL,
        -- <example>'http://www.brown.senate.gov/rss/feeds/?type=all&amp;'</example>
    start TEXT NULL,
        -- <example>'1993-01-05'</example>
    state TEXT NULL,
        -- <example>'OH'</example>
    state_rank TEXT NULL,
        -- <values>{'junior', 'senior'}</values>
    title TEXT NULL,
        -- <values>{'Majority Leader', 'Majority Whip', 'Minority Leader', 'Minority Whip', 'Speaker'}</values>
    type TEXT NULL,
        -- <values>{'rep', 'sen'}</values>
    url TEXT NULL,
        -- <example>'http://www.house.gov/sherrodbrown'</example>
    PRIMARY KEY (bioguide, end),
    FOREIGN KEY (bioguide) REFERENCES current(bioguide_id)
);

/*
Table: historical
Rows: 11864
Sample rows:
| ballotpedia_id   | bioguide_id   | bioguide_previous_id   | birthday_bio   | cspan_id   | fec_id   | first_name   | gender_bio   | google_entity_id_id   | govtrack_id   | house_history_alternate_id   | house_history_id   | icpsr_id   | last_name   | lis_id   | maplight_id   | middle_name   | nickname_name   | official_full_name   | opensecrets_id   | religion_bio   | suffix_name   | thomas_id   | votesmart_id   | wikidata_id   | wikipedia_id                   |
|------------------|---------------|------------------------|----------------|------------|----------|--------------|--------------|-----------------------|---------------|------------------------------|--------------------|------------|-------------|----------|---------------|---------------|-----------------|----------------------|------------------|----------------|---------------|-------------|----------------|---------------|--------------------------------|
| [NULL]           | B000226       | [NULL]                 | 1745-04-02     | [NULL]     | [NULL]   | Richard      | M            | kg:/m/02pz46          | 401222        | [NULL]                       | [NULL]             | 507.0      | Bassett     | [NULL]   | [NULL]        | [NULL]        | [NULL]          | [NULL]               | [NULL]           | [NULL]         | [NULL]        | [NULL]      | [NULL]         | Q518823       | Richard Bassett (politician)   |
| [NULL]           | B000546       | [NULL]                 | 1742-03-21     | [NULL]     | [NULL]   | Theodorick   | M            | kg:/m/033mf4          | 401521        | [NULL]                       | 9479.0             | 786.0      | Bland       | [NULL]   | [NULL]        | [NULL]        | [NULL]          | [NULL]               | [NULL]           | [NULL]         | [NULL]        | [NULL]      | [NULL]         | Q1749152      | Theodorick Bland (congressman) |
| [NULL]           | B001086       | [NULL]                 | 1743-06-16     | [NULL]     | [NULL]   | Aedanus      | M            | kg:/m/03yccv          | 402032        | [NULL]                       | 10177.0            | 1260.0     | Burke       | [NULL]   | [NULL]        | [NULL]        | [NULL]          | [NULL]               | [NULL]           | [NULL]         | [NULL]        | [NULL]      | [NULL]         | Q380504       | Aedanus Burke                  |
| [NULL]           | C000187       | [NULL]                 | 1730-07-22     | [NULL]     | [NULL]   | Daniel       | M            | kg:/m/02q22c          | 402334        | [NULL]                       | 10687.0            | 1538.0     | Carroll     | [NULL]   | [NULL]        | [NULL]        | [NULL]          | [NULL]               | [NULL]           | [NULL]         | [NULL]        | [NULL]      | [NULL]         | Q674371       | Daniel Carroll                 |
| [NULL]           | C000538       | [NULL]                 | 1739-03-16     | [NULL]     | [NULL]   | George       | M            | kg:/m/01mpsj          | 402671        | [NULL]                       | 11120.0            | 1859.0     | Clymer      | [NULL]   | [NULL]        | [NULL]        | [NULL]          | [NULL]               | [NULL]           | [NULL]         | [NULL]        | [NULL]      | [NULL]         | Q708913       | George Clymer                  |
| ...              | ...           | ...                    | ...            | ...        | ...      | ...          | ...          | ...                   | ...           | ...                          | ...                | ...        | ...         | ...      | ...           | ...           | ...             | ...                  | ...              | ...            | ...           | ...         | ...            | ...           | ...                            |
*/
CREATE TABLE historical (
    ballotpedia_id TEXT NULL,
        -- <example>'Mo Cowan'</example>
    bioguide_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'A000001'</example>
    bioguide_previous_id TEXT NULL,
        -- <values>{'['F000246']', '['L000266']', '['W000790']'}</values>
    birthday_bio TEXT NULL,
        -- <example>'1745-04-02'</example>
    cspan_id TEXT NULL,
        -- <example>'12590.0'</example>
    fec_id TEXT NULL,
        -- <example>'['S6CO00168']'</example>
    first_name TEXT NOT NULL,
        -- <example>'Richard'</example>
    gender_bio TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    google_entity_id_id TEXT NULL,
        -- <example>'kg:/m/02pz46'</example>
    govtrack_id INTEGER NOT NULL,
        -- <example>401222</example>
    house_history_alternate_id TEXT NULL,
        -- <values>{'13283.0'}</values>
    house_history_id REAL NULL,
        -- <example>9479.000</example>
    icpsr_id REAL NULL,
        -- <example>507.000</example>
    last_name TEXT NOT NULL,
        -- <example>'Bassett'</example>
    lis_id TEXT NULL,
        -- <example>'S134'</example>
    maplight_id TEXT NULL,
        -- <example>'232.0'</example>
    middle_name TEXT NULL,
        -- <example>'Samuel'</example>
    nickname_name TEXT NULL,
        -- <example>'of Carrollton'</example>
    official_full_name TEXT NULL,
        -- <example>'Enid Greene Waldholtz'</example>
    opensecrets_id TEXT NULL,
        -- <example>'N00008333'</example>
    religion_bio TEXT NULL,
        -- <example>'Baptist'</example>
    suffix_name TEXT NULL,
        -- <values>{'II', 'III', 'IV', 'Jr.', 'Sr.'}</values>
    thomas_id TEXT NULL,
        -- <example>'01308'</example>
    votesmart_id TEXT NULL,
        -- <example>'52156.0'</example>
    wikidata_id TEXT NULL,
        -- <example>'Q518823'</example>
    wikipedia_id TEXT NULL
        -- <example>'Richard Bassett (politician)'</example>
);

/*
Table: "historical-terms"
Rows: 11864
Sample rows:
| address   | bioguide   | chamber   | class   | contact_form   | district   | end        | fax    | last   | middle   | name   | office   | party               | party_affiliations   | phone   | relation   | rss_url   | start      | state   | state_rank   | title   | type   | url    |
|-----------|------------|-----------|---------|----------------|------------|------------|--------|--------|----------|--------|----------|---------------------|----------------------|---------|------------|-----------|------------|---------|--------------|---------|--------|--------|
| [NULL]    | B000226    | [NULL]    | 2.0     | [NULL]         | [NULL]     | 1793-03-03 | [NULL] | [NULL] | [NULL]   | [NULL] | [NULL]   | Anti-Administration | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 1789-03-04 | DE      | [NULL]       | [NULL]  | sen    | [NULL] |
| [NULL]    | B000546    | [NULL]    | [NULL]  | [NULL]         | 9.0        | 1791-03-03 | [NULL] | [NULL] | [NULL]   | [NULL] | [NULL]   | [NULL]              | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 1789-03-04 | VA      | [NULL]       | [NULL]  | rep    | [NULL] |
| [NULL]    | B001086    | [NULL]    | [NULL]  | [NULL]         | 2.0        | 1791-03-03 | [NULL] | [NULL] | [NULL]   | [NULL] | [NULL]   | [NULL]              | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 1789-03-04 | SC      | [NULL]       | [NULL]  | rep    | [NULL] |
| [NULL]    | C000187    | [NULL]    | [NULL]  | [NULL]         | 6.0        | 1791-03-03 | [NULL] | [NULL] | [NULL]   | [NULL] | [NULL]   | [NULL]              | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 1789-03-04 | MD      | [NULL]       | [NULL]  | rep    | [NULL] |
| [NULL]    | C000538    | [NULL]    | [NULL]  | [NULL]         | -1.0       | 1791-03-03 | [NULL] | [NULL] | [NULL]   | [NULL] | [NULL]   | [NULL]              | [NULL]               | [NULL]  | [NULL]     | [NULL]    | 1789-03-04 | PA      | [NULL]       | [NULL]  | rep    | [NULL] |
| ...       | ...        | ...       | ...     | ...            | ...        | ...        | ...    | ...    | ...      | ...    | ...      | ...                 | ...                  | ...     | ...        | ...       | ...        | ...     | ...          | ...     | ...    | ...    |
*/
CREATE TABLE "historical-terms" (
    address TEXT NULL,
        -- <example>'248 RUSSELL SENATE OFFICE BUILDING WASHINGTON DC 20510'</example>
    bioguide TEXT NOT NULL PRIMARY KEY,
        -- <example>'A000001'</example>
        -- <fk> -> historical.bioguide_id</fk>
    chamber TEXT NULL,
        -- <values>{'house', 'senate'}</values>
    class REAL NULL,
        -- <example>2.000</example>
    contact_form TEXT NULL,
        -- <example>'http://www.webb.senate.gov/contact.cfm'</example>
    district REAL NULL,
        -- <example>9.000</example>
    end TEXT NOT NULL,
        -- <example>'1793-03-03'</example>
    fax TEXT NULL,
        -- <example>'202-228-6363'</example>
    last TEXT NULL,
        -- <values>{'Bono', 'Lambert', 'Levy'}</values>
    middle TEXT NULL,
    name TEXT NULL,
    office TEXT NULL,
        -- <example>'248 Russell Senate Office Building'</example>
    party TEXT NULL,
        -- <example>'Anti-Administration'</example>
    party_affiliations TEXT NULL,
        -- <values>{'{'start': '2003-01-07', 'end': '2004-08-09', 'party': 'Democrat'}', '{'start': '2009-01-06', 'end': '2009-12-22', 'party': 'Democrat'}'}</values>
    phone TEXT NULL,
        -- <example>'202-224-4024'</example>
    relation TEXT NULL,
    rss_url TEXT NULL,
        -- <values>{'http://ayotte.senate.gov/rss/?p=news', 'http://bentivolio.house.gov/rss.xml', 'http://enyart.house.gov/rss.xml', 'http://gallego.house.gov/rss.xml', 'http://garcia.house.gov/rss.xml', 'http://horsford.house.gov/rss.xml', 'http://negretemcleod.house.gov/rss.xml', 'http://patrickmurphy.house.gov/news/rss.aspx', 'http://radel.house.gov/news/rss.aspx', 'http://www.begich.senate.gov/public/?a=rss.feed', 'http://www.hagan.senate.gov/rss', 'http://www.johanns.senate.gov/public/?a=RSS.Feed'}</values>
    start TEXT NULL,
        -- <example>'1789-03-04'</example>
    state TEXT NULL,
        -- <example>'DE'</example>
    state_rank TEXT NULL,
        -- <values>{'junior', 'senior'}</values>
    title TEXT NULL,
        -- <values>{'Majority Leader', 'Speaker'}</values>
    type TEXT NULL,
        -- <values>{'rep', 'sen'}</values>
    url TEXT NULL,
        -- <example>'http://edwards.senate.gov/'</example>
    FOREIGN KEY (bioguide) REFERENCES historical(bioguide_id)
);

/*
Table: "social-media"
Rows: 479
Sample rows:
| bioguide   | facebook                | facebook_id        | govtrack   | instagram    | instagram_id   | thomas   | twitter       | twitter_id   | youtube      | youtube_id               |
|------------|-------------------------|--------------------|------------|--------------|----------------|----------|---------------|--------------|--------------|--------------------------|
| R000600    | congresswomanaumuaamata | 1537155909907320.0 | 412664.0   | [NULL]       | [NULL]         | 2222     | RepAmata      | 3026622545.0 | [NULL]       | UCGdrLQbt1PYDTPsampx4t1A |
| Y000064    | RepToddYoung            | 186203844738421.0  | 412428.0   | [NULL]       | [NULL]         | 2019     | RepToddYoung  | 234128524.0  | RepToddYoung | UCuknj4PGn91gHDNAfboZEgQ |
| E000295    | senjoniernst            | 351671691660938.0  | 412667.0   | senjoniernst | 1582702853.0   | 2283     | SenJoniErnst  | 2856787757.0 | [NULL]       | UCLwrmtF_84FIcK3TyMs4MIw |
| T000476    | SenatorThomTillis       | 1576257352609470.0 | 412668.0   | [NULL]       | [NULL]         | 2291     | senthomtillis | 2964174789.0 | [NULL]       | UCUD9VGV4SSGWjGdbn37Ea2w |
| Y000063    | CongressmanKevinYoder   | 154026694650252.0  | 412430.0   | [NULL]       | [NULL]         | 2021     | RepKevinYoder | 252819642.0  | RepYoder     | UCCeYmn4A8kZEHCcAfeUW9lQ |
| ...        | ...                     | ...                | ...        | ...          | ...            | ...      | ...           | ...          | ...          | ...                      |
*/
CREATE TABLE "social-media" (
    bioguide TEXT NOT NULL PRIMARY KEY,
        -- <example>'A000055'</example>
        -- <fk> -> current.bioguide_id</fk>
    facebook TEXT NULL,
        -- <example>'congresswomanaumuaamata'</example>
    facebook_id REAL NULL,
        -- <example>1537155909907320.000</example>
    govtrack REAL NULL,
        -- <example>412664.000</example>
    instagram TEXT NULL,
        -- <example>'senjoniernst'</example>
    instagram_id REAL NULL,
        -- <example>1582702853.000</example>
    thomas INTEGER NULL,
        -- <example>2222</example>
    twitter TEXT NULL,
        -- <example>'RepAmata'</example>
    twitter_id REAL NULL,
        -- <example>3026622545.000</example>
    youtube TEXT NULL,
        -- <example>'RepToddYoung'</example>
    youtube_id TEXT NULL,
        -- <example>'UCGdrLQbt1PYDTPsampx4t1A'</example>
    FOREIGN KEY (bioguide) REFERENCES current(bioguide_id)
);
```