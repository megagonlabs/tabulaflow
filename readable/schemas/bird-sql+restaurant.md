```sql
-- Database: restaurant

-- Table: generalinfo (9590 rows)
CREATE TABLE generalinfo (
    id_restaurant INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    label TEXT NULL,
        -- <example>'sparky's diner'</example>
    food_type TEXT NULL,
        -- <example>'24 hour diner'</example>
    city TEXT NULL,
        -- <example>'san francisco'</example>
        -- <fk> -> geographic.city</fk>
    review REAL NULL,
        -- <example>2.300</example>
    FOREIGN KEY (city) REFERENCES geographic(city)
);

-- Table: geographic (168 rows)
CREATE TABLE geographic (
    city TEXT NOT NULL PRIMARY KEY,
        -- <example>'alameda'</example>
    county TEXT NULL,
        -- <example>'alameda county'</example>
    region TEXT NULL
        -- <values>{'bay area', 'lake tahoe', 'los angeles area', 'monterey', 'napa valley', 'northern california', 'sacramento area', 'unknown', 'yosemite and mono lake area'}</values>
);

-- Table: location (9539 rows)
CREATE TABLE location (
    id_restaurant INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> generalinfo.id_restaurant</fk>
    street_num INTEGER NULL,
        -- <example>242</example>
    street_name TEXT NULL,
        -- <example>'church st'</example>
    city TEXT NULL,
        -- <example>'san francisco'</example>
        -- <fk> -> geographic.city</fk>
    FOREIGN KEY (city) REFERENCES geographic(city),
    FOREIGN KEY (id_restaurant) REFERENCES generalinfo(id_restaurant)
);
```