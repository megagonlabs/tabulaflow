```sql
-- Database: legislator

-- Table: current (541 rows)
CREATE TABLE current (
    ballotpedia_id TEXT NULL,
        -- <example>'Sherrod Brown'</example>
    bioguide_id TEXT NULL,
        -- <example>'A000055'</example>
    birthday_bio DATE NULL,
        -- <example>'1952-11-09'</example>
    cspan_id REAL NULL,
        -- <example>45516.000</example>
    fec_id TEXT NULL,
        -- <example>'['H2OH13033', 'S6OH00163']'</example>
    first_name TEXT NULL,
        -- <example>'Sherrod'</example>
    gender_bio TEXT NULL,
        -- <values>{'F', 'M'}</values>
    google_entity_id_id TEXT NULL,
        -- <example>'kg:/m/034s80'</example>
    govtrack_id INTEGER NULL,
        -- <example>400050</example>
    house_history_id REAL NULL,
        -- <example>9996.000</example>
    icpsr_id REAL NULL,
        -- <example>29389.000</example>
    last_name TEXT NULL,
        -- <example>'Brown'</example>
    lis_id TEXT NULL,
        -- <example>'S307'</example>
    maplight_id REAL NULL,
        -- <example>168.000</example>
    middle_name TEXT NULL,
        -- <example>'L.'</example>
    nickname_name TEXT NULL,
        -- <example>'Bob'</example>
    official_full_name TEXT NULL,
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

-- Table: "current-terms" (3078 rows)
CREATE TABLE "current-terms" (
    address TEXT NULL,
        -- <example>'713 HART SENATE OFFICE BUILDING WASHINGTON DC 20510'</example>
    bioguide TEXT NULL,
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

-- Table: historical (11864 rows)
CREATE TABLE historical (
    ballotpedia_id TEXT NULL,
        -- <example>'Mo Cowan'</example>
    bioguide_id TEXT NULL PRIMARY KEY,
        -- <example>'A000001'</example>
    bioguide_previous_id TEXT NULL,
        -- <values>{'['F000246']', '['L000266']', '['W000790']'}</values>
    birthday_bio TEXT NULL,
        -- <example>'1745-04-02'</example>
    cspan_id TEXT NULL,
        -- <example>'12590.0'</example>
    fec_id TEXT NULL,
        -- <example>'['S6CO00168']'</example>
    first_name TEXT NULL,
        -- <example>'Richard'</example>
    gender_bio TEXT NULL,
        -- <values>{'F', 'M'}</values>
    google_entity_id_id TEXT NULL,
        -- <example>'kg:/m/02pz46'</example>
    govtrack_id INTEGER NULL,
        -- <example>401222</example>
    house_history_alternate_id TEXT NULL,
        -- <values>{'13283.0'}</values>
    house_history_id REAL NULL,
        -- <example>9479.000</example>
    icpsr_id REAL NULL,
        -- <example>507.000</example>
    last_name TEXT NULL,
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

-- Table: "historical-terms" (11864 rows)
CREATE TABLE "historical-terms" (
    address TEXT NULL,
        -- <example>'248 RUSSELL SENATE OFFICE BUILDING WASHINGTON DC 20510'</example>
    bioguide TEXT NULL PRIMARY KEY,
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
    end TEXT NULL,
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

-- Table: "social-media" (479 rows)
CREATE TABLE "social-media" (
    bioguide TEXT NULL PRIMARY KEY,
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