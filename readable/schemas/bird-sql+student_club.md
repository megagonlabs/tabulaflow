```sql
-- Database: student_club

-- Table: attendance (326 rows)
CREATE TABLE attendance (
    link_to_event TEXT NULL,
        -- <example>'rec2N69DMcrqN9PJC'</example>
        -- <fk> -> event.event_id</fk>
    link_to_member TEXT NULL,
        -- <example>'recD078PnS3x2doBe'</example>
        -- <fk> -> member.member_id</fk>
    PRIMARY KEY (link_to_event, link_to_member),
    FOREIGN KEY (link_to_event) REFERENCES event(event_id),
    FOREIGN KEY (link_to_member) REFERENCES member(member_id)
);

-- Table: budget (52 rows)
CREATE TABLE budget (
    budget_id TEXT NULL PRIMARY KEY,
        -- <example>'rec0QmEc3cSQFQ6V2'</example>
    category TEXT NULL,
        -- <values>{'Advertisement', 'Club T-Shirts', 'Food', 'Parking', 'Speaker Gifts'}</values>
    spent REAL NULL,
        -- <example>67.810</example>
    remaining REAL NULL,
        -- <example>7.190</example>
    amount INTEGER NULL,
        -- <example>75</example>
    event_status TEXT NULL,
        -- <values>{'Closed', 'Open', 'Planning'}</values>
    link_to_event TEXT NULL,
        -- <example>'recI43CzsZ0Q625ma'</example>
        -- <fk> -> event.event_id</fk>
    FOREIGN KEY (link_to_event) REFERENCES event(event_id)
);

-- Table: event (42 rows)
CREATE TABLE event (
    event_id TEXT NULL PRIMARY KEY,
        -- <example>'rec0Si5cQ4rJRVzd6'</example>
    event_name TEXT NULL,
        -- <example>'March Meeting'</example>
    event_date TEXT NULL,
        -- <example>'2020-03-10T12:00:00'</example>
    type TEXT NULL,
        -- <values>{'Budget', 'Community Service', 'Election', 'Game', 'Guest Speaker', 'Meeting', 'Registration', 'Social'}</values>
    notes TEXT NULL,
        -- <example>'All active members can vote for new officers between 4pm-8pm.'</example>
    location TEXT NULL,
        -- <example>'MU 215'</example>
    status TEXT NULL
        -- <values>{'Closed', 'Open', 'Planning'}</values>
);

-- Table: expense (32 rows)
CREATE TABLE expense (
    expense_id TEXT NULL PRIMARY KEY,
        -- <example>'rec017x6R3hQqkLAo'</example>
    expense_description TEXT NULL,
        -- <example>'Post Cards, Posters'</example>
    expense_date TEXT NULL,
        -- <example>'2019-08-20'</example>
    cost REAL NULL,
        -- <example>122.060</example>
    approved TEXT NULL,
        -- <values>{'true'}</values>
    link_to_member TEXT NULL,
        -- <values>{'rec4BLdZHS2Blfp4v', 'recD078PnS3x2doBe', 'recro8T1MPMwRadVH'}</values>
        -- <fk> -> member.member_id</fk>
    link_to_budget TEXT NULL,
        -- <example>'recvKTAWAFKkVNnXQ'</example>
        -- <fk> -> budget.budget_id</fk>
    FOREIGN KEY (link_to_budget) REFERENCES budget(budget_id),
    FOREIGN KEY (link_to_member) REFERENCES member(member_id)
);

-- Table: income (36 rows)
CREATE TABLE income (
    income_id TEXT NULL PRIMARY KEY,
        -- <example>'rec0s9ZrO15zhzUeE'</example>
    date_received TEXT NULL,
        -- <example>'2019-10-17'</example>
    amount INTEGER NULL,
        -- <example>50</example>
    source TEXT NULL,
        -- <values>{'Dues', 'Fundraising', 'School Appropration', 'Sponsorship'}</values>
    notes TEXT NULL,
        -- <values>{'Ad revenue for use on flyers used to advertise upcoming events.', 'Annual funding from Student Government.', 'Secured donations to help pay for speaker gifts.'}</values>
    link_to_member TEXT NULL,
        -- <example>'reccW7q1KkhSKZsea'</example>
        -- <fk> -> member.member_id</fk>
    FOREIGN KEY (link_to_member) REFERENCES member(member_id)
);

-- Table: major (113 rows)
CREATE TABLE major (
    major_id TEXT NULL PRIMARY KEY,
        -- <example>'rec06DF6vZ1CyPKpc'</example>
    major_name TEXT NULL,
        -- <example>'Outdoor Product Design and Development'</example>
    department TEXT NULL,
        -- <example>'School of Applied Sciences, Technology and Education'</example>
    college TEXT NULL
        -- <values>{'College of Agriculture and Applied Sciences', 'College of Education & Human Services', 'College of Engineering', 'College of Humanities and Social Sciences', 'College of Natural Resources', 'College of Science', 'College of the Arts', 'School of Business'}</values>
);

-- Table: member (33 rows)
CREATE TABLE member (
    member_id TEXT NULL PRIMARY KEY,
        -- <example>'rec1x5zBFIqoOuPW8'</example>
    first_name TEXT NULL,
        -- <example>'Angela'</example>
    last_name TEXT NULL,
        -- <example>'Sanders'</example>
    email TEXT NULL,
        -- <example>'angela.sanders@lpu.edu'</example>
    position TEXT NULL,
        -- <values>{'Inactive', 'Member', 'President', 'Secretary', 'Treasurer', 'Vice President'}</values>
    t_shirt_size TEXT NULL,
        -- <values>{'Large', 'Medium', 'Small', 'X-Large'}</values>
    phone TEXT NULL,
        -- <example>'(651) 928-4507'</example>
    zip INTEGER NULL,
        -- <example>55108</example>
        -- <fk> -> zip_code.zip_code</fk>
    link_to_major TEXT NULL,
        -- <example>'recxK3MHQFbR9J5uO'</example>
        -- <fk> -> major.major_id</fk>
    FOREIGN KEY (link_to_major) REFERENCES major(major_id),
    FOREIGN KEY (zip) REFERENCES zip_code(zip_code)
);

-- Table: zip_code (41877 rows)
CREATE TABLE zip_code (
    zip_code INTEGER NULL PRIMARY KEY,
        -- <example>501</example>
    type TEXT NULL,
        -- <values>{'PO Box', 'Standard', 'Unique'}</values>
    city TEXT NULL,
        -- <example>'Holtsville'</example>
    county TEXT NULL,
        -- <example>'Suffolk County'</example>
    state TEXT NULL,
        -- <example>'New York'</example>
    short_state TEXT NULL
        -- <example>'NY'</example>
);
```