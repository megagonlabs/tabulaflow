```sql
-- Database: donor

-- Table: donations (3097556 rows)
CREATE TABLE donations (
    donationid TEXT NOT NULL PRIMARY KEY,
        -- <example>'000000a91a14ed37bef82e125c102e77'</example>
    projectid TEXT NULL,
        -- <example>'ffffac55ee02a49d1abc87ba6fc61135'</example>
        -- <fk> -> projects.projectid</fk>
    donor_acctid TEXT NULL,
        -- <example>'22cbc920c9b5fa08dfb331422f5926b5'</example>
    donor_city TEXT NULL,
        -- <example>'Peachtree City'</example>
    donor_state TEXT NULL,
        -- <example>'GA'</example>
    donor_zip TEXT NULL,
        -- <example>'30269'</example>
    is_teacher_acct TEXT NULL,
        -- <values>{'f', 't'}</values>
    donation_timestamp DATETIME NULL,
        -- <example>'2011-08-25 14:27:34.807'</example>
    donation_to_project REAL NULL,
        -- <example>42.500</example>
    donation_optional_support REAL NULL,
        -- <example>7.500</example>
    donation_total REAL NULL,
        -- <example>50.000</example>
    dollar_amount TEXT NULL,
        -- <values>{'100_and_up', '10_to_100', 'under_10'}</values>
    donation_included_optional_support TEXT NULL,
        -- <values>{'f', 't'}</values>
    payment_method TEXT NULL,
        -- <values>{'almost_home_match', 'amazon', 'check', 'creditcard', 'double_your_impact_match', 'no_cash_received', 'paypal', 'promo_code_match'}</values>
    payment_included_acct_credit TEXT NULL,
        -- <values>{'f', 't'}</values>
    payment_included_campaign_gift_card TEXT NULL,
        -- <values>{'f', 't'}</values>
    payment_included_web_purchased_gift_card TEXT NULL,
        -- <values>{'f', 't'}</values>
    payment_was_promo_matched TEXT NULL,
        -- <values>{'f', 't'}</values>
    via_giving_page TEXT NULL,
        -- <values>{'f', 't'}</values>
    for_honoree TEXT NULL,
        -- <values>{'f', 't'}</values>
    donation_message TEXT NULL,
        -- <example>'I gave to this project because I support the effor...students, and her school, Suder Elementary School.'</example>
    FOREIGN KEY (projectid) REFERENCES projects(projectid)
);

-- Table: essays (99998 rows)
CREATE TABLE essays (
    projectid TEXT NULL,
        -- <example>'ffffc4f85b60efc5b52347df489d0238'</example>
    teacher_acctid TEXT NULL,
        -- <example>'c24011b20fc161ed02248e85beb59a90'</example>
    title TEXT NULL,
        -- <example>'iMath'</example>
    short_description TEXT NULL,
        -- <example>'It is imperative that teachers bring technology in...e iMath project will help students by obtaining cl'</example>
    need_statement TEXT NULL,
        -- <example>'My students need four iPods.'</example>
    essay TEXT NULL
        -- <example>'I am a fourth year fifth grade math teacher. The s... the process of completing a Masters degree in Tec'</example>
);

-- Table: projects (664098 rows)
CREATE TABLE projects (
    projectid TEXT NOT NULL PRIMARY KEY,
        -- <example>'00001ccc0e81598c4bd86bacb94d7acb'</example>
    teacher_acctid TEXT NULL,
        -- <example>'42d43fa6f37314365d08692e08680973'</example>
    schoolid TEXT NULL,
        -- <example>'c0e6ce89b244764085691a1b8e28cb81'</example>
    school_ncesid TEXT NULL,
        -- <example>'063627006187'</example>
    school_latitude REAL NULL,
        -- <example>36.576</example>
    school_longitude REAL NULL,
        -- <example>-119.609</example>
    school_city TEXT NULL,
        -- <example>'Selma'</example>
    school_state TEXT NULL,
        -- <example>'CA'</example>
    school_zip INTEGER NULL,
        -- <example>93662</example>
    school_metro TEXT NULL,
        -- <values>{'rural', 'suburban', 'urban'}</values>
    school_district TEXT NULL,
        -- <example>'Selma Unified Sch District'</example>
    school_county TEXT NULL,
        -- <example>'Fresno'</example>
    school_charter TEXT NULL,
        -- <values>{'f', 't'}</values>
    school_magnet TEXT NULL,
        -- <values>{'f', 't'}</values>
    school_year_round TEXT NULL,
        -- <values>{'f', 't'}</values>
    school_nlns TEXT NULL,
        -- <values>{'f', 't'}</values>
    school_kipp TEXT NULL,
        -- <values>{'f', 't'}</values>
    school_charter_ready_promise TEXT NULL,
        -- <values>{'f', 't'}</values>
    teacher_prefix TEXT NULL,
        -- <values>{'', 'Dr.', 'Mr. & Mrs.', 'Mr.', 'Mrs.', 'Ms.'}</values>
    teacher_teach_for_america TEXT NULL,
        -- <values>{'f', 't'}</values>
    teacher_ny_teaching_fellow TEXT NULL,
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
    poverty_level TEXT NULL,
        -- <values>{'high poverty', 'highest poverty', 'low poverty', 'moderate poverty'}</values>
    grade_level TEXT NULL,
        -- <values>{'Grades 3-5', 'Grades 6-8', 'Grades 9-12', 'Grades PreK-2'}</values>
    fulfillment_labor_materials REAL NULL,
        -- <example>30.000</example>
    total_price_excluding_optional_support REAL NULL,
        -- <example>555.810</example>
    total_price_including_optional_support REAL NULL,
        -- <example>653.890</example>
    students_reached INTEGER NULL,
        -- <example>32</example>
    eligible_double_your_impact_match TEXT NULL,
        -- <values>{'f', 't'}</values>
    eligible_almost_home_match TEXT NULL,
        -- <values>{'f', 't'}</values>
    date_posted DATE NULL
        -- <example>'2014-05-12'</example>
);

-- Table: resources (3666757 rows)
CREATE TABLE resources (
    resourceid TEXT NOT NULL PRIMARY KEY,
        -- <example>'0000037fecc4461faf0e49328ae66661'</example>
    projectid TEXT NULL,
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