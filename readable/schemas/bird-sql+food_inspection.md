```sql
-- Database: food_inspection

-- Table: businesses (6358 rows)
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
    owner_address TEXT NULL,
        -- <example>'33 Belden St'</example>
    owner_city TEXT NULL,
        -- <example>'San Francisco'</example>
    owner_state TEXT NULL,
        -- <example>'CA'</example>
    owner_zip TEXT NULL
        -- <example>'94104'</example>
);

-- Table: inspections (23764 rows)
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

-- Table: violations (36050 rows)
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