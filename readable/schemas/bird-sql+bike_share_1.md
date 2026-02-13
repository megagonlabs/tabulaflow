```sql
-- Database: bike_share_1

/*
Table: station
Rows: 70
Sample rows:
| id   | name                              | lat                | long                | dock_count   | city     | installation_date   |
|------|-----------------------------------|--------------------|---------------------|--------------|----------|---------------------|
| 2    | San Jose Diridon Caltrain Station | 37.329732          | -121.90178200000001 | 27           | San Jose | 8/6/2013            |
| 3    | San Jose Civic Center             | 37.330698          | -121.888979         | 15           | San Jose | 8/5/2013            |
| 4    | Santa Clara at Almaden            | 37.333988          | -121.894902         | 11           | San Jose | 8/6/2013            |
| 5    | Adobe on Almaden                  | 37.331415          | -121.8932           | 19           | San Jose | 8/5/2013            |
| 6    | San Pedro Square                  | 37.336721000000004 | -121.894074         | 15           | San Jose | 8/7/2013            |
| ...  | ...                               | ...                | ...                 | ...          | ...      | ...                 |
*/
CREATE TABLE station (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>2</example>
    name TEXT NOT NULL,
        -- <example>'San Jose Diridon Caltrain Station'</example>
    lat REAL NOT NULL,
        -- <example>37.330</example>
    long REAL NOT NULL,
        -- <example>-121.902</example>
    dock_count INTEGER NOT NULL,
        -- <example>27</example>
    city TEXT NOT NULL,
        -- <values>{'Mountain View', 'Palo Alto', 'Redwood City', 'San Francisco', 'San Jose'}</values>
    installation_date TEXT NOT NULL
        -- <example>'8/6/2013'</example>
);

/*
Table: status
Rows: 71984434
Sample rows:
| station_id   | bikes_available   | docks_available   | time                |
|--------------|-------------------|-------------------|---------------------|
| 2            | 2                 | 25                | 2013/08/29 12:06:01 |
| 2            | 2                 | 25                | 2013/08/29 12:07:01 |
| 2            | 2                 | 25                | 2013/08/29 12:08:01 |
| 2            | 2                 | 25                | 2013/08/29 12:09:01 |
| 2            | 2                 | 25                | 2013/08/29 12:10:01 |
| ...          | ...               | ...               | ...                 |
*/
CREATE TABLE status (
    station_id INTEGER NOT NULL,
        -- <example>2</example>
    bikes_available INTEGER NOT NULL,
        -- <example>2</example>
    docks_available INTEGER NOT NULL,
        -- <example>25</example>
    time TEXT NOT NULL
        -- <example>'2013/08/29 12:06:01'</example>
);

/*
Table: trip
Rows: 658901
Sample rows:
| id   | duration   | start_date     | start_station_name       | start_station_id   | end_date       | end_station_name                        | end_station_id   | bike_id   | subscription_type   | zip_code   |
|------|------------|----------------|--------------------------|--------------------|----------------|-----------------------------------------|------------------|-----------|---------------------|------------|
| 4069 | 174        | 8/29/2013 9:08 | 2nd at South Park        | 64                 | 8/29/2013 9:11 | 2nd at South Park                       | 64               | 288       | Subscriber          | 94114      |
| 4073 | 1067       | 8/29/2013 9:24 | South Van Ness at Market | 66                 | 8/29/2013 9:42 | San Francisco Caltrain 2 (330 Townsend) | 69               | 321       | Subscriber          | 94703      |
| 4074 | 1131       | 8/29/2013 9:24 | South Van Ness at Market | 66                 | 8/29/2013 9:43 | San Francisco Caltrain 2 (330 Townsend) | 69               | 317       | Subscriber          | 94115      |
| 4075 | 1117       | 8/29/2013 9:24 | South Van Ness at Market | 66                 | 8/29/2013 9:43 | San Francisco Caltrain 2 (330 Townsend) | 69               | 316       | Subscriber          | 94122      |
| 4076 | 1118       | 8/29/2013 9:25 | South Van Ness at Market | 66                 | 8/29/2013 9:43 | San Francisco Caltrain 2 (330 Townsend) | 69               | 322       | Subscriber          | 94597      |
| ...  | ...        | ...            | ...                      | ...                | ...            | ...                                     | ...              | ...       | ...                 | ...        |
*/
CREATE TABLE trip (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>4069</example>
    duration INTEGER NOT NULL,
        -- <example>174</example>
    start_date TEXT NOT NULL,
        -- <example>'8/29/2013 9:08'</example>
    start_station_name TEXT NOT NULL,
        -- <example>'2nd at South Park'</example>
    start_station_id INTEGER NOT NULL,
        -- <example>64</example>
    end_date TEXT NOT NULL,
        -- <example>'8/29/2013 9:11'</example>
    end_station_name TEXT NOT NULL,
        -- <example>'2nd at South Park'</example>
    end_station_id INTEGER NOT NULL,
        -- <example>64</example>
    bike_id INTEGER NOT NULL,
        -- <example>288</example>
    subscription_type TEXT NOT NULL,
        -- <values>{'Customer', 'Subscriber'}</values>
    zip_code INTEGER NULL
        -- <example>94114</example>
);

/*
Table: weather
Rows: 3665
Sample rows:
| date      | max_temperature_f   | mean_temperature_f   | min_temperature_f   | max_dew_point_f   | mean_dew_point_f   | min_dew_point_f   | max_humidity   | mean_humidity   | min_humidity   | max_sea_level_pressure_inches   | mean_sea_level_pressure_inches   | min_sea_level_pressure_inches   | max_visibility_miles   | mean_visibility_miles   | min_visibility_miles   | max_wind_Speed_mph   | mean_wind_speed_mph   | max_gust_speed_mph   | precipitation_inches   | cloud_cover   | events   | wind_dir_degrees   | zip_code   |
|-----------|---------------------|----------------------|---------------------|-------------------|--------------------|-------------------|----------------|-----------------|----------------|---------------------------------|----------------------------------|---------------------------------|------------------------|-------------------------|------------------------|----------------------|-----------------------|----------------------|------------------------|---------------|----------|--------------------|------------|
| 8/29/2013 | 74                  | 68                   | 61                  | 61                | 58                 | 56                | 93             | 75              | 57             | 30.07                           | 30.02                            | 29.97                           | 10                     | 10                      | 10                     | 23                   | 11                    | 28                   | 0                      | 4             |          | 286                | 94107      |
| 8/30/2013 | 78                  | 69                   | 60                  | 61                | 58                 | 56                | 90             | 70              | 50             | 30.05                           | 30.0                             | 29.93                           | 10                     | 10                      | 7                      | 29                   | 13                    | 35                   | 0                      | 2             |          | 291                | 94107      |
| 8/31/2013 | 71                  | 64                   | 57                  | 57                | 56                 | 54                | 93             | 75              | 57             | 30.0                            | 29.96                            | 29.92                           | 10                     | 10                      | 10                     | 26                   | 15                    | 31                   | 0                      | 4             |          | 284                | 94107      |
| 9/1/2013  | 74                  | 66                   | 58                  | 60                | 56                 | 53                | 87             | 68              | 49             | 29.96                           | 29.93                            | 29.91                           | 10                     | 10                      | 10                     | 25                   | 13                    | 29                   | 0                      | 4             |          | 284                | 94107      |
| 9/2/2013  | 75                  | 69                   | 62                  | 61                | 60                 | 58                | 93             | 77              | 61             | 29.97                           | 29.94                            | 29.9                            | 10                     | 10                      | 6                      | 23                   | 12                    | 30                   | 0                      | 6             |          | 277                | 94107      |
| ...       | ...                 | ...                  | ...                 | ...               | ...                | ...               | ...            | ...             | ...            | ...                             | ...                              | ...                             | ...                    | ...                     | ...                    | ...                  | ...                   | ...                  | ...                    | ...           | ...      | ...                | ...        |
*/
CREATE TABLE weather (
    date TEXT NOT NULL,
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
    precipitation_inches TEXT NOT NULL,
        -- <example>'0'</example>
    cloud_cover INTEGER NULL,
        -- <example>4</example>
    events TEXT NOT NULL,
        -- <values>{'', 'Fog', 'Fog-Rain', 'Rain', 'Rain-Thunderstorm', 'rain'}</values>
    wind_dir_degrees INTEGER NULL,
        -- <example>286</example>
    zip_code TEXT NOT NULL
        -- <values>{'94041', '94063', '94107', '94301', '95113'}</values>
);
```