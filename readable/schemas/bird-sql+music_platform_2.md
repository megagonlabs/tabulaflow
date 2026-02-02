```sql
-- Database: music_platform_2

-- Table: categories (210329 rows)
CREATE TABLE categories (
    podcast_id TEXT NOT NULL,
        -- <example>'a00018b54eb342567c94dacfb2a3e504'</example>
        -- <fk> -> podcasts.podcast_id</fk>
    category TEXT NOT NULL,
        -- <example>'arts'</example>
    PRIMARY KEY (podcast_id, category),
    FOREIGN KEY (podcast_id) REFERENCES podcasts(podcast_id)
);

-- Table: podcasts (108578 rows)
CREATE TABLE podcasts (
    podcast_id TEXT NULL PRIMARY KEY,
        -- <example>'a00018b54eb342567c94dacfb2a3e504'</example>
    itunes_id INTEGER NOT NULL,
        -- <example>1313466221</example>
    slug TEXT NOT NULL,
        -- <example>'scaling-global'</example>
    itunes_url TEXT NOT NULL,
        -- <example>'https://podcasts.apple.com/us/podcast/scaling-global/id1313466221'</example>
    title TEXT NOT NULL
        -- <example>'Scaling Global'</example>
);

-- Table: reviews (1964856 rows)
CREATE TABLE reviews (
    podcast_id TEXT NOT NULL,
        -- <example>'c61aa81c9b929a66f0c1db6cbe5d8548'</example>
        -- <fk> -> podcasts.podcast_id</fk>
    title TEXT NOT NULL,
        -- <example>'really interesting!'</example>
    content TEXT NOT NULL,
        -- <example>'Thanks for providing these insights.  Really enjoy the variety and depth -- please keep them coming!'</example>
    rating INTEGER NOT NULL,
        -- <example>5</example>
    author_id TEXT NOT NULL,
        -- <example>'F7E5A318989779D'</example>
    created_at TEXT NOT NULL,
        -- <example>'2018-04-24T12:05:16-07:00'</example>
    FOREIGN KEY (podcast_id) REFERENCES podcasts(podcast_id)
);

-- Table: runs (12 rows)
CREATE TABLE runs (
    run_at TEXT NOT NULL,
        -- <example>'2021-05-10 02:53:00'</example>
    max_rowid INTEGER NOT NULL,
        -- <example>3266481</example>
    reviews_added INTEGER NOT NULL
        -- <example>1215223</example>
);
```