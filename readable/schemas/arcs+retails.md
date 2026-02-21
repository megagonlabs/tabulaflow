```sql
-- Database: retails

/*
Schema: NULL
Table: CUSTOMER
Rows: 150000
Sample rows:
| c_custkey   | c_mktsegment   | c_nationkey   | c_name             | c_address              | c_phone      | c_acctbal   | c_comment                                                                     |
|-------------|----------------|---------------|--------------------|------------------------|--------------|-------------|-------------------------------------------------------------------------------|
| 1           | BUILDING       | 8             | Customer#000000001 | KwX3hMHjZ6             | 937-241-3198 | 3560.03     | ironic excuses detect slyly silent requests. requests according to the exc    |
| 2           | MACHINERY      | 16            | Customer#000000002 | ioUn,eqTTXOdo          | 906-965-7556 | 7550.21     | final express accounts mold slyly. ironic accounts cajole! quickly express a  |
| 3           | FURNITURE      | 11            | Customer#000000003 | YddJqmIdouNT9Yj        | 328-750-7603 | -926.96     | carefully express foxes sleep carefully. pending platelets sleep thinly for t |
| 4           | FURNITURE      | 24            | Customer#000000004 | iE7PADWuxr4pR5f9ewKqg  | 127-505-7633 | -78.75      | silent packages sleep. even re                                                |
| 5           | MACHINERY      | 4             | Customer#000000005 | h3yhvBTVbF2IJPzTKLoUe4 | 322-864-6707 | 7741.9      | slyly special frays nag quietly bl                                            |
| ...         | ...            | ...           | ...                | ...                    | ...          | ...         | ...                                                                           |
*/
CREATE TABLE CUSTOMER (
    "C_CUSTKEY" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "C_MKTSEGMENT" TEXT NOT NULL,
        -- <values>{'AUTOMOBILE', 'BUILDING', 'FURNITURE', 'HOUSEHOLD', 'MACHINERY'}</values>
    "C_NATIONKEY" INTEGER NOT NULL,
        -- <example>8</example>
        -- <fk> -> NATION."N_NATIONKEY"</fk>
    "C_NAME" TEXT NOT NULL,
        -- <example>'Customer#000000001'</example>
    "C_ADDRESS" TEXT NOT NULL,
        -- <example>'KwX3hMHjZ6'</example>
    "C_PHONE" TEXT NOT NULL,
        -- <example>'937-241-3198'</example>
    "C_ACCTBAL" REAL NOT NULL,
        -- <example>3560.030</example>
    "C_COMMENT" TEXT NOT NULL,
        -- <example>'ironic excuses detect slyly silent requests. requests according to the exc'</example>
    FOREIGN KEY ("C_NATIONKEY") REFERENCES NATION("N_NATIONKEY")
);

/*
Schema: NULL
Table: LINEITEM
Rows: 4423659
Sample rows:
| l_shipdate   | l_orderkey   | l_discount   | l_extendedprice   | l_suppkey   | l_quantity   | l_returnflag   | l_partkey   | l_linestatus   | l_tax   | l_commitdate   | l_receiptdate   | l_shipmode   | l_linenumber   | l_shipinstruct    | l_comment                             |
|--------------|--------------|--------------|-------------------|-------------|--------------|----------------|-------------|----------------|---------|----------------|-----------------|--------------|----------------|-------------------|---------------------------------------|
| 1995-08-16   | 1            | 0.1          | 58303.08          | 6296        | 33           | N              | 98768       | O              | 0.06    | 1995-07-12     | 1995-09-14      | RAIL         | 1              | NONE              | carefully bo                          |
| 1995-08-13   | 1            | 0.09         | 16947.7           | 8776        | 10           | N              | 23771       | O              | 0.08    | 1995-07-09     | 1995-08-27      | TRUCK        | 2              | TAKE BACK RETURN  | blithely regular pac                  |
| 1995-06-17   | 1            | 0.1          | 63642.9           | 3859        | 34           | N              | 113858      | O              | 0.08    | 1995-05-22     | 1995-06-30      | SHIP         | 3              | COLLECT COD       | ironic accounts sleep furiously silen |
| 1995-07-16   | 1            | 0.02         | 22521.96          | 7225        | 18           | N              | 127224      | O              | 0.07    | 1995-06-28     | 1995-07-18      | MAIL         | 4              | DELIVER IN PERSON | idly even platelets acr               |
| 1995-04-29   | 1            | 0.08         | 4081.08           | 5890        | 3            | A              | 98362       | F              | 0.02    | 1995-06-27     | 1995-05-19      | AIR          | 5              | NONE              | unusual speci                         |
| ...          | ...          | ...          | ...               | ...         | ...          | ...            | ...         | ...            | ...     | ...            | ...             | ...          | ...            | ...               | ...                                   |
*/
CREATE TABLE LINEITEM (
    "L_SHIPDATE" DATE NOT NULL,
        -- <example>'1995-08-16'</example>
    "L_ORDERKEY" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ORDERS."O_ORDERKEY"</fk>
    "L_DISCOUNT" REAL NOT NULL,
        -- <example>0.100</example>
    "L_EXTENDEDPRICE" REAL NOT NULL,
        -- <example>58303.080</example>
    "L_SUPPKEY" INTEGER NOT NULL,
        -- <example>6296</example>
        -- <fk>composite</fk>
    "L_QUANTITY" INTEGER NOT NULL,
        -- <example>33</example>
    "L_RETURNFLAG" TEXT NOT NULL,
        -- <values>{'A', 'N', 'R'}</values>
    "L_PARTKEY" INTEGER NOT NULL,
        -- <example>98768</example>
        -- <fk>composite</fk>
    "L_LINESTATUS" TEXT NOT NULL,
        -- <values>{'F', 'O'}</values>
    "L_TAX" REAL NOT NULL,
        -- <example>0.060</example>
    "L_COMMITDATE" DATE NOT NULL,
        -- <example>'1995-07-12'</example>
    "L_RECEIPTDATE" DATE NOT NULL,
        -- <example>'1995-09-14'</example>
    "L_SHIPMODE" TEXT NOT NULL,
        -- <values>{'AIR', 'FOB', 'MAIL', 'RAIL', 'REG AIR', 'SHIP', 'TRUCK'}</values>
    "L_LINENUMBER" INTEGER NOT NULL,
        -- <example>1</example>
    "L_SHIPINSTRUCT" TEXT NOT NULL,
        -- <values>{'COLLECT COD', 'DELIVER IN PERSON', 'NONE', 'TAKE BACK RETURN'}</values>
    "L_COMMENT" TEXT NOT NULL,
        -- <example>'carefully bo'</example>
    PRIMARY KEY ("L_ORDERKEY", "L_LINENUMBER"),
    FOREIGN KEY ("L_ORDERKEY") REFERENCES ORDERS("O_ORDERKEY"),
    FOREIGN KEY ("L_PARTKEY", "L_SUPPKEY") REFERENCES PARTSUPP("PS_PARTKEY", "PS_SUPPKEY")
);

/*
Schema: NULL
Table: NATION
Rows: 25
Sample rows:
| n_nationkey   | n_name    | n_regionkey   | n_comment                                                                                                        |
|---------------|-----------|---------------|------------------------------------------------------------------------------------------------------------------|
| 0             | ALGERIA   | 0             | slyly express pinto beans cajole idly. deposits use blithely unusual packages? fluffily final accounts x-r       |
| 1             | ARGENTINA | 1             | instructions detect blithely stealthily pending packages                                                         |
| 2             | BRAZIL    | 1             | blithely unusual deposits are quickly--                                                                          |
| 3             | CANADA    | 1             | carefully pending packages haggle blithely. blithely final pinto beans sleep quickly even accounts? depths aroun |
| 4             | EGYPT     | 0             | slyly express deposits haggle furiously. slyly final platelets nag c                                             |
| ...           | ...       | ...           | ...                                                                                                              |
*/
CREATE TABLE NATION (
    "N_NATIONKEY" INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    "N_NAME" TEXT NOT NULL,
        -- <example>'ALGERIA'</example>
    "N_REGIONKEY" INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> REGION."R_REGIONKEY"</fk>
    "N_COMMENT" TEXT NOT NULL,
        -- <example>'slyly express pinto beans cajole idly. deposits us...hely unusual packages? fluffily final accounts x-r'</example>
    FOREIGN KEY ("N_REGIONKEY") REFERENCES REGION("R_REGIONKEY")
);

/*
Schema: NULL
Table: ORDERS
Rows: 1500000
Sample rows:
| o_orderdate   | o_orderkey   | o_custkey   | o_orderpriority   | o_shippriority   | o_clerk         | o_orderstatus   | o_totalprice   | o_comment                                                           |
|---------------|--------------|-------------|-------------------|------------------|-----------------|-----------------|----------------|---------------------------------------------------------------------|
| 1995-04-19    | 1            | 73100       | 4-NOT SPECIFIED   | 0                | Clerk#000000916 | P               | 203198.56      | final packages sleep blithely packa                                 |
| 1996-11-04    | 2            | 92861       | 1-URGENT          | 0                | Clerk#000000373 | O               | 317719.99      | final excuses about the ironic even deposits detect express request |
| 1992-02-15    | 3            | 44875       | 1-URGENT          | 0                | Clerk#000000485 | F               | 146674.98      | final final deposits cajole foxes. blithely pendin                  |
| 1997-07-03    | 4            | 72076       | 4-NOT SPECIFIED   | 0                | Clerk#000000426 | O               | 317595.77      | deposits hang slyly across the en                                   |
| 1994-01-03    | 5            | 93697       | 5-LOW             | 0                | Clerk#000000944 | F               | 191918.92      | slowly even requests detect fluffily alongs                         |
| ...           | ...          | ...         | ...               | ...              | ...             | ...             | ...            | ...                                                                 |
*/
CREATE TABLE ORDERS (
    "O_ORDERDATE" DATE NOT NULL,
        -- <example>'1995-04-19'</example>
    "O_ORDERKEY" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "O_CUSTKEY" INTEGER NOT NULL,
        -- <example>73100</example>
        -- <fk> -> CUSTOMER."C_CUSTKEY"</fk>
    "O_ORDERPRIORITY" TEXT NOT NULL,
        -- <values>{'1-URGENT', '2-HIGH', '3-MEDIUM', '4-NOT SPECIFIED', '5-LOW'}</values>
    "O_SHIPPRIORITY" INTEGER NOT NULL,
        -- <example>0</example>
    "O_CLERK" TEXT NOT NULL,
        -- <example>'Clerk#000000916'</example>
    "O_ORDERSTATUS" TEXT NOT NULL,
        -- <values>{'F', 'O', 'P'}</values>
    "O_TOTALPRICE" REAL NOT NULL,
        -- <example>203198.560</example>
    "O_COMMENT" TEXT NOT NULL,
        -- <example>'final packages sleep blithely packa'</example>
    FOREIGN KEY ("O_CUSTKEY") REFERENCES CUSTOMER("C_CUSTKEY")
);

/*
Schema: NULL
Table: PART
Rows: 200000
Sample rows:
| p_partkey   | p_type                   | p_size   | p_brand   | p_name                             | p_container   | p_mfgr         | p_retailprice   | p_comment              |
|-------------|--------------------------|----------|-----------|------------------------------------|---------------|----------------|-----------------|------------------------|
| 1           | LARGE PLATED TIN         | 31       | Brand#43  | burlywood plum powder puff mint    | LG BAG        | Manufacturer#4 | 901.0           | blithely busy reque    |
| 2           | LARGE POLISHED STEEL     | 4        | Brand#55  | hot spring dodger dim light        | LG CASE       | Manufacturer#5 | 902.0           | even ironic requests s |
| 3           | STANDARD PLATED COPPER   | 30       | Brand#53  | dark slate grey steel misty        | WRAP CASE     | Manufacturer#5 | 903.0           | slyly ironic fox       |
| 4           | STANDARD BURNISHED BRASS | 3        | Brand#13  | cream turquoise dark thistle light | LG PKG        | Manufacturer#1 | 904.0           | even silent pla        |
| 5           | ECONOMY BRUSHED BRASS    | 7        | Brand#14  | drab papaya lemon orange yellow    | MED PACK      | Manufacturer#1 | 905.0           | regular accounts       |
| ...         | ...                      | ...      | ...       | ...                                | ...           | ...            | ...             | ...                    |
*/
CREATE TABLE PART (
    "P_PARTKEY" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "P_TYPE" TEXT NOT NULL,
        -- <example>'LARGE PLATED TIN'</example>
    "P_SIZE" INTEGER NOT NULL,
        -- <example>31</example>
    "P_BRAND" TEXT NOT NULL,
        -- <example>'Brand#43'</example>
    "P_NAME" TEXT NOT NULL,
        -- <example>'burlywood plum powder puff mint'</example>
    "P_CONTAINER" TEXT NOT NULL,
        -- <example>'LG BAG'</example>
    "P_MFGR" TEXT NOT NULL,
        -- <values>{'Manufacturer#1', 'Manufacturer#2', 'Manufacturer#3', 'Manufacturer#4', 'Manufacturer#5'}</values>
    "P_RETAILPRICE" REAL NOT NULL,
        -- <example>901.000</example>
    "P_COMMENT" TEXT NOT NULL
        -- <example>'blithely busy reque'</example>
);

/*
Schema: NULL
Table: PARTSUPP
Rows: 800000
Sample rows:
| ps_partkey   | ps_suppkey   | ps_supplycost   | ps_availqty   | ps_comment                                                                                                                                                            |
|--------------|--------------|-----------------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1            | 2            | 400.75          | 1111          | carefully ironic deposits use against the carefully unusual accounts. slyly silent platelets nag quickly even                                                         |
| 1            | 2502         | 702.61          | 3999          | slyly regular accounts serve carefully. asymptotes after the slyly even instructions cajole quickly ironic requests. pending dugouts about the slyly                  |
| 1            | 5002         | 383.95          | 7411          | carefully special ideas are slyly. slyly ironic epitaphs use pending pending foxes. furiously express pinto beans lose quiet even requests: special final packages ar |
| 1            | 7502         | 682.18          | 5795          | deposits along the ironic pinto beans boost fluffily even                                                                                                             |
| 2            | 3            | 42.67           | 4360          | regular pending foxes affix carefully furiously pending no                                                                                                            |
| ...          | ...          | ...             | ...           | ...                                                                                                                                                                   |
*/
CREATE TABLE PARTSUPP (
    "PS_PARTKEY" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> PART."P_PARTKEY"</fk>
    "PS_SUPPKEY" INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> SUPPLIER."S_SUPPKEY"</fk>
    "PS_SUPPLYCOST" REAL NOT NULL,
        -- <example>400.750</example>
    "PS_AVAILQTY" INTEGER NOT NULL,
        -- <example>1111</example>
    "PS_COMMENT" TEXT NOT NULL,
        -- <example>'carefully ironic deposits use against the carefull... accounts. slyly silent platelets nag quickly even'</example>
    PRIMARY KEY ("PS_PARTKEY", "PS_SUPPKEY"),
    FOREIGN KEY ("PS_PARTKEY") REFERENCES PART("P_PARTKEY"),
    FOREIGN KEY ("PS_SUPPKEY") REFERENCES SUPPLIER("S_SUPPKEY")
);

/*
Schema: NULL
Table: REGION
Rows: 5
All rows:
|   r_regionkey | r_name      | r_comment                                                                                         |
|---------------|-------------|---------------------------------------------------------------------------------------------------|
|             0 | AFRICA      | asymptotes sublate after the r                                                                    |
|             1 | AMERICA     | requests affix quickly final tithes. blithely even packages above the a                           |
|             2 | ASIA        | accounts cajole carefully according to the carefully exp                                          |
|             3 | EUROPE      | slyly even theodolites are carefully ironic pinto beans. platelets above the unusual accounts aff |
|             4 | MIDDLE EAST | furiously express accounts wake sly                                                               |
*/
CREATE TABLE REGION (
    "R_REGIONKEY" INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    "R_NAME" TEXT NOT NULL,
        -- <values>{'AFRICA', 'AMERICA', 'ASIA', 'EUROPE', 'MIDDLE EAST'}</values>
    "R_COMMENT" TEXT NOT NULL
        -- <values>{'accounts cajole carefully according to the carefully exp', 'asymptotes sublate after the r', 'furiously express accounts wake sly', 'requests affix quickly final tithes. blithely even packages above the a', 'slyly even theodolites are carefully ironic pinto beans. platelets above the unusual accounts aff'}</values>
);

/*
Schema: NULL
Table: SUPPLIER
Rows: 10000
Sample rows:
| s_suppkey   | s_nationkey   | s_comment                                                                          | s_name             | s_address                       | s_phone      | s_acctbal   |
|-------------|---------------|------------------------------------------------------------------------------------|--------------------|---------------------------------|--------------|-------------|
| 1           | 13            | blithely final pearls are. instructions thra                                       | Supplier#000000001 | ,wWs4pnykQOFl8mgVCU8EZMXqZs1w   | 800-807-9579 | 3082.86     |
| 2           | 5             | requests integrate fluffily. fluffily ironic deposits wake. bold                   | Supplier#000000002 | WkXT6MSAJrp4qWq3W9N             | 348-617-6055 | 3009.73     |
| 3           | 22            | carefully express ideas shall have to unwin                                        | Supplier#000000003 | KjUqa42JEHaRDVQTHV6Yq2h         | 471-986-9888 | 9159.78     |
| 4           | 22            | quickly ironic instructions snooze? express deposits are furiously along the slyly | Supplier#000000004 | dxp8WejdtFKFPKa Q7Emf0RjnKx3gR3 | 893-133-4384 | 9846.01     |
| 5           | 9             | regular requests haggle. final deposits according to the                           | Supplier#000000005 | W9VO4vl4dfoDYZ RhawP8xLoc       | 752-877-4449 | -74.94      |
| ...         | ...           | ...                                                                                | ...                | ...                             | ...          | ...         |
*/
CREATE TABLE SUPPLIER (
    "S_SUPPKEY" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "S_NATIONKEY" INTEGER NOT NULL,
        -- <example>13</example>
        -- <fk> -> NATION."N_NATIONKEY"</fk>
    "S_COMMENT" TEXT NOT NULL,
        -- <example>'blithely final pearls are. instructions thra'</example>
    "S_NAME" TEXT NOT NULL,
        -- <example>'Supplier#000000001'</example>
    "S_ADDRESS" TEXT NOT NULL,
        -- <example>',wWs4pnykQOFl8mgVCU8EZMXqZs1w'</example>
    "S_PHONE" TEXT NOT NULL,
        -- <example>'800-807-9579'</example>
    "S_ACCTBAL" REAL NOT NULL,
        -- <example>3082.860</example>
    FOREIGN KEY ("S_NATIONKEY") REFERENCES NATION("N_NATIONKEY")
);
```