```sql
-- Database: student_club

/*
Table: attendance
Rows: 326
Sample rows:
| link_to_event     | link_to_member    |
|-------------------|-------------------|
| rec2N69DMcrqN9PJC | recD078PnS3x2doBe |
| rec2N69DMcrqN9PJC | recP6DJPyi5donvXL |
| rec2N69DMcrqN9PJC | rec28ORZgcm1dtqBZ |
| rec2N69DMcrqN9PJC | recTjHY5xXhvkCdVT |
| rec2N69DMcrqN9PJC | recZ4PkGERzl9ziHO |
| ...               | ...               |
*/
CREATE TABLE attendance (
    link_to_event TEXT NOT NULL,
        -- <description>Event identifier for the attended event.</description>
        -- <example>'rec2N69DMcrqN9PJC'</example>
        -- <fk> -> event.event_id</fk>
    link_to_member TEXT NOT NULL,
        -- <description>Attending member identifier — the unique id of the member who attended the event.</description>
        -- <example>'recD078PnS3x2doBe'</example>
        -- <fk> -> member.member_id</fk>
    PRIMARY KEY (link_to_event, link_to_member),
    FOREIGN KEY (link_to_event) REFERENCES event(event_id),
    FOREIGN KEY (link_to_member) REFERENCES member(member_id)
);

/*
Table: budget
Rows: 52
Sample rows:
| budget_id         | category      | spent   | remaining          | amount   | event_status   | link_to_event     |
|-------------------|---------------|---------|--------------------|----------|----------------|-------------------|
| rec0QmEc3cSQFQ6V2 | Advertisement | 67.81   | 7.19               | 75       | Closed         | recI43CzsZ0Q625ma |
| rec1bG6HSft7XIvTP | Food          | 121.14  | 28.86              | 150      | Closed         | recggMW2eyCYceNcy |
| rec1z6ISJU2HdIsVm | Food          | 20.2    | -0.199999999999999 | 20       | Closed         | recJ4Witp9tpjaugn |
| rec33PFqxLtnp80RJ | Speaker Gifts | 0.0     | 25.0               | 25       | Open           | recHaMmaKyfktt5fW |
| rec4DYUKBHMPZXWB2 | Food          | 0.0     | 150.0              | 150      | Open           | recHaMmaKyfktt5fW |
| ...               | ...           | ...     | ...                | ...      | ...            | ...               |
*/
CREATE TABLE budget (
    budget_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Budget entry identifier — the unique primary-key identifier for a record in the Budget table. Example values include rectLnkwVg4AIgY0R and recN9yY7okNrFps0Y.</description>
        -- <example>'rec0QmEc3cSQFQ6V2'</example>
    category TEXT NOT NULL,
        -- <description>Budget line category indicating the area or purpose the budgeted funds apply to (used to group budget entries by spending purpose).</description>
        -- <values>{'Advertisement', 'Club T-Shirts', 'Food', 'Parking', 'Speaker Gifts'}</values>
    spent REAL NOT NULL,
        -- <description>Amount already spent for this budget line (dollars); typically the sum of related Expense.cost records.</description>
        -- <example>67.810</example>
    remaining REAL NOT NULL,
        -- <description>Remaining budget for the line item — the amount still available (budgeted minus spent); negative values indicate the budget has been exceeded.</description>
        -- <example>7.190</example>
    amount INTEGER NOT NULL,
        -- <description>Budgeted amount for the category and event — the planned dollar allocation (typically equals spent + remaining).</description>
        -- <example>75</example>
    event_status TEXT NOT NULL,
        -- <description>Event status for the budget line, indicating whether the linked event is Closed, Open, or Planning; when Closed or Planning the budget's spent and remaining amounts are final and won't change, while Open means spent/remaining may change as new expenses are recorded.</description>
        -- <values>{'Closed', 'Open', 'Planning'}</values>
    link_to_event TEXT NOT NULL,
        -- <description>Event identifier linking this budget line to its Event record (references event.event_id).</description>
        -- <example>'recI43CzsZ0Q625ma'</example>
        -- <fk> -> event.event_id</fk>
    FOREIGN KEY (link_to_event) REFERENCES event(event_id)
);

/*
Table: event
Rows: 42
Sample rows:
| event_id          | event_name                 | event_date          | type     | notes                                                         | location                       | status   |
|-------------------|----------------------------|---------------------|----------|---------------------------------------------------------------|--------------------------------|----------|
| rec0Si5cQ4rJRVzd6 | March Meeting              | 2020-03-10T12:00:00 | Meeting  | [NULL]                                                        | MU 215                         | Open     |
| rec0akZnLLpGUloLH | Officers meeting - January | 2020-01-14T09:30:00 | Meeting  | [NULL]                                                        | [NULL]                         | Open     |
| rec0dZPcWXF0QjNnE | Spring Elections           | 2019-11-24T09:00:00 | Election | All active members can vote for new officers between 4pm-8pm. | MU 215                         | Open     |
| rec180D2MI4EpckHy | Officers meeting - March   | 2020-03-10T09:30:00 | Meeting  | [NULL]                                                        | [NULL]                         | Planning |
| rec2N69DMcrqN9PJC | Women's Soccer             | 2019-10-05T12:00:00 | Game     | Attend Women's soccer game as a group.                        | Campus Soccer/Lacrosse stadium | Closed   |
| ...               | ...                        | ...                 | ...      | ...                                                           | ...                            | ...      |
*/
CREATE TABLE event (
    event_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Unique event identifier used to link an event to related records (for example, attendance and budget entries).</description>
        -- <example>'rec0Si5cQ4rJRVzd6'</example>
    event_name TEXT NOT NULL,
        -- <description>Event name — the human-readable title of the event used for display, listing, and identification (for example, “March Meeting” or “Guest Speaker”).</description>
        -- <example>'March Meeting'</example>
    event_date TEXT NOT NULL,
        -- <description>Event date and time — the scheduled or actual timestamp for when the event occurs (e.g., 2020-03-10T12:00:00).</description>
        -- <example>'2020-03-10T12:00:00'</example>
    type TEXT NOT NULL,
        -- <description>Event category indicating the kind of event (used to classify and filter events).</description>
        -- <values>{'Budget', 'Community Service', 'Election', 'Game', 'Guest Speaker', 'Meeting', 'Registration', 'Social'}</values>
    notes TEXT NULL,
        -- <description>Notes about the event — a free-text field for additional details, instructions, or context for the event (e.g., 'All active members can vote for new officers between 4pm-8pm.').</description>
        -- <example>'All active members can vote for new officers between 4pm-8pm.'</example>
    location TEXT NULL,
        -- <description>Event location (venue name or street address of where the event is/was scheduled to be held).</description>
        -- <example>'MU 215'</example>
    status TEXT NOT NULL
        -- <description>Event lifecycle status indicating the current stage of an event (planned, active/in‑progress, or completed).</description>
        -- <values>{'Closed', 'Open', 'Planning'}</values>
);

/*
Table: expense
Rows: 32
Sample rows:
| expense_id        | expense_description   | expense_date   | cost   | approved   | link_to_member    | link_to_budget    |
|-------------------|-----------------------|----------------|--------|------------|-------------------|-------------------|
| rec017x6R3hQqkLAo | Post Cards, Posters   | 2019-08-20     | 122.06 | true       | rec4BLdZHS2Blfp4v | recvKTAWAFKkVNnXQ |
| rec1nIjoZKTYayqZ6 | Water, Cookies        | 2019-10-08     | 20.2   | true       | recro8T1MPMwRadVH | recy8KY5bUdzF81vv |
| rec1oMgNFt7Y0G40x | Pizza                 | 2019-09-10     | 51.81  | true       | recD078PnS3x2doBe | recwXIiKoBMjXJsGZ |
| rec4Zg7WEmfiHXcnC | Posters               | 2019-10-10     | 67.81  | true       | rec4BLdZHS2Blfp4v | recsI0IzpUuxl2bPh |
| rec7gUiykKKW4RaJS | Parking               | 2019-11-19     | 6.0    | true       | recro8T1MPMwRadVH | recTUGXxhTaFZ2qkg |
| ...               | ...                   | ...            | ...    | ...        | ...               | ...               |
*/
CREATE TABLE expense (
    expense_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for an expense record in the Expense table (primary key used to reference individual expenses).</description>
        -- <example>'rec017x6R3hQqkLAo'</example>
    expense_description TEXT NOT NULL,
        -- <description>Expense description — free-text label describing the purpose or items purchased for the expense (e.g., 'Post Cards, Posters', 'Pizza', 'Parking').</description>
        -- <example>'Post Cards, Posters'</example>
    expense_date TEXT NOT NULL,
        -- <description>Expense date — the calendar date the expense was incurred (expected format: YYYY-MM-DD).</description>
        -- <example>'2019-08-20'</example>
    cost REAL NOT NULL,
        -- <description>Expense amount (dollars) — the monetary value recorded for the individual expense entry.</description>
        -- <example>122.060</example>
    approved TEXT NULL,
        -- <description>Expense approval flag indicating whether an expense was approved. Dataset metadata shows only 'true' values, so the column may be effectively constant and not informative.</description>
        -- <values>{'true'}</values>
    link_to_member TEXT NOT NULL,
        -- <description>Member identifier for the person who incurred or submitted the expense.</description>
        -- <values>{'rec4BLdZHS2Blfp4v', 'recD078PnS3x2doBe', 'recro8T1MPMwRadVH'}</values>
        -- <fk> -> member.member_id</fk>
    link_to_budget TEXT NOT NULL,
        -- <description>Budget record identifier linking this expense to the corresponding budget line for the event and category.</description>
        -- <example>'recvKTAWAFKkVNnXQ'</example>
        -- <fk> -> budget.budget_id</fk>
    FOREIGN KEY (link_to_budget) REFERENCES budget(budget_id),
    FOREIGN KEY (link_to_member) REFERENCES member(member_id)
);

/*
Table: income
Rows: 36
Sample rows:
| income_id         | date_received   | amount   | source   | notes   | link_to_member    |
|-------------------|-----------------|----------|----------|---------|-------------------|
| rec0s9ZrO15zhzUeE | 2019-10-17      | 50       | Dues     | [NULL]  | reccW7q1KkhSKZsea |
| rec7f5XMQZexgtQJo | 2019-09-04      | 50       | Dues     | [NULL]  | recTjHY5xXhvkCdVT |
| rec8BUJa8GXUjiglg | 2019-10-08      | 50       | Dues     | [NULL]  | recUdRhbhcEO1Hk5r |
| rec8V9BPNIoewWt2z | 2019-10-02      | 50       | Dues     | [NULL]  | rec3pH4DxMcWHMRB7 |
| recCRWMfFqifuKMc6 | 2019-09-18      | 50       | Dues     | [NULL]  | rec28ORZgcm1dtqBZ |
| ...               | ...             | ...      | ...      | ...     | ...               |
*/
CREATE TABLE income (
    income_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Income record identifier — an Airtable-style record ID used to uniquely reference an income entry (e.g., recOo362sJrXFv2az).</description>
        -- <example>'rec0s9ZrO15zhzUeE'</example>
    date_received TEXT NOT NULL,
        -- <description>Receipt date of funds for the income record (the date the funds were received, formatted as YYYY-MM-DD).</description>
        -- <example>'2019-10-17'</example>
    amount INTEGER NOT NULL,
        -- <description>Income amount received for the record (dollars).</description>
        -- <example>50</example>
    source TEXT NOT NULL,
        -- <description>Source of funds for the income record; common values include Dues, Fundraising, School Appropriation, and Sponsorship.</description>
        -- <values>{'Dues', 'Fundraising', 'School Appropration', 'Sponsorship'}</values>
    notes TEXT NULL,
        -- <description>Free-text notes about an income record, used to capture any additional details or context for the received funds (optional). Examples: “Annual funding from Student Government”, “Ad revenue for flyers used to advertise events”, “Secured donations to help pay for speaker gifts.”</description>
        -- <values>{'Ad revenue for use on flyers used to advertise upcoming events.', 'Annual funding from Student Government.', 'Secured donations to help pay for speaker gifts.'}</values>
    link_to_member TEXT NULL,
        -- <description>Member reference for the income record — identifies the member who provided or is associated with the funds (foreign key to member.member_id).</description>
        -- <example>'reccW7q1KkhSKZsea'</example>
        -- <fk> -> member.member_id</fk>
    FOREIGN KEY (link_to_member) REFERENCES member(member_id)
);

/*
Table: major
Rows: 113
Sample rows:
| major_id          | major_name                             | department                                           | college                                     |
|-------------------|----------------------------------------|------------------------------------------------------|---------------------------------------------|
| rec06DF6vZ1CyPKpc | Outdoor Product Design and Development | School of Applied Sciences, Technology and Education | College of Agriculture and Applied Sciences |
| rec09LedkREyskCNv | Agricultural Communication             | School of Applied Sciences, Technology and Education | College of Agriculture and Applied Sciences |
| rec0Eanv576RhQllI | Fisheries and Aquatic Sciences         | Watershed Sciences Department                        | College of Natural Resources                |
| rec0xRZtkzxrg8kj2 | Finance                                | Economics and Finance Department                     | School of Business                          |
| rec1N0upiVLy5esTO | Forest Ecology and Management          | Wildland Resources Department                        | College of Natural Resources                |
| ...               | ...                                    | ...                                                  | ...                                         |
*/
CREATE TABLE major (
    major_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for a major, used as the table's primary key and for referencing majors from other tables.</description>
        -- <example>'rec06DF6vZ1CyPKpc'</example>
    major_name TEXT NOT NULL,
        -- <description>Major name — the official name of the academic major or program (e.g., "Computer Engineering", "Environmental and Natural Resource Economics").</description>
        -- <example>'Outdoor Product Design and Development'</example>
    department TEXT NOT NULL,
        -- <description>Academic department that offers the major.</description>
        -- <example>'School of Applied Sciences, Technology and Education'</example>
    college TEXT NOT NULL
        -- <description>College that houses the department offering the major, i.e., the academic college affiliation for the major.</description>
        -- <values>{'College of Agriculture and Applied Sciences', 'College of Education & Human Services', 'College of Engineering', 'College of Humanities and Social Sciences', 'College of Natural Resources', 'College of Science', 'College of the Arts', 'School of Business'}</values>
);

/*
Table: member
Rows: 33
Sample rows:
| member_id         | first_name   | last_name   | email                  | position   | t_shirt_size   | phone          | zip   | link_to_major     |
|-------------------|--------------|-------------|------------------------|------------|----------------|----------------|-------|-------------------|
| rec1x5zBFIqoOuPW8 | Angela       | Sanders     | angela.sanders@lpu.edu | Member     | Medium         | (651) 928-4507 | 55108 | recxK3MHQFbR9J5uO |
| rec280Sk7o31iG0Tx | Grant        | Gilmour     | grant.gilmour@lpu.edu  | Member     | X-Large        | 403-555-1310   | 29440 | rec7BxKpjJ7bNph3O |
| rec28ORZgcm1dtqBZ | Luisa        | Guidi       | luisa.guidi@lpu.edu    | Member     | Medium         | 442-555-5882   | 10002 | recdIBgeU38UbV2sy |
| rec2a03QXbFQAUZ7X | Randy        | Woodard     | randy.woodard@lpu.edu  | Inactive   | X-Large        | 490-555-8460   | 8021  | [NULL]            |
| rec3pH4DxMcWHMRB7 | Connor       | Hilton      | connor.hilton@lpu.edu  | Member     | X-Large        | 454-555-7970   | 48236 | recaJdSK83k6ekRJL |
| ...               | ...          | ...         | ...                    | ...        | ...            | ...            | ...   | ...               |
*/
CREATE TABLE member (
    member_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Member identifier — a unique text ID assigned to each member, used to reference that member in related tables (e.g., attendance, expense, income).</description>
        -- <example>'rec1x5zBFIqoOuPW8'</example>
    first_name TEXT NOT NULL,
        -- <description>Member's first name — the member's given name used for display and contact purposes.</description>
        -- <example>'Angela'</example>
    last_name TEXT NOT NULL,
        -- <description>Member last name (surname); the family name used with first_name to form the member's full name (e.g., Hilton, Mason, Mccray).</description>
        -- <example>'Sanders'</example>
    email TEXT NOT NULL,
        -- <description>Member email address — the primary contact email for the club member.</description>
        -- <example>'angela.sanders@lpu.edu'</example>
    position TEXT NOT NULL,
        -- <description>Member role — the office or membership status held within the club (e.g., officer, regular member, inactive).</description>
        -- <values>{'Inactive', 'Member', 'President', 'Secretary', 'Treasurer', 'Vice President'}</values>
    t_shirt_size TEXT NOT NULL,
        -- <description>Preferred T-shirt size for the member, recorded for ordering shirts and other apparel.</description>
        -- <values>{'Large', 'Medium', 'Small', 'X-Large'}</values>
    phone TEXT NOT NULL,
        -- <description>Member contact phone number — the primary telephone number used to reach the member; formatting may vary (e.g., 475-555-3802, (651) 928-4507).</description>
        -- <example>'(651) 928-4507'</example>
    zip INTEGER NOT NULL,
        -- <description>Member home ZIP code (links to zip_code.zip_code).</description>
        -- <example>55108</example>
        -- <fk> -> zip_code.zip_code</fk>
    link_to_major TEXT NULL,
        -- <description>Member major reference (identifier of the member's academic major).</description>
        -- <example>'recxK3MHQFbR9J5uO'</example>
        -- <fk> -> major.major_id</fk>
    FOREIGN KEY (link_to_major) REFERENCES major(major_id),
    FOREIGN KEY (zip) REFERENCES zip_code(zip_code)
);

/*
Table: zip_code
Rows: 41877
Sample rows:
| zip_code   | type     | city       | county              | state       | short_state   |
|------------|----------|------------|---------------------|-------------|---------------|
| 501        | Unique   | Holtsville | Suffolk County      | New York    | NY            |
| 544        | Unique   | Holtsville | Suffolk County      | New York    | NY            |
| 601        | Standard | Adjuntas   | Adjuntas Municipio  | Puerto Rico | PR            |
| 602        | Standard | Aguada     | Aguada Municipio    | Puerto Rico | PR            |
| 603        | Standard | Aguadilla  | Aguadilla Municipio | Puerto Rico | PR            |
| ...        | ...      | ...        | ...                 | ...         | ...           |
*/
CREATE TABLE zip_code (
    zip_code INTEGER NOT NULL PRIMARY KEY,
        -- <description>U.S. ZIP code — the five-digit postal code that identifies the post office serving the location.</description>
        -- <example>501</example>
    type TEXT NOT NULL,
        -- <description>ZIP code classification indicating whether the ZIP is assigned to a single organization, covers a standard geographic delivery area, or represents a PO Box–only code.</description>
        -- <values>{'PO Box', 'Standard', 'Unique'}</values>
    city TEXT NOT NULL,
        -- <description>City associated with the ZIP code — the primary municipality for that ZIP.</description>
        -- <example>'Holtsville'</example>
    county TEXT NULL,
        -- <description>County of the ZIP code (e.g., Huron County, Osage County).</description>
        -- <example>'Suffolk County'</example>
    state TEXT NOT NULL,
        -- <description>State name for the ZIP code's location.</description>
        -- <example>'New York'</example>
    short_state TEXT NOT NULL
        -- <description>U.S. state postal abbreviation — the two-letter USPS code for the state associated with the ZIP code (e.g., NY, CA).</description>
        -- <example>'NY'</example>
);
```