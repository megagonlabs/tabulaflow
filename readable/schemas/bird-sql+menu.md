```sql
-- Database: menu

-- Table: Dish (426713 rows)
CREATE TABLE Dish (
    id INTEGER PRIMARY KEY,  -- e.g. 1
    name TEXT,  -- e.g. 'Consomme printaniere royal'
    description TEXT,  -- values: {''}
    menus_appeared INTEGER,  -- e.g. 8
    times_appeared INTEGER,  -- e.g. 8
    first_appeared INTEGER,  -- e.g. 1897
    last_appeared INTEGER,  -- e.g. 1927
    lowest_price REAL,  -- e.g. 0.200
    highest_price REAL  -- e.g. 0.400
);

-- Table: Menu (17527 rows)
CREATE TABLE Menu (
    id INTEGER PRIMARY KEY,  -- e.g. 12463
    name TEXT,  -- e.g. ''
    sponsor TEXT,  -- e.g. 'HOTEL EASTMAN'
    event TEXT,  -- e.g. 'BREAKFAST'
    venue TEXT,  -- e.g. 'COMMERCIAL'
    place TEXT,  -- e.g. 'HOT SPRINGS, AR'
    physical_description TEXT,  -- e.g. 'CARD; 4.75X7.5;'
    occasion TEXT,  -- e.g. 'EASTER;'
    notes TEXT,  -- e.g. ''
    call_number TEXT,  -- e.g. '1900-2822'
    keywords TEXT,
    language TEXT,
    date DATE,  -- e.g. '1900-04-15'
    location TEXT,  -- e.g. 'Hotel Eastman'
    location_type TEXT,
    currency TEXT,  -- e.g. 'Dollars'
    currency_symbol TEXT,  -- e.g. '$'
    status TEXT,  -- values: {'complete'}
    page_count INTEGER,  -- e.g. 2
    dish_count INTEGER  -- e.g. 67
);

-- Table: MenuItem (1334410 rows)
CREATE TABLE MenuItem (
    id INTEGER PRIMARY KEY,  -- e.g. 1
    menu_page_id INTEGER,  -- e.g. 1389; FK -> MenuPage.id
    price REAL,  -- e.g. 0.400
    high_price REAL,  -- e.g. 1.000
    dish_id INTEGER,  -- e.g. 1; FK -> Dish.id
    created_at TEXT,  -- e.g. '2011-03-28 15:00:44 UTC'
    updated_at TEXT,  -- e.g. '2011-04-19 04:33:15 UTC'
    xpos REAL,  -- e.g. 0.111
    ypos REAL,  -- e.g. 0.255
    FOREIGN KEY (dish_id) REFERENCES Dish(id),
    FOREIGN KEY (menu_page_id) REFERENCES MenuPage(id)
);

-- Table: MenuPage (66937 rows)
CREATE TABLE MenuPage (
    id INTEGER PRIMARY KEY,  -- e.g. 119
    menu_id INTEGER,  -- e.g. 12460; FK -> Menu.id
    page_number INTEGER,  -- e.g. 1
    image_id REAL,  -- e.g. 1603595.000
    full_height INTEGER,  -- e.g. 7230
    full_width INTEGER,  -- e.g. 5428
    uuid TEXT,  -- e.g. '510d47e4-2955-a3d9-e040-e00a18064a99'
    FOREIGN KEY (menu_id) REFERENCES Menu(id)
);
```