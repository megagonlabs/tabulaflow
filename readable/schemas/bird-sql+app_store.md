```sql
-- Database: app_store

-- Table: playstore (10840 rows)
CREATE TABLE playstore (
    App TEXT,  -- e.g. 'Photo Editor & Candy Camera & Grid & ScrapBook'
    Category TEXT,  -- e.g. 'ART_AND_DESIGN'
    Rating REAL,  -- e.g. 4.100
    Reviews INTEGER,  -- e.g. 159
    Size TEXT,  -- e.g. '19M'
    Installs TEXT,  -- e.g. '10,000+'
    Type TEXT,  -- values: {'Free', 'NaN', 'Paid'}
    Price TEXT,  -- e.g. '0'
    "Content Rating" TEXT,  -- values: {'Adults only 18+', 'Everyone 10+', 'Everyone', 'Mature 17+', 'Teen', 'Unrated'}
    Genres TEXT  -- e.g. 'Art & Design'
);

-- Table: user_reviews (64286 rows)
CREATE TABLE user_reviews (
    App TEXT,  -- e.g. '10 Best Foods for You'; FK -> playstore.App
    Translated_Review TEXT,  -- e.g. 'I like eat delicious food. That's I'm cooking food... Foods" helps lot, also "Best Before (Shelf Life)"'
    Sentiment TEXT,  -- values: {'Negative', 'Neutral', 'Positive', 'nan'}
    Sentiment_Polarity TEXT,  -- e.g. '1.0'
    Sentiment_Subjectivity TEXT,  -- e.g. '0.5333333333333333'
    FOREIGN KEY (App) REFERENCES playstore(App)
);
```