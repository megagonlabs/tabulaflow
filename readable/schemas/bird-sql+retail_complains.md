```sql
-- Database: retail_complains

/*
Schema: NULLTable: callcenterlogs
Rows: 3999
Sample rows:
| Date received   | Complaint ID   | rand client   | phonefinal   | vru+line   | call_id   | priority   | type   | outcome   | server   | ser_start   | ser_exit   | ser_time   |
|-----------------|----------------|---------------|--------------|------------|-----------|------------|--------|-----------|----------|-------------|------------|------------|
| 2017-03-27      | CR2406263      | C00004587     | 977-806-9726 | AA0103     | 34536     | 0          | NW     | AGENT     | MICHAL   | 13:34:11    | 13:40:23   | 00:06:12   |
| 2017-03-27      | CR2405641      | C00003328     | 322-598-7152 | AA0205     | 34537     | 0          | PS     | AGENT     | TOVA     | 10:58:22    | 11:16:10   | 00:17:48   |
| 2017-03-27      | CR2405629      | C00001685     | 508-311-5237 | AA0110     | 34538     | 2          | PS     | AGENT     | YIFAT    | 13:00:54    | 13:13:31   | 00:12:37   |
| 2017-03-23      | CR2400594      | C00001945     | 265-394-2727 | AA0113     | 34540     | 2          | PS     | AGENT     | AVNI     | 16:18:21    | 16:19:40   | 00:01:19   |
| 2017-03-22      | CR2399607      | C00004303     | 206-008-0460 | AA0102     | 34541     | 1          | PS     | AGENT     | STEREN   | 14:48:22    | 14:55:19   | 00:06:57   |
| ...             | ...            | ...           | ...          | ...        | ...       | ...        | ...    | ...       | ...      | ...         | ...        | ...        |
*/
CREATE TABLE callcenterlogs (
    "Date received" DATE NOT NULL,
        -- <example>'2017-03-27'</example>
    "Complaint ID" TEXT NULL PRIMARY KEY,
        -- <example>'CR0000072'</example>
    "rand client" TEXT NULL,
        -- <example>'C00004587'</example>
        -- <fk> -> client.client_id</fk>
    phonefinal TEXT NOT NULL,
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
    ser_start TEXT NOT NULL,
        -- <example>'13:34:11'</example>
    ser_exit TEXT NOT NULL,
        -- <example>'13:40:23'</example>
    ser_time TEXT NOT NULL,
        -- <example>'00:06:12'</example>
    FOREIGN KEY ("rand client") REFERENCES client(client_id)
);

/*
Schema: NULLTable: client
Rows: 5369
Sample rows:
| client_id   | sex    | day   | month   | year   | age   | social      | first   | middle     | last     | phone        | email                      | address_1              | address_2   | city          | state   | zipcode   | district_id   |
|-------------|--------|-------|---------|--------|-------|-------------|---------|------------|----------|--------------|----------------------------|------------------------|-------------|---------------|---------|-----------|---------------|
| C00000001   | Female | 13    | 12      | 1990   | 29    | 926-93-2157 | Emma    | Avaya      | Smith    | 367-171-6840 | emma.smith@gmail.com       | 387 Wellington Ave.    | Unit 1      | Albuquerque   | NM      | 47246     | 18            |
| C00000002   | Male   | 4     | 2       | 1965   | 54    | 806-94-5725 | Noah    | Everest    | Thompson | 212-423-7734 | noah.thompson@gmail.com    | 75 W. Berkshire St.    | [NULL]      | New York City | NY      | 10040     | 1             |
| C00000003   | Female | 9     | 10      | 1960   | 59    | 614-70-9100 | Olivia  | Brooklynne | Johnson  | 212-425-6932 | olivia.johnson@outlook.com | 36 Second St.          | [NULL]      | New York City | NY      | 10162     | 1             |
| C00000004   | Male   | 1     | 12      | 1976   | 43    | 580-20-3414 | Liam    | Irvin      | White    | 951-567-8925 | liam.white@gmail.com       | 7607 Sunnyslope Street | [NULL]      | Indianapolis  | IN      | 49047     | 5             |
| C00000005   | Female | 3     | 7       | 1980   | 39    | 536-14-5809 | Sophia  | Danae      | Williams | 428-265-1568 | sophia.williams@gmail.com  | 755 Galvin Street      | [NULL]      | Indianapolis  | IN      | 40852     | 5             |
| ...         | ...    | ...   | ...     | ...    | ...   | ...         | ...     | ...        | ...      | ...          | ...                        | ...                    | ...         | ...           | ...     | ...       | ...           |
*/
CREATE TABLE client (
    client_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'C00000001'</example>
    sex TEXT NOT NULL,
        -- <values>{'Female', 'Male'}</values>
    day INTEGER NOT NULL,
        -- <example>13</example>
    month INTEGER NOT NULL,
        -- <example>12</example>
    year INTEGER NOT NULL,
        -- <example>1990</example>
    age INTEGER NOT NULL,
        -- <example>29</example>
    social TEXT NOT NULL,
        -- <example>'926-93-2157'</example>
    first TEXT NOT NULL,
        -- <example>'Emma'</example>
    middle TEXT NOT NULL,
        -- <example>'Avaya'</example>
    last TEXT NOT NULL,
        -- <example>'Smith'</example>
    phone TEXT NOT NULL,
        -- <example>'367-171-6840'</example>
    email TEXT NOT NULL,
        -- <example>'emma.smith@gmail.com'</example>
    address_1 TEXT NOT NULL,
        -- <example>'387 Wellington Ave.'</example>
    address_2 TEXT NULL,
        -- <example>'Unit 1'</example>
    city TEXT NOT NULL,
        -- <example>'Albuquerque'</example>
    state TEXT NOT NULL,
        -- <example>'NM'</example>
    zipcode INTEGER NOT NULL,
        -- <example>47246</example>
    district_id INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> district.district_id</fk>
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

/*
Schema: NULLTable: district
Rows: 77
Sample rows:
| district_id   | city          | state_abbrev   | division           |
|---------------|---------------|----------------|--------------------|
| 1             | New York City | NY             | Middle Atlantic    |
| 2             | Jacksonville  | FL             | South Atlantic     |
| 3             | Columbus      | OH             | East North Central |
| 4             | Charlotte     | NC             | South Atlantic     |
| 5             | Indianapolis  | IN             | East North Central |
| ...           | ...           | ...            | ...                |
*/
CREATE TABLE district (
    district_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    city TEXT NOT NULL,
        -- <example>'New York City'</example>
    state_abbrev TEXT NOT NULL,
        -- <example>'NY'</example>
        -- <fk> -> state.StateCode</fk>
    division TEXT NOT NULL,
        -- <values>{'East North Central', 'East South Central', 'Middle Atlantic', 'Mountain', 'New England', 'Pacific', 'South Atlantic', 'West North Central', 'West South Central'}</values>
    FOREIGN KEY (state_abbrev) REFERENCES state(StateCode)
);

/*
Schema: NULLTable: events
Rows: 23419
Sample rows:
| Date received   | Product                 | Sub-product      | Issue                                   | Sub-issue   | Consumer complaint narrative   | Tags   | Consumer consent provided?   | Submitted via   | Date sent to company   | Company response to consumer   | Timely response?   | Consumer disputed?   | Complaint ID   | Client_ID   |
|-----------------|-------------------------|------------------|-----------------------------------------|-------------|--------------------------------|--------|------------------------------|-----------------|------------------------|--------------------------------|--------------------|----------------------|----------------|-------------|
| 2014-07-03      | Bank account or service | Checking account | Deposits and withdrawals                | [NULL]      | [NULL]                         | [NULL] | N/A                          | Email           | 2014-07-09             | Closed with explanation        | Yes                | No                   | CR0922485      | C00001925   |
| 2012-04-12      | Bank account or service | Savings account  | Account opening, closing, or management | [NULL]      | [NULL]                         | [NULL] | N/A                          | Email           | 2012-04-13             | Closed with relief             | Yes                | No                   | CR0057298      | C00003141   |
| 2012-04-03      | Bank account or service | Checking account | Account opening, closing, or management | [NULL]      | [NULL]                         | [NULL] | N/A                          | Email           | 2012-04-03             | Closed without relief          | Yes                | No                   | CR0043811      | C00000297   |
| 2012-03-14      | Credit card             | [NULL]           | Billing disputes                        | [NULL]      | [NULL]                         | [NULL] | N/A                          | Email           | 2012-03-14             | Closed with relief             | Yes                | No                   | CR0035411      | C00004275   |
| 2012-03-05      | Bank account or service | Checking account | Account opening, closing, or management | [NULL]      | [NULL]                         | [NULL] | N/A                          | Email           | 2012-03-06             | Closed with relief             | Yes                | No                   | CR0030939      | C00000900   |
| ...             | ...                     | ...              | ...                                     | ...         | ...                            | ...    | ...                          | ...             | ...                    | ...                            | ...                | ...                  | ...            | ...         |
*/
CREATE TABLE events (
    "Date received" DATE NOT NULL,
        -- <example>'2014-07-03'</example>
    Product TEXT NOT NULL,
        -- <values>{'Bank account or service', 'Credit card'}</values>
    "Sub-product" TEXT NULL,
        -- <values>{'(CD) Certificate of deposit', 'Cashing a check without an account', 'Checking account', 'Other bank product/service', 'Savings account'}</values>
    Issue TEXT NOT NULL,
        -- <example>'Deposits and withdrawals'</example>
    "Sub-issue" TEXT NULL,
    "Consumer complaint narrative" TEXT NULL,
        -- <example>'Deposited a XXXX check into my account, BOFA is te...e gas and I am XXXX miles from home in a new state'</example>
    Tags TEXT NULL,
        -- <values>{'Older American', 'Older American, Servicemember', 'Servicemember'}</values>
    "Consumer consent provided?" TEXT NULL,
        -- <values>{'Consent not provided', 'Consent provided', 'N/A', 'Other'}</values>
    "Submitted via" TEXT NOT NULL,
        -- <values>{'Email', 'Fax', 'Phone', 'Postal mail', 'Referral', 'Web'}</values>
    "Date sent to company" TEXT NOT NULL,
        -- <example>'2014-07-09'</example>
    "Company response to consumer" TEXT NOT NULL,
        -- <values>{'Closed with explanation', 'Closed with monetary relief', 'Closed with non-monetary relief', 'Closed with relief', 'Closed without relief', 'Closed', 'In progress', 'Untimely response'}</values>
    "Timely response?" TEXT NOT NULL,
        -- <values>{'No', 'Yes'}</values>
    "Consumer disputed?" TEXT NULL,
        -- <values>{'No', 'Yes'}</values>
    "Complaint ID" TEXT NOT NULL,
        -- <example>'CR0000072'</example>
        -- <fk> -> callcenterlogs."Complaint ID"</fk>
    Client_ID TEXT NOT NULL,
        -- <example>'C00003714'</example>
        -- <fk> -> client.client_id</fk>
    PRIMARY KEY ("Complaint ID", Client_ID),
    FOREIGN KEY ("Complaint ID") REFERENCES callcenterlogs("Complaint ID"),
    FOREIGN KEY (Client_ID) REFERENCES client(client_id)
);

/*
Schema: NULLTable: reviews
Rows: 377
Sample rows:
| Date       | Stars   | Reviews                                                                                                                                                                                                     | Product                 | district_id   |
|------------|---------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------|---------------|
| 2017-10-04 | 5       | Great job, Eagle National! Each person was professional and helped us move through our refinance process smoothly. Thank you!                                                                               | Eagle National Mortgage | 65            |
| 2017-10-02 | 5       | Matthew Richardson is professional and helpful. He helped us find the correct product for our mortgage. Thank you very much for the excellent service, Matthew!                                             | Eagle National Mortgage | 66            |
| 2017-08-21 | 5       | We had a past experience with Eagle National Mortgage and would without question use again and again...mka and the Eagle National Mortgage team for your mortgage needs. Sincerest thanks Eagle!! Ed & Lind | Eagle National Mortgage | 23            |
| 2017-12-17 | 5       | We have been dealing with Brad Thomka from the beginning of what started out to be a very stressful ...he Eagle National Mortgage team for your mortgage needs. Sincerest thanks Eagle!! Ed & LindRead Less | Eagle National Mortgage | 55            |
| 2016-05-27 | 5       | I can't express how grateful I am for the support that Zach provided to me and my family during this...educate me about the process along the way. I highly recommend working with Zach and Eagle National! | Eagle National Mortgage | 24            |
| ...        | ...     | ...                                                                                                                                                                                                         | ...                     | ...           |
*/
CREATE TABLE reviews (
    Date DATE NOT NULL PRIMARY KEY,
        -- <example>'2013-02-04'</example>
    Stars INTEGER NOT NULL,
        -- <example>5</example>
    Reviews TEXT NULL,
        -- <example>'Great job, Eagle National! Each person was profess...through our refinance process smoothly. Thank you!'</example>
    Product TEXT NOT NULL,
        -- <values>{'Eagle Capital', 'Eagle National Bank', 'Eagle National Mortgage'}</values>
    district_id INTEGER NOT NULL,
        -- <example>65</example>
        -- <fk> -> district.district_id</fk>
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

/*
Schema: NULLTable: state
Rows: 48
Sample rows:
| StateCode   | State      | Region   |
|-------------|------------|----------|
| AL          | Alabama    | South    |
| AR          | Arkansas   | South    |
| AZ          | Arizona    | West     |
| CA          | California | West     |
| CO          | Colorado   | West     |
| ...         | ...        | ...      |
*/
CREATE TABLE state (
    StateCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'AL'</example>
    State TEXT NOT NULL,
        -- <example>'Alabama'</example>
    Region TEXT NOT NULL
        -- <values>{'Midwest', 'Northeast', 'South', 'West'}</values>
);
```