```sql
-- Database: coinmarketcap

/*
Table: coins
Rows: 8927
Sample rows:
| id   | name      | slug      | symbol   | status   | category   | description                                                                                                                                                                                                 | subreddit   | notice   | tags                                                                                                                                                                                                        | tag_names                                                                                                                                                                                                  | website                   | platform_id   | date_added               | date_launched   |
|------|-----------|-----------|----------|----------|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|---------------|--------------------------|-----------------|
| 1    | Bitcoin   | bitcoin   | BTC      | active   | coin       | ## **What Is Bitcoin (BTC)?**\n\nBitcoin is a decentralized cryptocurrency originally described in a.../glossary/whitepaper) by a person, or group of people, using the alias [Satoshi Nakamoto](https://co | bitcoin     | [NULL]   | mineable, pow, sha-256, store-of-value, state-channels, coinbase-ventures-portfolio, three-arrows-ca...abs-portfolio, arrington-xrp-capital, blockchain-capital-portfolio, boostvc-portfolio, cms-holdings- | Mineable, PoW, SHA-256, Store of Value, State channels, Coinbase Ventures Portfolio, Three Arrows Ca...abs Portfolio, Arrington XRP capital, Blockchain Capital Portfolio, BoostVC Portfolio, CMS Holdings | https://bitcoin.org/      | [NULL]        | 2013-04-28T00:00:00.000Z | [NULL]          |
| 2    | Litecoin  | litecoin  | LTC      | active   | coin       | ## What Is Litecoin (LTC)?\n\nLitecoin (LTC) is a cryptocurrency that was designed to provide fast, ...roperties of [blockchain](https://coinmarketcap.com/alexandria/glossary/blockchain) technology. \n\n | litecoin    | [NULL]   | mineable, pow, scrypt, medium-of-exchange, binance-chain                                                                                                                                                    | Mineable, PoW, Scrypt, Medium of Exchange, Binance Chain                                                                                                                                                   | https://litecoin.org/     | [NULL]        | 2013-04-28T00:00:00.000Z | [NULL]          |
| 3    | Namecoin  | namecoin  | NMC      | active   | coin       | Namecoin (NMC) is a cryptocurrency . Users are able to generate NMC through the process of mining. N...own price of Namecoin is 2.14833562 USD and is up 0.40 over the last 24 hours. It is currently tradi | namecoin    | [NULL]   | mineable, pow, sha-256, platform                                                                                                                                                                            | Mineable, PoW, SHA-256, Platform                                                                                                                                                                           | https://www.namecoin.org/ | [NULL]        | 2013-04-28T00:00:00.000Z | [NULL]          |
| 4    | Terracoin | terracoin | TRC      | active   | coin       | Terracoin (TRC) launched in 2012 with the aim to create an easier to use replacement of fiat currenc...o empower the users of TRC decentralized governance and masternodes were added in 2017. Terracoin wa | terracoin   | [NULL]   | mineable, pow, sha-256, masternodes                                                                                                                                                                         | Mineable, PoW, SHA-256, Masternodes                                                                                                                                                                        | http://www.terracoin.io/  | [NULL]        | 2013-04-28T00:00:00.000Z | [NULL]          |
| 5    | Peercoin  | peercoin  | PPC      | active   | coin       | Peercoin (PPC) is a cryptocurrency . Users are able to generate PPC through the process of mining. P...e last known price of Peercoin is 1.07004915 USD and is down -1.70 over the last 24 hours. It is cur | peercoin    | [NULL]   | mineable, hybrid-pow-pos, sha-256, medium-of-exchange, payments                                                                                                                                             | Mineable, Hybrid - PoW & PoS, SHA-256, Medium of Exchange, Payments                                                                                                                                        | http://www.peercoin.net   | [NULL]        | 2013-04-28T00:00:00.000Z | [NULL]          |
| ...  | ...       | ...       | ...      | ...      | ...        | ...                                                                                                                                                                                                         | ...         | ...      | ...                                                                                                                                                                                                         | ...                                                                                                                                                                                                        | ...                       | ...           | ...                      | ...             |
*/
CREATE TABLE coins (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NOT NULL,
        -- <example>'Bitcoin'</example>
    slug TEXT NOT NULL,
        -- <example>'bitcoin'</example>
    symbol TEXT NOT NULL,
        -- <example>'BTC'</example>
    status TEXT NOT NULL,
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
    date_added TEXT NOT NULL,
        -- <example>'2013-04-28T00:00:00.000Z'</example>
    date_launched TEXT NULL
        -- <example>'2018-01-16T00:00:00.000Z'</example>
);

/*
Table: historical
Rows: 4441972
Sample rows:
| date       | coin_id   | cmc_rank   | market_cap         | price             | open   | high   | low    | close   | time_high   | time_low   | volume_24h   | percent_change_1h   | percent_change_24h   | percent_change_7d   | circulating_supply   | total_supply   | max_supply   | num_market_pairs   |
|------------|-----------|------------|--------------------|-------------------|--------|--------|--------|---------|-------------|------------|--------------|---------------------|----------------------|---------------------|----------------------|----------------|--------------|--------------------|
| 2013-04-28 | 1         | 1          | 1488566971.9558687 | 134.210021972656  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL]      | [NULL]     | 0.0          | 0.639231            | [NULL]               | [NULL]              | 11091325.0           | 11091325.0     | 21000000.0   | [NULL]             |
| 2013-04-28 | 2         | 2          | 74637021.56790735  | 4.34840488433838  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL]      | [NULL]     | 0.0          | 0.799273            | [NULL]               | [NULL]              | 17164230.0           | 17164230.0     | 84000000.0   | [NULL]             |
| 2013-04-28 | 5         | 3          | 7250186.647688276  | 0.386524856090546 | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL]      | [NULL]     | 0.0          | -0.934763           | [NULL]               | [NULL]              | 18757362.0           | 18757362.0     | [NULL]       | [NULL]             |
| 2013-04-28 | 3         | 4          | 5995997.185385211  | 1.10723268985748  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL]      | [NULL]     | 0.0          | -0.0505028          | [NULL]               | [NULL]              | 5415300.0            | 5415300.0      | [NULL]       | [NULL]             |
| 2013-04-28 | 4         | 5          | 1503099.4011388426 | 0.646892309188843 | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL]      | [NULL]     | 0.0          | 0.609159            | [NULL]               | [NULL]              | 2323569.75           | 2323569.75     | 42000000.0   | [NULL]             |
| ...        | ...       | ...        | ...                | ...               | ...    | ...    | ...    | ...     | ...         | ...        | ...          | ...                 | ...                  | ...                 | ...                  | ...            | ...          | ...                |
*/
CREATE TABLE historical (
    date DATE NOT NULL,
        -- <example>'2013-04-28'</example>
    coin_id INTEGER NOT NULL,
        -- <example>1</example>
    cmc_rank INTEGER NOT NULL,
        -- <example>1</example>
    market_cap REAL NULL,
        -- <example>1488566971.956</example>
    price REAL NOT NULL,
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
    volume_24h REAL NOT NULL,
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