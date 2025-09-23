# Old prompt:

# ```
# Translate the following natural language question into a SQLite query.
# - The query must follow the database schema.
# - You must use the hints to generate the query.
# - The final answer must be the query rather than the result of the query.
# - To connect multiple tables, you must use JOIN on one of the pairs in the 【Foreign keys】 section in the database schema.
#   -  Keep in mind that the records in the tables may not perfectly align: the some entities in one table might not be covered by another table.
# - When submitting the final query, remove any additional columns that are not required by the question.
#   - If there are multiple columns that cover similar information, only include the one that is the most relevant and precise.
#     - For example, if the question asks for only the list of events, only include the event ids without the dates.
#     - For example, if the question asks for only the country and there are city, country, location, zipcode columns, only include the country column.
#   - For example, if the question only ask for the highest score but not the name of the student, do not include the name of the student.
#   - Similarly, if the question only ask for the student with the highest score but not his score, do not include the score.
#   - Example:
#     Table: student
#     [
#     (id:TEXT, Primary Key, Example: 1),
#     (name:TEXT, Examples: [John]),
#     (readScore:INTEGER, Examples: [100, 95, 90]),
#     (writeScore:INTEGER, Examples: [100, 95, 90]),
#     (streetAddress:TEXT, Examples: ["123 Main St", "456 Maple Ave"]),
#     (city:TEXT, Examples: ["Anytown", "Anycity"]),
#     ]
#     Question: What is the highest score in reading?
#     Query: SELECT MAX(readScore) FROM student
#     Question: What is the student with the highest score in reading?
#     Query: SELECT name FROM student WHERE readScore = (SELECT MAX(readScore) FROM student)
#     Question: What is the address of the student with the highest score in reading?
#     Query: SELECT streetAddress FROM student WHERE readScore = (SELECT MAX(readScore) FROM student)
# - DO NOT decompose the question into sub-questions, and use the intermediate results of previous queries to construct the final query
#   - All logic of previous queries for sub-questions must be included in the final query.
#   - However, you can debug a query by testing smaller components.
#   - THIS IS NOT ALLOWED:
#     * Question: What is the writing score of the student with the highest reading score?
#     * Query 1: SELECT MAX(readScore) FROM student
#     * Observation 1: 97
#     * Final Query (NOT ALLOWED): SELECT writeScore FROM student WHERE readScore = 97
#     The correct query should be: SELECT writeScore FROM student WHERE readScore = (SELECT MAX(readScore) FROM student)
# - For non-digit text columns, always use the `search_keywords` tool to search for the keyword and ensure it exists in the database.
#   - Try to search over all possible relevant columns across the database. Try to be very comprehensive.
#   - Similarly, include potential synonyms in the keyword list.
# - Before submitting the final query as answer, always use the `check_final_answer` tool to validate the query.

# === Your Task ===

# Database Schema:
# 【DB_ID】 california_schools
# 【Schema】
# # Table: satscores
# [
# (cds:TEXT, Primary Key, Examples: [10101080000000, 10101080109991, 10101080111682]),
# (rtype:TEXT, Examples: [D, S]),
# (sname:TEXT, Examples: [FAME Public Charter]),
# (dname:TEXT, Examples: [Alameda County Office of Education]),
# (cname:TEXT, Examples: [Alameda, Amador, Butte]),
# (enroll12:INTEGER, Examples: [398, 62, 75]),
# (NumTstTakr:INTEGER, Examples: [88, 17, 71]),
# (AvgScrRead:INTEGER, Examples: [418, 503, 397]),
# (AvgScrMath:INTEGER, Examples: [418, 546, 387]),
# (AvgScrWrite:INTEGER, Examples: [417, 505, 395]),
# (NumGE1500:INTEGER, Examples: [14, 9, 5])
# ]
# # Table: schools
# [
# (CDSCode:TEXT, Primary Key, Examples: [01100170000000, 01100170109835, 01100170112607]),
# (NCESDist:TEXT, Examples: [0691051, 0600002, 0600003]),
# (NCESSchool:TEXT, Examples: [10546, 10947, 12283]),
# (StatusType:TEXT, Examples: [Active, Closed, Merged]),
# (County:TEXT, Examples: [Alameda, Alpine, Amador]),
# (District:TEXT),
# (School:TEXT, Examples: [FAME Public Charter]),
# (Street:TEXT, Examples: [313 West Winton Avenue]),
# (StreetAbr:TEXT, Examples: [313 West Winton Ave.]),
# (City:TEXT, Examples: [Hayward, Newark, Oakland]),
# (Zip:TEXT, Examples: [94544-1136, 94560-5359, 94612-3355]),
# (State:TEXT, Examples: [CA]),
# (MailStreet:TEXT, Examples: [313 West Winton Avenue]),
# (MailStrAbr:TEXT, Examples: [313 West Winton Ave.]),
# (MailCity:TEXT, Examples: [Hayward, Newark, Oakland]),
# (MailZip:TEXT, Examples: [94544-1136, 94560-5359, 94612]),
# (MailState:TEXT, Examples: [CA]),
# (Phone:TEXT, Examples: [(510) 887-0152, (510) 596-8901, (510) 686-4131]),
# (Ext:TEXT, Examples: [130, 1240, 1200]),
# (Website:TEXT, Examples: [www.acoe.org]),
# (OpenDate:DATE, Examples: [2005-08-29]),
# (ClosedDate:DATE, Examples: [2015-07-31]),
# (Charter:INTEGER, Examples: [1, 0]),
# (CharterNum:TEXT, Examples: [0728, 0811, 1049]),
# (FundingType:TEXT, Examples: [Directly funded]),
# (DOC:TEXT, Examples: [00, 31, 34]),
# (DOCType:TEXT, Examples: [County Office of Education (COE)]),
# (SOC:TEXT, Examples: [65, 66, 60]),
# (SOCType:TEXT, Examples: [K-12 Schools (Public)]),
# (EdOpsCode:TEXT, Examples: [TRAD, JUV, COMM]),
# (EdOpsName:TEXT, Examples: [Traditional]),
# (EILCode:TEXT, Examples: [ELEMHIGH, HS, ELEM]),
# (EILName:TEXT, Examples: [Elementary-High Combination]),
# (GSoffered:TEXT, Examples: [K-12, 9-12, K-8]),
# (GSserved:TEXT, Examples: [K-12, 9-12, K-7]),
# (Virtual:TEXT, Examples: [P, N, F]),
# (Magnet:INTEGER, Examples: [0, 1]),
# (Latitude:REAL, Examples: [37.658212, 37.521436, 37.80452]),
# (Longitude:REAL, Examples: [-122.09713, -121.99391, -122.26815]),
# (AdmFName1:TEXT, Examples: [L Karen, Laura, Clifford]),
# (AdmLName1:TEXT, Examples: [Monroe, Robell, Thompson]),
# (AdmEmail1:TEXT),
# (AdmFName2:TEXT, Examples: [Sau-Lim (Lance), Jennifer, Annalisa]),
# (AdmLName2:TEXT, Examples: [Tsang, Koelling, Moore]),
# (AdmEmail2:TEXT),
# (AdmFName3:TEXT, Examples: [Drew, Irma, Vickie]),
# (AdmLName3:TEXT, Examples: [Sarratore, Munoz, Chang]),
# (AdmEmail3:TEXT),
# (LastUpdate:DATE, Examples: [2015-06-23])
# ]
# # Table: frpm
# [
# (CDSCode:TEXT, Primary Key, Examples: [01100170109835, 01100170112607, 01100170118489]),
# ("Academic Year":TEXT, Examples: [2014-2015]),
# ("County Code":TEXT, Examples: [01, 02, 03]),
# ("District Code":INTEGER, Examples: [10017, 31609, 31617]),
# ("School Code":TEXT, Examples: [0109835, 0112607, 0118489]),
# ("County Name":TEXT, Examples: [Alameda, Alpine, Amador]),
# ("District Name":TEXT),
# ("School Name":TEXT, Examples: [FAME Public Charter]),
# ("District Type":TEXT, Examples: [County Office of Education (COE)]),
# ("School Type":TEXT, Examples: [K-12 Schools (Public)]),
# ("Educational Option Type":TEXT, Examples: [Traditional]),
# ("NSLP Provision Status":TEXT, Examples: [Breakfast Provision 2]),
# ("Charter School (Y/N)":INTEGER, Examples: [1, 0]),
# ("Charter School Number":TEXT, Examples: [0728, 0811, 1049]),
# ("Charter Funding Type":TEXT, Examples: [Directly funded]),
# (IRC:INTEGER, Examples: [1, 0]),
# ("Low Grade":TEXT, Examples: [K, 9, 1]),
# ("High Grade":TEXT, Examples: [12, 8, 5]),
# ("Enrollment (K-12)":REAL, Examples: [1087.0, 395.0, 244.0]),
# ("Free Meal Count (K-12)":REAL, Examples: [565.0, 186.0, 134.0]),
# ("Percent (%) Eligible Free (K-12)":REAL, Examples: [0.519779208831647, 0.470886075949367, 0.549180327868853]),
# ("FRPM Count (K-12)":REAL, Examples: [715.0, 186.0, 175.0]),
# ("Percent (%) Eligible FRPM (K-12)":REAL, Examples: [0.657773689052438, 0.470886075949367, 0.717213114754098]),
# ("Enrollment (Ages 5-17)":REAL, Examples: [1070.0, 376.0, 230.0]),
# ("Free Meal Count (Ages 5-17)":REAL, Examples: [553.0, 182.0, 128.0]),
# ("Percent (%) Eligible Free (Ages 5-17)":REAL, Examples: [0.516822429906542, 0.484042553191489, 0.556521739130435]),
# ("FRPM Count (Ages 5-17)":REAL, Examples: [702.0, 182.0, 168.0]),
# ("Percent (%) Eligible FRPM (Ages 5-17)":REAL, Examples: [0.65607476635514, 0.484042553191489, 0.730434782608696]),
# ("2013-14 CALPADS Fall 1 Certification Status":INTEGER, Examples: [1])
# ]
# 【Foreign keys】
# satscores.cds=schools.CDSCode
# frpm.CDSCode=schools.CDSCode


# Question: Please list the lowest three eligible free rates for students aged 5-17 in continuation schools.

# Hints:
# Eligible free rates for students aged 5-17 = `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)`

# SQLite Query:
# ```
