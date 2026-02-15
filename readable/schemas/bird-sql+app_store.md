```sql
-- Database: app_store

/*
Schema: NULL
Table: playstore
Rows: 10840
Sample rows:
| App                                                | Category       | Rating   | Reviews   | Size   | Installs    | Type   | Price   | Content Rating   | Genres                    |
|----------------------------------------------------|----------------|----------|-----------|--------|-------------|--------|---------|------------------|---------------------------|
| Photo Editor & Candy Camera & Grid & ScrapBook     | ART_AND_DESIGN | 4.1      | 159       | 19M    | 10,000+     | Free   | 0       | Everyone         | Art & Design              |
| Coloring book moana                                | ART_AND_DESIGN | 3.9      | 967       | 14M    | 500,000+    | Free   | 0       | Everyone         | Art & Design;Pretend Play |
| U Launcher Lite – FREE Live Cool Themes, Hide Apps | ART_AND_DESIGN | 4.7      | 87510     | 8.7M   | 5,000,000+  | Free   | 0       | Everyone         | Art & Design              |
| Sketch - Draw & Paint                              | ART_AND_DESIGN | 4.5      | 215644    | 25M    | 50,000,000+ | Free   | 0       | Teen             | Art & Design              |
| Pixel Draw - Number Art Coloring Book              | ART_AND_DESIGN | 4.3      | 967       | 2.8M   | 100,000+    | Free   | 0       | Everyone         | Art & Design;Creativity   |
| ...                                                | ...            | ...      | ...       | ...    | ...         | ...    | ...     | ...              | ...                       |
*/
CREATE TABLE playstore (
    "App" TEXT NOT NULL,
        -- <example>'Photo Editor & Candy Camera & Grid & ScrapBook'</example>
    "Category" TEXT NOT NULL,
        -- <example>'ART_AND_DESIGN'</example>
    "Rating" REAL NULL,
        -- <example>4.100</example>
    "Reviews" INTEGER NOT NULL,
        -- <example>159</example>
    "Size" TEXT NOT NULL,
        -- <example>'19M'</example>
    "Installs" TEXT NOT NULL,
        -- <example>'10,000+'</example>
    "Type" TEXT NOT NULL,
        -- <values>{'Free', 'NaN', 'Paid'}</values>
    "Price" TEXT NOT NULL,
        -- <example>'0'</example>
    "Content Rating" TEXT NOT NULL,
        -- <values>{'Adults only 18+', 'Everyone 10+', 'Everyone', 'Mature 17+', 'Teen', 'Unrated'}</values>
    "Genres" TEXT NOT NULL
        -- <example>'Art & Design'</example>
);

/*
Schema: NULL
Table: user_reviews
Rows: 64286
Sample rows:
| App                   | Translated_Review                                                                                                          | Sentiment   | Sentiment_Polarity   | Sentiment_Subjectivity   |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------|-------------|----------------------|--------------------------|
| 10 Best Foods for You | I like eat delicious food. That's I'm cooking food myself, case "10 Best Foods" helps lot, also "Best Before (Shelf Life)" | Positive    | 1.0                  | 0.5333333333333333       |
| 10 Best Foods for You | This help eating healthy exercise regular basis                                                                            | Positive    | 0.25                 | 0.28846153846153844      |
| 10 Best Foods for You | nan                                                                                                                        | nan         | nan                  | nan                      |
| 10 Best Foods for You | Works great especially going grocery store                                                                                 | Positive    | 0.4                  | 0.875                    |
| 10 Best Foods for You | Best idea us                                                                                                               | Positive    | 1.0                  | 0.3                      |
| ...                   | ...                                                                                                                        | ...         | ...                  | ...                      |
*/
CREATE TABLE user_reviews (
    "App" TEXT NOT NULL,
        -- <example>'10 Best Foods for You'</example>
        -- <fk> -> playstore."App"</fk>
    "Translated_Review" TEXT NULL,
        -- <example>'I like eat delicious food. That's I'm cooking food... Foods" helps lot, also "Best Before (Shelf Life)"'</example>
    "Sentiment" TEXT NOT NULL,
        -- <values>{'Negative', 'Neutral', 'Positive', 'nan'}</values>
    "Sentiment_Polarity" TEXT NOT NULL,
        -- <example>'1.0'</example>
    "Sentiment_Subjectivity" TEXT NOT NULL,
        -- <example>'0.5333333333333333'</example>
    FOREIGN KEY ("App") REFERENCES playstore("App")
);
```