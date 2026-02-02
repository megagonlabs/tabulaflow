```sql
-- Database: menu

-- Table: Dish (426713 rows)
CREATE TABLE Dish (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NULL,
        -- <example>'Consomme printaniere royal'</example>
    description TEXT NULL,
        -- <values>{''}</values>
    menus_appeared INTEGER NULL,
        -- <example>8</example>
    times_appeared INTEGER NULL,
        -- <example>8</example>
    first_appeared INTEGER NULL,
        -- <example>1897</example>
    last_appeared INTEGER NULL,
        -- <example>1927</example>
    lowest_price REAL NULL,
        -- <example>0.200</example>
    highest_price REAL NULL
        -- <example>0.400</example>
);

-- Table: Menu (17527 rows)
CREATE TABLE Menu (
    id INTEGER NULL PRIMARY KEY,
        -- <example>12463</example>
    name TEXT NULL,
        -- <example>''</example>
    sponsor TEXT NULL,
        -- <example>'HOTEL EASTMAN'</example>
    event TEXT NULL,
        -- <example>'BREAKFAST'</example>
    venue TEXT NULL,
        -- <example>'COMMERCIAL'</example>
    place TEXT NULL,
        -- <example>'HOT SPRINGS, AR'</example>
    physical_description TEXT NULL,
        -- <example>'CARD; 4.75X7.5;'</example>
    occasion TEXT NULL,
        -- <example>'EASTER;'</example>
    notes TEXT NULL,
        -- <example>''</example>
    call_number TEXT NULL,
        -- <example>'1900-2822'</example>
    keywords TEXT NULL,
    language TEXT NULL,
    date DATE NULL,
        -- <example>'1900-04-15'</example>
    location TEXT NULL,
        -- <example>'Hotel Eastman'</example>
    location_type TEXT NULL,
    currency TEXT NULL,
        -- <example>'Dollars'</example>
    currency_symbol TEXT NULL,
        -- <example>'$'</example>
    status TEXT NULL,
        -- <values>{'complete'}</values>
    page_count INTEGER NULL,
        -- <example>2</example>
    dish_count INTEGER NULL
        -- <example>67</example>
);

-- Table: MenuItem (1334410 rows)
CREATE TABLE MenuItem (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    menu_page_id INTEGER NULL,
        -- <example>1389</example>
        -- <fk> -> MenuPage.id</fk>
    price REAL NULL,
        -- <example>0.400</example>
    high_price REAL NULL,
        -- <example>1.000</example>
    dish_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Dish.id</fk>
    created_at TEXT NULL,
        -- <example>'2011-03-28 15:00:44 UTC'</example>
    updated_at TEXT NULL,
        -- <example>'2011-04-19 04:33:15 UTC'</example>
    xpos REAL NULL,
        -- <example>0.111</example>
    ypos REAL NULL,
        -- <example>0.255</example>
    FOREIGN KEY (dish_id) REFERENCES Dish(id),
    FOREIGN KEY (menu_page_id) REFERENCES MenuPage(id)
);

-- Table: MenuPage (66937 rows)
CREATE TABLE MenuPage (
    id INTEGER NULL PRIMARY KEY,
        -- <example>119</example>
    menu_id INTEGER NULL,
        -- <example>12460</example>
        -- <fk> -> Menu.id</fk>
    page_number INTEGER NULL,
        -- <example>1</example>
    image_id REAL NULL,
        -- <example>1603595.000</example>
    full_height INTEGER NULL,
        -- <example>7230</example>
    full_width INTEGER NULL,
        -- <example>5428</example>
    uuid TEXT NULL,
        -- <example>'510d47e4-2955-a3d9-e040-e00a18064a99'</example>
    FOREIGN KEY (menu_id) REFERENCES Menu(id)
);
```