```sql
-- Database: app_store

-- Table: playstore (10840 rows)
CREATE TABLE playstore (
    App TEXT NULL,
        -- <example>'Photo Editor & Candy Camera & Grid & ScrapBook'</example>
    Category TEXT NULL,
        -- <example>'ART_AND_DESIGN'</example>
    Rating REAL NULL,
        -- <example>4.100</example>
    Reviews INTEGER NULL,
        -- <example>159</example>
    Size TEXT NULL,
        -- <example>'19M'</example>
    Installs TEXT NULL,
        -- <example>'10,000+'</example>
    Type TEXT NULL,
        -- <values>{'Free', 'NaN', 'Paid'}</values>
    Price TEXT NULL,
        -- <example>'0'</example>
    "Content Rating" TEXT NULL,
        -- <values>{'Adults only 18+', 'Everyone 10+', 'Everyone', 'Mature 17+', 'Teen', 'Unrated'}</values>
    Genres TEXT NULL
        -- <example>'Art & Design'</example>
);

-- Table: user_reviews (64286 rows)
CREATE TABLE user_reviews (
    App TEXT NULL,
        -- <example>'10 Best Foods for You'</example>
        -- <fk> -> playstore.App</fk>
    Translated_Review TEXT NULL,
        -- <example>'I like eat delicious food. That's I'm cooking food... Foods" helps lot, also "Best Before (Shelf Life)"'</example>
    Sentiment TEXT NULL,
        -- <values>{'Negative', 'Neutral', 'Positive', 'nan'}</values>
    Sentiment_Polarity TEXT NULL,
        -- <example>'1.0'</example>
    Sentiment_Subjectivity TEXT NULL,
        -- <example>'0.5333333333333333'</example>
    FOREIGN KEY (App) REFERENCES playstore(App)
);
```