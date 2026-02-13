```sql
-- Database: donor

/*
Table: donations
Rows: 3097556
Sample rows:
| donationid                       | projectid                        | donor_acctid                     | donor_city     | donor_state   | donor_zip   | is_teacher_acct   | donation_timestamp      | donation_to_project   | donation_optional_support   | donation_total   | dollar_amount   | donation_included_optional_support   | payment_method   | payment_included_acct_credit   | payment_included_campaign_gift_card   | payment_included_web_purchased_gift_card   | payment_was_promo_matched   | via_giving_page   | for_honoree   | donation_message                                                                                                                                                                                            |
|----------------------------------|----------------------------------|----------------------------------|----------------|---------------|-------------|-------------------|-------------------------|-----------------------|-----------------------------|------------------|-----------------|--------------------------------------|------------------|--------------------------------|---------------------------------------|--------------------------------------------|-----------------------------|-------------------|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 431d720bc3dfd75ae445a5eaa0b0638d | ffffac55ee02a49d1abc87ba6fc61135 | 22cbc920c9b5fa08dfb331422f5926b5 | Peachtree City | GA            | 30269       | f                 | 2011-08-25 14:27:34.807 | 42.5                  | 7.5                         | 50.0             | 10_to_100       | t                                    | no_cash_received | f                              | t                                     | f                                          | f                           | f                 | f             | I gave to this project because I support the efforts of this teacher with each of her students, and her school, Suder Elementary School.                                                                    |
| fcfedba1c8a0ba77d280cace80a909f6 | ffffac55ee02a49d1abc87ba6fc61135 | 521f1830a77c9dbbf8119d99c6206a16 | [NULL]         | GA            | [NULL]      | f                 | 2011-11-04 07:54:21.552 | 26.83                 | 4.73                        | 31.56            | 10_to_100       | t                                    | creditcard       | f                              | t                                     | f                                          | f                           | f                 | f             | I donated because I want to support kids in Georgia.                                                                                                                                                        |
| 3fa95d29986aa6f401c6719ced3a3ce7 | ffffac55ee02a49d1abc87ba6fc61135 | 1e0a63fc8141c7ba26b8b44ca0871b90 | Rockville      | MD            | 20853       | f                 | 2011-11-02 22:53:53.019 | 55.35                 | 0.0                         | 55.35            | 10_to_100       | f                                    | no_cash_received | t                              | f                                     | f                                          | f                           | t                 | f             | The Spark's 'pet' projects include those which support deaf students.  With just a few days left, th...k's donors fund half of what remains, and challenge others to pull this project through to fruition. |
| 020ad6bd5e88a35741d23b5e08f8b8e8 | ffffac55ee02a49d1abc87ba6fc61135 | 1d4acb508df29d5f1cc6d382969576cb | Salem          | IN            | 47167       | f                 | 2011-11-03 23:54:01.109 | 8.5                   | 1.5                         | 10.0             | 10_to_100       | t                                    | paypal           | f                              | f                                     | f                                          | f                           | f                 | f             | I gave to this project because Education is important and any method that makes it more fun and effective is worthwhile.                                                                                    |
| 4b44b03f304d6425ae94446686f93cd6 | ffffac55ee02a49d1abc87ba6fc61135 | 59c3c3cfcccc53ae855f7eee911c478b | anonymous      | [NULL]        | 0           | f                 | 2011-11-02 23:21:00.043 | 20.0                  | 0.0                         | 20.0             | 10_to_100       | f                                    | no_cash_received | f                              | f                                     | t                                          | f                           | t                 | f             | I lent a paw to help the children in this classroom in Georgia Together we can all work together to ...child forever. Please help the children, it will mean the world to them to know you care. Thank you. |
| ...                              | ...                              | ...                              | ...            | ...           | ...         | ...               | ...                     | ...                   | ...                         | ...              | ...             | ...                                  | ...              | ...                            | ...                                   | ...                                        | ...                         | ...               | ...           | ...                                                                                                                                                                                                         |
*/
CREATE TABLE donations (
    donationid TEXT NOT NULL PRIMARY KEY,
        -- <example>'000000a91a14ed37bef82e125c102e77'</example>
    projectid TEXT NOT NULL,
        -- <example>'ffffac55ee02a49d1abc87ba6fc61135'</example>
        -- <fk> -> projects.projectid</fk>
    donor_acctid TEXT NOT NULL,
        -- <example>'22cbc920c9b5fa08dfb331422f5926b5'</example>
    donor_city TEXT NULL,
        -- <example>'Peachtree City'</example>
    donor_state TEXT NULL,
        -- <example>'GA'</example>
    donor_zip TEXT NULL,
        -- <example>'30269'</example>
    is_teacher_acct TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    donation_timestamp DATETIME NOT NULL,
        -- <example>'2011-08-25 14:27:34.807'</example>
    donation_to_project REAL NOT NULL,
        -- <example>42.500</example>
    donation_optional_support REAL NOT NULL,
        -- <example>7.500</example>
    donation_total REAL NOT NULL,
        -- <example>50.000</example>
    dollar_amount TEXT NOT NULL,
        -- <values>{'100_and_up', '10_to_100', 'under_10'}</values>
    donation_included_optional_support TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    payment_method TEXT NOT NULL,
        -- <values>{'almost_home_match', 'amazon', 'check', 'creditcard', 'double_your_impact_match', 'no_cash_received', 'paypal', 'promo_code_match'}</values>
    payment_included_acct_credit TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    payment_included_campaign_gift_card TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    payment_included_web_purchased_gift_card TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    payment_was_promo_matched TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    via_giving_page TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    for_honoree TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    donation_message TEXT NULL,
        -- <example>'I gave to this project because I support the effor...students, and her school, Suder Elementary School.'</example>
    FOREIGN KEY (projectid) REFERENCES projects(projectid)
);

/*
Table: essays
Rows: 99998
Sample rows:
| projectid                        | teacher_acctid                   | title                                        | short_description                                                                                                                                                                                           | need_statement                                                                                                                             | essay                                                                                                                                                                                                       |
|----------------------------------|----------------------------------|----------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ffffc4f85b60efc5b52347df489d0238 | c24011b20fc161ed02248e85beb59a90 | iMath                                        | It is imperative that teachers bring technology into the classroom, if students are going to be able... be ever changing along with the outside world. The iMath project will help students by obtaining cl | My students need four iPods.                                                                                                               | I am a fourth year fifth grade math teacher. The school I teach in is a fifth and sixth grade public...of our students get free lunch. Presently, I am in the process of completing a Masters degree in Tec |
| ffffac55ee02a49d1abc87ba6fc61135 | 947066d0af47e0566f334566553dd6a6 | Recording Rockin' Readers                    | Can you imagine having to translate everything you read into sign language and relate it to what you already know? Help us do just that by giving us the camera that will record our stories and...         | My students need a camcorder.                                                                                                              | Can you imagine having to translate everything you read into sign language and relate it to what you...mera that will record our stories and interpretations! 
\n
\nMy students are all deaf or hard of hea                                                                                                                                                                                                             |
| ffff97ed93720407d70a2787475932b0 | 462270f5d5c212162fcab11afa2623cb | Kindergarten In Need of Important Materials! | It takes a special person to donate to a group of children they don't know, especially in these hard...serve to have the proper supplies to ensure that their long education gets off to the right start, s | My students need 17 assorted classroom materials to ensure that they can learn as much as possible this year.                              | Hi. I teach a wonderful group of 4-5 year old Kindergarten students.  They come in wanting and willi... I work hard to ensure that my students get the most out of the entire school year. 
\n
\nFor the mo                                                                                                                                                                                                             |
| ffff7266778f71242675416e600b94e1 | b9a8f14199e0d8109200ece179281f4f | Let's Find Out!                              | My Kindergarten students come from a variety of backgrounds. As their teacher, it is my duty to provide a wide variety of texts as we begin to learn how to read. Kindergarten students are excited...      | My students need 25 copies of Scholastic's "Let's Find Out!" weekly magazine!                                                              | My Kindergarten students come from a variety of backgrounds. As their teacher, it is my duty to prov... read. 
\n
\nKindergarten students are excited about school - especially about learning to read. I h                                                                                                                                                                                                             |
| ffff418bb42fad24347527ad96100f81 | e885fb002a1d0d39aaed9d21a7683549 | Whistle While We Work!                       | By using the cross curricular games requested, students will be able to participate in this type of ...for my students, thus making it possible for my students to reach their goal of becoming life long l | My students need grade level appropriate games so that they may work in small groups to review skills they have not successfully mastered. | All work and no play makes school a dull place to learn. Our class is a 4th grade general education ...has cut WAY down on the number of copies that can be made.  This makes it very difficult to accurate |
| ...                              | ...                              | ...                                          | ...                                                                                                                                                                                                         | ...                                                                                                                                        | ...                                                                                                                                                                                                         |
*/
CREATE TABLE essays (
    projectid TEXT NOT NULL,
        -- <example>'ffffc4f85b60efc5b52347df489d0238'</example>
    teacher_acctid TEXT NOT NULL,
        -- <example>'c24011b20fc161ed02248e85beb59a90'</example>
    title TEXT NULL,
        -- <example>'iMath'</example>
    short_description TEXT NULL,
        -- <example>'It is imperative that teachers bring technology in...e iMath project will help students by obtaining cl'</example>
    need_statement TEXT NULL,
        -- <example>'My students need four iPods.'</example>
    essay TEXT NOT NULL
        -- <example>'I am a fourth year fifth grade math teacher. The s... the process of completing a Masters degree in Tec'</example>
);

/*
Table: projects
Rows: 664098
Sample rows:
| projectid                        | teacher_acctid                   | schoolid                         | school_ncesid   | school_latitude   | school_longitude   | school_city   | school_state   | school_zip   | school_metro   | school_district                | school_county    | school_charter   | school_magnet   | school_year_round   | school_nlns   | school_kipp   | school_charter_ready_promise   | teacher_prefix   | teacher_teach_for_america   | teacher_ny_teaching_fellow   | primary_focus_subject   | primary_focus_area   | secondary_focus_subject   | secondary_focus_area   | resource_type   | poverty_level   | grade_level   | fulfillment_labor_materials   | total_price_excluding_optional_support   | total_price_including_optional_support   | students_reached   | eligible_double_your_impact_match   | eligible_almost_home_match   | date_posted   |
|----------------------------------|----------------------------------|----------------------------------|-----------------|-------------------|--------------------|---------------|----------------|--------------|----------------|--------------------------------|------------------|------------------|-----------------|---------------------|---------------|---------------|--------------------------------|------------------|-----------------------------|------------------------------|-------------------------|----------------------|---------------------------|------------------------|-----------------|-----------------|---------------|-------------------------------|------------------------------------------|------------------------------------------|--------------------|-------------------------------------|------------------------------|---------------|
| 316ed8fb3b81402ff6ac8f721bb31192 | 42d43fa6f37314365d08692e08680973 | c0e6ce89b244764085691a1b8e28cb81 | 063627006187    | 36.57634          | -119.608713        | Selma         | CA             | 93662        | [NULL]         | Selma Unified Sch District     | Fresno           | f                | f               | f                   | f             | f             | f                              | Mrs.             | f                           | f                            | Literature & Writing    | Literacy & Language  | College & Career Prep     | Applied Learning       | Books           | highest poverty | Grades 6-8    | 30.0                          | 555.81                                   | 653.89                                   | 32                 | f                                   | f                            | 2014-05-12    |
| 90de744e368a7e4883223ca49318ae30 | 864eb466462bf704bf7a16a585ef296a | d711e47810900c96f26a5d0be30c446d | 483702008193    | 32.911179         | -96.72364          | Dallas        | TX             | 75243        | urban          | Richardson Ind School District | Dallas           | f                | f               | f                   | f             | f             | f                              | Mrs.             | f                           | f                            | Literacy                | Literacy & Language  | ESL                       | Literacy & Language    | Books           | highest poverty | Grades PreK-2 | 30.0                          | 296.47                                   | 348.79                                   | 22                 | f                                   | f                            | 2014-05-12    |
| 32943bb1063267de6ed19fc0ceb4b9a7 | 37f85135259ece793213aca9d8765542 | 665c3613013ba0a66e3a2a26b89f1b68 | 410327000109    | 45.166039         | -122.414576        | Colton        | OR             | 97017        | rural          | Colton School District 53      | Clackamas        | f                | f               | f                   | f             | f             | f                              | Mr.              | f                           | f                            | Literacy                | Literacy & Language  | Mathematics               | Math & Science         | Technology      | high poverty    | Grades PreK-2 | 30.0                          | 430.89                                   | 506.93                                   | 17                 | f                                   | f                            | 2014-05-11    |
| bb18f409abda2f264d5acda8cab577a9 | 2133fc46f951f1e7d60645b0f9e48a6c | 4f12c3fa0c1cce823c7ba1df57e90ccb | 360015302507    | 40.641727         | -73.965655         | Brooklyn      | NY             | 11226        | urban          | New York City Dept Of Ed       | Kings (Brooklyn) | f                | t               | f                   | f             | f             | f                              | Mr.              | t                           | f                            | Social Sciences         | History & Civics     | Special Needs             | Special Needs          | Books           | highest poverty | Grades 3-5    | 30.0                          | 576.07                                   | 677.73                                   | 12                 | f                                   | f                            | 2014-05-11    |
| 24761b686e18e5eace634607acbcc19f | 867ff478a63f5457eaf41049536c47cd | 10179fd362d7b8cf0e89baa1ca3025bb | 062271003157    | 34.043939         | -118.288371        | Los Angeles   | CA             | 90006        | urban          | Los Angeles Unif Sch Dist      | Los Angeles      | f                | f               | f                   | f             | f             | f                              | Ms.              | f                           | f                            | Mathematics             | Math & Science       | Literacy                  | Literacy & Language    | Other           | highest poverty | Grades PreK-2 | 30.0                          | 408.4                                    | 480.47                                   | 24                 | f                                   | f                            | 2014-05-11    |
| ...                              | ...                              | ...                              | ...             | ...               | ...                | ...           | ...            | ...          | ...            | ...                            | ...              | ...              | ...             | ...                 | ...           | ...           | ...                            | ...              | ...                         | ...                          | ...                     | ...                  | ...                       | ...                    | ...             | ...             | ...           | ...                           | ...                                      | ...                                      | ...                | ...                                 | ...                          | ...           |
*/
CREATE TABLE projects (
    projectid TEXT NOT NULL PRIMARY KEY,
        -- <example>'00001ccc0e81598c4bd86bacb94d7acb'</example>
    teacher_acctid TEXT NOT NULL,
        -- <example>'42d43fa6f37314365d08692e08680973'</example>
    schoolid TEXT NOT NULL,
        -- <example>'c0e6ce89b244764085691a1b8e28cb81'</example>
    school_ncesid TEXT NULL,
        -- <example>'063627006187'</example>
    school_latitude REAL NOT NULL,
        -- <example>36.576</example>
    school_longitude REAL NOT NULL,
        -- <example>-119.609</example>
    school_city TEXT NOT NULL,
        -- <example>'Selma'</example>
    school_state TEXT NOT NULL,
        -- <example>'CA'</example>
    school_zip INTEGER NULL,
        -- <example>93662</example>
    school_metro TEXT NULL,
        -- <values>{'rural', 'suburban', 'urban'}</values>
    school_district TEXT NULL,
        -- <example>'Selma Unified Sch District'</example>
    school_county TEXT NULL,
        -- <example>'Fresno'</example>
    school_charter TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    school_magnet TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    school_year_round TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    school_nlns TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    school_kipp TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    school_charter_ready_promise TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    teacher_prefix TEXT NOT NULL,
        -- <values>{'', 'Dr.', 'Mr. & Mrs.', 'Mr.', 'Mrs.', 'Ms.'}</values>
    teacher_teach_for_america TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    teacher_ny_teaching_fellow TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    primary_focus_subject TEXT NULL,
        -- <example>'Literature & Writing'</example>
    primary_focus_area TEXT NULL,
        -- <values>{'Applied Learning', 'Health & Sports', 'History & Civics', 'Literacy & Language', 'Math & Science', 'Music & The Arts', 'Special Needs'}</values>
    secondary_focus_subject TEXT NULL,
        -- <example>'College & Career Prep'</example>
    secondary_focus_area TEXT NULL,
        -- <values>{'Applied Learning', 'Health & Sports', 'History & Civics', 'Literacy & Language', 'Math & Science', 'Music & The Arts', 'Special Needs'}</values>
    resource_type TEXT NULL,
        -- <values>{'Books', 'Other', 'Supplies', 'Technology', 'Trips', 'Visitors'}</values>
    poverty_level TEXT NOT NULL,
        -- <values>{'high poverty', 'highest poverty', 'low poverty', 'moderate poverty'}</values>
    grade_level TEXT NULL,
        -- <values>{'Grades 3-5', 'Grades 6-8', 'Grades 9-12', 'Grades PreK-2'}</values>
    fulfillment_labor_materials REAL NULL,
        -- <example>30.000</example>
    total_price_excluding_optional_support REAL NOT NULL,
        -- <example>555.810</example>
    total_price_including_optional_support REAL NOT NULL,
        -- <example>653.890</example>
    students_reached INTEGER NULL,
        -- <example>32</example>
    eligible_double_your_impact_match TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    eligible_almost_home_match TEXT NOT NULL,
        -- <values>{'f', 't'}</values>
    date_posted DATE NOT NULL
        -- <example>'2014-05-12'</example>
);

/*
Table: resources
Rows: 3666757
Sample rows:
| resourceid                       | projectid                        | vendorid   | vendor_name                  | project_resource_type   | item_name                                                    | item_number   | item_unit_price   | item_quantity   |
|----------------------------------|----------------------------------|------------|------------------------------|-------------------------|--------------------------------------------------------------|---------------|-------------------|-----------------|
| 8a1c1c45bc30d065061912fd9114fcf3 | ffffc4f85b60efc5b52347df489d0238 | 430        | Woodwind and Brasswind       | Technology              | iPod nano 4th Gen 8GB (Black)                                | 249995.001    | 149.0             | 4               |
| 015d2c4935c50427964a12dc3f584091 | ffffac55ee02a49d1abc87ba6fc61135 | 82         | Best Buy for Business        | Technology              | Sony bloggie MHS-FS1 - camcorder - internal flash memory     | BB11216668    | 148.0             | 1               |
| 26a02944b2f0c25f9abdeacca3ede3ee | ffff97ed93720407d70a2787475932b0 | 767        | Lakeshore Learning Materials | Supplies                | VX748 - Best-Buy Jumbo Crayons - 12-Color Box                | VX748         | 69.95             | 1               |
| 7fef1f92cb4447d18d599f69ea27e833 | ffff97ed93720407d70a2787475932b0 | 767        | Lakeshore Learning Materials | Supplies                | LA138 - Best-Buy Write & Wipe Broad-Tip Markers - Class Pack | LA138         | 34.95             | 1               |
| 8dccf77df25ee615bb1a68b98ba9d861 | ffff97ed93720407d70a2787475932b0 | 767        | Lakeshore Learning Materials | Supplies                | BJ7471 - 1 1/2&#34; Ruled Chart Tablet                       | BJ7471        | 10.95             | 4               |
| ...                              | ...                              | ...        | ...                          | ...                     | ...                                                          | ...           | ...               | ...             |
*/
CREATE TABLE resources (
    resourceid TEXT NOT NULL PRIMARY KEY,
        -- <example>'0000037fecc4461faf0e49328ae66661'</example>
    projectid TEXT NOT NULL,
        -- <example>'ffffc4f85b60efc5b52347df489d0238'</example>
        -- <fk> -> projects.projectid</fk>
    vendorid INTEGER NULL,
        -- <example>430</example>
    vendor_name TEXT NULL,
        -- <example>'Woodwind and Brasswind'</example>
    project_resource_type TEXT NULL,
        -- <values>{'Books', 'Other', 'Supplies', 'Technology', 'Trips', 'Visitors'}</values>
    item_name TEXT NULL,
        -- <example>'iPod nano 4th Gen 8GB (Black)'</example>
    item_number TEXT NULL,
        -- <example>'249995.001'</example>
    item_unit_price REAL NULL,
        -- <example>149.000</example>
    item_quantity INTEGER NULL,
        -- <example>4</example>
    FOREIGN KEY (projectid) REFERENCES projects(projectid)
);
```