```sql
-- Database: talkingdata

-- Table: app_all (113211 rows)
CREATE TABLE app_all (
    app_id INTEGER NOT NULL PRIMARY KEY
        -- <example>-9223281467940916832</example>
);

-- Table: app_events (32473067 rows)
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

-- Table: app_events_relevant (3701900 rows)
CREATE TABLE app_events_relevant (
    event_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> events_relevant.event_id</fk>
    app_id INTEGER NOT NULL,
        -- <example>-8942695423876075857</example>
        -- <fk> -> app_all.app_id</fk>
    is_installed INTEGER NULL,
        -- <example>1</example>
    is_active INTEGER NULL,
        -- <example>0</example>
    PRIMARY KEY (event_id, app_id),
    FOREIGN KEY (app_id) REFERENCES app_all(app_id),
    FOREIGN KEY (event_id) REFERENCES events_relevant(event_id)
);

-- Table: app_labels (459943 rows)
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

-- Table: events (3252950 rows)
CREATE TABLE events (
    event_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    device_id INTEGER NULL,
        -- <example>29182687948017175</example>
    timestamp DATETIME NULL,
        -- <example>'2016-05-01 00:55:25.0'</example>
    longitude REAL NULL,
        -- <example>121.000</example>
    latitude REAL NULL
        -- <example>31.000</example>
);

-- Table: events_relevant (167389 rows)
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

-- Table: gender_age (186697 rows)
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

-- Table: gender_age_test (112071 rows)
CREATE TABLE gender_age_test (
    device_id INTEGER NOT NULL PRIMARY KEY
        -- <example>-9223321966609553846</example>
);

-- Table: gender_age_train (74645 rows)
CREATE TABLE gender_age_train (
    device_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>-9223067244542181226</example>
    gender TEXT NULL,
        -- <values>{'F', 'M'}</values>
    age INTEGER NULL,
        -- <example>24</example>
    group TEXT NULL
        -- <values>{'F23-', 'F24-26', 'F27-28', 'F29-32', 'F33-42', 'F43+', 'M22-', 'M23-26', 'M27-28', 'M29-31', 'M32-38', 'M39+'}</values>
);

-- Table: label_categories (930 rows)
CREATE TABLE label_categories (
    label_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    category TEXT NULL
        -- <example>'game-game type'</example>
);

-- Table: phone_brand_device_model2 (89200 rows)
CREATE TABLE phone_brand_device_model2 (
    device_id INTEGER NOT NULL,
        -- <example>-9223321966609553846</example>
    phone_brand TEXT NOT NULL,
        -- <example>'小米'</example>
    device_model TEXT NOT NULL,
        -- <example>'红米note'</example>
    PRIMARY KEY (device_id, phone_brand, device_model)
);

-- Table: sample_submission (13700 rows)
CREATE TABLE sample_submission (
    device_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>-9223321966609553846</example>
    "F23-" REAL NULL,
        -- <example>0.083</example>
    "F24-26" REAL NULL,
        -- <example>0.083</example>
    "F27-28" REAL NULL,
        -- <example>0.083</example>
    "F29-32" REAL NULL,
        -- <example>0.083</example>
    "F33-42" REAL NULL,
        -- <example>0.083</example>
    "F43+" REAL NULL,
        -- <example>0.083</example>
    "M22-" REAL NULL,
        -- <example>0.083</example>
    "M23-26" REAL NULL,
        -- <example>0.083</example>
    "M27-28" REAL NULL,
        -- <example>0.083</example>
    "M29-31" REAL NULL,
        -- <example>0.083</example>
    "M32-38" REAL NULL,
        -- <example>0.083</example>
    "M39+" REAL NULL
        -- <example>0.083</example>
);
```