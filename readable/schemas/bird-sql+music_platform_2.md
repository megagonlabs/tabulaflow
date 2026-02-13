```sql
-- Database: music_platform_2

/*
Table: categories
Rows: 210329
Sample rows:
| podcast_id                       | category             |
|----------------------------------|----------------------|
| c61aa81c9b929a66f0c1db6cbe5d8548 | arts                 |
| c61aa81c9b929a66f0c1db6cbe5d8548 | arts-performing-arts |
| c61aa81c9b929a66f0c1db6cbe5d8548 | music                |
| ad4f2bf69c72b8db75978423c25f379e | arts                 |
| ad4f2bf69c72b8db75978423c25f379e | arts-design          |
| ...                              | ...                  |
*/
CREATE TABLE categories (
    podcast_id TEXT NOT NULL,
        -- <example>'a00018b54eb342567c94dacfb2a3e504'</example>
        -- <fk> -> podcasts.podcast_id</fk>
    category TEXT NOT NULL,
        -- <example>'arts'</example>
    PRIMARY KEY (podcast_id, category),
    FOREIGN KEY (podcast_id) REFERENCES podcasts(podcast_id)
);

/*
Table: podcasts
Rows: 108578
Sample rows:
| podcast_id                       | itunes_id   | slug                                  | itunes_url                                                                              | title                                 |
|----------------------------------|-------------|---------------------------------------|-----------------------------------------------------------------------------------------|---------------------------------------|
| a00018b54eb342567c94dacfb2a3e504 | 1313466221  | scaling-global                        | https://podcasts.apple.com/us/podcast/scaling-global/id1313466221                       | Scaling Global                        |
| a00043d34e734b09246d17dc5d56f63c | 158973461   | cornerstone-baptist-church-of-orlando | https://podcasts.apple.com/us/podcast/cornerstone-baptist-church-of-orlando/id158973461 | Cornerstone Baptist Church of Orlando |
| a0004b1ef445af9dc84dad1e7821b1e3 | 139076942   | mystery-dancing-in-the-dark           | https://podcasts.apple.com/us/podcast/mystery-dancing-in-the-dark/id139076942           | Mystery: Dancing in the Dark          |
| a00071f9aaae9ac725c3a586701abf4d | 1332508972  | kts-money-matters                     | https://podcasts.apple.com/us/podcast/kts-money-matters/id1332508972                    | KTs Money Matters                     |
| a000aa69852b276565c4f5eb9cdd999b | 1342447811  | speedway-soccer                       | https://podcasts.apple.com/us/podcast/speedway-soccer/id1342447811                      | Speedway Soccer                       |
| ...                              | ...         | ...                                   | ...                                                                                     | ...                                   |
*/
CREATE TABLE podcasts (
    podcast_id TEXT NOT NULL PRIMARY KEY,
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

/*
Table: reviews
Rows: 1964856
Sample rows:
| podcast_id                       | title                                            | content                                                                                                                                                                                                     | rating   | author_id       | created_at                |
|----------------------------------|--------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|-----------------|---------------------------|
| c61aa81c9b929a66f0c1db6cbe5d8548 | really interesting!                              | Thanks for providing these insights.  Really enjoy the variety and depth -- please keep them coming!                                                                                                        | 5        | F7E5A318989779D | 2018-04-24T12:05:16-07:00 |
| c61aa81c9b929a66f0c1db6cbe5d8548 | Must listen for anyone interested in the arts!!! | Super excited to see this podcast grow. So many fun topics to talk about...Shari is really engaging. Definitely subscribing and would recommend to anyone interested in the arts!!                          | 5        | F6BF5472689BD12 | 2018-05-09T18:14:32-07:00 |
| ad4f2bf69c72b8db75978423c25f379e | nauseatingly left                                | I'm a liberal myself, but its pretty obvious and annoying that they're trying to push their beliefs ...tically diverse production staff, we like to see issues from multiple point of views not just yours. | 1        | 1AB95B8E6E1309E | 2019-06-11T14:53:39-07:00 |
| ad4f2bf69c72b8db75978423c25f379e | Diverse stories                                  | I find Tedx talks very inspirational but I often don’t have time to watch a video. I love that this provides an easy way for me to get in diverse information.                                              | 5        | 11BB760AA5DEBD1 | 2018-05-31T13:08:09-07:00 |
| ad4f2bf69c72b8db75978423c25f379e | 👍👍👍👍                                         | I love this podcast, it is so good.                                                                                                                                                                         | 5        | D86032C8E57D15A | 2019-06-19T13:56:05-07:00 |
| ...                              | ...                                              | ...                                                                                                                                                                                                         | ...      | ...             | ...                       |
*/
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

/*
Table: runs
Rows: 12
Sample rows:
| run_at              | max_rowid   | reviews_added   |
|---------------------|-------------|-----------------|
| 2021-05-10 02:53:00 | 3266481     | 1215223         |
| 2021-06-06 21:34:36 | 3300773     | 13139           |
| 2021-07-02 18:04:55 | 3329699     | 11561           |
| 2021-08-01 17:54:42 | 3360315     | 11855           |
| 2021-09-02 18:00:30 | 3390165     | 11714           |
| ...                 | ...         | ...             |
*/
CREATE TABLE runs (
    run_at TEXT NOT NULL,
        -- <example>'2021-05-10 02:53:00'</example>
    max_rowid INTEGER NOT NULL,
        -- <example>3266481</example>
    reviews_added INTEGER NOT NULL
        -- <example>1215223</example>
);
```