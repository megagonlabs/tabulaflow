```sql
-- Database: human_resources

-- Table: employee (25 rows)
CREATE TABLE employee (
    ssn TEXT NULL PRIMARY KEY,
        -- <example>'000-01-0000'</example>
    lastname TEXT NULL,
        -- <example>'Milgrom'</example>
    firstname TEXT NULL,
        -- <example>'Patricia'</example>
    hiredate TEXT NULL,
        -- <example>'10/1/04'</example>
    salary TEXT NULL,
        -- <example>'US$57,500.00'</example>
    gender TEXT NULL,
        -- <values>{'F', 'M'}</values>
    performance TEXT NULL,
        -- <values>{'Average', 'Good', 'Poor'}</values>
    positionID INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> position.positionID</fk>
    locationID INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> location.locationID</fk>
    FOREIGN KEY (locationID) REFERENCES location(locationID),
    FOREIGN KEY (positionID) REFERENCES position(positionID)
);

-- Table: location (8 rows)
CREATE TABLE location (
    locationID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    locationcity TEXT NULL,
        -- <values>{'Atlanta', 'Boston', 'Chicago', 'Denver', 'Los Angeles', 'Miami', 'New York City', 'Salt Lake City'}</values>
    address TEXT NULL,
        -- <values>{'1400 Main St', '1650 Washington Blvd', '210 Biscayne Blvd', '3 Commons Blvd', '312 Mount View Dr', '316 S. State St', '450 Peachtree Rd', '500 Loop Highway'}</values>
    state TEXT NULL,
        -- <values>{'CA', 'CO', 'FL', 'GA', 'IL', 'MA', 'NY', 'UT'}</values>
    zipcode INTEGER NULL,
        -- <example>30316</example>
    officephone TEXT NULL
        -- <values>{'(205)607-5289', '(305)787-9999', '(312)444-6666', '(404)333-5555', '(518)256-3100', '(617)123-4444', '(705)639-0227', '(801)459-6652'}</values>
);

-- Table: position (4 rows)
CREATE TABLE position (
    positionID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    positiontitle TEXT NULL,
        -- <values>{'Account Representative', 'Manager', 'Regional Manager', 'Trainee'}</values>
    educationrequired TEXT NULL,
        -- <values>{'2 year degree', '4 year degree', '6 year degree'}</values>
    minsalary TEXT NULL,
        -- <values>{'US$100,000.00', 'US$18,000.00', 'US$25,000.00', 'US$50,000.00'}</values>
    maxsalary TEXT NULL
        -- <values>{'US$150,000.00', 'US$25,000.00', 'US$250,000.00', 'US$75,000.00'}</values>
);
```