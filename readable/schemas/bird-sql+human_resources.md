```sql
-- Database: human_resources

/*
Schema: NULL
Table: employee
Rows: 25
Sample rows:
| ssn         | lastname   | firstname   | hiredate   | salary       | gender   | performance   | positionID   | locationID   |
|-------------|------------|-------------|------------|--------------|----------|---------------|--------------|--------------|
| 000-01-0000 | Milgrom    | Patricia    | 10/1/04    | US$57,500.00 | F        | Average       | 2            | 2            |
| 000-02-2222 | Adams      | Sandy       | 1/15/01    | US$19,500.00 | F        | Average       | 3            | 1            |
| 109-87-6543 | Wood       | Emily       | 3/12/97    | US$69,000.00 | F        | Average       | 2            | 5            |
| 109-87-6544 | Foster     | Harold      | 8/14/05    | US$55,000.00 | M        | Good          | 1            | 3            |
| 111-12-1111 | Johnson    | James       | 5/3/96     | US$47,500.00 | M        | Good          | 1            | 3            |
| ...         | ...        | ...         | ...        | ...          | ...      | ...           | ...          | ...          |
*/
CREATE TABLE employee (
    "ssn" TEXT NOT NULL PRIMARY KEY,
        -- <example>'000-01-0000'</example>
    "lastname" TEXT NOT NULL,
        -- <example>'Milgrom'</example>
    "firstname" TEXT NOT NULL,
        -- <example>'Patricia'</example>
    "hiredate" TEXT NOT NULL,
        -- <example>'10/1/04'</example>
    "salary" TEXT NOT NULL,
        -- <example>'US$57,500.00'</example>
    "gender" TEXT NULL,
        -- <values>{'F', 'M'}</values>
    "performance" TEXT NULL,
        -- <values>{'Average', 'Good', 'Poor'}</values>
    "positionID" INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> position."positionID"</fk>
    "locationID" INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> location."locationID"</fk>
    FOREIGN KEY ("locationID") REFERENCES location("locationID"),
    FOREIGN KEY ("positionID") REFERENCES position("positionID")
);

/*
Schema: NULL
Table: location
Rows: 8
All rows:
|   locationID | locationcity   | address              | state   |   zipcode | officephone   |
|--------------|----------------|----------------------|---------|-----------|---------------|
|            1 | Atlanta        | 450 Peachtree Rd     | GA      |     30316 | (404)333-5555 |
|            2 | Boston         | 3 Commons Blvd       | MA      |      2190 | (617)123-4444 |
|            3 | Chicago        | 500 Loop Highway     | IL      |     60620 | (312)444-6666 |
|            4 | Miami          | 210 Biscayne Blvd    | FL      |     33103 | (305)787-9999 |
|            5 | New York City  | 1650 Washington Blvd | NY      |     15648 | (518)256-3100 |
|            6 | Denver         | 312 Mount View Dr    | CO      |     54657 | (205)607-5289 |
|            7 | Salt Lake City | 316 S. State St      | UT      |     84125 | (801)459-6652 |
|            8 | Los Angeles    | 1400 Main St         | CA      |     94235 | (705)639-0227 |
*/
CREATE TABLE location (
    "locationID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "locationcity" TEXT NOT NULL,
        -- <values>{'Atlanta', 'Boston', 'Chicago', 'Denver', 'Los Angeles', 'Miami', 'New York City', 'Salt Lake City'}</values>
    "address" TEXT NOT NULL,
        -- <values>{'1400 Main St', '1650 Washington Blvd', '210 Biscayne Blvd', '3 Commons Blvd', '312 Mount View Dr', '316 S. State St', '450 Peachtree Rd', '500 Loop Highway'}</values>
    "state" TEXT NOT NULL,
        -- <values>{'CA', 'CO', 'FL', 'GA', 'IL', 'MA', 'NY', 'UT'}</values>
    "zipcode" INTEGER NOT NULL,
        -- <example>30316</example>
    "officephone" TEXT NOT NULL
        -- <values>{'(205)607-5289', '(305)787-9999', '(312)444-6666', '(404)333-5555', '(518)256-3100', '(617)123-4444', '(705)639-0227', '(801)459-6652'}</values>
);

/*
Schema: NULL
Table: position
Rows: 4
All rows:
|   positionID | positiontitle          | educationrequired   | minsalary     | maxsalary     |
|--------------|------------------------|---------------------|---------------|---------------|
|            1 | Account Representative | 4 year degree       | US$25,000.00  | US$75,000.00  |
|            2 | Manager                | 4 year degree       | US$50,000.00  | US$150,000.00 |
|            3 | Trainee                | 2 year degree       | US$18,000.00  | US$25,000.00  |
|            4 | Regional Manager       | 6 year degree       | US$100,000.00 | US$250,000.00 |
*/
CREATE TABLE position (
    "positionID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "positiontitle" TEXT NOT NULL,
        -- <values>{'Account Representative', 'Manager', 'Regional Manager', 'Trainee'}</values>
    "educationrequired" TEXT NOT NULL,
        -- <values>{'2 year degree', '4 year degree', '6 year degree'}</values>
    "minsalary" TEXT NOT NULL,
        -- <values>{'US$100,000.00', 'US$18,000.00', 'US$25,000.00', 'US$50,000.00'}</values>
    "maxsalary" TEXT NOT NULL
        -- <values>{'US$150,000.00', 'US$25,000.00', 'US$250,000.00', 'US$75,000.00'}</values>
);
```