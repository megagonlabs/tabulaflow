```sql
-- Database: retail_complains

-- Table: callcenterlogs (3999 rows)
CREATE TABLE callcenterlogs (
    "Date received" DATE NULL,
        -- <example>'2017-03-27'</example>
    "Complaint ID" TEXT NULL PRIMARY KEY,
        -- <example>'CR0000072'</example>
    "rand client" TEXT NULL,
        -- <example>'C00004587'</example>
        -- <fk> -> client.client_id</fk>
    phonefinal TEXT NULL,
        -- <example>'977-806-9726'</example>
    "vru+line" TEXT NULL,
        -- <example>'AA0103'</example>
    call_id INTEGER NULL,
        -- <example>34536</example>
    priority INTEGER NULL,
        -- <example>0</example>
    type TEXT NULL,
        -- <values>{'IN', 'NE', 'NW', 'PE', 'PS', 'TT'}</values>
    outcome TEXT NULL,
        -- <values>{'AGENT', 'HANG', 'PHANTOM'}</values>
    server TEXT NULL,
        -- <example>'MICHAL'</example>
    ser_start TEXT NULL,
        -- <example>'13:34:11'</example>
    ser_exit TEXT NULL,
        -- <example>'13:40:23'</example>
    ser_time TEXT NULL,
        -- <example>'00:06:12'</example>
    FOREIGN KEY ("rand client") REFERENCES client(client_id)
);

-- Table: client (5369 rows)
CREATE TABLE client (
    client_id TEXT NULL PRIMARY KEY,
        -- <example>'C00000001'</example>
    sex TEXT NULL,
        -- <values>{'Female', 'Male'}</values>
    day INTEGER NULL,
        -- <example>13</example>
    month INTEGER NULL,
        -- <example>12</example>
    year INTEGER NULL,
        -- <example>1990</example>
    age INTEGER NULL,
        -- <example>29</example>
    social TEXT NULL,
        -- <example>'926-93-2157'</example>
    first TEXT NULL,
        -- <example>'Emma'</example>
    middle TEXT NULL,
        -- <example>'Avaya'</example>
    last TEXT NULL,
        -- <example>'Smith'</example>
    phone TEXT NULL,
        -- <example>'367-171-6840'</example>
    email TEXT NULL,
        -- <example>'emma.smith@gmail.com'</example>
    address_1 TEXT NULL,
        -- <example>'387 Wellington Ave.'</example>
    address_2 TEXT NULL,
        -- <example>'Unit 1'</example>
    city TEXT NULL,
        -- <example>'Albuquerque'</example>
    state TEXT NULL,
        -- <example>'NM'</example>
    zipcode INTEGER NULL,
        -- <example>47246</example>
    district_id INTEGER NULL,
        -- <example>18</example>
        -- <fk> -> district.district_id</fk>
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

-- Table: district (77 rows)
CREATE TABLE district (
    district_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    city TEXT NULL,
        -- <example>'New York City'</example>
    state_abbrev TEXT NULL,
        -- <example>'NY'</example>
        -- <fk> -> state.StateCode</fk>
    division TEXT NULL,
        -- <values>{'East North Central', 'East South Central', 'Middle Atlantic', 'Mountain', 'New England', 'Pacific', 'South Atlantic', 'West North Central', 'West South Central'}</values>
    FOREIGN KEY (state_abbrev) REFERENCES state(StateCode)
);

-- Table: events (23419 rows)
CREATE TABLE events (
    "Date received" DATE NULL,
        -- <example>'2014-07-03'</example>
    Product TEXT NULL,
        -- <values>{'Bank account or service', 'Credit card'}</values>
    "Sub-product" TEXT NULL,
        -- <values>{'(CD) Certificate of deposit', 'Cashing a check without an account', 'Checking account', 'Other bank product/service', 'Savings account'}</values>
    Issue TEXT NULL,
        -- <example>'Deposits and withdrawals'</example>
    "Sub-issue" TEXT NULL,
    "Consumer complaint narrative" TEXT NULL,
        -- <example>'Deposited a XXXX check into my account, BOFA is te...e gas and I am XXXX miles from home in a new state'</example>
    Tags TEXT NULL,
        -- <values>{'Older American', 'Older American, Servicemember', 'Servicemember'}</values>
    "Consumer consent provided?" TEXT NULL,
        -- <values>{'Consent not provided', 'Consent provided', 'N/A', 'Other'}</values>
    "Submitted via" TEXT NULL,
        -- <values>{'Email', 'Fax', 'Phone', 'Postal mail', 'Referral', 'Web'}</values>
    "Date sent to company" TEXT NULL,
        -- <example>'2014-07-09'</example>
    "Company response to consumer" TEXT NULL,
        -- <values>{'Closed with explanation', 'Closed with monetary relief', 'Closed with non-monetary relief', 'Closed with relief', 'Closed without relief', 'Closed', 'In progress', 'Untimely response'}</values>
    "Timely response?" TEXT NULL,
        -- <values>{'No', 'Yes'}</values>
    "Consumer disputed?" TEXT NULL,
        -- <values>{'No', 'Yes'}</values>
    "Complaint ID" TEXT NULL,
        -- <example>'CR0000072'</example>
        -- <fk> -> callcenterlogs."Complaint ID"</fk>
    Client_ID TEXT NULL,
        -- <example>'C00003714'</example>
        -- <fk> -> client.client_id</fk>
    PRIMARY KEY ("Complaint ID", Client_ID),
    FOREIGN KEY ("Complaint ID") REFERENCES callcenterlogs("Complaint ID"),
    FOREIGN KEY (Client_ID) REFERENCES client(client_id)
);

-- Table: reviews (377 rows)
CREATE TABLE reviews (
    Date DATE NULL PRIMARY KEY,
        -- <example>'2013-02-04'</example>
    Stars INTEGER NULL,
        -- <example>5</example>
    Reviews TEXT NULL,
        -- <example>'Great job, Eagle National! Each person was profess...through our refinance process smoothly. Thank you!'</example>
    Product TEXT NULL,
        -- <values>{'Eagle Capital', 'Eagle National Bank', 'Eagle National Mortgage'}</values>
    district_id INTEGER NULL,
        -- <example>65</example>
        -- <fk> -> district.district_id</fk>
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

-- Table: state (48 rows)
CREATE TABLE state (
    StateCode TEXT NULL PRIMARY KEY,
        -- <example>'AL'</example>
    State TEXT NULL,
        -- <example>'Alabama'</example>
    Region TEXT NULL
        -- <values>{'Midwest', 'Northeast', 'South', 'West'}</values>
);
```