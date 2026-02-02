```sql
-- Database: student_club

-- Table: attendance (326 rows)
CREATE TABLE attendance (
    link_to_event TEXT NULL,
        -- <description>Link to the attended event record — associates each attendance row with a specific event.</description>
        -- <example>'rec2N69DMcrqN9PJC'</example>
        -- <fk> -> event.event_id</fk>
    link_to_member TEXT NULL,
        -- <description>Member link for attendance — identifier of the member associated with this attendance record (references member.member_id).</description>
        -- <example>'recD078PnS3x2doBe'</example>
        -- <fk> -> member.member_id</fk>
    PRIMARY KEY (link_to_event, link_to_member),
    FOREIGN KEY (link_to_event) REFERENCES event(event_id),
    FOREIGN KEY (link_to_member) REFERENCES member(member_id)
);

-- Table: budget (52 rows)
CREATE TABLE budget (
    budget_id TEXT NULL PRIMARY KEY,
        -- <description>Budget entry identifier — identifier for a budget row used as the reference from related records (for example, expenses) to associate costs with a specific budget line.</description>
        -- <example>'rec0QmEc3cSQFQ6V2'</example>
    category TEXT NULL,
        -- <description>Budget category — the area or purpose for which a budget line is allocated, used to classify and group budget amounts for reporting and tracking.</description>
        -- <values>{'Advertisement', 'Club T-Shirts', 'Food', 'Parking', 'Speaker Gifts'}</values>
    spent REAL NULL,
        -- <description>Amount spent for the budget line (in dollars); total spent for that category and event, summarized from Expense records.</description>
        -- <example>67.810</example>
    remaining REAL NULL,
        -- <description>Remaining budget for the category and event — the dollar amount still available (calculated as amount − spent). Negative values indicate the category has been overspent.</description>
        -- <example>7.190</example>
    amount INTEGER NULL,
        -- <description>Budgeted amount for the specified event and category, in US dollars — typically computed as spent + remaining.</description>
        -- <example>75</example>
    event_status TEXT NULL,
        -- <description>Event status — indicates whether the budget line is active or finalized; determines if the spent and remaining amounts are expected to change (active budgets may accept new expenses; finalized or planning budgets typically do not).</description>
        -- <values>{'Closed', 'Open', 'Planning'}</values>
    link_to_event TEXT NULL,
        -- <description>Event linked to the budget line — the event record this budget entry applies to.</description>
        -- <example>'recI43CzsZ0Q625ma'</example>
        -- <fk> -> event.event_id</fk>
    FOREIGN KEY (link_to_event) REFERENCES event(event_id)
);

-- Table: event (42 rows)
CREATE TABLE event (
    event_id TEXT NULL PRIMARY KEY,
        -- <description>Unique event identifier used to reference and link event records across the database.</description>
        -- <example>'rec0Si5cQ4rJRVzd6'</example>
    event_name TEXT NULL,
        -- <description>Event name — human-readable title of the event (used as the event's display/identifying label).</description>
        -- <example>'March Meeting'</example>
    event_date TEXT NULL,
        -- <description>Event date and time (ISO 8601 timestamp) indicating when the event occurred or is scheduled — typically stored as 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS' (e.g., '2020-03-10T12:00:00').</description>
        -- <example>'2020-03-10T12:00:00'</example>
    type TEXT NULL,
        -- <description>Event category describing the purpose or kind of the event (used to classify events for scheduling, reporting, and grouping).</description>
        -- <values>{'Budget', 'Community Service', 'Election', 'Game', 'Guest Speaker', 'Meeting', 'Registration', 'Social'}</values>
    notes TEXT NULL,
        -- <description>Event notes — free-text details or instructions about the event (logistics, attendance guidance, reminders); present for roughly 20 of 42 events.</description>
        -- <example>'All active members can vote for new officers between 4pm-8pm.'</example>
    location TEXT NULL,
        -- <description>Event location — free-text venue name or street address describing where the event took place or is scheduled to take place (e.g., MU 215, Campus Football stadium, 1308 106th Ave.).</description>
        -- <example>'MU 215'</example>
    status TEXT NULL
        -- <description>Event status indicating the event's lifecycle; used to track whether the event is upcoming, active, or finished and to determine if related records (budgets, expenses, attendance) remain editable.</description>
        -- <values>{'Closed', 'Open', 'Planning'}</values>
);

-- Table: expense (32 rows)
CREATE TABLE expense (
    expense_id TEXT NULL PRIMARY KEY,
        -- <description>Unique identifier for an expense record.</description>
        -- <example>'rec017x6R3hQqkLAo'</example>
    expense_description TEXT NULL,
        -- <description>Brief description of the purchased item or service — a short free-text note explaining what the expense paid for (examples: "Pizza", "Post Cards, Posters").</description>
        -- <example>'Post Cards, Posters'</example>
    expense_date TEXT NULL,
        -- <description>Expense date — the date the expense was incurred, recorded in ISO format (YYYY-MM-DD). Values in this dataset span 2019-08-20 to 2019-11-19 (no missing values).</description>
        -- <example>'2019-08-20'</example>
    cost REAL NULL,
        -- <description>Expense amount in US dollars.</description>
        -- <example>122.060</example>
    approved TEXT NULL,
        -- <description>Expense approval flag indicating whether an expense record was approved.</description>
        -- <values>{'true'}</values>
    link_to_member TEXT NULL,
        -- <description>Member reference linking each expense to the member who incurred it (all 32 rows reference one of three members; no nulls).</description>
        -- <values>{'rec4BLdZHS2Blfp4v', 'recD078PnS3x2doBe', 'recro8T1MPMwRadVH'}</values>
        -- <fk> -> member.member_id</fk>
    link_to_budget TEXT NULL,
        -- <description>Linked budget line — the Budget record this expense is charged against.</description>
        -- <example>'recvKTAWAFKkVNnXQ'</example>
        -- <fk> -> budget.budget_id</fk>
    FOREIGN KEY (link_to_budget) REFERENCES budget(budget_id),
    FOREIGN KEY (link_to_member) REFERENCES member(member_id)
);

-- Table: income (36 rows)
CREATE TABLE income (
    income_id TEXT NULL PRIMARY KEY,
        -- <description>Income record identifier</description>
        -- <example>'rec0s9ZrO15zhzUeE'</example>
    date_received TEXT NULL,
        -- <description>Date the income was received, recorded as an ISO date (YYYY-MM-DD). Values present for all 36 rows and range from 2019-09-01 to 2019-10-31.</description>
        -- <example>'2019-10-17'</example>
    amount INTEGER NULL,
        -- <description>Amount received — dollar amount recorded for each income record; in this dataset values range from $50 to $3,000 (mean ≈ $162.50).</description>
        -- <example>50</example>
    source TEXT NULL,
        -- <description>Source of income — indicates where the club’s funds originated (e.g., membership dues, fundraising, sponsorships, or a school appropriation). Note: the dataset contains the label 'School Appropration' (likely a typo for 'School Appropriation').</description>
        -- <values>{'Dues', 'Fundraising', 'School Appropration', 'Sponsorship'}</values>
    notes TEXT NULL,
        -- <description>Free-text income note describing details about the funds received (mostly empty — 3 of 36 rows populated). Example values: 'Annual funding from Student Government', 'Ad revenue for use on flyers', 'Secured donations to help pay for speaker gifts.'</description>
        -- <values>{'Ad revenue for use on flyers used to advertise upcoming events.', 'Annual funding from Student Government.', 'Secured donations to help pay for speaker gifts.'}</values>
    link_to_member TEXT NULL,
        -- <description>Reference to the Member record (foreign key to member.member_id); nullable — identifies the member associated with the income record when known. Most rows include a member (31 distinct non-null values across 36 rows; 3 NULLs) and all non-null values match existing member.member_id values.</description>
        -- <example>'reccW7q1KkhSKZsea'</example>
        -- <fk> -> member.member_id</fk>
    FOREIGN KEY (link_to_member) REFERENCES member(member_id)
);

-- Table: major (113 rows)
CREATE TABLE major (
    major_id TEXT NULL PRIMARY KEY,
        -- <description>Major identifier — unique primary key that identifies each record in the Major table.</description>
        -- <example>'rec06DF6vZ1CyPKpc'</example>
    major_name TEXT NULL,
        -- <description>Major name — the official title of the academic major; populated for all 113 rows (no missing values).</description>
        -- <example>'Outdoor Product Design and Development'</example>
    department TEXT NULL,
        -- <description>Academic department that offers the major (department name). Example values: Aerospace Studies Program; Biology Department; Chemistry and Biochemistry Department.</description>
        -- <example>'School of Applied Sciences, Technology and Education'</example>
    college TEXT NULL
        -- <description>Academic college that houses the department offering the major.</description>
        -- <values>{'College of Agriculture and Applied Sciences', 'College of Education & Human Services', 'College of Engineering', 'College of Humanities and Social Sciences', 'College of Natural Resources', 'College of Science', 'College of the Arts', 'School of Business'}</values>
);

-- Table: member (33 rows)
CREATE TABLE member (
    member_id TEXT NULL PRIMARY KEY,
        -- <description>Unique member identifier (primary key); used to link members to attendance, expense, and income records.</description>
        -- <example>'rec1x5zBFIqoOuPW8'</example>
    first_name TEXT NULL,
        -- <description>Member's first (given) name — the given name used to identify and contact a club member (e.g., Angela, Grant).</description>
        -- <example>'Angela'</example>
    last_name TEXT NULL,
        -- <description>Member's family name (surname); combined with first_name to form the member's full name. In the current dataset every member row has a non-empty last_name and values are unique.</description>
        -- <example>'Sanders'</example>
    email TEXT NULL,
        -- <description>Primary contact email address for the member; populated for all records and unique across the table (33 non-empty, 33 distinct values).</description>
        -- <example>'angela.sanders@lpu.edu'</example>
    position TEXT NULL,
        -- <description>Member role within the club — the office or membership status a person holds (used to distinguish officers from regular or inactive members).</description>
        -- <values>{'Inactive', 'Member', 'President', 'Secretary', 'Treasurer', 'Vice President'}</values>
    t_shirt_size TEXT NULL,
        -- <description>Preferred T‑shirt size for a member (used when ordering shirts).</description>
        -- <values>{'Large', 'Medium', 'Small', 'X-Large'}</values>
    phone TEXT NULL,
        -- <description>Primary contact telephone number for the member — the best phone number to reach them. Formatting may vary (e.g., parentheses or dashes).</description>
        -- <example>'(651) 928-4507'</example>
    zip INTEGER NULL,
        -- <description>Member hometown ZIP code — the postal ZIP for each member's hometown. All 33 members have a non-null ZIP; every value in this column matches an entry in the zip_code table.</description>
        -- <example>55108</example>
        -- <fk> -> zip_code.zip_code</fk>
    link_to_major TEXT NULL,
        -- <description>Member's major identifier — the Major record selected for the member. Most members have a value (32 of 33); there are 26 distinct major values present.</description>
        -- <example>'recxK3MHQFbR9J5uO'</example>
        -- <fk> -> major.major_id</fk>
    FOREIGN KEY (link_to_major) REFERENCES major(major_id),
    FOREIGN KEY (zip) REFERENCES zip_code(zip_code)
);

-- Table: zip_code (41877 rows)
CREATE TABLE zip_code (
    zip_code INTEGER NULL PRIMARY KEY,
        -- <description>ZIP code — five‑digit U.S. postal code identifying the post office (note: values may omit leading zeros, e.g. 00501 stored as 501).</description>
        -- <example>501</example>
    type TEXT NULL,
        -- <description>ZIP code classification indicating whether the ZIP is a standard geographic code, a PO Box-only code, or a unique code assigned to a single organization.</description>
        -- <values>{'PO Box', 'Standard', 'Unique'}</values>
    city TEXT NULL,
        -- <description>City name associated with the ZIP code (the place name for each ZIP). Present for all rows in the table (41,877) with 18,729 distinct city values.</description>
        -- <example>'Holtsville'</example>
    county TEXT NULL,
        -- <description>County name for the ZIP code (U.S. county, e.g., 'Suffolk County').</description>
        -- <example>'Suffolk County'</example>
    state TEXT NULL,
        -- <description>State name corresponding to the ZIP code's location (full U.S. state names, e.g., Texas, California, Pennsylvania).</description>
        -- <example>'New York'</example>
    short_state TEXT NULL
        -- <description>State postal abbreviation — the two-letter USPS code for the state or territory associated with the ZIP code.</description>
        -- <example>'NY'</example>
);
```