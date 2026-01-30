```sql
-- Database: legislator

-- Table: current (541 rows)
CREATE TABLE current (
    ballotpedia_id TEXT,  -- e.g. 'Sherrod Brown'
    bioguide_id TEXT,  -- e.g. 'A000055'
    birthday_bio DATE,  -- e.g. '1952-11-09'
    cspan_id REAL,  -- e.g. 45516.000
    fec_id TEXT,  -- e.g. '['H2OH13033', 'S6OH00163']'
    first_name TEXT,  -- e.g. 'Sherrod'
    gender_bio TEXT,  -- values: {'F', 'M'}
    google_entity_id_id TEXT,  -- e.g. 'kg:/m/034s80'
    govtrack_id INTEGER,  -- e.g. 400050
    house_history_id REAL,  -- e.g. 9996.000
    icpsr_id REAL,  -- e.g. 29389.000
    last_name TEXT,  -- e.g. 'Brown'
    lis_id TEXT,  -- e.g. 'S307'
    maplight_id REAL,  -- e.g. 168.000
    middle_name TEXT,  -- e.g. 'L.'
    nickname_name TEXT,  -- e.g. 'Bob'
    official_full_name TEXT,  -- e.g. 'Sherrod Brown'
    opensecrets_id TEXT,  -- e.g. 'N00003535'
    religion_bio TEXT,  -- e.g. 'Lutheran'
    suffix_name TEXT,  -- values: {'II', 'III', 'Jr.'}
    thomas_id INTEGER,  -- e.g. 136
    votesmart_id REAL,  -- e.g. 27018.000
    wikidata_id TEXT,  -- e.g. 'Q381880'
    wikipedia_id TEXT,  -- e.g. 'Sherrod Brown'
    PRIMARY KEY (bioguide_id, cspan_id)
);

-- Table: "current-terms" (3078 rows)
CREATE TABLE "current-terms" (
    address TEXT,  -- e.g. '713 HART SENATE OFFICE BUILDING WASHINGTON DC 20510'
    bioguide TEXT,  -- e.g. 'A000055'; FK -> current.bioguide_id
    caucus TEXT,  -- values: {'Democrat'}
    chamber TEXT,  -- values: {'house', 'senate'}
    class REAL,  -- e.g. 1.000
    contact_form TEXT,  -- e.g. 'http://www.brown.senate.gov/contact/'
    district REAL,  -- e.g. 13.000
    end TEXT,  -- e.g. '1999-01-03'
    fax TEXT,  -- e.g. '202-228-6321'
    last TEXT,  -- values: {'Menendez'}
    name TEXT,  -- e.g. 'Stewart Lee Udall'
    office TEXT,  -- e.g. '713 Hart Senate Office Building'
    party TEXT,  -- values: {'Democrat', 'Independent', 'Republican'}
    party_affiliations TEXT,  -- values: {'{'start': '1993-01-05', 'end': '1994-11-09', 'party': 'Democrat'}', '{'start': '2009-01-06', 'end': '2009-02-23', 'party': 'Independent'}'}
    phone TEXT,  -- e.g. '202-224-2315'
    relation TEXT,  -- values: {'brother', 'cousin', 'daughter', 'first cousin once removed', 'grandson', 'great great grandson', 'great great great nephew', 'great nephew', 'nephew', 'relative', 'sister', 'son', 'wife'}
    rss_url TEXT,  -- e.g. 'http://www.brown.senate.gov/rss/feeds/?type=all&amp;'
    start TEXT,  -- e.g. '1993-01-05'
    state TEXT,  -- e.g. 'OH'
    state_rank TEXT,  -- values: {'junior', 'senior'}
    title TEXT,  -- values: {'Majority Leader', 'Majority Whip', 'Minority Leader', 'Minority Whip', 'Speaker'}
    type TEXT,  -- values: {'rep', 'sen'}
    url TEXT,  -- e.g. 'http://www.house.gov/sherrodbrown'
    PRIMARY KEY (bioguide, end),
    FOREIGN KEY (bioguide) REFERENCES current(bioguide_id)
);

-- Table: historical (11864 rows)
CREATE TABLE historical (
    ballotpedia_id TEXT,  -- e.g. 'Mo Cowan'
    bioguide_id TEXT PRIMARY KEY,  -- e.g. 'A000001'
    bioguide_previous_id TEXT,  -- values: {'['F000246']', '['L000266']', '['W000790']'}
    birthday_bio TEXT,  -- e.g. '1745-04-02'
    cspan_id TEXT,  -- e.g. '12590.0'
    fec_id TEXT,  -- e.g. '['S6CO00168']'
    first_name TEXT,  -- e.g. 'Richard'
    gender_bio TEXT,  -- values: {'F', 'M'}
    google_entity_id_id TEXT,  -- e.g. 'kg:/m/02pz46'
    govtrack_id INTEGER,  -- e.g. 401222
    house_history_alternate_id TEXT,  -- values: {'13283.0'}
    house_history_id REAL,  -- e.g. 9479.000
    icpsr_id REAL,  -- e.g. 507.000
    last_name TEXT,  -- e.g. 'Bassett'
    lis_id TEXT,  -- e.g. 'S134'
    maplight_id TEXT,  -- e.g. '232.0'
    middle_name TEXT,  -- e.g. 'Samuel'
    nickname_name TEXT,  -- e.g. 'of Carrollton'
    official_full_name TEXT,  -- e.g. 'Enid Greene Waldholtz'
    opensecrets_id TEXT,  -- e.g. 'N00008333'
    religion_bio TEXT,  -- e.g. 'Baptist'
    suffix_name TEXT,  -- values: {'II', 'III', 'IV', 'Jr.', 'Sr.'}
    thomas_id TEXT,  -- e.g. '01308'
    votesmart_id TEXT,  -- e.g. '52156.0'
    wikidata_id TEXT,  -- e.g. 'Q518823'
    wikipedia_id TEXT  -- e.g. 'Richard Bassett (politician)'
);

-- Table: "historical-terms" (11864 rows)
CREATE TABLE "historical-terms" (
    address TEXT,  -- e.g. '248 RUSSELL SENATE OFFICE BUILDING WASHINGTON DC 20510'
    bioguide TEXT PRIMARY KEY,  -- e.g. 'A000001'; FK -> historical.bioguide_id
    chamber TEXT,  -- values: {'house', 'senate'}
    class REAL,  -- e.g. 2.000
    contact_form TEXT,  -- e.g. 'http://www.webb.senate.gov/contact.cfm'
    district REAL,  -- e.g. 9.000
    end TEXT,  -- e.g. '1793-03-03'
    fax TEXT,  -- e.g. '202-228-6363'
    last TEXT,  -- values: {'Bono', 'Lambert', 'Levy'}
    middle TEXT,
    name TEXT,
    office TEXT,  -- e.g. '248 Russell Senate Office Building'
    party TEXT,  -- e.g. 'Anti-Administration'
    party_affiliations TEXT,  -- values: {'{'start': '2003-01-07', 'end': '2004-08-09', 'party': 'Democrat'}', '{'start': '2009-01-06', 'end': '2009-12-22', 'party': 'Democrat'}'}
    phone TEXT,  -- e.g. '202-224-4024'
    relation TEXT,
    rss_url TEXT,  -- values: {'http://ayotte.senate.gov/rss/?p=news', 'http://bentivolio.house.gov/rss.xml', 'http://enyart.house.gov/rss.xml', 'http://gallego.house.gov/rss.xml', 'http://garcia.house.gov/rss.xml', 'http://horsford.house.gov/rss.xml', 'http://negretemcleod.house.gov/rss.xml', 'http://patrickmurphy.house.gov/news/rss.aspx', 'http://radel.house.gov/news/rss.aspx', 'http://www.begich.senate.gov/public/?a=rss.feed', 'http://www.hagan.senate.gov/rss', 'http://www.johanns.senate.gov/public/?a=RSS.Feed'}
    start TEXT,  -- e.g. '1789-03-04'
    state TEXT,  -- e.g. 'DE'
    state_rank TEXT,  -- values: {'junior', 'senior'}
    title TEXT,  -- values: {'Majority Leader', 'Speaker'}
    type TEXT,  -- values: {'rep', 'sen'}
    url TEXT,  -- e.g. 'http://edwards.senate.gov/'
    FOREIGN KEY (bioguide) REFERENCES historical(bioguide_id)
);

-- Table: "social-media" (479 rows)
CREATE TABLE "social-media" (
    bioguide TEXT PRIMARY KEY,  -- e.g. 'A000055'; FK -> current.bioguide_id
    facebook TEXT,  -- e.g. 'congresswomanaumuaamata'
    facebook_id REAL,  -- e.g. 1537155909907320.000
    govtrack REAL,  -- e.g. 412664.000
    instagram TEXT,  -- e.g. 'senjoniernst'
    instagram_id REAL,  -- e.g. 1582702853.000
    thomas INTEGER,  -- e.g. 2222
    twitter TEXT,  -- e.g. 'RepAmata'
    twitter_id REAL,  -- e.g. 3026622545.000
    youtube TEXT,  -- e.g. 'RepToddYoung'
    youtube_id TEXT,  -- e.g. 'UCGdrLQbt1PYDTPsampx4t1A'
    FOREIGN KEY (bioguide) REFERENCES current(bioguide_id)
);
```