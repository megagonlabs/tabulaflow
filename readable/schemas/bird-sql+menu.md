```sql
-- Database: menu

/*
Schema: NULL
Table: Dish
Rows: 426713
Sample rows:
| id   | name                       | description   | menus_appeared   | times_appeared   | first_appeared   | last_appeared   | lowest_price   | highest_price   |
|------|----------------------------|---------------|------------------|------------------|------------------|-----------------|----------------|-----------------|
| 1    | Consomme printaniere royal | [NULL]        | 8                | 8                | 1897             | 1927            | 0.2            | 0.4             |
| 2    | Chicken gumbo              | [NULL]        | 111              | 117              | 1895             | 1960            | 0.1            | 0.8             |
| 3    | Tomato aux croutons        | [NULL]        | 14               | 14               | 1893             | 1917            | 0.25           | 0.4             |
| 4    | Onion au gratin            | [NULL]        | 41               | 41               | 1900             | 1971            | 0.25           | 1.0             |
| 5    | St. Emilion                | [NULL]        | 66               | 68               | 1881             | 1981            | 0.0            | 18.0            |
| ...  | ...                        | ...           | ...              | ...              | ...              | ...             | ...            | ...             |
*/
CREATE TABLE Dish (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "name" TEXT NOT NULL,
        -- <example>'Consomme printaniere royal'</example>
    "description" TEXT NULL,
        -- <values>{''}</values>
    "menus_appeared" INTEGER NOT NULL,
        -- <example>8</example>
    "times_appeared" INTEGER NOT NULL,
        -- <example>8</example>
    "first_appeared" INTEGER NOT NULL,
        -- <example>1897</example>
    "last_appeared" INTEGER NOT NULL,
        -- <example>1927</example>
    "lowest_price" REAL NULL,
        -- <example>0.200</example>
    "highest_price" REAL NULL
        -- <example>0.400</example>
);

/*
Schema: NULL
Table: Menu
Rows: 17527
Sample rows:
| id    | name   | sponsor                    | event                | venue      | place                              | physical_description        | occasion   | notes                                                                                                                                                                                                       | call_number   | keywords   | language   | date       | location                   | location_type   | currency   | currency_symbol   | status   | page_count   | dish_count   |
|-------|--------|----------------------------|----------------------|------------|------------------------------------|-----------------------------|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|------------|------------|------------|----------------------------|-----------------|------------|-------------------|----------|--------------|--------------|
| 12463 | [NULL] | HOTEL EASTMAN              | BREAKFAST            | COMMERCIAL | HOT SPRINGS, AR                    | CARD; 4.75X7.5;             | EASTER;    |                                                                                                                                                                                                             | 1900-2822     | [NULL]     | [NULL]     | 1900-04-15 | Hotel Eastman              | [NULL]          | [NULL]     | [NULL]            | complete | 2            | 67           |
| 12464 |        | REPUBLICAN HOUSE           | [DINNER]             | COMMERCIAL | MILWAUKEE, [WI];                   | CARD; ILLUS; COL; 7.0X9.0;  | EASTER;    | WEDGEWOOD BLUE CARD; WHITE EMBOSSED GREEK KEY BORDER; "EASTER SUNDAY" EMBOSSED IN WHITE; VIOLET COLORED SPRAY OF FLOWERS IN UPPER LEFT CORNER;                                                              | 1900-2825     | [NULL]     | [NULL]     | 1900-04-15 | Republican House           | [NULL]          | [NULL]     | [NULL]            | complete | 2            | 34           |
| 12465 | [NULL] | NORDDEUTSCHER LLOYD BREMEN | FRUHSTUCK/BREAKFAST; | COMMERCIAL | DAMPFER KAISER WILHELM DER GROSSE; | CARD; ILLU; COL; 5.5X8.0;   |            | MENU IN GERMAN AND ENGLISH; ILLUS, STEAMSHIP AND SAILING VESSEL;                                                                                                                                            | 1900-2827     | [NULL]     | [NULL]     | 1900-04-16 | Norddeutscher Lloyd Bremen | [NULL]          | [NULL]     | [NULL]            | complete | 2            | 84           |
| 12466 |        | NORDDEUTSCHER LLOYD BREMEN | LUNCH;               | COMMERCIAL | DAMPFER KAISER WILHELM DER GROSSE; | CARD; ILLU; COL; 5.5X8.0;   |            | MENU IN GERMAN AND ENGLISH; ILLUS, HARBOR SCENE WITH SAILING VESSEL;                                                                                                                                        | 1900-2828     | [NULL]     | [NULL]     | 1900-04-16 | Norddeutscher Lloyd Bremen | [NULL]          | [NULL]     | [NULL]            | complete | 2            | 63           |
| 12467 |        | NORDDEUTSCHER LLOYD BREMEN | DINNER;              | COMMERCIAL | DAMPFER KAISER WILHELM DER GROSSE; | FOLDER; ILLU; COL; 5.5X7.5; |            | MENU IN GERMAN AND ENGLISH; ILLUS, HARBOR SCENE WITH ROCKS AND LIGHTHOUSE; STEAMSHIP AND SAILING VES...GERMAN SIDE OF MENU "MONTAG, DEN 16 APRIL 1900"; ON ENGLISH SIDE OF MENU "MONDAY, APRIL 15TH, 1900"; | 1900-2829     | [NULL]     | [NULL]     | 1900-04-16 | Norddeutscher Lloyd Bremen | [NULL]          | [NULL]     | [NULL]            | complete | 4            | 33           |
| ...   | ...    | ...                        | ...                  | ...        | ...                                | ...                         | ...        | ...                                                                                                                                                                                                         | ...           | ...        | ...        | ...        | ...                        | ...             | ...        | ...               | ...      | ...          | ...          |
*/
CREATE TABLE Menu (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>12463</example>
    "name" TEXT NULL,
        -- <example>''</example>
    "sponsor" TEXT NULL,
        -- <example>'HOTEL EASTMAN'</example>
    "event" TEXT NULL,
        -- <example>'BREAKFAST'</example>
    "venue" TEXT NULL,
        -- <example>'COMMERCIAL'</example>
    "place" TEXT NULL,
        -- <example>'HOT SPRINGS, AR'</example>
    "physical_description" TEXT NULL,
        -- <example>'CARD; 4.75X7.5;'</example>
    "occasion" TEXT NULL,
        -- <example>'EASTER;'</example>
    "notes" TEXT NULL,
        -- <example>''</example>
    "call_number" TEXT NULL,
        -- <example>'1900-2822'</example>
    "keywords" TEXT NULL,
    "language" TEXT NULL,
    "date" DATE NULL,
        -- <example>'1900-04-15'</example>
    "location" TEXT NOT NULL,
        -- <example>'Hotel Eastman'</example>
    "location_type" TEXT NULL,
    "currency" TEXT NULL,
        -- <example>'Dollars'</example>
    "currency_symbol" TEXT NULL,
        -- <example>'$'</example>
    "status" TEXT NOT NULL,
        -- <values>{'complete'}</values>
    "page_count" INTEGER NOT NULL,
        -- <example>2</example>
    "dish_count" INTEGER NOT NULL
        -- <example>67</example>
);

/*
Schema: NULL
Table: MenuItem
Rows: 1334410
Sample rows:
| id   | menu_page_id   | price   | high_price   | dish_id   | created_at              | updated_at              | xpos     | ypos     |
|------|----------------|---------|--------------|-----------|-------------------------|-------------------------|----------|----------|
| 1    | 1389           | 0.4     | [NULL]       | 1         | 2011-03-28 15:00:44 UTC | 2011-04-19 04:33:15 UTC | 0.111429 | 0.254735 |
| 2    | 1389           | 0.6     | [NULL]       | 2         | 2011-03-28 15:01:13 UTC | 2011-04-19 15:00:54 UTC | 0.438571 | 0.254735 |
| 3    | 1389           | 0.4     | [NULL]       | 3         | 2011-03-28 15:01:40 UTC | 2011-04-19 19:10:05 UTC | 0.14     | 0.261922 |
| 4    | 1389           | 0.5     | [NULL]       | 4         | 2011-03-28 15:01:51 UTC | 2011-04-19 19:07:01 UTC | 0.377143 | 0.26272  |
| 5    | 3079           | 0.5     | 1.0          | 5         | 2011-03-28 15:21:26 UTC | 2011-04-13 15:25:27 UTC | 0.105714 | 0.313178 |
| ...  | ...            | ...     | ...          | ...       | ...                     | ...                     | ...      | ...      |
*/
CREATE TABLE MenuItem (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "menu_page_id" INTEGER NOT NULL,
        -- <example>1389</example>
        -- <fk> -> MenuPage."id"</fk>
    "price" REAL NULL,
        -- <example>0.400</example>
    "high_price" REAL NULL,
        -- <example>1.000</example>
    "dish_id" INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Dish."id"</fk>
    "created_at" TEXT NOT NULL,
        -- <example>'2011-03-28 15:00:44 UTC'</example>
    "updated_at" TEXT NOT NULL,
        -- <example>'2011-04-19 04:33:15 UTC'</example>
    "xpos" REAL NOT NULL,
        -- <example>0.111</example>
    "ypos" REAL NOT NULL,
        -- <example>0.255</example>
    FOREIGN KEY ("dish_id") REFERENCES Dish("id"),
    FOREIGN KEY ("menu_page_id") REFERENCES MenuPage("id")
);

/*
Schema: NULL
Table: MenuPage
Rows: 66937
Sample rows:
| id   | menu_id   | page_number   | image_id   | full_height   | full_width   | uuid                                 |
|------|-----------|---------------|------------|---------------|--------------|--------------------------------------|
| 119  | 12460     | 1             | 1603595.0  | 7230.0        | 5428.0       | 510d47e4-2955-a3d9-e040-e00a18064a99 |
| 120  | 12460     | 2             | 1603596.0  | 5428.0        | 7230.0       | 510d47e4-2956-a3d9-e040-e00a18064a99 |
| 121  | 12460     | 3             | 1603597.0  | 7230.0        | 5428.0       | 510d47e4-2957-a3d9-e040-e00a18064a99 |
| 122  | 12460     | 4             | 1603598.0  | 7230.0        | 5428.0       | 510d47e4-2958-a3d9-e040-e00a18064a99 |
| 123  | 12461     | 1             | 1603591.0  | 7230.0        | 5428.0       | 510d47e4-2959-a3d9-e040-e00a18064a99 |
| ...  | ...       | ...           | ...        | ...           | ...          | ...                                  |
*/
CREATE TABLE MenuPage (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>119</example>
    "menu_id" INTEGER NOT NULL,
        -- <example>12460</example>
        -- <fk> -> Menu."id"</fk>
    "page_number" INTEGER NULL,
        -- <example>1</example>
    "image_id" REAL NULL,
        -- <example>1603595.000</example>
    "full_height" INTEGER NULL,
        -- <example>7230</example>
    "full_width" INTEGER NULL,
        -- <example>5428</example>
    "uuid" TEXT NOT NULL,
        -- <example>'510d47e4-2955-a3d9-e040-e00a18064a99'</example>
    FOREIGN KEY ("menu_id") REFERENCES Menu("id")
);
```