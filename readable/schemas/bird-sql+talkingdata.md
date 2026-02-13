```sql
-- Database: talkingdata

/*
Table: app_all
Rows: 113211
Sample rows:
| app_id               |
|----------------------|
| -9223281467940916832 |
| -9222877069545393219 |
| -9222785464897897681 |
| -9222198347540756780 |
| -9221970424041518544 |
| ...                  |
*/
CREATE TABLE app_all (
    app_id INTEGER NOT NULL PRIMARY KEY
        -- <example>-9223281467940916832</example>
);

/*
Table: app_events
Rows: 32473067
Sample rows:
| event_id   | app_id               | is_installed   | is_active   |
|------------|----------------------|----------------|-------------|
| 2          | -8942695423876075857 | 1              | 0           |
| 2          | -8022267440849930066 | 1              | 0           |
| 2          | -5720078949152207372 | 1              | 0           |
| 2          | -3725672010020973973 | 1              | 0           |
| 2          | -1758857579862594461 | 1              | 0           |
| ...        | ...                  | ...            | ...         |
*/
CREATE TABLE app_events (
    event_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> events.event_id</fk>
    app_id INTEGER NOT NULL,
        -- <example>-8942695423876075857</example>
    is_installed INTEGER NOT NULL,
        -- <example>1</example>
    is_active INTEGER NOT NULL,
        -- <example>0</example>
    PRIMARY KEY (event_id, app_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id)
);

/*
Table: app_events_relevant
Rows: 3701900
Sample rows:
| event_id   | app_id               | is_installed   | is_active   |
|------------|----------------------|----------------|-------------|
| 2          | -8942695423876075857 | 1              | 0           |
| 2          | -8022267440849930066 | 1              | 0           |
| 2          | -5720078949152207372 | 1              | 0           |
| 2          | -3725672010020973973 | 1              | 0           |
| 2          | -1758857579862594461 | 1              | 0           |
| ...        | ...                  | ...            | ...         |
*/
CREATE TABLE app_events_relevant (
    event_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> events_relevant.event_id</fk>
    app_id INTEGER NOT NULL,
        -- <example>-8942695423876075857</example>
        -- <fk> -> app_all.app_id</fk>
    is_installed INTEGER NOT NULL,
        -- <example>1</example>
    is_active INTEGER NOT NULL,
        -- <example>0</example>
    PRIMARY KEY (event_id, app_id),
    FOREIGN KEY (app_id) REFERENCES app_all(app_id),
    FOREIGN KEY (event_id) REFERENCES events_relevant(event_id)
);

/*
Table: app_labels
Rows: 459943
Sample rows:
| app_id               | label_id   |
|----------------------|------------|
| 7324884708820027918  | 251        |
| -4494216993218550286 | 251        |
| 6058196446775239644  | 406        |
| 6058196446775239644  | 407        |
| 8694625920731541625  | 406        |
| ...                  | ...        |
*/
CREATE TABLE app_labels (
    app_id INTEGER NOT NULL,
        -- <example>7324884708820027918</example>
        -- <fk> -> app_all.app_id</fk>
    label_id INTEGER NOT NULL,
        -- <example>251</example>
        -- <fk> -> label_categories.label_id</fk>
    FOREIGN KEY (app_id) REFERENCES app_all(app_id),
    FOREIGN KEY (label_id) REFERENCES label_categories(label_id)
);

/*
Table: events
Rows: 3252950
Sample rows:
| event_id   | device_id            | timestamp             | longitude   | latitude   |
|------------|----------------------|-----------------------|-------------|------------|
| 1          | 29182687948017175    | 2016-05-01 00:55:25.0 | 121.0       | 31.0       |
| 2          | -6401643145415154744 | 2016-05-01 00:54:12.0 | 104.0       | 31.0       |
| 3          | -4833982096941402721 | 2016-05-01 00:08:05.0 | 107.0       | 30.0       |
| 4          | -6815121365017318426 | 2016-05-01 00:06:40.0 | 104.0       | 23.0       |
| 5          | -5373797595892518570 | 2016-05-01 00:07:18.0 | 116.0       | 29.0       |
| ...        | ...                  | ...                   | ...         | ...        |
*/
CREATE TABLE events (
    event_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    device_id INTEGER NOT NULL,
        -- <example>29182687948017175</example>
    timestamp DATETIME NOT NULL,
        -- <example>'2016-05-01 00:55:25.0'</example>
    longitude REAL NOT NULL,
        -- <example>121.000</example>
    latitude REAL NOT NULL
        -- <example>31.000</example>
);

/*
Table: events_relevant
Rows: 167389
Sample rows:
| event_id   | device_id   | timestamp            | longitude   | latitude   |
|------------|-------------|----------------------|-------------|------------|
| 2          | [NULL]      | -8942695423876075857 | 1.0         | 0.0        |
| 6          | [NULL]      | -8764672938472212518 | 1.0         | 1.0        |
| 7          | [NULL]      | -9050100410106163077 | 1.0         | 0.0        |
| 9          | [NULL]      | -7680145830980282919 | 1.0         | 0.0        |
| 16         | [NULL]      | -9142957261685295367 | 1.0         | 0.0        |
| ...        | ...         | ...                  | ...         | ...        |
*/
CREATE TABLE events_relevant (
    event_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>2</example>
    device_id INTEGER NULL,
        -- <fk> -> gender_age.device_id</fk>
    timestamp DATETIME NOT NULL,
        -- <example>-8942695423876075857</example>
    longitude REAL NOT NULL,
        -- <example>1.000</example>
    latitude REAL NOT NULL,
        -- <example>0.000</example>
    FOREIGN KEY (device_id) REFERENCES gender_age(device_id)
);

/*
Table: gender_age
Rows: 186697
Sample rows:
| device_id            | gender   | age    | group   |
|----------------------|----------|--------|---------|
| -9221086586254644858 | M        | 29.0   | M29-31  |
| -9221079146476055829 | [NULL]   | [NULL] | [NULL]  |
| -9221066489596332354 | M        | 31.0   | M29-31  |
| -9221046405740900422 | M        | 38.0   | M32-38  |
| -9221026417907250887 | F        | 31.0   | F29-32  |
| ...                  | ...      | ...    | ...     |
*/
CREATE TABLE gender_age (
    device_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>-9221086586254644858</example>
        -- <fk> -> phone_brand_device_model2.device_id</fk>
    gender TEXT NULL,
        -- <values>{'F', 'M'}</values>
    age INTEGER NULL,
        -- <example>29</example>
    group TEXT NULL,
        -- <values>{'F23-', 'F24-26', 'F27-28', 'F29-32', 'F33-42', 'F43+', 'M22-', 'M23-26', 'M27-28', 'M29-31', 'M32-38', 'M39+'}</values>
    FOREIGN KEY (device_id) REFERENCES phone_brand_device_model2(device_id)
);

/*
Table: gender_age_test
Rows: 112071
Sample rows:
| device_id            |
|----------------------|
| -9223321966609553846 |
| -9223042152723782980 |
| -9222896629442493034 |
| -9222894989445037972 |
| -9222894319703307262 |
| ...                  |
*/
CREATE TABLE gender_age_test (
    device_id INTEGER NOT NULL PRIMARY KEY
        -- <example>-9223321966609553846</example>
);

/*
Table: gender_age_train
Rows: 74645
Sample rows:
| device_id            | gender   | age   | group   |
|----------------------|----------|-------|---------|
| -9223067244542181226 | M        | 24    | M23-26  |
| -9222956879900151005 | M        | 36    | M32-38  |
| -9222754701995937853 | M        | 29    | M29-31  |
| -9222352239947207574 | M        | 23    | M23-26  |
| -9222173362545970626 | F        | 56    | F43+    |
| ...                  | ...      | ...   | ...     |
*/
CREATE TABLE gender_age_train (
    device_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>-9223067244542181226</example>
    gender TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    age INTEGER NOT NULL,
        -- <example>24</example>
    group TEXT NOT NULL
        -- <values>{'F23-', 'F24-26', 'F27-28', 'F29-32', 'F33-42', 'F43+', 'M22-', 'M23-26', 'M27-28', 'M29-31', 'M32-38', 'M39+'}</values>
);

/*
Table: label_categories
Rows: 930
Sample rows:
| label_id   | category          |
|------------|-------------------|
| 1          | [NULL]            |
| 2          | game-game type    |
| 3          | game-Game themes  |
| 4          | game-Art Style    |
| 5          | game-Leisure time |
| ...        | ...               |
*/
CREATE TABLE label_categories (
    label_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    category TEXT NULL
        -- <example>'game-game type'</example>
);

/*
Table: phone_brand_device_model2
Rows: 89200
Sample rows:
| device_id            | phone_brand   | device_model   |
|----------------------|---------------|----------------|
| -9223321966609553846 | 小米          | 红米note       |
| -9223067244542181226 | vivo          | Y19T           |
| -9223042152723782980 | 小米          | MI 3           |
| -9222956879900151005 | 三星          | Galaxy Note 2  |
| -9222896629442493034 | OPPO          | A31            |
| ...                  | ...           | ...            |
*/
CREATE TABLE phone_brand_device_model2 (
    device_id INTEGER NOT NULL,
        -- <example>-9223321966609553846</example>
    phone_brand TEXT NOT NULL,
        -- <example>'小米'</example>
    device_model TEXT NOT NULL,
        -- <example>'红米note'</example>
    PRIMARY KEY (device_id, phone_brand, device_model)
);

/*
Table: sample_submission
Rows: 13700
Sample rows:
| device_id            | F23-   | F24-26   | F27-28   | F29-32   | F33-42   | F43+   | M22-   | M23-26   | M27-28   | M29-31   | M32-38   | M39+   |
|----------------------|--------|----------|----------|----------|----------|--------|--------|----------|----------|----------|----------|--------|
| -9223321966609553846 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 |
| -9223042152723782980 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 |
| -9222896629442493034 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 |
| -9222894989445037972 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 |
| -9222894319703307262 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 | 0.0833 | 0.0833   | 0.0833   | 0.0833   | 0.0833   | 0.0833 |
| ...                  | ...    | ...      | ...      | ...      | ...      | ...    | ...    | ...      | ...      | ...      | ...      | ...    |
*/
CREATE TABLE sample_submission (
    device_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>-9223321966609553846</example>
    "F23-" REAL NOT NULL,
        -- <example>0.083</example>
    "F24-26" REAL NOT NULL,
        -- <example>0.083</example>
    "F27-28" REAL NOT NULL,
        -- <example>0.083</example>
    "F29-32" REAL NOT NULL,
        -- <example>0.083</example>
    "F33-42" REAL NOT NULL,
        -- <example>0.083</example>
    "F43+" REAL NOT NULL,
        -- <example>0.083</example>
    "M22-" REAL NOT NULL,
        -- <example>0.083</example>
    "M23-26" REAL NOT NULL,
        -- <example>0.083</example>
    "M27-28" REAL NOT NULL,
        -- <example>0.083</example>
    "M29-31" REAL NOT NULL,
        -- <example>0.083</example>
    "M32-38" REAL NOT NULL,
        -- <example>0.083</example>
    "M39+" REAL NOT NULL
        -- <example>0.083</example>
);
```