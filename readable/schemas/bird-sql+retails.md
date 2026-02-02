```sql
-- Database: retails

-- Table: customer (150000 rows)
CREATE TABLE customer (
    c_custkey INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    c_mktsegment TEXT NULL,
        -- <values>{'AUTOMOBILE', 'BUILDING', 'FURNITURE', 'HOUSEHOLD', 'MACHINERY'}</values>
    c_nationkey INTEGER NULL,
        -- <example>8</example>
        -- <fk> -> nation.n_nationkey</fk>
    c_name TEXT NULL,
        -- <example>'Customer#000000001'</example>
    c_address TEXT NULL,
        -- <example>'KwX3hMHjZ6'</example>
    c_phone TEXT NULL,
        -- <example>'937-241-3198'</example>
    c_acctbal REAL NULL,
        -- <example>3560.030</example>
    c_comment TEXT NULL,
        -- <example>'ironic excuses detect slyly silent requests. requests according to the exc'</example>
    FOREIGN KEY (c_nationkey) REFERENCES nation(n_nationkey)
);

-- Table: lineitem (4423659 rows)
CREATE TABLE lineitem (
    l_shipdate DATE NULL,
        -- <example>'1995-08-16'</example>
    l_orderkey INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> orders.o_orderkey</fk>
    l_discount REAL NOT NULL,
        -- <example>0.100</example>
    l_extendedprice REAL NOT NULL,
        -- <example>58303.080</example>
    l_suppkey INTEGER NOT NULL,
        -- <example>6296</example>
        -- <fk>composite</fk>
    l_quantity INTEGER NOT NULL,
        -- <example>33</example>
    l_returnflag TEXT NULL,
        -- <values>{'A', 'N', 'R'}</values>
    l_partkey INTEGER NOT NULL,
        -- <example>98768</example>
        -- <fk>composite</fk>
    l_linestatus TEXT NULL,
        -- <values>{'F', 'O'}</values>
    l_tax REAL NOT NULL,
        -- <example>0.060</example>
    l_commitdate DATE NULL,
        -- <example>'1995-07-12'</example>
    l_receiptdate DATE NULL,
        -- <example>'1995-09-14'</example>
    l_shipmode TEXT NULL,
        -- <values>{'AIR', 'FOB', 'MAIL', 'RAIL', 'REG AIR', 'SHIP', 'TRUCK'}</values>
    l_linenumber INTEGER NOT NULL,
        -- <example>1</example>
    l_shipinstruct TEXT NULL,
        -- <values>{'COLLECT COD', 'DELIVER IN PERSON', 'NONE', 'TAKE BACK RETURN'}</values>
    l_comment TEXT NULL,
        -- <example>'carefully bo'</example>
    PRIMARY KEY (l_orderkey, l_linenumber),
    FOREIGN KEY (l_orderkey) REFERENCES orders(o_orderkey),
    FOREIGN KEY (l_partkey, l_suppkey) REFERENCES partsupp(ps_partkey, ps_suppkey)
);

-- Table: nation (25 rows)
CREATE TABLE nation (
    n_nationkey INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    n_name TEXT NULL,
        -- <example>'ALGERIA'</example>
    n_regionkey INTEGER NULL,
        -- <example>0</example>
        -- <fk> -> region.r_regionkey</fk>
    n_comment TEXT NULL,
        -- <example>'slyly express pinto beans cajole idly. deposits us...hely unusual packages? fluffily final accounts x-r'</example>
    FOREIGN KEY (n_regionkey) REFERENCES region(r_regionkey)
);

-- Table: orders (1500000 rows)
CREATE TABLE orders (
    o_orderdate DATE NULL,
        -- <example>'1995-04-19'</example>
    o_orderkey INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    o_custkey INTEGER NOT NULL,
        -- <example>73100</example>
        -- <fk> -> customer.c_custkey</fk>
    o_orderpriority TEXT NULL,
        -- <values>{'1-URGENT', '2-HIGH', '3-MEDIUM', '4-NOT SPECIFIED', '5-LOW'}</values>
    o_shippriority INTEGER NULL,
        -- <example>0</example>
    o_clerk TEXT NULL,
        -- <example>'Clerk#000000916'</example>
    o_orderstatus TEXT NULL,
        -- <values>{'F', 'O', 'P'}</values>
    o_totalprice REAL NULL,
        -- <example>203198.560</example>
    o_comment TEXT NULL,
        -- <example>'final packages sleep blithely packa'</example>
    FOREIGN KEY (o_custkey) REFERENCES customer(c_custkey)
);

-- Table: part (200000 rows)
CREATE TABLE part (
    p_partkey INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    p_type TEXT NULL,
        -- <example>'LARGE PLATED TIN'</example>
    p_size INTEGER NULL,
        -- <example>31</example>
    p_brand TEXT NULL,
        -- <example>'Brand#43'</example>
    p_name TEXT NULL,
        -- <example>'burlywood plum powder puff mint'</example>
    p_container TEXT NULL,
        -- <example>'LG BAG'</example>
    p_mfgr TEXT NULL,
        -- <values>{'Manufacturer#1', 'Manufacturer#2', 'Manufacturer#3', 'Manufacturer#4', 'Manufacturer#5'}</values>
    p_retailprice REAL NULL,
        -- <example>901.000</example>
    p_comment TEXT NULL
        -- <example>'blithely busy reque'</example>
);

-- Table: partsupp (800000 rows)
CREATE TABLE partsupp (
    ps_partkey INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> part.p_partkey</fk>
    ps_suppkey INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> supplier.s_suppkey</fk>
    ps_supplycost REAL NOT NULL,
        -- <example>400.750</example>
    ps_availqty INTEGER NULL,
        -- <example>1111</example>
    ps_comment TEXT NULL,
        -- <example>'carefully ironic deposits use against the carefull... accounts. slyly silent platelets nag quickly even'</example>
    PRIMARY KEY (ps_partkey, ps_suppkey),
    FOREIGN KEY (ps_partkey) REFERENCES part(p_partkey),
    FOREIGN KEY (ps_suppkey) REFERENCES supplier(s_suppkey)
);

-- Table: region (5 rows)
CREATE TABLE region (
    r_regionkey INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    r_name TEXT NULL,
        -- <values>{'AFRICA', 'AMERICA', 'ASIA', 'EUROPE', 'MIDDLE EAST'}</values>
    r_comment TEXT NULL
        -- <values>{'accounts cajole carefully according to the carefully exp', 'asymptotes sublate after the r', 'furiously express accounts wake sly', 'requests affix quickly final tithes. blithely even packages above the a', 'slyly even theodolites are carefully ironic pinto beans. platelets above the unusual accounts aff'}</values>
);

-- Table: supplier (10000 rows)
CREATE TABLE supplier (
    s_suppkey INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    s_nationkey INTEGER NULL,
        -- <example>13</example>
        -- <fk> -> nation.n_nationkey</fk>
    s_comment TEXT NULL,
        -- <example>'blithely final pearls are. instructions thra'</example>
    s_name TEXT NULL,
        -- <example>'Supplier#000000001'</example>
    s_address TEXT NULL,
        -- <example>',wWs4pnykQOFl8mgVCU8EZMXqZs1w'</example>
    s_phone TEXT NULL,
        -- <example>'800-807-9579'</example>
    s_acctbal REAL NULL,
        -- <example>3082.860</example>
    FOREIGN KEY (s_nationkey) REFERENCES nation(n_nationkey)
);
```