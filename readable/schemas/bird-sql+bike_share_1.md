```sql
-- Database: bike_share_1

-- Table: station (70 rows)
CREATE TABLE station (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>2</example>
    name TEXT NULL,
        -- <example>'San Jose Diridon Caltrain Station'</example>
    lat REAL NULL,
        -- <example>37.330</example>
    long REAL NULL,
        -- <example>-121.902</example>
    dock_count INTEGER NULL,
        -- <example>27</example>
    city TEXT NULL,
        -- <values>{'Mountain View', 'Palo Alto', 'Redwood City', 'San Francisco', 'San Jose'}</values>
    installation_date TEXT NULL
        -- <example>'8/6/2013'</example>
);

-- Table: status (71984434 rows)
CREATE TABLE status (
    station_id INTEGER NULL,
        -- <example>2</example>
    bikes_available INTEGER NULL,
        -- <example>2</example>
    docks_available INTEGER NULL,
        -- <example>25</example>
    time TEXT NULL
        -- <example>'2013/08/29 12:06:01'</example>
);

-- Table: trip (658901 rows)
CREATE TABLE trip (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>4069</example>
    duration INTEGER NULL,
        -- <example>174</example>
    start_date TEXT NULL,
        -- <example>'8/29/2013 9:08'</example>
    start_station_name TEXT NULL,
        -- <example>'2nd at South Park'</example>
    start_station_id INTEGER NULL,
        -- <example>64</example>
    end_date TEXT NULL,
        -- <example>'8/29/2013 9:11'</example>
    end_station_name TEXT NULL,
        -- <example>'2nd at South Park'</example>
    end_station_id INTEGER NULL,
        -- <example>64</example>
    bike_id INTEGER NULL,
        -- <example>288</example>
    subscription_type TEXT NULL,
        -- <values>{'Customer', 'Subscriber'}</values>
    zip_code INTEGER NULL
        -- <example>94114</example>
);

-- Table: weather (3665 rows)
CREATE TABLE weather (
    date TEXT NULL,
        -- <example>'8/29/2013'</example>
    max_temperature_f INTEGER NULL,
        -- <example>74</example>
    mean_temperature_f INTEGER NULL,
        -- <example>68</example>
    min_temperature_f INTEGER NULL,
        -- <example>61</example>
    max_dew_point_f INTEGER NULL,
        -- <example>61</example>
    mean_dew_point_f INTEGER NULL,
        -- <example>58</example>
    min_dew_point_f INTEGER NULL,
        -- <example>56</example>
    max_humidity INTEGER NULL,
        -- <example>93</example>
    mean_humidity INTEGER NULL,
        -- <example>75</example>
    min_humidity INTEGER NULL,
        -- <example>57</example>
    max_sea_level_pressure_inches REAL NULL,
        -- <example>30.070</example>
    mean_sea_level_pressure_inches REAL NULL,
        -- <example>30.020</example>
    min_sea_level_pressure_inches REAL NULL,
        -- <example>29.970</example>
    max_visibility_miles INTEGER NULL,
        -- <example>10</example>
    mean_visibility_miles INTEGER NULL,
        -- <example>10</example>
    min_visibility_miles INTEGER NULL,
        -- <example>10</example>
    max_wind_Speed_mph INTEGER NULL,
        -- <example>23</example>
    mean_wind_speed_mph INTEGER NULL,
        -- <example>11</example>
    max_gust_speed_mph INTEGER NULL,
        -- <example>28</example>
    precipitation_inches TEXT NULL,
        -- <example>'0'</example>
    cloud_cover INTEGER NULL,
        -- <example>4</example>
    events TEXT NULL,
        -- <values>{'', 'Fog', 'Fog-Rain', 'Rain', 'Rain-Thunderstorm', 'rain'}</values>
    wind_dir_degrees INTEGER NULL,
        -- <example>286</example>
    zip_code TEXT NULL
        -- <values>{'94041', '94063', '94107', '94301', '95113'}</values>
);
```