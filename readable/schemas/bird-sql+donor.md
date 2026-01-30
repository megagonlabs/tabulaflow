```sql
-- Database: donor

-- Table: donations (3097556 rows)
CREATE TABLE donations (
    donationid TEXT NOT NULL PRIMARY KEY,  -- e.g. '000000a91a14ed37bef82e125c102e77'
    projectid TEXT,  -- e.g. 'ffffac55ee02a49d1abc87ba6fc61135'; FK -> projects.projectid
    donor_acctid TEXT,  -- e.g. '22cbc920c9b5fa08dfb331422f5926b5'
    donor_city TEXT,  -- e.g. 'Peachtree City'
    donor_state TEXT,  -- e.g. 'GA'
    donor_zip TEXT,  -- e.g. '30269'
    is_teacher_acct TEXT,  -- values: {'f', 't'}
    donation_timestamp DATETIME,  -- e.g. '2011-08-25 14:27:34.807'
    donation_to_project REAL,  -- e.g. 42.500
    donation_optional_support REAL,  -- e.g. 7.500
    donation_total REAL,  -- e.g. 50.000
    dollar_amount TEXT,  -- values: {'100_and_up', '10_to_100', 'under_10'}
    donation_included_optional_support TEXT,  -- values: {'f', 't'}
    payment_method TEXT,  -- values: {'almost_home_match', 'amazon', 'check', 'creditcard', 'double_your_impact_match', 'no_cash_received', 'paypal', 'promo_code_match'}
    payment_included_acct_credit TEXT,  -- values: {'f', 't'}
    payment_included_campaign_gift_card TEXT,  -- values: {'f', 't'}
    payment_included_web_purchased_gift_card TEXT,  -- values: {'f', 't'}
    payment_was_promo_matched TEXT,  -- values: {'f', 't'}
    via_giving_page TEXT,  -- values: {'f', 't'}
    for_honoree TEXT,  -- values: {'f', 't'}
    donation_message TEXT,  -- e.g. 'I gave to this project because I support the effor...students, and her school, Suder Elementary School.'
    FOREIGN KEY (projectid) REFERENCES projects(projectid)
);

-- Table: essays (99998 rows)
CREATE TABLE essays (
    projectid TEXT,  -- e.g. 'ffffc4f85b60efc5b52347df489d0238'
    teacher_acctid TEXT,  -- e.g. 'c24011b20fc161ed02248e85beb59a90'
    title TEXT,  -- e.g. 'iMath'
    short_description TEXT,  -- e.g. 'It is imperative that teachers bring technology in...e iMath project will help students by obtaining cl'
    need_statement TEXT,  -- e.g. 'My students need four iPods.'
    essay TEXT  -- e.g. 'I am a fourth year fifth grade math teacher. The s... the process of completing a Masters degree in Tec'
);

-- Table: projects (664098 rows)
CREATE TABLE projects (
    projectid TEXT NOT NULL PRIMARY KEY,  -- e.g. '00001ccc0e81598c4bd86bacb94d7acb'
    teacher_acctid TEXT,  -- e.g. '42d43fa6f37314365d08692e08680973'
    schoolid TEXT,  -- e.g. 'c0e6ce89b244764085691a1b8e28cb81'
    school_ncesid TEXT,  -- e.g. '063627006187'
    school_latitude REAL,  -- e.g. 36.576
    school_longitude REAL,  -- e.g. -119.609
    school_city TEXT,  -- e.g. 'Selma'
    school_state TEXT,  -- e.g. 'CA'
    school_zip INTEGER,  -- e.g. 93662
    school_metro TEXT,  -- values: {'rural', 'suburban', 'urban'}
    school_district TEXT,  -- e.g. 'Selma Unified Sch District'
    school_county TEXT,  -- e.g. 'Fresno'
    school_charter TEXT,  -- values: {'f', 't'}
    school_magnet TEXT,  -- values: {'f', 't'}
    school_year_round TEXT,  -- values: {'f', 't'}
    school_nlns TEXT,  -- values: {'f', 't'}
    school_kipp TEXT,  -- values: {'f', 't'}
    school_charter_ready_promise TEXT,  -- values: {'f', 't'}
    teacher_prefix TEXT,  -- values: {'', 'Dr.', 'Mr. & Mrs.', 'Mr.', 'Mrs.', 'Ms.'}
    teacher_teach_for_america TEXT,  -- values: {'f', 't'}
    teacher_ny_teaching_fellow TEXT,  -- values: {'f', 't'}
    primary_focus_subject TEXT,  -- e.g. 'Literature & Writing'
    primary_focus_area TEXT,  -- values: {'Applied Learning', 'Health & Sports', 'History & Civics', 'Literacy & Language', 'Math & Science', 'Music & The Arts', 'Special Needs'}
    secondary_focus_subject TEXT,  -- e.g. 'College & Career Prep'
    secondary_focus_area TEXT,  -- values: {'Applied Learning', 'Health & Sports', 'History & Civics', 'Literacy & Language', 'Math & Science', 'Music & The Arts', 'Special Needs'}
    resource_type TEXT,  -- values: {'Books', 'Other', 'Supplies', 'Technology', 'Trips', 'Visitors'}
    poverty_level TEXT,  -- values: {'high poverty', 'highest poverty', 'low poverty', 'moderate poverty'}
    grade_level TEXT,  -- values: {'Grades 3-5', 'Grades 6-8', 'Grades 9-12', 'Grades PreK-2'}
    fulfillment_labor_materials REAL,  -- e.g. 30.000
    total_price_excluding_optional_support REAL,  -- e.g. 555.810
    total_price_including_optional_support REAL,  -- e.g. 653.890
    students_reached INTEGER,  -- e.g. 32
    eligible_double_your_impact_match TEXT,  -- values: {'f', 't'}
    eligible_almost_home_match TEXT,  -- values: {'f', 't'}
    date_posted DATE  -- e.g. '2014-05-12'
);

-- Table: resources (3666757 rows)
CREATE TABLE resources (
    resourceid TEXT NOT NULL PRIMARY KEY,  -- e.g. '0000037fecc4461faf0e49328ae66661'
    projectid TEXT,  -- e.g. 'ffffc4f85b60efc5b52347df489d0238'; FK -> projects.projectid
    vendorid INTEGER,  -- e.g. 430
    vendor_name TEXT,  -- e.g. 'Woodwind and Brasswind'
    project_resource_type TEXT,  -- values: {'Books', 'Other', 'Supplies', 'Technology', 'Trips', 'Visitors'}
    item_name TEXT,  -- e.g. 'iPod nano 4th Gen 8GB (Black)'
    item_number TEXT,  -- e.g. '249995.001'
    item_unit_price REAL,  -- e.g. 149.000
    item_quantity INTEGER,  -- e.g. 4
    FOREIGN KEY (projectid) REFERENCES projects(projectid)
);
```