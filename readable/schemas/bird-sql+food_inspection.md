```sql
-- Database: food_inspection

/*
Schema: NULLTable: businesses
Rows: 6358
Sample rows:
| business_id   | name                               | address                       | city          | postal_code   | latitude   | longitude   | phone_number   | tax_code   | business_certificate   | application_date   | owner_name                    | owner_address                | owner_city    | owner_state   | owner_zip   |
|---------------|------------------------------------|-------------------------------|---------------|---------------|------------|-------------|----------------|------------|------------------------|--------------------|-------------------------------|------------------------------|---------------|---------------|-------------|
| 10            | Tiramisu Kitchen                   | 033 Belden Pl                 | San Francisco | 94104         | 37.7911    | -122.404    | [NULL]         | H24        | 779059                 | [NULL]             | Tiramisu LLC                  | 33 Belden St                 | San Francisco | CA            | 94104       |
| 24            | OMNI S.F. Hotel - 2nd Floor Pantry | 500 California St, 2nd  Floor | San Francisco | 94104         | 37.7929    | -122.403    | [NULL]         | H24        | 352312                 | [NULL]             | OMNI San Francisco Hotel Corp | 500 California St, 2nd Floor | San Francisco | CA            | 94104       |
| 31            | Norman's Ice Cream and Freezes     | 2801 Leavenworth St           | San Francisco | 94133         | 37.8072    | -122.419    | [NULL]         | H24        | 346882                 | [NULL]             | Norman Antiforda              | 2801 Leavenworth St          | San Francisco | CA            | 94133       |
| 45            | CHARLIE'S DELI CAFE                | 3202 FOLSOM St                | S.F.          | 94110         | 37.7471    | -122.414    | [NULL]         | H24        | 340024                 | 2001-10-10         | HARB, CHARLES AND KRISTIN     | 1150 SANCHEZ                 | S.F.          | CA            | 94114       |
| 48            | ART'S CAFE                         | 747 IRVING St                 | SAN FRANCISCO | 94122         | 37.764     | -122.466    | [NULL]         | H24        | 318022                 | [NULL]             | YOON HAE RYONG                | 1567 FUNSTON AVE             | SAN FRANCISCO | CA            | 94122       |
| ...           | ...                                | ...                           | ...           | ...           | ...        | ...         | ...            | ...        | ...                    | ...                | ...                           | ...                          | ...           | ...           | ...         |
*/
CREATE TABLE businesses (
    business_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>10</example>
    name TEXT NOT NULL,
        -- <example>'Tiramisu Kitchen'</example>
    address TEXT NULL,
        -- <example>'033 Belden Pl'</example>
    city TEXT NULL,
        -- <example>'San Francisco'</example>
    postal_code TEXT NULL,
        -- <example>'94104'</example>
    latitude REAL NULL,
        -- <example>37.791</example>
    longitude REAL NULL,
        -- <example>-122.404</example>
    phone_number INTEGER NULL,
        -- <example>14155345060</example>
    tax_code TEXT NULL,
        -- <example>'H24'</example>
    business_certificate INTEGER NOT NULL,
        -- <example>779059</example>
    application_date DATE NULL,
        -- <example>'2001-10-10'</example>
    owner_name TEXT NOT NULL,
        -- <example>'Tiramisu LLC'</example>
    owner_address TEXT NOT NULL,
        -- <example>'33 Belden St'</example>
    owner_city TEXT NULL,
        -- <example>'San Francisco'</example>
    owner_state TEXT NULL,
        -- <example>'CA'</example>
    owner_zip TEXT NOT NULL
        -- <example>'94104'</example>
);

/*
Schema: NULLTable: inspections
Rows: 23764
Sample rows:
| business_id   | score   | date       | type                  |
|---------------|---------|------------|-----------------------|
| 10            | 92.0    | 2014-01-14 | Routine - Unscheduled |
| 10            | [NULL]  | 2014-01-24 | Reinspection/Followup |
| 10            | 94.0    | 2014-07-29 | Routine - Unscheduled |
| 10            | [NULL]  | 2014-08-07 | Reinspection/Followup |
| 10            | 82.0    | 2016-05-03 | Routine - Unscheduled |
| ...           | ...     | ...        | ...                   |
*/
CREATE TABLE inspections (
    business_id INTEGER NOT NULL,
        -- <example>10</example>
        -- <fk> -> businesses.business_id</fk>
    score INTEGER NULL,
        -- <example>92</example>
    date DATE NOT NULL,
        -- <example>'2014-01-14'</example>
    type TEXT NOT NULL,
        -- <values>{'Administrative or Document Review', 'Complaint Reinspection/Followup', 'Complaint', 'Foodborne Illness Investigation', 'Multi-agency Investigation', 'New Construction', 'New Ownership', 'Non-inspection site visit', 'Reinspection/Followup', 'Routine - Scheduled', 'Routine - Unscheduled', 'Special Event', 'Structural Inspection'}</values>
    FOREIGN KEY (business_id) REFERENCES businesses(business_id)
);

/*
Schema: NULLTable: violations
Rows: 36050
Sample rows:
| business_id   | date       | violation_type_id   | risk_category   | description                                        |
|---------------|------------|---------------------|-----------------|----------------------------------------------------|
| 10            | 2014-07-29 | 103129              | Moderate Risk   | Insufficient hot water or running water            |
| 10            | 2014-07-29 | 103144              | Low Risk        | Unapproved or unmaintained equipment or utensils   |
| 10            | 2014-01-14 | 103119              | Moderate Risk   | Inadequate and inaccessible handwashing facilities |
| 10            | 2014-01-14 | 103145              | Low Risk        | Improper storage of equipment utensils or linens   |
| 10            | 2014-01-14 | 103154              | Low Risk        | Unclean or degraded floors walls or ceilings       |
| ...           | ...        | ...                 | ...             | ...                                                |
*/
CREATE TABLE violations (
    business_id INTEGER NOT NULL,
        -- <example>10</example>
        -- <fk> -> businesses.business_id</fk>
    date DATE NOT NULL,
        -- <example>'2014-07-29'</example>
    violation_type_id TEXT NOT NULL,
        -- <example>'103129'</example>
    risk_category TEXT NOT NULL,
        -- <values>{'High Risk', 'Low Risk', 'Moderate Risk'}</values>
    description TEXT NOT NULL,
        -- <example>'Insufficient hot water or running water'</example>
    FOREIGN KEY (business_id) REFERENCES businesses(business_id)
);
```