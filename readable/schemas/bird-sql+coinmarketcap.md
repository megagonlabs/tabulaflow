```sql
-- Database: coinmarketcap

-- Table: coins (8927 rows)
CREATE TABLE coins (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NULL,
        -- <example>'Bitcoin'</example>
    slug TEXT NULL,
        -- <example>'bitcoin'</example>
    symbol TEXT NULL,
        -- <example>'BTC'</example>
    status TEXT NULL,
        -- <values>{'active', 'extinct', 'inactive', 'untracked'}</values>
    category TEXT NULL,
        -- <values>{'coin', 'token'}</values>
    description TEXT NULL,
        -- <example>'## **What Is Bitcoin (BTC)?**\n\nBitcoin is a dece...ple, using the alias [Satoshi Nakamoto](https://co'</example>
    subreddit TEXT NULL,
        -- <example>'bitcoin'</example>
    notice TEXT NULL,
        -- <example>'TIPS has undergone a [swap](https://bitcointalk.or...//coinmarketcap.com/currencies/fedora-gold) (FED).'</example>
    tags TEXT NULL,
        -- <example>'mineable, pow, sha-256, store-of-value, state-chan...apital-portfolio, boostvc-portfolio, cms-holdings-'</example>
    tag_names TEXT NULL,
        -- <example>'Mineable, PoW, SHA-256, Store of Value, State chan...apital Portfolio, BoostVC Portfolio, CMS Holdings '</example>
    website TEXT NULL,
        -- <example>'https://bitcoin.org/'</example>
    platform_id INTEGER NULL,
        -- <example>1027</example>
    date_added TEXT NULL,
        -- <example>'2013-04-28T00:00:00.000Z'</example>
    date_launched TEXT NULL
        -- <example>'2018-01-16T00:00:00.000Z'</example>
);

-- Table: historical (4441972 rows)
CREATE TABLE historical (
    date DATE NULL,
        -- <example>'2013-04-28'</example>
    coin_id INTEGER NULL,
        -- <example>1</example>
    cmc_rank INTEGER NULL,
        -- <example>1</example>
    market_cap REAL NULL,
        -- <example>1488566971.956</example>
    price REAL NULL,
        -- <example>134.210</example>
    open REAL NULL,
        -- <example>134.444</example>
    high REAL NULL,
        -- <example>147.488</example>
    low REAL NULL,
        -- <example>134.000</example>
    close REAL NULL,
        -- <example>144.540</example>
    time_high TEXT NULL,
        -- <example>'13:15:01'</example>
    time_low TEXT NULL,
        -- <example>'05:20:01'</example>
    volume_24h REAL NULL,
        -- <example>0.000</example>
    percent_change_1h REAL NULL,
        -- <example>0.639</example>
    percent_change_24h REAL NULL,
        -- <example>7.636</example>
    percent_change_7d REAL NULL,
        -- <example>-13.809</example>
    circulating_supply REAL NULL,
        -- <example>11091325.000</example>
    total_supply REAL NULL,
        -- <example>11091325.000</example>
    max_supply REAL NULL,
        -- <example>21000000.000</example>
    num_market_pairs INTEGER NULL
        -- <example>7050</example>
);
```