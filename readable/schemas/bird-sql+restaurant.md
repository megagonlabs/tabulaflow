```sql
-- Database: restaurant

-- Table: generalinfo (9590 rows)
CREATE TABLE generalinfo (
    id_restaurant INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    label TEXT,  -- e.g. 'sparky's diner'
    food_type TEXT,  -- e.g. '24 hour diner'
    city TEXT,  -- e.g. 'san francisco'; FK -> geographic.city
    review REAL,  -- e.g. 2.300
    FOREIGN KEY (city) REFERENCES geographic(city)
);

-- Table: geographic (168 rows)
CREATE TABLE geographic (
    city TEXT NOT NULL PRIMARY KEY,  -- e.g. 'alameda'
    county TEXT,  -- e.g. 'alameda county'
    region TEXT  -- values: {'bay area', 'lake tahoe', 'los angeles area', 'monterey', 'napa valley', 'northern california', 'sacramento area', 'unknown', 'yosemite and mono lake area'}
);

-- Table: location (9539 rows)
CREATE TABLE location (
    id_restaurant INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1; FK -> generalinfo.id_restaurant
    street_num INTEGER,  -- e.g. 242
    street_name TEXT,  -- e.g. 'church st'
    city TEXT,  -- e.g. 'san francisco'; FK -> geographic.city
    FOREIGN KEY (city) REFERENCES geographic(city),
    FOREIGN KEY (id_restaurant) REFERENCES generalinfo(id_restaurant)
);
```