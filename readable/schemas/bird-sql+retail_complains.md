```sql
-- Database: retail_complains

-- Table: callcenterlogs (3999 rows)
CREATE TABLE callcenterlogs (
    "Date received" DATE,  -- e.g. '2017-03-27'
    "Complaint ID" TEXT PRIMARY KEY,  -- e.g. 'CR0000072'
    "rand client" TEXT,  -- e.g. 'C00004587'; FK -> client.client_id
    phonefinal TEXT,  -- e.g. '977-806-9726'
    "vru+line" TEXT,  -- e.g. 'AA0103'
    call_id INTEGER,  -- e.g. 34536
    priority INTEGER,  -- e.g. 0
    type TEXT,  -- values: {'IN', 'NE', 'NW', 'PE', 'PS', 'TT'}
    outcome TEXT,  -- values: {'AGENT', 'HANG', 'PHANTOM'}
    server TEXT,  -- e.g. 'MICHAL'
    ser_start TEXT,  -- e.g. '13:34:11'
    ser_exit TEXT,  -- e.g. '13:40:23'
    ser_time TEXT,  -- e.g. '00:06:12'
    FOREIGN KEY ("rand client") REFERENCES client(client_id)
);

-- Table: client (5369 rows)
CREATE TABLE client (
    client_id TEXT PRIMARY KEY,  -- e.g. 'C00000001'
    sex TEXT,  -- values: {'Female', 'Male'}
    day INTEGER,  -- e.g. 13
    month INTEGER,  -- e.g. 12
    year INTEGER,  -- e.g. 1990
    age INTEGER,  -- e.g. 29
    social TEXT,  -- e.g. '926-93-2157'
    first TEXT,  -- e.g. 'Emma'
    middle TEXT,  -- e.g. 'Avaya'
    last TEXT,  -- e.g. 'Smith'
    phone TEXT,  -- e.g. '367-171-6840'
    email TEXT,  -- e.g. 'emma.smith@gmail.com'
    address_1 TEXT,  -- e.g. '387 Wellington Ave.'
    address_2 TEXT,  -- e.g. 'Unit 1'
    city TEXT,  -- e.g. 'Albuquerque'
    state TEXT,  -- e.g. 'NM'
    zipcode INTEGER,  -- e.g. 47246
    district_id INTEGER,  -- e.g. 18; FK -> district.district_id
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

-- Table: district (77 rows)
CREATE TABLE district (
    district_id INTEGER PRIMARY KEY,  -- e.g. 1
    city TEXT,  -- e.g. 'New York City'
    state_abbrev TEXT,  -- e.g. 'NY'; FK -> state.StateCode
    division TEXT,  -- values: {'East North Central', 'East South Central', 'Middle Atlantic', 'Mountain', 'New England', 'Pacific', 'South Atlantic', 'West North Central', 'West South Central'}
    FOREIGN KEY (state_abbrev) REFERENCES state(StateCode)
);

-- Table: events (23419 rows)
CREATE TABLE events (
    "Date received" DATE,  -- e.g. '2014-07-03'
    Product TEXT,  -- values: {'Bank account or service', 'Credit card'}
    "Sub-product" TEXT,  -- values: {'(CD) Certificate of deposit', 'Cashing a check without an account', 'Checking account', 'Other bank product/service', 'Savings account'}
    Issue TEXT,  -- e.g. 'Deposits and withdrawals'
    "Sub-issue" TEXT,
    "Consumer complaint narrative" TEXT,  -- e.g. 'Deposited a XXXX check into my account, BOFA is te...e gas and I am XXXX miles from home in a new state'
    Tags TEXT,  -- values: {'Older American', 'Older American, Servicemember', 'Servicemember'}
    "Consumer consent provided?" TEXT,  -- values: {'Consent not provided', 'Consent provided', 'N/A', 'Other'}
    "Submitted via" TEXT,  -- values: {'Email', 'Fax', 'Phone', 'Postal mail', 'Referral', 'Web'}
    "Date sent to company" TEXT,  -- e.g. '2014-07-09'
    "Company response to consumer" TEXT,  -- values: {'Closed with explanation', 'Closed with monetary relief', 'Closed with non-monetary relief', 'Closed with relief', 'Closed without relief', 'Closed', 'In progress', 'Untimely response'}
    "Timely response?" TEXT,  -- values: {'No', 'Yes'}
    "Consumer disputed?" TEXT,  -- values: {'No', 'Yes'}
    "Complaint ID" TEXT,  -- e.g. 'CR0000072'; FK -> callcenterlogs."Complaint ID"
    Client_ID TEXT,  -- e.g. 'C00003714'; FK -> client.client_id
    PRIMARY KEY ("Complaint ID", Client_ID),
    FOREIGN KEY ("Complaint ID") REFERENCES callcenterlogs("Complaint ID"),
    FOREIGN KEY (Client_ID) REFERENCES client(client_id)
);

-- Table: reviews (377 rows)
CREATE TABLE reviews (
    Date DATE PRIMARY KEY,  -- e.g. '2013-02-04'
    Stars INTEGER,  -- e.g. 5
    Reviews TEXT,  -- e.g. 'Great job, Eagle National! Each person was profess...through our refinance process smoothly. Thank you!'
    Product TEXT,  -- values: {'Eagle Capital', 'Eagle National Bank', 'Eagle National Mortgage'}
    district_id INTEGER,  -- e.g. 65; FK -> district.district_id
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

-- Table: state (48 rows)
CREATE TABLE state (
    StateCode TEXT PRIMARY KEY,  -- e.g. 'AL'
    State TEXT,  -- e.g. 'Alabama'
    Region TEXT  -- values: {'Midwest', 'Northeast', 'South', 'West'}
);
```