```sql
-- Database: AIRLINES

/*
Schema: airlinesTable: aircrafts_data
Rows: 9
All rows:
| aircraft_code   | model                                                      |   range |
|-----------------|------------------------------------------------------------|---------|
| 773             | {"en": "Boeing 777-300", "ru": "Боинг 777-300"}            |   11100 |
| 763             | {"en": "Boeing 767-300", "ru": "Боинг 767-300"}            |    7900 |
| SU9             | {"en": "Sukhoi Superjet-100", "ru": "Сухой Суперджет-100"} |    3000 |
| 320             | {"en": "Airbus A320-200", "ru": "Аэробус A320-200"}        |    5700 |
| 321             | {"en": "Airbus A321-200", "ru": "Аэробус A321-200"}        |    5600 |
| 319             | {"en": "Airbus A319-100", "ru": "Аэробус A319-100"}        |    6700 |
| 733             | {"en": "Boeing 737-300", "ru": "Боинг 737-300"}            |    4200 |
| CN1             | {"en": "Cessna 208 Caravan", "ru": "Сессна 208 Караван"}   |    1200 |
| CR2             | {"en": "Bombardier CRJ-200", "ru": "Бомбардье CRJ-200"}    |    2700 |
*/
CREATE TABLE airlines.aircrafts_data (
    aircraft_code VARCHAR NOT NULL,
        -- <values>{'319', '320', '321', '733', '763', '773', 'CN1', 'CR2', 'SU9'}</values>
    model VARCHAR NOT NULL,
        -- <values>{'{"en": "Airbus A319-100", "ru": "Аэробус A319-100"}', '{"en": "Airbus A320-200", "ru": "Аэробус A320-200"}', '{"en": "Airbus A321-200", "ru": "Аэробус A321-200"}', '{"en": "Boeing 737-300", "ru": "Боинг 737-300"}', '{"en": "Boeing 767-300", "ru": "Боинг 767-300"}', '{"en": "Boeing 777-300", "ru": "Боинг 777-300"}', '{"en": "Bombardier CRJ-200", "ru": "Бомбардье CRJ-200"}', '{"en": "Cessna 208 Caravan", "ru": "Сессна 208 Караван"}', '{"en": "Sukhoi Superjet-100", "ru": "Сухой Суперджет-100"}'}</values>
    range DECIMAL NOT NULL
        -- <example>11100</example>
);

/*
Schema: airlinesTable: airports_data
Rows: 104
Sample rows:
| airport_code   | airport_name                                               | city                                                      | coordinates                               | timezone         |
|----------------|------------------------------------------------------------|-----------------------------------------------------------|-------------------------------------------|------------------|
| YKS            | {"en": "Yakutsk Airport", "ru": "Якутск"}                  | {"en": "Yakutsk", "ru": "Якутск"}                         | (129.77099609375,62.0932998657226562)     | Asia/Yakutsk     |
| MJZ            | {"en": "Mirny Airport", "ru": "Мирный"}                    | {"en": "Mirnyj", "ru": "Мирный"}                          | (114.03900146484375,62.534698486328125)   | Asia/Yakutsk     |
| KHV            | {"en": "Khabarovsk-Novy Airport", "ru": "Хабаровск-Новый"} | {"en": "Khabarovsk", "ru": "Хабаровск"}                   | (135.18800354004,48.5279998779300001)     | Asia/Vladivostok |
| PKC            | {"en": "Yelizovo Airport", "ru": "Елизово"}                | {"en": "Petropavlovsk", "ru": "Петропавловск-Камчатский"} | (158.453994750976562,53.1679000854492188) | Asia/Kamchatka   |
| UUS            | {"en": "Yuzhno-Sakhalinsk Airport", "ru": "Хомутово"}      | {"en": "Yuzhno-Sakhalinsk", "ru": "Южно-Сахалинск"}       | (142.718002319335938,46.8886985778808594) | Asia/Sakhalin    |
| ...            | ...                                                        | ...                                                       | ...                                       | ...              |
*/
CREATE TABLE airlines.airports_data (
    airport_code VARCHAR NOT NULL,
        -- <example>'MJZ'</example>
    airport_name VARCHAR NOT NULL,
        -- <example>'{"en": "Stavropol Shpakovskoye Airport", "ru": "Ставрополь"}'</example>
    city VARCHAR NOT NULL,
        -- <example>'{"en": "Samara", "ru": "Самара"}'</example>
    coordinates VARCHAR NOT NULL,
        -- <example>'(114.03900146484375,62.534698486328125)'</example>
    timezone VARCHAR NOT NULL
        -- <example>'Asia/Sakhalin'</example>
);

/*
Schema: airlinesTable: boarding_passes
Rows: 579686
Sample rows:
| ticket_no     | flight_id   | boarding_no   | seat_no   |
|---------------|-------------|---------------|-----------|
| 0005435212351 | 30625       | 1             | 2D        |
| 0005435212386 | 30625       | 2             | 3G        |
| 0005435212381 | 30625       | 3             | 4H        |
| 0005432211370 | 30625       | 4             | 5D        |
| 0005435212357 | 30625       | 5             | 11A       |
| ...           | ...         | ...           | ...       |
*/
CREATE TABLE airlines.boarding_passes (
    ticket_no VARCHAR NOT NULL,
        -- <example>'0005435212381'</example>
    flight_id DECIMAL NOT NULL,
        -- <example>30625</example>
    boarding_no DECIMAL NOT NULL,
        -- <example>1</example>
    seat_no VARCHAR NOT NULL
        -- <example>'11A'</example>
);

/*
Schema: airlinesTable: bookings
Rows: 262788
Sample rows:
| book_ref   | book_date              | total_amount   |
|------------|------------------------|----------------|
| 00000F     | 2017-07-05 03:12:00+03 | 265700         |
| 000012     | 2017-07-14 09:02:00+03 | 37900          |
| 000068     | 2017-08-15 14:27:00+03 | 18100          |
| 000181     | 2017-08-10 13:28:00+03 | 131800         |
| 0002D8     | 2017-08-07 21:40:00+03 | 23600          |
| ...        | ...                    | ...            |
*/
CREATE TABLE airlines.bookings (
    book_ref VARCHAR NOT NULL,
        -- <example>'00000F'</example>
    book_date VARCHAR NOT NULL,
        -- <example>'2017-08-09 02:14:00+03'</example>
    total_amount DECIMAL NOT NULL
        -- <example>265700</example>
);

/*
Schema: airlinesTable: flights
Rows: 33121
Sample rows:
| flight_id   | flight_no   | scheduled_departure    | scheduled_arrival      | departure_airport   | arrival_airport   | status    | aircraft_code   | actual_departure   | actual_arrival   |
|-------------|-------------|------------------------|------------------------|---------------------|-------------------|-----------|-----------------|--------------------|------------------|
| 1185        | PG0134      | 2017-09-10 09:50:00+03 | 2017-09-10 14:55:00+03 | DME                 | BTK               | Scheduled | 319             | \N                 | \N               |
| 3979        | PG0052      | 2017-08-25 14:50:00+03 | 2017-08-25 17:35:00+03 | VKO                 | HMA               | Scheduled | CR2             | \N                 | \N               |
| 4739        | PG0561      | 2017-09-05 12:30:00+03 | 2017-09-05 14:15:00+03 | VKO                 | AER               | Scheduled | 763             | \N                 | \N               |
| 5502        | PG0529      | 2017-09-12 09:50:00+03 | 2017-09-12 11:20:00+03 | SVO                 | UFA               | Scheduled | 763             | \N                 | \N               |
| 6938        | PG0461      | 2017-09-04 12:25:00+03 | 2017-09-04 13:20:00+03 | SVO                 | ULV               | Scheduled | SU9             | \N                 | \N               |
| ...         | ...         | ...                    | ...                    | ...                 | ...               | ...       | ...             | ...                | ...              |
*/
CREATE TABLE airlines.flights (
    flight_id DECIMAL NOT NULL,
        -- <example>1185</example>
    flight_no VARCHAR NOT NULL,
        -- <example>'PG0529'</example>
    scheduled_departure VARCHAR NOT NULL,
        -- <example>'2017-09-04 12:25:00+03'</example>
    scheduled_arrival VARCHAR NOT NULL,
        -- <example>'2017-09-12 11:20:00+03'</example>
    departure_airport VARCHAR NOT NULL,
        -- <example>'SVX'</example>
    arrival_airport VARCHAR NOT NULL,
        -- <example>'BTK'</example>
    status VARCHAR NOT NULL,
        -- <values>{'Arrived', 'Cancelled', 'Delayed', 'Departed', 'On Time', 'Scheduled'}</values>
    aircraft_code VARCHAR NOT NULL,
        -- <values>{'319', '321', '733', '763', '773', 'CN1', 'CR2', 'SU9'}</values>
    actual_departure VARCHAR NOT NULL,
        -- <example>'2017-08-06 09:39:00+03'</example>
    actual_arrival VARCHAR NOT NULL
        -- <example>'2017-08-05 10:34:00+03'</example>
);

/*
Schema: airlinesTable: seats
Rows: 1339
Sample rows:
| aircraft_code   | seat_no   | fare_conditions   |
|-----------------|-----------|-------------------|
| 319             | 2A        | Business          |
| 319             | 2C        | Business          |
| 319             | 2D        | Business          |
| 319             | 2F        | Business          |
| 319             | 3A        | Business          |
| ...             | ...       | ...               |
*/
CREATE TABLE airlines.seats (
    aircraft_code VARCHAR NOT NULL,
        -- <values>{'319', '320', '321', '733', '763', '773', 'CN1', 'CR2', 'SU9'}</values>
    seat_no VARCHAR NOT NULL,
        -- <example>'2C'</example>
    fare_conditions VARCHAR NOT NULL
        -- <values>{'Business', 'Comfort', 'Economy'}</values>
);

/*
Schema: airlinesTable: tickets
Rows: 366733
Sample rows:
| ticket_no     | book_ref   | passenger_id   |
|---------------|------------|----------------|
| 0005432000987 | 06B046     | 8149 604011    |
| 0005432000988 | 06B046     | 8499 420203    |
| 0005432000989 | E170C3     | 1011 752484    |
| 0005432000990 | E170C3     | 4849 400049    |
| 0005432000991 | F313DD     | 6615 976589    |
| ...           | ...        | ...            |
*/
CREATE TABLE airlines.tickets (
    ticket_no VARCHAR NOT NULL,
        -- <example>'0005432000992'</example>
    book_ref VARCHAR NOT NULL,
        -- <example>'4B75D1'</example>
    passenger_id VARCHAR NOT NULL
        -- <example>'6615 976589'</example>
);

/*
Schema: airlinesTable: ticket_flights
Rows: 1045726
Sample rows:
| ticket_no     | flight_id   | fare_conditions   | amount   |
|---------------|-------------|-------------------|----------|
| 0005432159776 | 30625       | Business          | 42100    |
| 0005435212351 | 30625       | Business          | 42100    |
| 0005435212386 | 30625       | Business          | 42100    |
| 0005435212381 | 30625       | Business          | 42100    |
| 0005432211370 | 30625       | Business          | 42100    |
| ...           | ...         | ...               | ...      |
*/
CREATE TABLE airlines.ticket_flights (
    ticket_no VARCHAR NOT NULL,
        -- <example>'0005435212381'</example>
    flight_id DECIMAL NOT NULL,
        -- <example>30625</example>
    fare_conditions VARCHAR NOT NULL,
        -- <values>{'Business', 'Comfort', 'Economy'}</values>
    amount DECIMAL NOT NULL
        -- <example>42100</example>
);
```