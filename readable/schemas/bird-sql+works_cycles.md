```sql
-- Database: works_cycles

/*
Schema: NULL
Table: Address
Rows: 19614
Sample rows:
| AddressID   | AddressLine1         | AddressLine2   | City    | StateProvinceID   | PostalCode   | SpatialLocation                                      | rowguid                              | ModifiedDate          |
|-------------|----------------------|----------------|---------|-------------------|--------------|------------------------------------------------------|--------------------------------------|-----------------------|
| 1           | 1970 Napa Ct.        | [NULL]         | Bothell | 79                | 98011        | 0x00000000010100000067A89189898A5EC0AE8BFC28BCE44740 | 9AADCB0D-36CF-483F-84D8-585C2D4EC6E9 | 2007-12-04 00:00:00.0 |
| 2           | 9833 Mt. Dias Blv.   | [NULL]         | Bothell | 79                | 98011        | 0x000000000101000000BC262A0A03905EC0D6FA851AE6D74740 | 32A54B9E-E034-4BFB-B573-A71CDE60D8C0 | 2008-11-30 00:00:00.0 |
| 3           | 7484 Roundtree Drive | [NULL]         | Bothell | 79                | 98011        | 0x000000000101000000DA930C7893915EC018E304C4ADE14740 | 4C506923-6D1B-452C-A07C-BAA6F5B142A4 | 2013-03-07 00:00:00.0 |
| 4           | 9539 Glenside Dr     | [NULL]         | Bothell | 79                | 98011        | 0x00000000010100000011A5C28A7C955EC0813A0D5F9FDE4740 | E5946C78-4BCC-477F-9FA1-CC09DE16A880 | 2009-02-03 00:00:00.0 |
| 5           | 1226 Shoe St.        | [NULL]         | Bothell | 79                | 98011        | 0x000000000101000000C460EA3FD8855EC061C64D8ABBD94740 | FBAFF937-4A97-4AF0-81FD-B849900E9BB0 | 2008-12-19 00:00:00.0 |
| ...         | ...                  | ...            | ...     | ...               | ...          | ...                                                  | ...                                  | ...                   |
*/
CREATE TABLE Address (
    "AddressID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>18089</example>
    "AddressLine1" TEXT NOT NULL,
        -- <example>'#500-75 O'Connor Street'</example>
    "AddressLine2" TEXT NULL,
        -- <example>'Space 55'</example>
    "City" TEXT NOT NULL,
        -- <example>'Ottawa'</example>
    "StateProvinceID" INTEGER NOT NULL,
        -- <example>57</example>
        -- <fk> -> StateProvince."StateProvinceID"</fk>
    "PostalCode" TEXT NOT NULL,
        -- <example>'K4B 1S2'</example>
    "SpatialLocation" TEXT NOT NULL,
        -- <example>'0x00000000010100000067A89189898A5EC0AE8BFC28BCE44740'</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'00093F9C-0487-4723-B376-D90FF565AD6F'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2007-12-04 00:00:00.0'</example>
    FOREIGN KEY ("StateProvinceID") REFERENCES StateProvince("StateProvinceID")
);

/*
Schema: NULL
Table: AddressType
Rows: 6
All rows:
|   AddressTypeID | Name        | rowguid                              | ModifiedDate          |
|-----------------|-------------|--------------------------------------|-----------------------|
|               1 | Billing     | B84F78B1-4EFE-4A0E-8CB7-70E9F112F886 | 2008-04-30 00:00:00.0 |
|               2 | Home        | 41BC2FF6-F0FC-475F-8EB9-CEC0805AA0F2 | 2008-04-30 00:00:00.0 |
|               3 | Main Office | 8EEEC28C-07A2-4FB9-AD0A-42D4A0BBC575 | 2008-04-30 00:00:00.0 |
|               4 | Primary     | 24CB3088-4345-47C4-86C5-17B535133D1E | 2008-04-30 00:00:00.0 |
|               5 | Shipping    | B29DA3F8-19A3-47DA-9DAA-15C84F4A83A5 | 2008-04-30 00:00:00.0 |
|               6 | Archive     | A67F238A-5BA2-444B-966C-0467ED9C427F | 2008-04-30 00:00:00.0 |
*/
CREATE TABLE AddressType (
    "AddressTypeID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>4</example>
    "Name" TEXT NOT NULL,
        -- <values>{'Archive', 'Billing', 'Home', 'Main Office', 'Primary', 'Shipping'}</values>
    "rowguid" TEXT NOT NULL,
        -- <values>{'24CB3088-4345-47C4-86C5-17B535133D1E', '41BC2FF6-F0FC-475F-8EB9-CEC0805AA0F2', '8EEEC28C-07A2-4FB9-AD0A-42D4A0BBC575', 'A67F238A-5BA2-444B-966C-0467ED9C427F', 'B29DA3F8-19A3-47DA-9DAA-15C84F4A83A5', 'B84F78B1-4EFE-4A0E-8CB7-70E9F112F886'}</values>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: BillOfMaterials
Rows: 2679
Sample rows:
| BillOfMaterialsID   | ProductAssemblyID   | ComponentID   | StartDate             | EndDate   | UnitMeasureCode   | BOMLevel   | PerAssemblyQty   | ModifiedDate          |
|---------------------|---------------------|---------------|-----------------------|-----------|-------------------|------------|------------------|-----------------------|
| 1                   | 807.0               | 1             | 2010-03-04 00:00:00.0 | [NULL]    | EA                | 2          | 1.0              | 2010-02-18 00:00:00.0 |
| 2                   | 782.0               | 995           | 2010-03-04 00:00:00.0 | [NULL]    | EA                | 1          | 1.0              | 2010-02-18 00:00:00.0 |
| 3                   | [NULL]              | 989           | 2010-03-04 00:00:00.0 | [NULL]    | EA                | 0          | 1.0              | 2010-02-18 00:00:00.0 |
| 4                   | [NULL]              | 785           | 2010-03-04 00:00:00.0 | [NULL]    | EA                | 0          | 1.0              | 2010-02-18 00:00:00.0 |
| 5                   | [NULL]              | 775           | 2010-03-04 00:00:00.0 | [NULL]    | EA                | 0          | 1.0              | 2010-02-18 00:00:00.0 |
| ...                 | ...                 | ...           | ...                   | ...       | ...               | ...        | ...              | ...                   |
*/
CREATE TABLE BillOfMaterials (
    "BillOfMaterialsID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>893</example>
    "ProductAssemblyID" INTEGER NULL,
        -- <example>3</example>
        -- <fk> -> Product."ProductID"</fk>
    "ComponentID" INTEGER NOT NULL,
        -- <example>749</example>
        -- <fk> -> Product."ProductID"</fk>
    "StartDate" DATETIME NOT NULL,
        -- <example>'2010-05-26 00:00:00.0'</example>
    "EndDate" DATETIME NULL,
        -- <example>'2010-05-03 00:00:00.0'</example>
    "UnitMeasureCode" TEXT NOT NULL,
        -- <values>{'EA', 'IN', 'OZ'}</values>
        -- <fk> -> UnitMeasure."UnitMeasureCode"</fk>
    "BOMLevel" INTEGER NOT NULL,
        -- <example>2</example>
    "PerAssemblyQty" REAL NOT NULL,
        -- <example>1.000</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2010-02-18 00:00:00.0'</example>
    FOREIGN KEY ("UnitMeasureCode") REFERENCES UnitMeasure("UnitMeasureCode"),
    FOREIGN KEY ("ComponentID") REFERENCES Product("ProductID"),
    FOREIGN KEY ("ProductAssemblyID") REFERENCES Product("ProductID")
);

/*
Schema: NULL
Table: BusinessEntity
Rows: 20777
Sample rows:
| BusinessEntityID   | rowguid                              | ModifiedDate          |
|--------------------|--------------------------------------|-----------------------|
| 1                  | 0C7D8F81-D7B1-4CF0-9C0A-4CD8B6B50087 | 2017-12-13 13:20:24.0 |
| 2                  | 6648747F-7843-4002-B317-65389684C398 | 2017-12-13 13:20:24.0 |
| 3                  | 568204DA-93D7-42F4-8A7A-4446A144277D | 2017-12-13 13:20:24.0 |
| 4                  | 0EFF57B9-4F4F-41A6-8867-658C199A5FC0 | 2017-12-13 13:20:24.0 |
| 5                  | B82F88D1-FF79-4FD9-8C54-9D24C140F647 | 2017-12-13 13:20:24.0 |
| ...                | ...                                  | ...                   |
*/
CREATE TABLE BusinessEntity (
    "BusinessEntityID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>8722</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'00021813-91EF-4A97-9682-0D2AC8C9EA97'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2017-12-13 13:20:24.0'</example>
);

/*
Schema: NULL
Table: BusinessEntityAddress
Rows: 19614
Sample rows:
| BusinessEntityID   | AddressID   | AddressTypeID   | rowguid                              | ModifiedDate          |
|--------------------|-------------|-----------------|--------------------------------------|-----------------------|
| 1                  | 249         | 2               | 3A5D0A00-6739-4DFE-A8F7-844CD9DEE3DF | 2014-09-12 11:15:06.0 |
| 2                  | 293         | 2               | 84AE7057-EDF4-4C51-8B8D-3AEAEFBFB4A1 | 2014-09-12 11:15:06.0 |
| 3                  | 224         | 2               | 3C915B31-7C05-4A05-9859-0DF663677240 | 2014-09-12 11:15:06.0 |
| 4                  | 11387       | 2               | 3DC70CC4-3AE8-424F-8B1F-481C5478E941 | 2014-09-12 11:15:06.0 |
| 5                  | 190         | 2               | C0ED2F68-937B-4594-9459-581AC53C98E3 | 2014-09-12 11:15:06.0 |
| ...                | ...         | ...             | ...                                  | ...                   |
*/
CREATE TABLE BusinessEntityAddress (
    "BusinessEntityID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> BusinessEntity."BusinessEntityID"</fk>
    "AddressID" INTEGER NOT NULL,
        -- <example>249</example>
        -- <fk> -> Address."AddressID"</fk>
    "AddressTypeID" INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> AddressType."AddressTypeID"</fk>
    "rowguid" TEXT NOT NULL,
        -- <example>'00013363-E32F-4615-9439-AFF156D480AE'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2014-09-12 11:15:06.0'</example>
    PRIMARY KEY ("BusinessEntityID", "AddressID", "AddressTypeID"),
    FOREIGN KEY ("AddressID") REFERENCES Address("AddressID"),
    FOREIGN KEY ("AddressTypeID") REFERENCES AddressType("AddressTypeID"),
    FOREIGN KEY ("BusinessEntityID") REFERENCES BusinessEntity("BusinessEntityID")
);

/*
Schema: NULL
Table: BusinessEntityContact
Rows: 909
Sample rows:
| BusinessEntityID   | PersonID   | ContactTypeID   | rowguid                              | ModifiedDate          |
|--------------------|------------|-----------------|--------------------------------------|-----------------------|
| 292                | 291        | 11              | 7D4D2DBC-4A44-48F5-911D-A63ABAFD5120 | 2017-12-13 13:21:02.0 |
| 294                | 293        | 11              | 3EA25B65-9579-4260-977D-D6F00D7D20EE | 2017-12-13 13:21:02.0 |
| 296                | 295        | 11              | DADAC1FF-3351-4827-9AE0-95004885C193 | 2017-12-13 13:21:02.0 |
| 298                | 297        | 11              | B924F26F-6446-45D1-A92B-6F418374F075 | 2017-12-13 13:21:02.0 |
| 300                | 299        | 11              | 5BA4E7BE-8D29-46A2-B68D-67B1615B124A | 2017-12-13 13:21:02.0 |
| ...                | ...        | ...             | ...                                  | ...                   |
*/
CREATE TABLE BusinessEntityContact (
    "BusinessEntityID" INTEGER NOT NULL,
        -- <example>292</example>
        -- <fk> -> BusinessEntity."BusinessEntityID"</fk>
    "PersonID" INTEGER NOT NULL,
        -- <example>291</example>
        -- <fk> -> Person."BusinessEntityID"</fk>
    "ContactTypeID" INTEGER NOT NULL,
        -- <example>11</example>
        -- <fk> -> ContactType."ContactTypeID"</fk>
    "rowguid" TEXT NOT NULL,
        -- <example>'0022434C-E325-47B0-92A0-7302FFA5046F'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2017-12-13 13:21:02.0'</example>
    PRIMARY KEY ("BusinessEntityID", "PersonID", "ContactTypeID"),
    FOREIGN KEY ("BusinessEntityID") REFERENCES BusinessEntity("BusinessEntityID"),
    FOREIGN KEY ("ContactTypeID") REFERENCES ContactType("ContactTypeID"),
    FOREIGN KEY ("PersonID") REFERENCES Person("BusinessEntityID")
);

/*
Schema: NULL
Table: ContactType
Rows: 20
Sample rows:
| ContactTypeID   | Name                           | ModifiedDate          |
|-----------------|--------------------------------|-----------------------|
| 1               | Accounting Manager             | 2008-04-30 00:00:00.0 |
| 2               | Assistant Sales Agent          | 2008-04-30 00:00:00.0 |
| 3               | Assistant Sales Representative | 2008-04-30 00:00:00.0 |
| 4               | Coordinator Foreign Markets    | 2008-04-30 00:00:00.0 |
| 5               | Export Administrator           | 2008-04-30 00:00:00.0 |
| ...             | ...                            | ...                   |
*/
CREATE TABLE ContactType (
    "ContactTypeID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Name" TEXT NOT NULL,
        -- <example>'Accounting Manager'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: CountryRegion
Rows: 239
Sample rows:
| CountryRegionCode   | Name                 | ModifiedDate          |
|---------------------|----------------------|-----------------------|
| Cou                 | Name                 | ModifiedDate          |
| AD                  | Andorra              | 2008-04-30 00:00:00.0 |
| AE                  | United Arab Emirates | 2008-04-30 00:00:00.0 |
| AF                  | Afghanistan          | 2008-04-30 00:00:00.0 |
| AG                  | Antigua and Barbuda  | 2008-04-30 00:00:00.0 |
| ...                 | ...                  | ...                   |
*/
CREATE TABLE CountryRegion (
    "CountryRegionCode" TEXT NOT NULL PRIMARY KEY,
        -- <example>'AD'</example>
    "Name" TEXT NOT NULL,
        -- <example>'Afghanistan'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'ModifiedDate'</example>
);

/*
Schema: NULL
Table: CountryRegionCurrency
Rows: 109
Sample rows:
| CountryRegionCode   | CurrencyCode   | ModifiedDate          |
|---------------------|----------------|-----------------------|
| AE                  | AED            | 2014-02-08 10:17:21.0 |
| AR                  | ARS            | 2014-02-08 10:17:21.0 |
| AT                  | ATS            | 2014-02-08 10:17:21.0 |
| AT                  | EUR            | 2008-04-30 00:00:00.0 |
| AU                  | AUD            | 2014-02-08 10:17:21.0 |
| ...                 | ...            | ...                   |
*/
CREATE TABLE CountryRegionCurrency (
    "CountryRegionCode" TEXT NOT NULL,
        -- <example>'AE'</example>
        -- <fk> -> CountryRegion."CountryRegionCode"</fk>
    "CurrencyCode" TEXT NOT NULL,
        -- <example>'AED'</example>
        -- <fk> -> Currency."CurrencyCode"</fk>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2014-02-08 10:17:21.0'</example>
    PRIMARY KEY ("CountryRegionCode", "CurrencyCode"),
    FOREIGN KEY ("CountryRegionCode") REFERENCES CountryRegion("CountryRegionCode"),
    FOREIGN KEY ("CurrencyCode") REFERENCES Currency("CurrencyCode")
);

/*
Schema: NULL
Table: CreditCard
Rows: 19118
Sample rows:
| CreditCardID   | CardType      | CardNumber     | ExpMonth   | ExpYear   | ModifiedDate          |
|----------------|---------------|----------------|------------|-----------|-----------------------|
| 1              | SuperiorCard  | 33332664695310 | 11         | 2006      | 2013-07-29 00:00:00.0 |
| 2              | Distinguish   | 55552127249722 | 8          | 2005      | 2013-12-05 00:00:00.0 |
| 3              | ColonialVoice | 77778344838353 | 7          | 2005      | 2014-01-14 00:00:00.0 |
| 4              | ColonialVoice | 77774915718248 | 7          | 2006      | 2013-05-20 00:00:00.0 |
| 5              | Vista         | 11114404600042 | 4          | 2005      | 2013-02-01 00:00:00.0 |
| ...            | ...           | ...            | ...        | ...       | ...                   |
*/
CREATE TABLE CreditCard (
    "CreditCardID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>11935</example>
    "CardType" TEXT NOT NULL,
        -- <values>{'ColonialVoice', 'Distinguish', 'SuperiorCard', 'Vista'}</values>
    "CardNumber" TEXT NOT NULL,
        -- <example>'11111000471254'</example>
    "ExpMonth" INTEGER NOT NULL,
        -- <example>11</example>
    "ExpYear" INTEGER NOT NULL,
        -- <example>2006</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2013-07-29 00:00:00.0'</example>
);

/*
Schema: NULL
Table: Culture
Rows: 8
All rows:
| CultureID   | Name                                   | ModifiedDate          |
|-------------|----------------------------------------|-----------------------|
|             | Invariant Language (Invariant Country) | 2008-04-30 00:00:00.0 |
| ar          | Arabic                                 | 2008-04-30 00:00:00.0 |
| en          | English                                | 2008-04-30 00:00:00.0 |
| es          | Spanish                                | 2008-04-30 00:00:00.0 |
| fr          | French                                 | 2008-04-30 00:00:00.0 |
| he          | Hebrew                                 | 2008-04-30 00:00:00.0 |
| th          | Thai                                   | 2008-04-30 00:00:00.0 |
| zh-cht      | Chinese                                | 2008-04-30 00:00:00.0 |
*/
CREATE TABLE Culture (
    "CultureID" TEXT NOT NULL PRIMARY KEY,
        -- <values>{'', 'ar', 'en', 'es', 'fr', 'he', 'th', 'zh-cht'}</values>
    "Name" TEXT NOT NULL,
        -- <values>{'Arabic', 'Chinese', 'English', 'French', 'Hebrew', 'Invariant Language (Invariant Country)', 'Spanish', 'Thai'}</values>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: Currency
Rows: 105
Sample rows:
| CurrencyCode   | Name                          | ModifiedDate          |
|----------------|-------------------------------|-----------------------|
| AED            | Emirati Dirham                | 2008-04-30 00:00:00.0 |
| AFA            | Afghani                       | 2008-04-30 00:00:00.0 |
| ALL            | Lek                           | 2008-04-30 00:00:00.0 |
| AMD            | Armenian Dram                 | 2008-04-30 00:00:00.0 |
| ANG            | Netherlands Antillian Guilder | 2008-04-30 00:00:00.0 |
| ...            | ...                           | ...                   |
*/
CREATE TABLE Currency (
    "CurrencyCode" TEXT NOT NULL PRIMARY KEY,
        -- <example>'AED'</example>
    "Name" TEXT NOT NULL,
        -- <example>'Afghani'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: CurrencyRate
Rows: 13532
Sample rows:
| CurrencyRateID   | CurrencyRateDate      | FromCurrencyCode   | ToCurrencyCode   | AverageRate   | EndOfDayRate   | ModifiedDate          |
|------------------|-----------------------|--------------------|------------------|---------------|----------------|-----------------------|
| 1                | 2011-05-31 00:00:00.0 | USD                | ARS              | 1.0           | 1.0002         | 2011-05-31 00:00:00.0 |
| 2                | 2011-05-31 00:00:00.0 | USD                | AUD              | 1.5491        | 1.55           | 2011-05-31 00:00:00.0 |
| 3                | 2011-05-31 00:00:00.0 | USD                | BRL              | 1.9379        | 1.9419         | 2011-05-31 00:00:00.0 |
| 4                | 2011-05-31 00:00:00.0 | USD                | CAD              | 1.4641        | 1.4683         | 2011-05-31 00:00:00.0 |
| 5                | 2011-05-31 00:00:00.0 | USD                | CNY              | 8.2781        | 8.2784         | 2011-05-31 00:00:00.0 |
| ...              | ...                   | ...                | ...              | ...           | ...            | ...                   |
*/
CREATE TABLE CurrencyRate (
    "CurrencyRateID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "CurrencyRateDate" DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    "FromCurrencyCode" TEXT NOT NULL,
        -- <values>{'USD'}</values>
        -- <fk> -> Currency."CurrencyCode"</fk>
    "ToCurrencyCode" TEXT NOT NULL,
        -- <values>{'ARS', 'AUD', 'BRL', 'CAD', 'CNY', 'DEM', 'EUR', 'FRF', 'GBP', 'JPY', 'MXN', 'SAR', 'USD', 'VEB'}</values>
        -- <fk> -> Currency."CurrencyCode"</fk>
    "AverageRate" REAL NOT NULL,
        -- <example>1.000</example>
    "EndOfDayRate" REAL NOT NULL,
        -- <example>1.000</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    FOREIGN KEY ("ToCurrencyCode") REFERENCES Currency("CurrencyCode"),
    FOREIGN KEY ("FromCurrencyCode") REFERENCES Currency("CurrencyCode")
);

/*
Schema: NULL
Table: Customer
Rows: 0
*/
CREATE TABLE Customer (
    "CustomerID" INTEGER NOT NULL PRIMARY KEY,
    "PersonID" INTEGER NOT NULL,
        -- <fk> -> Person."BusinessEntityID"</fk>
    "StoreID" INTEGER NOT NULL,
        -- <fk> -> Store."BusinessEntityID"</fk>
    "TerritoryID" INTEGER NOT NULL,
        -- <fk> -> SalesTerritory."TerritoryID"</fk>
    "AccountNumber" TEXT NOT NULL,
    "rowguid" TEXT NOT NULL,
    "ModifiedDate" DATETIME NOT NULL,
    FOREIGN KEY ("PersonID") REFERENCES Person("BusinessEntityID"),
    FOREIGN KEY ("TerritoryID") REFERENCES SalesTerritory("TerritoryID"),
    FOREIGN KEY ("StoreID") REFERENCES Store("BusinessEntityID")
);

/*
Schema: NULL
Table: Department
Rows: 16
Sample rows:
| DepartmentID   | Name        | GroupName                | ModifiedDate          |
|----------------|-------------|--------------------------|-----------------------|
| 1              | Engineering | Research and Development | 2008-04-30 00:00:00.0 |
| 2              | Tool Design | Research and Development | 2008-04-30 00:00:00.0 |
| 3              | Sales       | Sales and Marketing      | 2008-04-30 00:00:00.0 |
| 4              | Marketing   | Sales and Marketing      | 2008-04-30 00:00:00.0 |
| 5              | Purchasing  | Inventory Management     | 2008-04-30 00:00:00.0 |
| ...            | ...         | ...                      | ...                   |
*/
CREATE TABLE Department (
    "DepartmentID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>12</example>
    "Name" TEXT NOT NULL,
        -- <example>'Document Control'</example>
    "GroupName" TEXT NOT NULL,
        -- <values>{'Executive General and Administration', 'Inventory Management', 'Manufacturing', 'Quality Assurance', 'Research and Development', 'Sales and Marketing'}</values>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: Document
Rows: 13
Sample rows:
| DocumentNode   | DocumentLevel   | Title                         | Owner   | FolderFlag   | FileName                          | FileExtension   | Revision   | ChangeNumber   | Status   | DocumentSummary                                                                                                                                                                                           | Document                                                                                                                                                                                                    | rowguid                              | ModifiedDate          |
|----------------|-----------------|-------------------------------|---------|--------------|-----------------------------------|-----------------|------------|----------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|-----------------------|
| /              | 0               | Documents                     | 217     | 1            | Documents                         |                 | 0          | 0              | 2        | [NULL]                                                                                                                                                                                                    | [NULL]                                                                                                                                                                                                      | 27CF33AF-C338-4842-966C-75CA11AAA6A3 | 2017-12-13 13:58:03.0 |
| /1/            | 1               | Overview                      | 217     | 1            | Overview                          |                 | 0          | 0              | 2        | [NULL]                                                                                                                                                                                                    | [NULL]                                                                                                                                                                                                      | 26A266F1-1D23-40E2-AF48-6AB8D954FE37 | 2017-12-13 13:58:03.0 |
| /1/1/          | 2               | Introduction 1                | 219     | 0            | Introduction 1.doc                | .doc            | 4          | 28             | 2        | [NULL]                                                                                                                                                                                                    | 0xD0CF11E0A1B11AE1000000000000000000000000000000003E000300FEFF09000600000000000000000000000100000034...0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 | 48265174-8451-4967-973A-639C2276CFAF | 2013-05-30 00:00:00.0 |
| /1/2/          | 2               | Repair and Service Guidelines | 220     | 0            | Repair and Service Guidelines.doc | .doc            | 0          | 8              | 2        | It is important that you maintain your bicycle and keep it in good repair. Detailed repair and servi...uidelines are provided along with instructions for adjusting the tightness of the suspension fork. | 0xD0CF11E0A1B11AE1000000000000000000000000000000003E000300FEFF0900060000000000000000000000010000002E...0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 | 7ED4DEF5-D5BB-4818-8748-5BB5F8315FA2 | 2008-03-31 00:00:00.0 |
| /2/            | 1               | Maintenance                   | 217     | 1            | Maintenance                       |                 | 0          | 0              | 2        | [NULL]                                                                                                                                                                                                    | [NULL]                                                                                                                                                                                                      | 5184D96A-EE8C-499A-9316-625496784DE6 | 2017-12-13 13:58:04.0 |
| ...            | ...             | ...                           | ...     | ...          | ...                               | ...             | ...        | ...            | ...      | ...                                                                                                                                                                                                       | ...                                                                                                                                                                                                         | ...                                  | ...                   |
*/
CREATE TABLE Document (
    "DocumentNode" TEXT NOT NULL PRIMARY KEY,
        -- <example>'/'</example>
    "DocumentLevel" INTEGER NOT NULL,
        -- <example>0</example>
    "Title" TEXT NOT NULL,
        -- <example>'Documents'</example>
    "Owner" INTEGER NOT NULL,
        -- <example>217</example>
        -- <fk> -> Employee."BusinessEntityID"</fk>
    "FolderFlag" INTEGER NOT NULL,
        -- <example>1</example>
    "FileName" TEXT NOT NULL,
        -- <example>'Documents'</example>
    "FileExtension" TEXT NOT NULL,
        -- <values>{'', '.doc'}</values>
    "Revision" TEXT NOT NULL,
        -- <values>{'0', '1', '2', '3', '4', '8'}</values>
    "ChangeNumber" INTEGER NOT NULL,
        -- <example>0</example>
    "Status" INTEGER NOT NULL,
        -- <example>2</example>
    "DocumentSummary" TEXT NULL,
        -- <values>{'Detailed instructions for replacing pedals with Ad... parts when replacing worn or broken components. 
', 'Guidelines and recommendations for lubricating the...quency at which oil or grease should be applied. 
', 'It is important that you maintain your bicycle and... adjusting the tightness of the suspension fork.

', 'Reflectors are vital safety components of your bic... bracket of your Adventure Works Cycles bicycle.

', 'Worn or damaged seats can be easily replaced follo...parts when replacing worn or broken components. 

'}</values>
    "Document" BLOB NULL,
        -- <example>'0xD0CF11E0A1B11AE100000000000000000000000000000000...00000000000000000000000000000000000000000000000000'</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'26A266F1-1D23-40E2-AF48-6AB8D954FE37'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2017-12-13 13:58:03.0'</example>
    FOREIGN KEY ("Owner") REFERENCES Employee("BusinessEntityID")
);

/*
Schema: NULL
Table: EmailAddress
Rows: 19972
Sample rows:
| BusinessEntityID   | EmailAddressID   | EmailAddress                 | rowguid                              | ModifiedDate          |
|--------------------|------------------|------------------------------|--------------------------------------|-----------------------|
| 1                  | 1                | ken0@adventure-works.com     | 8A1901E4-671B-431A-871C-EADB2942E9EE | 2009-01-07 00:00:00.0 |
| 2                  | 2                | terri0@adventure-works.com   | B5FF9EFD-72A2-4F87-830B-F338FDD4D162 | 2008-01-24 00:00:00.0 |
| 3                  | 3                | roberto0@adventure-works.com | C8A51084-1C03-4C58-A8B3-55854AE7C499 | 2007-11-04 00:00:00.0 |
| 4                  | 4                | rob0@adventure-works.com     | 17703ED1-0031-4B4A-AFD2-77487A556B3B | 2007-11-28 00:00:00.0 |
| 5                  | 5                | gail0@adventure-works.com    | E76D2EA3-08E5-409C-BBE2-5DD1CDF89A3B | 2007-12-30 00:00:00.0 |
| ...                | ...              | ...                          | ...                                  | ...                   |
*/
CREATE TABLE EmailAddress (
    "BusinessEntityID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Person."BusinessEntityID"</fk>
    "EmailAddressID" INTEGER NOT NULL,
        -- <example>1</example>
    "EmailAddress" TEXT NOT NULL,
        -- <example>'ken0@adventure-works.com'</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'8A1901E4-671B-431A-871C-EADB2942E9EE'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2009-01-07 00:00:00.0'</example>
    PRIMARY KEY ("BusinessEntityID", "EmailAddressID"),
    FOREIGN KEY ("BusinessEntityID") REFERENCES Person("BusinessEntityID")
);

/*
Schema: NULL
Table: Employee
Rows: 290
Sample rows:
| BusinessEntityID   | NationalIDNumber   | LoginID                  | OrganizationNode   | OrganizationLevel   | JobTitle                      | BirthDate   | MaritalStatus   | Gender   | HireDate   | SalariedFlag   | VacationHours   | SickLeaveHours   | CurrentFlag   | rowguid                              | ModifiedDate          |
|--------------------|--------------------|--------------------------|--------------------|---------------------|-------------------------------|-------------|-----------------|----------|------------|----------------|-----------------|------------------|---------------|--------------------------------------|-----------------------|
| 1                  | 295847284          | adventure-works\ken0     | [NULL]             | [NULL]              | Chief Executive Officer       | 1969-01-29  | S               | M        | 2009-01-14 | 1              | 99              | 69               | 1             | F01251E5-96A3-448D-981E-0F99D789110D | 2014-06-30 00:00:00.0 |
| 2                  | 245797967          | adventure-works\terri0   | /1/                | 1.0                 | Vice President of Engineering | 1971-08-01  | S               | F        | 2008-01-31 | 1              | 1               | 20               | 1             | 45E8F437-670D-4409-93CB-F9424A40D6EE | 2014-06-30 00:00:00.0 |
| 3                  | 509647174          | adventure-works\roberto0 | /1/1/              | 2.0                 | Engineering Manager           | 1974-11-12  | M               | M        | 2007-11-11 | 1              | 2               | 21               | 1             | 9BBBFB2C-EFBB-4217-9AB7-F97689328841 | 2014-06-30 00:00:00.0 |
| 4                  | 112457891          | adventure-works\rob0     | /1/1/1/            | 3.0                 | Senior Tool Designer          | 1974-12-23  | S               | M        | 2007-12-05 | 0              | 48              | 80               | 1             | 59747955-87B8-443F-8ED4-F8AD3AFDF3A9 | 2014-06-30 00:00:00.0 |
| 5                  | 695256908          | adventure-works\gail0    | /1/1/2/            | 3.0                 | Design Engineer               | 1952-09-27  | M               | F        | 2008-01-06 | 1              | 5               | 22               | 1             | EC84AE09-F9B8-4A15-B4A9-6CCBAB919B08 | 2014-06-30 00:00:00.0 |
| ...                | ...                | ...                      | ...                | ...                 | ...                           | ...         | ...             | ...      | ...        | ...            | ...             | ...              | ...           | ...                                  | ...                   |
*/
CREATE TABLE Employee (
    "BusinessEntityID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>151</example>
        -- <fk> -> Person."BusinessEntityID"</fk>
    "NationalIDNumber" TEXT NOT NULL,
        -- <example>'10708100'</example>
    "LoginID" TEXT NOT NULL,
        -- <example>'adventure-works\alan0'</example>
    "OrganizationNode" TEXT NULL,
        -- <example>'/1/'</example>
    "OrganizationLevel" INTEGER NULL,
        -- <example>1</example>
    "JobTitle" TEXT NOT NULL,
        -- <example>'Chief Executive Officer'</example>
    "BirthDate" DATE NOT NULL,
        -- <example>'1969-01-29'</example>
    "MaritalStatus" TEXT NOT NULL,
        -- <values>{'M', 'S'}</values>
    "Gender" TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    "HireDate" DATE NOT NULL,
        -- <example>'2009-01-14'</example>
    "SalariedFlag" INTEGER NOT NULL,
        -- <example>1</example>
    "VacationHours" INTEGER NOT NULL,
        -- <example>99</example>
    "SickLeaveHours" INTEGER NOT NULL,
        -- <example>69</example>
    "CurrentFlag" INTEGER NOT NULL,
        -- <example>1</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'00027A8C-C2F8-4A31-ABA8-8A203638B8F1'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2014-06-30 00:00:00.0'</example>
    FOREIGN KEY ("BusinessEntityID") REFERENCES Person("BusinessEntityID")
);

/*
Schema: NULL
Table: EmployeeDepartmentHistory
Rows: 296
Sample rows:
| BusinessEntityID   | DepartmentID   | ShiftID   | StartDate   | EndDate    | ModifiedDate          |
|--------------------|----------------|-----------|-------------|------------|-----------------------|
| 1                  | 16             | 1         | 2009-01-14  | [NULL]     | 2009-01-13 00:00:00.0 |
| 2                  | 1              | 1         | 2008-01-31  | [NULL]     | 2008-01-30 00:00:00.0 |
| 3                  | 1              | 1         | 2007-11-11  | [NULL]     | 2007-11-10 00:00:00.0 |
| 4                  | 1              | 1         | 2007-12-05  | 2010-05-30 | 2010-05-28 00:00:00.0 |
| 4                  | 2              | 1         | 2010-05-31  | [NULL]     | 2010-05-30 00:00:00.0 |
| ...                | ...            | ...       | ...         | ...        | ...                   |
*/
CREATE TABLE EmployeeDepartmentHistory (
    "BusinessEntityID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Employee."BusinessEntityID"</fk>
    "DepartmentID" INTEGER NOT NULL,
        -- <example>16</example>
        -- <fk> -> Department."DepartmentID"</fk>
    "ShiftID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Shift."ShiftID"</fk>
    "StartDate" DATE NOT NULL,
        -- <example>'2009-01-14'</example>
    "EndDate" DATE NULL,
        -- <example>'2010-05-30'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2009-01-13 00:00:00.0'</example>
    PRIMARY KEY ("BusinessEntityID", "DepartmentID", "ShiftID", "StartDate"),
    FOREIGN KEY ("ShiftID") REFERENCES Shift("ShiftID"),
    FOREIGN KEY ("DepartmentID") REFERENCES Department("DepartmentID"),
    FOREIGN KEY ("BusinessEntityID") REFERENCES Employee("BusinessEntityID")
);

/*
Schema: NULL
Table: EmployeePayHistory
Rows: 316
Sample rows:
| BusinessEntityID   | RateChangeDate        | Rate    | PayFrequency   | ModifiedDate          |
|--------------------|-----------------------|---------|----------------|-----------------------|
| 1                  | 2009-01-14 00:00:00.0 | 125.5   | 2              | 2014-06-30 00:00:00.0 |
| 2                  | 2008-01-31 00:00:00.0 | 63.4615 | 2              | 2014-06-30 00:00:00.0 |
| 3                  | 2007-11-11 00:00:00.0 | 43.2692 | 2              | 2014-06-30 00:00:00.0 |
| 4                  | 2007-12-05 00:00:00.0 | 8.62    | 2              | 2007-11-21 00:00:00.0 |
| 4                  | 2010-05-31 00:00:00.0 | 23.72   | 2              | 2010-05-16 00:00:00.0 |
| ...                | ...                   | ...     | ...            | ...                   |
*/
CREATE TABLE EmployeePayHistory (
    "BusinessEntityID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Employee."BusinessEntityID"</fk>
    "RateChangeDate" DATETIME NOT NULL,
        -- <example>'2009-01-14 00:00:00.0'</example>
    "Rate" REAL NOT NULL,
        -- <example>125.500</example>
    "PayFrequency" INTEGER NOT NULL,
        -- <example>2</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2014-06-30 00:00:00.0'</example>
    PRIMARY KEY ("BusinessEntityID", "RateChangeDate"),
    FOREIGN KEY ("BusinessEntityID") REFERENCES Employee("BusinessEntityID")
);

/*
Schema: NULL
Table: JobCandidate
Rows: 12
Sample rows:
| JobCandidateID   | BusinessEntityID   | Resume                                                                                                                                                                                                      | ModifiedDate          |
|------------------|--------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------|
| 2                | [NULL]             | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"><ns:Name...:EMail>Max@Wingtiptoys.com</ns:EMail><ns:WebSite>http://www.Wingtiptoys.com</ns:WebSite></ns:Resume> | 2007-06-23 00:00:00.0 |
| 3                | [NULL]             | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"><ns:Name...>Krishna@TreyResearch.net</ns:EMail><ns:WebSite>http://www.TreyResearch.net</ns:WebSite></ns:Resume> | 2007-06-23 00:00:00.0 |
| 4                | 274.0              | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"><ns:Name...e></ns:Addr.Telephone></ns:Address><ns:EMail>Stephen@example.com</ns:EMail><ns:WebSite/></ns:Resume> | 2013-12-22 18:32:21.0 |
| 5                | [NULL]             | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"><ns:Name...</ns:Tel.Number></ns:Telephone></ns:Addr.Telephone></ns:Address><ns:EMail/><ns:WebSite/></ns:Resume> | 2007-06-23 00:00:00.0 |
| 6                | [NULL]             | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"><ns:Name...</ns:Tel.Number></ns:Telephone></ns:Addr.Telephone></ns:Address><ns:EMail/><ns:WebSite/></ns:Resume> | 2007-06-23 00:00:00.0 |
| ...              | ...                | ...                                                                                                                                                                                                         | ...                   |
*/
CREATE TABLE JobCandidate (
    "JobCandidateID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>2</example>
    "BusinessEntityID" INTEGER NULL,
        -- <example>274</example>
        -- <fk> -> Employee."BusinessEntityID"</fk>
    "Resume" TEXT NOT NULL,
        -- <example>'<ns:Resume xmlns:ns="http://schemas.microsoft.com/...ttp://www.Wingtiptoys.com</ns:WebSite></ns:Resume>'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2007-06-23 00:00:00.0'</example>
    FOREIGN KEY ("BusinessEntityID") REFERENCES Employee("BusinessEntityID")
);

/*
Schema: NULL
Table: Location
Rows: 14
Sample rows:
| LocationID   | Name              | CostRate   | Availability   | ModifiedDate          |
|--------------|-------------------|------------|----------------|-----------------------|
| 1            | Tool Crib         | 0.0        | 0.0            | 2008-04-30 00:00:00.0 |
| 2            | Sheet Metal Racks | 0.0        | 0.0            | 2008-04-30 00:00:00.0 |
| 3            | Paint Shop        | 0.0        | 0.0            | 2008-04-30 00:00:00.0 |
| 4            | Paint Storage     | 0.0        | 0.0            | 2008-04-30 00:00:00.0 |
| 5            | Metal Storage     | 0.0        | 0.0            | 2008-04-30 00:00:00.0 |
| ...          | ...               | ...        | ...            | ...                   |
*/
CREATE TABLE Location (
    "LocationID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>30</example>
    "Name" TEXT NOT NULL,
        -- <example>'Debur and Polish'</example>
    "CostRate" REAL NOT NULL,
        -- <example>0.000</example>
    "Availability" REAL NOT NULL,
        -- <example>0.000</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: Password
Rows: 19972
Sample rows:
| BusinessEntityID   | PasswordHash                                 | PasswordSalt   | rowguid                              | ModifiedDate          |
|--------------------|----------------------------------------------|----------------|--------------------------------------|-----------------------|
| 1                  | pbFwXWE99vobT6g+vPWFy93NtUU/orrIWafF01hccfM= | bE3XiWw=       | 329EACBE-C883-4F48-B8B6-17AA4627EFFF | 2009-01-07 00:00:00.0 |
| 2                  | bawRVNrZQYQ05qF05Gz6VLilnviZmrqBReTTAGAudm0= | EjJaC3U=       | A4C82398-7466-4FE6-B9EE-CEC34D116F68 | 2008-01-24 00:00:00.0 |
| 3                  | 8BUXrZfDqO1IyHCWOYzYmqN1IhTUn3CJMpdx/UCQ3iY= | wbPZqMw=       | AC3F4536-BB2E-41C5-B70D-454BE460C1BD | 2007-11-04 00:00:00.0 |
| 4                  | SjLXpiarHSlz+6AG+H+4QpB/IPRzras/+9q/5Wr7tf8= | PwSunQU=       | B3FA4C24-2E96-477C-A923-0CB0F6FA5C80 | 2007-11-28 00:00:00.0 |
| 5                  | 8FYdAiY6gWuBsgjCFdg0UibtsqOcWHf9TyaHIP7+paA= | qYhZRiM=       | C4D13BCF-0209-44C7-AC67-6F817FDD7F16 | 2007-12-30 00:00:00.0 |
| ...                | ...                                          | ...            | ...                                  | ...                   |
*/
CREATE TABLE Password (
    "BusinessEntityID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> Person."BusinessEntityID"</fk>
    "PasswordHash" TEXT NOT NULL,
        -- <example>'pbFwXWE99vobT6g+vPWFy93NtUU/orrIWafF01hccfM='</example>
    "PasswordSalt" TEXT NOT NULL,
        -- <example>'bE3XiWw='</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'329EACBE-C883-4F48-B8B6-17AA4627EFFF'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2009-01-07 00:00:00.0'</example>
    FOREIGN KEY ("BusinessEntityID") REFERENCES Person("BusinessEntityID")
);

/*
Schema: NULL
Table: Person
Rows: 19972
Sample rows:
| BusinessEntityID   | PersonType   | NameStyle   | Title   | FirstName   | MiddleName   | LastName   | Suffix   | EmailPromotion   | AdditionalContactInfo   | Demographics                                                                                                                                                        | rowguid                              | ModifiedDate          |
|--------------------|--------------|-------------|---------|-------------|--------------|------------|----------|------------------|-------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|-----------------------|
| 1                  | EM           | 0           | [NULL]  | Ken         | J            | Sánchez    | [NULL]   | 0                | [NULL]                  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey"><TotalPurchaseYTD>0</TotalPurchaseYTD></IndividualSurvey> | 92C4279F-1207-48A3-8448-4636514EB7E2 | 2009-01-07 00:00:00.0 |
| 2                  | EM           | 0           | [NULL]  | Terri       | Lee          | Duffy      | [NULL]   | 1                | [NULL]                  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey"><TotalPurchaseYTD>0</TotalPurchaseYTD></IndividualSurvey> | D8763459-8AA8-47CC-AFF7-C9079AF79033 | 2008-01-24 00:00:00.0 |
| 3                  | EM           | 0           | [NULL]  | Roberto     | [NULL]       | Tamburello | [NULL]   | 0                | [NULL]                  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey"><TotalPurchaseYTD>0</TotalPurchaseYTD></IndividualSurvey> | E1A2555E-0828-434B-A33B-6F38136A37DE | 2007-11-04 00:00:00.0 |
| 4                  | EM           | 0           | [NULL]  | Rob         | [NULL]       | Walters    | [NULL]   | 0                | [NULL]                  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey"><TotalPurchaseYTD>0</TotalPurchaseYTD></IndividualSurvey> | F2D7CE06-38B3-4357-805B-F4B6B71C01FF | 2007-11-28 00:00:00.0 |
| 5                  | EM           | 0           | Ms.     | Gail        | A            | Erickson   | [NULL]   | 0                | [NULL]                  | <IndividualSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey"><TotalPurchaseYTD>0</TotalPurchaseYTD></IndividualSurvey> | F3A3F6B4-AE3B-430C-A754-9F2231BA6FEF | 2007-12-30 00:00:00.0 |
| ...                | ...          | ...         | ...     | ...         | ...          | ...        | ...      | ...              | ...                     | ...                                                                                                                                                                 | ...                                  | ...                   |
*/
CREATE TABLE Person (
    "BusinessEntityID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>14617</example>
        -- <fk> -> BusinessEntity."BusinessEntityID"</fk>
    "PersonType" TEXT NOT NULL,
        -- <values>{'EM', 'GC', 'IN', 'SC', 'SP', 'VC'}</values>
    "NameStyle" INTEGER NOT NULL,
        -- <example>0</example>
    "Title" TEXT NULL,
        -- <values>{'Mr.', 'Mrs.', 'Ms', 'Ms.', 'Sr.', 'Sra.'}</values>
    "FirstName" TEXT NOT NULL,
        -- <example>'Ken'</example>
    "MiddleName" TEXT NULL,
        -- <example>'J'</example>
    "LastName" TEXT NOT NULL,
        -- <example>'Sánchez'</example>
    "Suffix" TEXT NULL,
        -- <values>{'II', 'III', 'IV', 'Jr.', 'PhD', 'Sr.'}</values>
    "EmailPromotion" INTEGER NOT NULL,
        -- <example>0</example>
    "AdditionalContactInfo" TEXT NULL,
        -- <values>{'<AdditionalContactInfo xmlns="http://schemas.micro...</act:number></act:mobile></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...</act:number></act:mobile></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...icing.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...is up.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...obile></crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...obile></crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...odels.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...reach.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...sales.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...tract.</crm:ContactRecord></AdditionalContactInfo>'}</values>
    "Demographics" TEXT NOT NULL,
        -- <example>'<IndividualSurvey xmlns="http://schemas.microsoft....urchaseYTD>0</TotalPurchaseYTD></IndividualSurvey>'</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'000191EF-7424-4A5F-AB19-0852B1F0B78D'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2009-01-07 00:00:00.0'</example>
    FOREIGN KEY ("BusinessEntityID") REFERENCES BusinessEntity("BusinessEntityID")
);

/*
Schema: NULL
Table: PersonCreditCard
Rows: 19118
Sample rows:
| BusinessEntityID   | CreditCardID   | ModifiedDate          |
|--------------------|----------------|-----------------------|
| 293                | 17038          | 2013-07-31 00:00:00.0 |
| 295                | 15369          | 2011-08-01 00:00:00.0 |
| 297                | 8010           | 2011-08-01 00:00:00.0 |
| 299                | 5316           | 2013-07-31 00:00:00.0 |
| 301                | 6653           | 2011-05-31 00:00:00.0 |
| ...                | ...            | ...                   |
*/
CREATE TABLE PersonCreditCard (
    "BusinessEntityID" INTEGER NOT NULL,
        -- <example>293</example>
        -- <fk> -> Person."BusinessEntityID"</fk>
    "CreditCardID" INTEGER NOT NULL,
        -- <example>17038</example>
        -- <fk> -> CreditCard."CreditCardID"</fk>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2013-07-31 00:00:00.0'</example>
    PRIMARY KEY ("BusinessEntityID", "CreditCardID"),
    FOREIGN KEY ("CreditCardID") REFERENCES CreditCard("CreditCardID"),
    FOREIGN KEY ("BusinessEntityID") REFERENCES Person("BusinessEntityID")
);

/*
Schema: NULL
Table: PhoneNumberType
Rows: 3
All rows:
|   PhoneNumberTypeID | Name   | ModifiedDate          |
|---------------------|--------|-----------------------|
|                   1 | Cell   | 2017-12-13 13:19:22.0 |
|                   2 | Home   | 2017-12-13 13:19:22.0 |
|                   3 | Work   | 2017-12-13 13:19:22.0 |
*/
CREATE TABLE PhoneNumberType (
    "PhoneNumberTypeID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Name" TEXT NOT NULL,
        -- <values>{'Cell', 'Home', 'Work'}</values>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2017-12-13 13:19:22.0'</example>
);

/*
Schema: NULL
Table: Product
Rows: 504
Sample rows:
| ProductID   | Name                  | ProductNumber   | MakeFlag   | FinishedGoodsFlag   | Color   | SafetyStockLevel   | ReorderPoint   | StandardCost   | ListPrice   | Size   | SizeUnitMeasureCode   | WeightUnitMeasureCode   | Weight   | DaysToManufacture   | ProductLine   | Class   | Style   | ProductSubcategoryID   | ProductModelID   | SellStartDate         | SellEndDate   | DiscontinuedDate   | rowguid                              | ModifiedDate          |
|-------------|-----------------------|-----------------|------------|---------------------|---------|--------------------|----------------|----------------|-------------|--------|-----------------------|-------------------------|----------|---------------------|---------------|---------|---------|------------------------|------------------|-----------------------|---------------|--------------------|--------------------------------------|-----------------------|
| 1           | Adjustable Race       | AR-5381         | 0          | 0                   | [NULL]  | 1000               | 750            | 0.0            | 0.0         | [NULL] | [NULL]                | [NULL]                  | [NULL]   | 0                   | [NULL]        | [NULL]  | [NULL]  | [NULL]                 | [NULL]           | 2008-04-30 00:00:00.0 | [NULL]        | [NULL]             | 694215B7-08F7-4C0D-ACB1-D734BA44C0C8 | 2014-02-08 10:01:36.0 |
| 2           | Bearing Ball          | BA-8327         | 0          | 0                   | [NULL]  | 1000               | 750            | 0.0            | 0.0         | [NULL] | [NULL]                | [NULL]                  | [NULL]   | 0                   | [NULL]        | [NULL]  | [NULL]  | [NULL]                 | [NULL]           | 2008-04-30 00:00:00.0 | [NULL]        | [NULL]             | 58AE3C20-4F3A-4749-A7D4-D568806CC537 | 2014-02-08 10:01:36.0 |
| 3           | BB Ball Bearing       | BE-2349         | 1          | 0                   | [NULL]  | 800                | 600            | 0.0            | 0.0         | [NULL] | [NULL]                | [NULL]                  | [NULL]   | 1                   | [NULL]        | [NULL]  | [NULL]  | [NULL]                 | [NULL]           | 2008-04-30 00:00:00.0 | [NULL]        | [NULL]             | 9C21AED2-5BFA-4F18-BCB8-F11638DC2E4E | 2014-02-08 10:01:36.0 |
| 4           | Headset Ball Bearings | BE-2908         | 0          | 0                   | [NULL]  | 800                | 600            | 0.0            | 0.0         | [NULL] | [NULL]                | [NULL]                  | [NULL]   | 0                   | [NULL]        | [NULL]  | [NULL]  | [NULL]                 | [NULL]           | 2008-04-30 00:00:00.0 | [NULL]        | [NULL]             | ECFED6CB-51FF-49B5-B06C-7D8AC834DB8B | 2014-02-08 10:01:36.0 |
| 316         | Blade                 | BL-2036         | 1          | 0                   | [NULL]  | 800                | 600            | 0.0            | 0.0         | [NULL] | [NULL]                | [NULL]                  | [NULL]   | 1                   | [NULL]        | [NULL]  | [NULL]  | [NULL]                 | [NULL]           | 2008-04-30 00:00:00.0 | [NULL]        | [NULL]             | E73E9750-603B-4131-89F5-3DD15ED5FF80 | 2014-02-08 10:01:36.0 |
| ...         | ...                   | ...             | ...        | ...                 | ...     | ...                | ...            | ...            | ...         | ...    | ...                   | ...                     | ...      | ...                 | ...           | ...     | ...     | ...                    | ...              | ...                   | ...           | ...                | ...                                  | ...                   |
*/
CREATE TABLE Product (
    "ProductID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>921</example>
    "Name" TEXT NOT NULL,
        -- <example>'AWC Logo Cap'</example>
    "ProductNumber" TEXT NOT NULL,
        -- <example>'AR-5381'</example>
    "MakeFlag" INTEGER NOT NULL,
        -- <example>0</example>
    "FinishedGoodsFlag" INTEGER NOT NULL,
        -- <example>0</example>
    "Color" TEXT NULL,
        -- <values>{'Black', 'Blue', 'Grey', 'Multi', 'Red', 'Silver', 'Silver/Black', 'White', 'Yellow'}</values>
    "SafetyStockLevel" INTEGER NOT NULL,
        -- <example>1000</example>
    "ReorderPoint" INTEGER NOT NULL,
        -- <example>750</example>
    "StandardCost" REAL NOT NULL,
        -- <example>0.000</example>
    "ListPrice" REAL NOT NULL,
        -- <example>0.000</example>
    "Size" TEXT NULL,
        -- <example>'58'</example>
    "SizeUnitMeasureCode" TEXT NULL,
        -- <values>{'CM'}</values>
        -- <fk> -> UnitMeasure."UnitMeasureCode"</fk>
    "WeightUnitMeasureCode" TEXT NULL,
        -- <values>{'G', 'LB'}</values>
        -- <fk> -> UnitMeasure."UnitMeasureCode"</fk>
    "Weight" REAL NULL,
        -- <example>435.000</example>
    "DaysToManufacture" INTEGER NOT NULL,
        -- <example>0</example>
    "ProductLine" TEXT NULL,
        -- <values>{'M', 'R', 'S', 'T'}</values>
    "Class" TEXT NULL,
        -- <values>{'H', 'L', 'M'}</values>
    "Style" TEXT NULL,
        -- <values>{'M', 'U', 'W'}</values>
    "ProductSubcategoryID" INTEGER NULL,
        -- <example>14</example>
        -- <fk> -> ProductSubcategory."ProductSubcategoryID"</fk>
    "ProductModelID" INTEGER NULL,
        -- <example>6</example>
        -- <fk> -> ProductModel."ProductModelID"</fk>
    "SellStartDate" DATETIME NOT NULL,
        -- <example>'2008-04-30 00:00:00.0'</example>
    "SellEndDate" DATETIME NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    "DiscontinuedDate" DATETIME NULL,
    "rowguid" TEXT NOT NULL,
        -- <example>'01A8C3FC-ED52-458E-A634-D5B6E2ACCFED'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2014-02-08 10:01:36.0'</example>
    FOREIGN KEY ("ProductModelID") REFERENCES ProductModel("ProductModelID"),
    FOREIGN KEY ("ProductSubcategoryID") REFERENCES ProductSubcategory("ProductSubcategoryID"),
    FOREIGN KEY ("WeightUnitMeasureCode") REFERENCES UnitMeasure("UnitMeasureCode"),
    FOREIGN KEY ("SizeUnitMeasureCode") REFERENCES UnitMeasure("UnitMeasureCode")
);

/*
Schema: NULL
Table: ProductCategory
Rows: 4
All rows:
|   ProductCategoryID | Name        | rowguid                              | ModifiedDate          |
|---------------------|-------------|--------------------------------------|-----------------------|
|                   1 | Bikes       | CFBDA25C-DF71-47A7-B81B-64EE161AA37C | 2008-04-30 00:00:00.0 |
|                   2 | Components  | C657828D-D808-4ABA-91A3-AF2CE02300E9 | 2008-04-30 00:00:00.0 |
|                   3 | Clothing    | 10A7C342-CA82-48D4-8A38-46A2EB089B74 | 2008-04-30 00:00:00.0 |
|                   4 | Accessories | 2BE3BE36-D9A2-4EEE-B593-ED895D97C2A6 | 2008-04-30 00:00:00.0 |
*/
CREATE TABLE ProductCategory (
    "ProductCategoryID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>3</example>
    "Name" TEXT NOT NULL,
        -- <values>{'Accessories', 'Bikes', 'Clothing', 'Components'}</values>
    "rowguid" TEXT NOT NULL,
        -- <values>{'10A7C342-CA82-48D4-8A38-46A2EB089B74', '2BE3BE36-D9A2-4EEE-B593-ED895D97C2A6', 'C657828D-D808-4ABA-91A3-AF2CE02300E9', 'CFBDA25C-DF71-47A7-B81B-64EE161AA37C'}</values>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: ProductCostHistory
Rows: 395
Sample rows:
| ProductID   | StartDate             | EndDate               | StandardCost   | ModifiedDate          |
|-------------|-----------------------|-----------------------|----------------|-----------------------|
| 707         | 2011-05-31 00:00:00.0 | 2012-05-29 00:00:00.0 | 12.0278        | 2012-05-29 00:00:00.0 |
| 707         | 2012-05-30 00:00:00.0 | 2013-05-29 00:00:00.0 | 13.8782        | 2013-05-29 00:00:00.0 |
| 707         | 2013-05-30 00:00:00.0 | [NULL]                | 13.0863        | 2013-05-16 00:00:00.0 |
| 708         | 2011-05-31 00:00:00.0 | 2012-05-29 00:00:00.0 | 12.0278        | 2012-05-29 00:00:00.0 |
| 708         | 2012-05-30 00:00:00.0 | 2013-05-29 00:00:00.0 | 13.8782        | 2013-05-29 00:00:00.0 |
| ...         | ...                   | ...                   | ...            | ...                   |
*/
CREATE TABLE ProductCostHistory (
    "ProductID" INTEGER NOT NULL,
        -- <example>707</example>
        -- <fk> -> Product."ProductID"</fk>
    "StartDate" DATE NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    "EndDate" DATE NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    "StandardCost" REAL NOT NULL,
        -- <example>12.028</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    PRIMARY KEY ("ProductID", "StartDate"),
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID")
);

/*
Schema: NULL
Table: ProductDescription
Rows: 762
Sample rows:
| ProductDescriptionID   | Description                                                                                                                                             | rowguid                              | ModifiedDate          |
|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|-----------------------|
| 3                      | Chromoly steel.                                                                                                                                         | 301EED3A-1A82-4855-99CB-2AFE8290D641 | 2013-04-30 00:00:00.0 |
| 4                      | Aluminum alloy cups; large diameter spindle.                                                                                                            | DFEBA528-DA11-4650-9D86-CAFDA7294EB0 | 2013-04-30 00:00:00.0 |
| 5                      | Aluminum alloy cups and a hollow axle.                                                                                                                  | F7178DA7-1A7E-4997-8470-06737181305E | 2013-04-30 00:00:00.0 |
| 8                      | Suitable for any type of riding, on or off-road. Fits any budget. Smooth-shifting with a comfortable ride.                                              | 8E6746E5-AD97-46E2-BD24-FCEA075C3B52 | 2013-04-30 00:00:00.0 |
| 64                     | This bike delivers a high-level of performance on a budget. It is responsive and maneuverable, and offers peace-of-mind when you decide to go off-road. | 7B1C4E90-85E2-4792-B47B-E0C424E2EC94 | 2013-04-30 00:00:00.0 |
| ...                    | ...                                                                                                                                                     | ...                                  | ...                   |
*/
CREATE TABLE ProductDescription (
    "ProductDescriptionID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1954</example>
    "Description" TEXT NOT NULL,
        -- <example>'Chromoly steel.'</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'00FFDFAC-0207-4DF0-8051-7D3C884816F3'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2013-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: ProductDocument
Rows: 32
Sample rows:
| ProductID   | DocumentNode   | ModifiedDate          |
|-------------|----------------|-----------------------|
| 317         | /2/1/          | 2013-12-29 13:51:58.0 |
| 318         | /2/1/          | 2013-12-29 13:51:58.0 |
| 319         | /2/1/          | 2013-12-29 13:51:58.0 |
| 506         | /3/1/          | 2013-12-29 13:51:58.0 |
| 506         | /3/2/          | 2013-12-29 13:51:58.0 |
| ...         | ...            | ...                   |
*/
CREATE TABLE ProductDocument (
    "ProductID" INTEGER NOT NULL,
        -- <example>317</example>
        -- <fk> -> Product."ProductID"</fk>
    "DocumentNode" TEXT NOT NULL,
        -- <values>{'/1/1/', '/2/1/', '/3/1/', '/3/2/', '/3/3/', '/3/4/'}</values>
        -- <fk> -> Document."DocumentNode"</fk>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2013-12-29 13:51:58.0'</example>
    PRIMARY KEY ("ProductID", "DocumentNode"),
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID"),
    FOREIGN KEY ("DocumentNode") REFERENCES Document("DocumentNode")
);

/*
Schema: NULL
Table: ProductInventory
Rows: 1069
Sample rows:
| ProductID   | LocationID   | Shelf   | Bin   | Quantity   | rowguid                              | ModifiedDate          |
|-------------|--------------|---------|-------|------------|--------------------------------------|-----------------------|
| 1           | 1            | A       | 1     | 408        | 47A24246-6C43-48EB-968F-025738A8A410 | 2014-08-08 00:00:00.0 |
| 1           | 6            | B       | 5     | 324        | D4544D7D-CAF5-46B3-AB22-5718DCC26B5E | 2014-08-08 00:00:00.0 |
| 1           | 50           | A       | 5     | 353        | BFF7DC60-96A8-43CA-81A7-D6D2ED3000A8 | 2014-08-08 00:00:00.0 |
| 2           | 1            | A       | 2     | 427        | F407C07A-CA14-4684-A02C-608BD00C2233 | 2014-08-08 00:00:00.0 |
| 2           | 6            | B       | 1     | 318        | CA1FF2F4-48FB-4960-8D92-3940B633E4C1 | 2014-08-08 00:00:00.0 |
| ...         | ...          | ...     | ...   | ...        | ...                                  | ...                   |
*/
CREATE TABLE ProductInventory (
    "ProductID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Product."ProductID"</fk>
    "LocationID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Location."LocationID"</fk>
    "Shelf" TEXT NOT NULL,
        -- <example>'A'</example>
    "Bin" INTEGER NOT NULL,
        -- <example>1</example>
    "Quantity" INTEGER NOT NULL,
        -- <example>408</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'47A24246-6C43-48EB-968F-025738A8A410'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2014-08-08 00:00:00.0'</example>
    PRIMARY KEY ("ProductID", "LocationID"),
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID"),
    FOREIGN KEY ("LocationID") REFERENCES Location("LocationID")
);

/*
Schema: NULL
Table: ProductListPriceHistory
Rows: 395
Sample rows:
| ProductID   | StartDate             | EndDate               | ListPrice   | ModifiedDate          |
|-------------|-----------------------|-----------------------|-------------|-----------------------|
| 707         | 2011-05-31 00:00:00.0 | 2012-05-29 00:00:00.0 | 33.6442     | 2012-05-29 00:00:00.0 |
| 707         | 2012-05-30 00:00:00.0 | 2013-05-29 00:00:00.0 | 33.6442     | 2013-05-29 00:00:00.0 |
| 707         | 2013-05-30 00:00:00.0 | [NULL]                | 34.99       | 2013-05-09 00:00:00.0 |
| 708         | 2011-05-31 00:00:00.0 | 2012-05-29 00:00:00.0 | 33.6442     | 2012-05-29 00:00:00.0 |
| 708         | 2012-05-30 00:00:00.0 | 2013-05-29 00:00:00.0 | 33.6442     | 2013-05-29 00:00:00.0 |
| ...         | ...                   | ...                   | ...         | ...                   |
*/
CREATE TABLE ProductListPriceHistory (
    "ProductID" INTEGER NOT NULL,
        -- <example>707</example>
        -- <fk> -> Product."ProductID"</fk>
    "StartDate" DATE NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    "EndDate" DATE NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    "ListPrice" REAL NOT NULL,
        -- <example>33.644</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    PRIMARY KEY ("ProductID", "StartDate"),
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID")
);

/*
Schema: NULL
Table: ProductModel
Rows: 128
Sample rows:
| ProductModelID   | Name               | CatalogDescription   | Instructions   | rowguid                              | ModifiedDate          |
|------------------|--------------------|----------------------|----------------|--------------------------------------|-----------------------|
| 1                | Classic Vest       | [NULL]               | [NULL]         | 29321D47-1E4C-4AAC-887C-19634328C25E | 2013-04-30 00:00:00.0 |
| 2                | Cycling Cap        | [NULL]               | [NULL]         | 474FB654-3C96-4CB9-82DF-2152EEFFBDB0 | 2011-05-01 00:00:00.0 |
| 3                | Full-Finger Gloves | [NULL]               | [NULL]         | A75483FE-3C47-4AA4-93CF-664B51192987 | 2012-04-30 00:00:00.0 |
| 4                | Half-Finger Gloves | [NULL]               | [NULL]         | 14B56F2A-D4AA-40A4-B9A2-984F165ED702 | 2012-04-30 00:00:00.0 |
| 5                | HL Mountain Frame  | [NULL]               | [NULL]         | FDD5407B-C2DB-49D1-A86B-C13A2E3582A2 | 2011-05-01 00:00:00.0 |
| ...              | ...                | ...                  | ...            | ...                                  | ...                   |
*/
CREATE TABLE ProductModel (
    "ProductModelID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>82</example>
    "Name" TEXT NOT NULL,
        -- <example>'All-Purpose Bike Stand'</example>
    "CatalogDescription" TEXT NULL,
        -- <values>{'<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>'}</values>
    "Instructions" TEXT NULL,
        -- <values>{'<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...flate the tube to 35 PSI.</step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...lustration <diag>7</diag></step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...p><step>Move to shipping.</step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...p><step>Move to shipping.</step></Location></root>'}</values>
    "rowguid" TEXT NOT NULL,
        -- <example>'00CE9171-8944-4D49-BA37-485C1D122F5C'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2013-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: ProductModelProductDescriptionCulture
Rows: 762
Sample rows:
| ProductModelID   | ProductDescriptionID   | CultureID   | ModifiedDate          |
|------------------|------------------------|-------------|-----------------------|
| 1                | 1199                   | en          | 2013-04-30 00:00:00.0 |
| 1                | 1467                   | ar          | 2013-04-30 00:00:00.0 |
| 1                | 1589                   | fr          | 2013-04-30 00:00:00.0 |
| 1                | 1712                   | th          | 2013-04-30 00:00:00.0 |
| 1                | 1838                   | he          | 2013-04-30 00:00:00.0 |
| ...              | ...                    | ...         | ...                   |
*/
CREATE TABLE ProductModelProductDescriptionCulture (
    "ProductModelID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ProductModel."ProductModelID"</fk>
    "ProductDescriptionID" INTEGER NOT NULL,
        -- <example>1199</example>
        -- <fk> -> ProductDescription."ProductDescriptionID"</fk>
    "CultureID" TEXT NOT NULL,
        -- <values>{'ar', 'en', 'fr', 'he', 'th', 'zh-cht'}</values>
        -- <fk> -> Culture."CultureID"</fk>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2013-04-30 00:00:00.0'</example>
    PRIMARY KEY ("ProductModelID", "ProductDescriptionID", "CultureID"),
    FOREIGN KEY ("ProductModelID") REFERENCES ProductModel("ProductModelID"),
    FOREIGN KEY ("ProductDescriptionID") REFERENCES ProductDescription("ProductDescriptionID"),
    FOREIGN KEY ("CultureID") REFERENCES Culture("CultureID")
);

/*
Schema: NULL
Table: ProductPhoto
Rows: 100
Sample rows:
| ProductPhotoID   | ThumbNailPhoto                                                                                                                                                                                              | ThumbnailPhotoFileName    | LargePhoto                                                                                                                                                                                                  | LargePhotoFileName        | ModifiedDate          |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|-----------------------|
| 69               | 0x47494638396150003100F70000E3E3FCA6ACB3F5F6FE303D47F8FAFDEDEEFE989DA2F6F8FD6C86B5999B9DD3D3D5E2E5EA...12292B17512415A000AF000DD0400334700121007734391DA7B10653A210B9C00FDA2026E4C00F1299108D3811010100003B | racer02_black_f_small.gif | 0x474946383961F0009500F70000D3D3FEE2E3FE86878ADBDCFED7D8E7929BA8545659C9CAD8B7C4CD97999B030405767A84...410448A11640815E57801444A059DDF5D0B60D54F5555FFF632ECA61C0785440D755E992B335FC5561171648172B2000003B | racer02_black_f_large.gif | 2008-04-30 00:00:00.0 |
| 70               | 0x47494638396150003100F70000E3E3FCEBECF3F5F6FE999B9DEDEDFEDCE3EB374249B2BCCFABADB2F9FAFDD3D3D4373C44...400B8689125BF1000A9005F4400F355003124001AB291EE2811AD6213388020D12300003B00ED0302609519013111000003B | racer02_black_small.gif   | 0x474946383961F0009500F7000086878AECEDFED7D8E7D3D3FEE3E3FE909AA8DCDDFE545559C7C8D997999BB8C4CD96A2AF...462014668113A2F9054281F996992F97037BBBD49AAD5927E2E31CBEAF82B3F998E3EB7353629BCF199D33789C020200003B | racer02_black_large.gif   | 2012-10-19 09:56:38.0 |
| 72               | 0x47494638396150003100F70000F1F2FEE3E3FCA3ACB6EBEBF3F5F6FEEDEEFE66676BF9FAFEE2E5EAB7BAC65656593B4753...E08F28B12B1516E000BA400DD4900339500A1E00251F791C88611BCAA210DB00025BC200E58002979210793811010100003B | racer02_blue_f_small.gif  | 0x474946383961F0009500F700008EAFC785868991A5B2B5C7D1F2F3F4ECEDFE97989AD7D8E7D3D3FEE2E3FEDCDDFEC7C9D9...A0156CE114DED4065A01048E344D89C4DFF8B217EBB44EA3E243D6E1AD6A134FCBB4D8FE526FF4D4500F3537D92A2000003B | racer02_blue_f_large.gif  | 2012-10-19 09:56:38.0 |
| 73               | 0x47494638396150003100F700004978A7E2E3F3FAFCFE34353A46474BE1E3E4E3E3FBF1F2FE66686CEBECF352669175777B...87260B39891259F10123C00CCFF00C555005F37002B7001656F31D8D71320AF10E23202A18800E3C802509C18B131110003B | racer02_blue_small.gif    | 0x474946383961F0009500F700008B99A9708FAEA5A7AA8CAECA97A4AFD7D8E7F2F3F4ECEDFED3D3FEB7C5CEE2E3FEDCDDFE...F1A4B98E9F41056E410762C19B73E016D40F9B39F376E1789CC7B9310683221679DEA8D95A71D76CCE599EE7F9F00202003B | racer02_blue_large.gif    | 2012-10-19 09:56:38.0 |
| 76               | 0x47494638396150003100F700007689B3B1D5A475777BECEBF234353A85A376FAFCFE45474BF1F2FEE2E2FC6B919D4D5A6C...DE582B17911525F005D3C00EECC0044C900234E08FCFF11CA06107048310C0F00161B202CDC003DE9810615810010100003B | racer02_green_f_small.gif | 0x474946383961F0009500F70000CACBF8D6E4EFA3D19EECEDFEF3F4F4D3D3FEE2E3FEDCDDFED7D7E7979AA6B4C7CEA5A7AA...A1077EC00AACE00774A10540144865C46EFAB1329BB44979A241CE21ABE0733E79F401B53227A4D44BBFB412952B2000003B | racer02_green_f_large.gif | 2012-10-19 09:56:38.0 |
| ...              | ...                                                                                                                                                                                                         | ...                       | ...                                                                                                                                                                                                         | ...                       | ...                   |
*/
CREATE TABLE ProductPhoto (
    "ProductPhotoID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>69</example>
    "ThumbNailPhoto" BLOB NOT NULL,
        -- <example>'0x47494638396150003100F70000E3E3FCA6ACB3F5F6FE303D...B10653A210B9C00FDA2026E4C00F1299108D3811010100003B'</example>
    "ThumbnailPhotoFileName" TEXT NOT NULL,
        -- <example>'racer02_black_f_small.gif'</example>
    "LargePhoto" BLOB NOT NULL,
        -- <example>'0x474946383961F0009500F70000D3D3FEE2E3FE86878ADBDC...2ECA61C0785440D755E992B335FC5561171648172B2000003B'</example>
    "LargePhotoFileName" TEXT NOT NULL,
        -- <example>'racer02_black_f_large.gif'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: ProductProductPhoto
Rows: 504
Sample rows:
| ProductID   | ProductPhotoID   | Primary   | ModifiedDate          |
|-------------|------------------|-----------|-----------------------|
| 1           | 1                | 1         | 2008-03-31 00:00:00.0 |
| 2           | 1                | 1         | 2008-03-31 00:00:00.0 |
| 3           | 1                | 1         | 2008-03-31 00:00:00.0 |
| 4           | 1                | 1         | 2008-03-31 00:00:00.0 |
| 316         | 1                | 1         | 2008-03-31 00:00:00.0 |
| ...         | ...              | ...       | ...                   |
*/
CREATE TABLE ProductProductPhoto (
    "ProductID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Product."ProductID"</fk>
    "ProductPhotoID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ProductPhoto."ProductPhotoID"</fk>
    "Primary" INTEGER NOT NULL,
        -- <example>1</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2008-03-31 00:00:00.0'</example>
    PRIMARY KEY ("ProductID", "ProductPhotoID"),
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID"),
    FOREIGN KEY ("ProductPhotoID") REFERENCES ProductPhoto("ProductPhotoID")
);

/*
Schema: NULL
Table: ProductReview
Rows: 4
All rows:
|   ProductReviewID |   ProductID | ReviewerName   | ReviewDate            | EmailAddress                     |   Rating | Comments                                                                                                                                                                                                    | ModifiedDate          |
|-------------------|-------------|----------------|-----------------------|----------------------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------|
|                 1 |         709 | John Smith     | 2013-09-18 00:00:00.0 | john@fourthcoffee.com            |        5 | I can't believe I'm singing the praises of a pair of socks, but I just came back from a grueling
3-d...last. They're lightweight yet really cushioned my feet all day. 
The reinforced toe is nearly bullet                                                                                                                                                                                                             | 2013-09-18 00:00:00.0 |
|                 2 |         937 | David          | 2013-11-13 00:00:00.0 | david@graphicdesigninstitute.com |        4 | A little on the heavy side, but overall the entry/exit is easy in all conditions. I've used these pe...m. Cleanup is easy. Mud and sand don't get trapped. I would like 
them even better if there was a we                                                                                                                                                                                                             | 2013-11-13 00:00:00.0 |
|                 3 |         937 | Jill           | 2013-11-15 00:00:00.0 | jill@margiestravel.com           |        2 | Maybe it's just because I'm new to mountain biking, but I had a terrible time getting use
to these p...ease my foot. Any suggestions on
ways I can adjust the pedals, or is it just a learning curve thing?                                                                                                                                                                                                             | 2013-11-15 00:00:00.0 |
|                 4 |         798 | Laura Norman   | 2013-11-15 00:00:00.0 | laura@treyresearch.net           |        5 | The Road-550-W from Adventure Works Cycles is everything it's advertised to be. Finally, a quality b...trol and comfort in one neat package. The top tube is shorter, the suspension is weight-tuned and th | 2013-11-15 00:00:00.0 |
*/
CREATE TABLE ProductReview (
    "ProductReviewID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "ProductID" INTEGER NOT NULL,
        -- <example>709</example>
        -- <fk> -> Product."ProductID"</fk>
    "ReviewerName" TEXT NOT NULL,
        -- <values>{'David', 'Jill', 'John Smith', 'Laura Norman'}</values>
    "ReviewDate" DATETIME NOT NULL,
        -- <example>'2013-09-18 00:00:00.0'</example>
    "EmailAddress" TEXT NOT NULL,
        -- <values>{'david@graphicdesigninstitute.com', 'jill@margiestravel.com', 'john@fourthcoffee.com', 'laura@treyresearch.net'}</values>
    "Rating" INTEGER NOT NULL,
        -- <example>5</example>
    "Comments" TEXT NOT NULL,
        -- <values>{'A little on the heavy side, but overall the entry/.... I would like 
them even better if there was a we', 'I can't believe I'm singing the praises of a pair ...feet all day. 
The reinforced toe is nearly bullet', 'Maybe it's just because I'm new to mountain biking... the pedals, or is it just a learning curve thing?', 'The Road-550-W from Adventure Works Cycles is ever... is shorter, the suspension is weight-tuned and th'}</values>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2013-09-18 00:00:00.0'</example>
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID")
);

/*
Schema: NULL
Table: ProductSubcategory
Rows: 37
Sample rows:
| ProductSubcategoryID   | ProductCategoryID   | Name            | rowguid                              | ModifiedDate          |
|------------------------|---------------------|-----------------|--------------------------------------|-----------------------|
| 1                      | 1                   | Mountain Bikes  | 2D364ADE-264A-433C-B092-4FCBF3804E01 | 2008-04-30 00:00:00.0 |
| 2                      | 1                   | Road Bikes      | 000310C0-BCC8-42C4-B0C3-45AE611AF06B | 2008-04-30 00:00:00.0 |
| 3                      | 1                   | Touring Bikes   | 02C5061D-ECDC-4274-B5F1-E91D76BC3F37 | 2008-04-30 00:00:00.0 |
| 4                      | 2                   | Handlebars      | 3EF2C725-7135-4C85-9AE6-AE9A3BDD9283 | 2008-04-30 00:00:00.0 |
| 5                      | 2                   | Bottom Brackets | A9E54089-8A1E-4CF5-8646-E3801F685934 | 2008-04-30 00:00:00.0 |
| ...                    | ...                 | ...             | ...                                  | ...                   |
*/
CREATE TABLE ProductSubcategory (
    "ProductSubcategoryID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>2</example>
    "ProductCategoryID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ProductCategory."ProductCategoryID"</fk>
    "Name" TEXT NOT NULL,
        -- <example>'Bib-Shorts'</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'000310C0-BCC8-42C4-B0C3-45AE611AF06B'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2008-04-30 00:00:00.0'</example>
    FOREIGN KEY ("ProductCategoryID") REFERENCES ProductCategory("ProductCategoryID")
);

/*
Schema: NULL
Table: ProductVendor
Rows: 460
Sample rows:
| ProductID   | BusinessEntityID   | AverageLeadTime   | StandardPrice   | LastReceiptCost   | LastReceiptDate       | MinOrderQty   | MaxOrderQty   | OnOrderQty   | UnitMeasureCode   | ModifiedDate          |
|-------------|--------------------|-------------------|-----------------|-------------------|-----------------------|---------------|---------------|--------------|-------------------|-----------------------|
| 1           | 1580               | 17                | 47.87           | 50.2635           | 2011-08-29 00:00:00.0 | 1             | 5             | 3.0          | CS                | 2011-08-29 00:00:00.0 |
| 2           | 1688               | 19                | 39.92           | 41.916            | 2011-08-29 00:00:00.0 | 1             | 5             | 3.0          | CTN               | 2011-08-29 00:00:00.0 |
| 4           | 1650               | 17                | 54.31           | 57.0255           | 2011-08-29 00:00:00.0 | 1             | 5             | [NULL]       | CTN               | 2011-08-29 00:00:00.0 |
| 317         | 1578               | 19                | 28.17           | 29.5785           | 2011-08-29 00:00:00.0 | 100           | 1000          | 300.0        | EA                | 2011-08-29 00:00:00.0 |
| 317         | 1678               | 17                | 25.77           | 27.0585           | 2011-08-25 00:00:00.0 | 100           | 1000          | [NULL]       | EA                | 2011-08-25 00:00:00.0 |
| ...         | ...                | ...               | ...             | ...               | ...                   | ...           | ...           | ...          | ...               | ...                   |
*/
CREATE TABLE ProductVendor (
    "ProductID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Product."ProductID"</fk>
    "BusinessEntityID" INTEGER NOT NULL,
        -- <example>1580</example>
        -- <fk> -> Vendor."BusinessEntityID"</fk>
    "AverageLeadTime" INTEGER NOT NULL,
        -- <example>17</example>
    "StandardPrice" REAL NOT NULL,
        -- <example>47.870</example>
    "LastReceiptCost" REAL NOT NULL,
        -- <example>50.264</example>
    "LastReceiptDate" DATETIME NOT NULL,
        -- <example>'2011-08-29 00:00:00.0'</example>
    "MinOrderQty" INTEGER NOT NULL,
        -- <example>1</example>
    "MaxOrderQty" INTEGER NOT NULL,
        -- <example>5</example>
    "OnOrderQty" INTEGER NULL,
        -- <example>3</example>
    "UnitMeasureCode" TEXT NOT NULL,
        -- <values>{'CAN', 'CS', 'CTN', 'DZ', 'EA', 'GAL', 'PAK'}</values>
        -- <fk> -> UnitMeasure."UnitMeasureCode"</fk>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-08-29 00:00:00.0'</example>
    PRIMARY KEY ("ProductID", "BusinessEntityID"),
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID"),
    FOREIGN KEY ("BusinessEntityID") REFERENCES Vendor("BusinessEntityID"),
    FOREIGN KEY ("UnitMeasureCode") REFERENCES UnitMeasure("UnitMeasureCode")
);

/*
Schema: NULL
Table: PurchaseOrderDetail
Rows: 8845
Sample rows:
| PurchaseOrderID   | PurchaseOrderDetailID   | DueDate               | OrderQty   | ProductID   | UnitPrice   | LineTotal   | ReceivedQty   | RejectedQty   | StockedQty   | ModifiedDate          |
|-------------------|-------------------------|-----------------------|------------|-------------|-------------|-------------|---------------|---------------|--------------|-----------------------|
| 1                 | 1                       | 2011-04-30 00:00:00.0 | 4          | 1           | 50.0        | 201.0       | 3.0           | 0.0           | 3.0          | 2011-04-23 00:00:00.0 |
| 2                 | 2                       | 2011-04-30 00:00:00.0 | 3          | 359         | 45.0        | 135.0       | 3.0           | 0.0           | 3.0          | 2011-04-23 00:00:00.0 |
| 2                 | 3                       | 2011-04-30 00:00:00.0 | 3          | 360         | 46.0        | 137.0       | 3.0           | 0.0           | 3.0          | 2011-04-23 00:00:00.0 |
| 3                 | 4                       | 2011-04-30 00:00:00.0 | 550        | 530         | 16.0        | 8847.0      | 550.0         | 0.0           | 550.0        | 2011-04-23 00:00:00.0 |
| 4                 | 5                       | 2011-04-30 00:00:00.0 | 3          | 4           | 57.0        | 171.0       | 2.0           | 1.0           | 1.0          | 2011-04-23 00:00:00.0 |
| ...               | ...                     | ...                   | ...        | ...         | ...         | ...         | ...           | ...           | ...          | ...                   |
*/
CREATE TABLE PurchaseOrderDetail (
    "PurchaseOrderID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> PurchaseOrderHeader."PurchaseOrderID"</fk>
    "PurchaseOrderDetailID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "DueDate" DATETIME NOT NULL,
        -- <example>'2011-04-30 00:00:00.0'</example>
    "OrderQty" INTEGER NOT NULL,
        -- <example>4</example>
    "ProductID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Product."ProductID"</fk>
    "UnitPrice" REAL NOT NULL,
        -- <example>50.000</example>
    "LineTotal" REAL NOT NULL,
        -- <example>201.000</example>
    "ReceivedQty" REAL NOT NULL,
        -- <example>3.000</example>
    "RejectedQty" REAL NOT NULL,
        -- <example>0.000</example>
    "StockedQty" REAL NOT NULL,
        -- <example>3.000</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-04-23 00:00:00.0'</example>
    FOREIGN KEY ("PurchaseOrderID") REFERENCES PurchaseOrderHeader("PurchaseOrderID"),
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID")
);

/*
Schema: NULL
Table: PurchaseOrderHeader
Rows: 4012
Sample rows:
| PurchaseOrderID   | RevisionNumber   | Status   | EmployeeID   | VendorID   | ShipMethodID   | OrderDate             | ShipDate              | SubTotal   | TaxAmt   | Freight   | TotalDue   | ModifiedDate          |
|-------------------|------------------|----------|--------------|------------|----------------|-----------------------|-----------------------|------------|----------|-----------|------------|-----------------------|
| 1                 | 4                | 4        | 258          | 1580       | 3              | 2011-04-16 00:00:00.0 | 2011-04-25 00:00:00.0 | 201.04     | 16.0832  | 5.026     | 222.1492   | 2011-04-25 00:00:00.0 |
| 2                 | 4                | 1        | 254          | 1496       | 5              | 2011-04-16 00:00:00.0 | 2011-04-25 00:00:00.0 | 272.1015   | 21.7681  | 6.8025    | 300.6721   | 2011-04-25 00:00:00.0 |
| 3                 | 4                | 4        | 257          | 1494       | 2              | 2011-04-16 00:00:00.0 | 2011-04-25 00:00:00.0 | 8847.3     | 707.784  | 221.1825  | 9776.2665  | 2011-04-25 00:00:00.0 |
| 4                 | 4                | 3        | 261          | 1650       | 5              | 2011-04-16 00:00:00.0 | 2011-04-25 00:00:00.0 | 171.0765   | 13.6861  | 4.2769    | 189.0395   | 2011-04-25 00:00:00.0 |
| 5                 | 4                | 4        | 251          | 1654       | 4              | 2011-04-30 00:00:00.0 | 2011-05-09 00:00:00.0 | 20397.3    | 1631.784 | 509.9325  | 22539.0165 | 2011-05-09 00:00:00.0 |
| ...               | ...              | ...      | ...          | ...        | ...            | ...                   | ...                   | ...        | ...      | ...       | ...        | ...                   |
*/
CREATE TABLE PurchaseOrderHeader (
    "PurchaseOrderID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "RevisionNumber" INTEGER NOT NULL,
        -- <example>4</example>
    "Status" INTEGER NOT NULL,
        -- <example>4</example>
    "EmployeeID" INTEGER NOT NULL,
        -- <example>258</example>
        -- <fk> -> Employee."BusinessEntityID"</fk>
    "VendorID" INTEGER NOT NULL,
        -- <example>1580</example>
        -- <fk> -> Vendor."BusinessEntityID"</fk>
    "ShipMethodID" INTEGER NOT NULL,
        -- <example>3</example>
        -- <fk> -> ShipMethod."ShipMethodID"</fk>
    "OrderDate" DATETIME NOT NULL,
        -- <example>'2011-04-16 00:00:00.0'</example>
    "ShipDate" DATETIME NOT NULL,
        -- <example>'2011-04-25 00:00:00.0'</example>
    "SubTotal" REAL NOT NULL,
        -- <example>201.040</example>
    "TaxAmt" REAL NOT NULL,
        -- <example>16.083</example>
    "Freight" REAL NOT NULL,
        -- <example>5.026</example>
    "TotalDue" REAL NOT NULL,
        -- <example>222.149</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-04-25 00:00:00.0'</example>
    FOREIGN KEY ("EmployeeID") REFERENCES Employee("BusinessEntityID"),
    FOREIGN KEY ("VendorID") REFERENCES Vendor("BusinessEntityID"),
    FOREIGN KEY ("ShipMethodID") REFERENCES ShipMethod("ShipMethodID")
);

/*
Schema: NULL
Table: SalesOrderDetail
Rows: 121317
Sample rows:
| SalesOrderID   | SalesOrderDetailID   | CarrierTrackingNumber   | OrderQty   | ProductID   | SpecialOfferID   | UnitPrice   | UnitPriceDiscount   | LineTotal   | rowguid                              | ModifiedDate          |
|----------------|----------------------|-------------------------|------------|-------------|------------------|-------------|---------------------|-------------|--------------------------------------|-----------------------|
| 43659          | 1                    | 4911-403C-98            | 1          | 776         | 1                | 2025.0      | 0.0                 | 2025.0      | B207C96D-D9E6-402B-8470-2CC176C42283 | 2011-05-31 00:00:00.0 |
| 43659          | 2                    | 4911-403C-98            | 3          | 777         | 1                | 2025.0      | 0.0                 | 6075.0      | 7ABB600D-1E77-41BE-9FE5-B9142CFC08FA | 2011-05-31 00:00:00.0 |
| 43659          | 3                    | 4911-403C-98            | 1          | 778         | 1                | 2025.0      | 0.0                 | 2025.0      | 475CF8C6-49F6-486E-B0AD-AFC6A50CDD2F | 2011-05-31 00:00:00.0 |
| 43659          | 4                    | 4911-403C-98            | 1          | 771         | 1                | 2040.0      | 0.0                 | 2040.0      | 04C4DE91-5815-45D6-8670-F462719FBCE3 | 2011-05-31 00:00:00.0 |
| 43659          | 5                    | 4911-403C-98            | 1          | 772         | 1                | 2040.0      | 0.0                 | 2040.0      | 5A74C7D2-E641-438E-A7AC-37BF23280301 | 2011-05-31 00:00:00.0 |
| ...            | ...                  | ...                     | ...        | ...         | ...              | ...         | ...                 | ...         | ...                                  | ...                   |
*/
CREATE TABLE SalesOrderDetail (
    "SalesOrderID" INTEGER NOT NULL,
        -- <example>43659</example>
        -- <fk> -> SalesOrderHeader."SalesOrderID"</fk>
    "SalesOrderDetailID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>54351</example>
    "CarrierTrackingNumber" TEXT NULL,
        -- <example>'4911-403C-98'</example>
    "OrderQty" INTEGER NOT NULL,
        -- <example>1</example>
    "ProductID" INTEGER NOT NULL,
        -- <example>776</example>
        -- <fk>composite</fk>
    "SpecialOfferID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk>composite</fk>
    "UnitPrice" REAL NOT NULL,
        -- <example>2025.000</example>
    "UnitPriceDiscount" REAL NOT NULL,
        -- <example>0.000</example>
    "LineTotal" REAL NOT NULL,
        -- <example>2025.000</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'0000C99C-2B71-4885-B976-C1CCAE896EF2'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    FOREIGN KEY ("SalesOrderID") REFERENCES SalesOrderHeader("SalesOrderID"),
    FOREIGN KEY ("SpecialOfferID", "ProductID") REFERENCES SpecialOfferProduct("SpecialOfferID", "ProductID")
);

/*
Schema: NULL
Table: SalesOrderHeader
Rows: 31465
Sample rows:
| SalesOrderID   | RevisionNumber   | OrderDate             | DueDate               | ShipDate              | Status   | OnlineOrderFlag   | SalesOrderNumber   | PurchaseOrderNumber   | AccountNumber   | CustomerID   | SalesPersonID   | TerritoryID   | BillToAddressID   | ShipToAddressID   | ShipMethodID   | CreditCardID   | CreditCardApprovalCode   | CurrencyRateID   | SubTotal   | TaxAmt    | Freight   | TotalDue   | Comment   | rowguid                              | ModifiedDate          |
|----------------|------------------|-----------------------|-----------------------|-----------------------|----------|-------------------|--------------------|-----------------------|-----------------|--------------|-----------------|---------------|-------------------|-------------------|----------------|----------------|--------------------------|------------------|------------|-----------|-----------|------------|-----------|--------------------------------------|-----------------------|
| 43659          | 8                | 2011-05-31 00:00:00.0 | 2011-06-12 00:00:00.0 | 2011-06-07 00:00:00.0 | 5        | 0                 | SO43659            | PO522145787           | 10-4020-000676  | 29825        | 279             | 5             | 985               | 985               | 5              | 16281          | 105041Vi84182            | [NULL]           | 20565.6206 | 1971.5149 | 616.0984  | 23153.2339 | [NULL]    | 79B65321-39CA-4115-9CBA-8FE0903E12E6 | 2011-06-07 00:00:00.0 |
| 43660          | 8                | 2011-05-31 00:00:00.0 | 2011-06-12 00:00:00.0 | 2011-06-07 00:00:00.0 | 5        | 0                 | SO43660            | PO18850127500         | 10-4020-000117  | 29672        | 279             | 5             | 921               | 921               | 5              | 5618           | 115213Vi29411            | [NULL]           | 1294.2529  | 124.2483  | 38.8276   | 1457.3288  | [NULL]    | 738DC42D-D03B-48A1-9822-F95A67EA7389 | 2011-06-07 00:00:00.0 |
| 43661          | 8                | 2011-05-31 00:00:00.0 | 2011-06-12 00:00:00.0 | 2011-06-07 00:00:00.0 | 5        | 0                 | SO43661            | PO18473189620         | 10-4020-000442  | 29734        | 282             | 6             | 517               | 517               | 5              | 1346           | 85274Vi6854              | 4.0              | 32726.4786 | 3153.7696 | 985.553   | 36865.8012 | [NULL]    | D91B9131-18A4-4A11-BC3A-90B6F53E9D74 | 2011-06-07 00:00:00.0 |
| 43662          | 8                | 2011-05-31 00:00:00.0 | 2011-06-12 00:00:00.0 | 2011-06-07 00:00:00.0 | 5        | 0                 | SO43662            | PO18444174044         | 10-4020-000227  | 29994        | 282             | 6             | 482               | 482               | 5              | 10456          | 125295Vi53935            | 4.0              | 28832.5289 | 2775.1646 | 867.2389  | 32474.9324 | [NULL]    | 4A1ECFC0-CC3A-4740-B028-1C50BB48711C | 2011-06-07 00:00:00.0 |
| 43663          | 8                | 2011-05-31 00:00:00.0 | 2011-06-12 00:00:00.0 | 2011-06-07 00:00:00.0 | 5        | 0                 | SO43663            | PO18009186470         | 10-4020-000510  | 29565        | 276             | 4             | 1073              | 1073              | 5              | 4322           | 45303Vi22691             | [NULL]           | 419.4589   | 40.2681   | 12.5838   | 472.3108   | [NULL]    | 9B1E7A40-6AE0-4AD3-811C-A64951857C4B | 2011-06-07 00:00:00.0 |
| ...            | ...              | ...                   | ...                   | ...                   | ...      | ...               | ...                | ...                   | ...             | ...          | ...             | ...           | ...               | ...               | ...            | ...            | ...                      | ...              | ...        | ...       | ...       | ...        | ...       | ...                                  | ...                   |
*/
CREATE TABLE SalesOrderHeader (
    "SalesOrderID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>71821</example>
    "RevisionNumber" INTEGER NOT NULL,
        -- <example>8</example>
    "OrderDate" DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    "DueDate" DATETIME NOT NULL,
        -- <example>'2011-06-12 00:00:00.0'</example>
    "ShipDate" DATETIME NOT NULL,
        -- <example>'2011-06-07 00:00:00.0'</example>
    "Status" INTEGER NOT NULL,
        -- <example>5</example>
    "OnlineOrderFlag" INTEGER NOT NULL,
        -- <example>0</example>
    "SalesOrderNumber" TEXT NOT NULL,
        -- <example>'SO43659'</example>
    "PurchaseOrderNumber" TEXT NULL,
        -- <example>'PO522145787'</example>
    "AccountNumber" TEXT NOT NULL,
        -- <example>'10-4020-000676'</example>
    "CustomerID" INTEGER NOT NULL,
        -- <example>29825</example>
        -- <fk> -> Customer."CustomerID"</fk>
    "SalesPersonID" INTEGER NULL,
        -- <example>279</example>
        -- <fk> -> SalesPerson."BusinessEntityID"</fk>
    "TerritoryID" INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> SalesTerritory."TerritoryID"</fk>
    "BillToAddressID" INTEGER NOT NULL,
        -- <example>985</example>
        -- <fk> -> Address."AddressID"</fk>
    "ShipToAddressID" INTEGER NOT NULL,
        -- <example>985</example>
        -- <fk> -> Address."AddressID"</fk>
    "ShipMethodID" INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> Address."AddressID"</fk>
    "CreditCardID" INTEGER NULL,
        -- <example>16281</example>
        -- <fk> -> CreditCard."CreditCardID"</fk>
    "CreditCardApprovalCode" TEXT NULL,
        -- <example>'105041Vi84182'</example>
    "CurrencyRateID" INTEGER NULL,
        -- <example>4</example>
        -- <fk> -> CurrencyRate."CurrencyRateID"</fk>
    "SubTotal" REAL NOT NULL,
        -- <example>20565.621</example>
    "TaxAmt" REAL NOT NULL,
        -- <example>1971.515</example>
    "Freight" REAL NOT NULL,
        -- <example>616.098</example>
    "TotalDue" REAL NOT NULL,
        -- <example>23153.234</example>
    "Comment" TEXT NULL,
    "rowguid" TEXT NOT NULL,
        -- <example>'0000DE87-AB3F-4920-AC46-C404834241A0'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-06-07 00:00:00.0'</example>
    FOREIGN KEY ("CurrencyRateID") REFERENCES CurrencyRate("CurrencyRateID"),
    FOREIGN KEY ("CreditCardID") REFERENCES CreditCard("CreditCardID"),
    FOREIGN KEY ("ShipMethodID") REFERENCES Address("AddressID"),
    FOREIGN KEY ("ShipToAddressID") REFERENCES Address("AddressID"),
    FOREIGN KEY ("BillToAddressID") REFERENCES Address("AddressID"),
    FOREIGN KEY ("TerritoryID") REFERENCES SalesTerritory("TerritoryID"),
    FOREIGN KEY ("SalesPersonID") REFERENCES SalesPerson("BusinessEntityID"),
    FOREIGN KEY ("CustomerID") REFERENCES Customer("CustomerID")
);

/*
Schema: NULL
Table: SalesOrderHeaderSalesReason
Rows: 27647
Sample rows:
| SalesOrderID   | SalesReasonID   | ModifiedDate          |
|----------------|-----------------|-----------------------|
| 43697          | 5               | 2011-05-31 00:00:00.0 |
| 43697          | 9               | 2011-05-31 00:00:00.0 |
| 43702          | 5               | 2011-06-01 00:00:00.0 |
| 43702          | 9               | 2011-06-01 00:00:00.0 |
| 43703          | 5               | 2011-06-01 00:00:00.0 |
| ...            | ...             | ...                   |
*/
CREATE TABLE SalesOrderHeaderSalesReason (
    "SalesOrderID" INTEGER NOT NULL,
        -- <example>43697</example>
        -- <fk> -> SalesOrderHeader."SalesOrderID"</fk>
    "SalesReasonID" INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> SalesReason."SalesReasonID"</fk>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    PRIMARY KEY ("SalesOrderID", "SalesReasonID"),
    FOREIGN KEY ("SalesOrderID") REFERENCES SalesOrderHeader("SalesOrderID"),
    FOREIGN KEY ("SalesReasonID") REFERENCES SalesReason("SalesReasonID")
);

/*
Schema: NULL
Table: SalesPerson
Rows: 17
Sample rows:
| BusinessEntityID   | TerritoryID   | SalesQuota   | Bonus   | CommissionPct   | SalesYTD     | SalesLastYear   | rowguid                              | ModifiedDate          |
|--------------------|---------------|--------------|---------|-----------------|--------------|-----------------|--------------------------------------|-----------------------|
| 274                | [NULL]        | [NULL]       | 0.0     | 0.0             | 559697.5639  | 0.0             | 48754992-9EE0-4C0E-8C94-9451604E3E02 | 2010-12-28 00:00:00.0 |
| 275                | 2.0           | 300000.0     | 4100.0  | 0.012           | 3763178.1787 | 1750406.4785    | 1E0A7274-3064-4F58-88EE-4C6586C87169 | 2011-05-24 00:00:00.0 |
| 276                | 4.0           | 250000.0     | 2000.0  | 0.015           | 4251368.5497 | 1439156.0291    | 4DD9EEE4-8E81-4F8C-AF97-683394C1F7C0 | 2011-05-24 00:00:00.0 |
| 277                | 3.0           | 250000.0     | 2500.0  | 0.015           | 3189418.3662 | 1997186.2037    | 39012928-BFEC-4242-874D-423162C3F567 | 2011-05-24 00:00:00.0 |
| 278                | 6.0           | 250000.0     | 500.0   | 0.01            | 1453719.4653 | 1620276.8966    | 7A0AE1AB-B283-40F9-91D1-167ABF06D720 | 2011-05-24 00:00:00.0 |
| ...                | ...           | ...          | ...     | ...             | ...          | ...             | ...                                  | ...                   |
*/
CREATE TABLE SalesPerson (
    "BusinessEntityID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>287</example>
        -- <fk> -> Employee."BusinessEntityID"</fk>
    "TerritoryID" INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> SalesTerritory."TerritoryID"</fk>
    "SalesQuota" REAL NULL,
        -- <example>300000.000</example>
    "Bonus" REAL NOT NULL,
        -- <example>0.000</example>
    "CommissionPct" REAL NOT NULL,
        -- <example>0.000</example>
    "SalesYTD" REAL NOT NULL,
        -- <example>559697.564</example>
    "SalesLastYear" REAL NOT NULL,
        -- <example>0.000</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'1DD1F689-DF74-4149-8600-59555EEF154B'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2010-12-28 00:00:00.0'</example>
    FOREIGN KEY ("BusinessEntityID") REFERENCES Employee("BusinessEntityID"),
    FOREIGN KEY ("TerritoryID") REFERENCES SalesTerritory("TerritoryID")
);

/*
Schema: NULL
Table: SalesPersonQuotaHistory
Rows: 163
Sample rows:
| BusinessEntityID   | QuotaDate             | SalesQuota   | rowguid                              | ModifiedDate          |
|--------------------|-----------------------|--------------|--------------------------------------|-----------------------|
| 274                | 2011-05-31 00:00:00.0 | 28000.0      | 99109BBF-8693-4587-BC23-6036EC89E1BE | 2011-04-16 00:00:00.0 |
| 274                | 2011-08-31 00:00:00.0 | 7000.0       | DFD01444-8900-461C-8D6F-04598DAE01D4 | 2011-07-17 00:00:00.0 |
| 274                | 2011-12-01 00:00:00.0 | 91000.0      | 0A69F453-9689-4CCF-A08C-C644670F5668 | 2011-10-17 00:00:00.0 |
| 274                | 2012-02-29 00:00:00.0 | 140000.0     | DA8D1458-5FB9-4C3E-9EAD-8F5CE1393047 | 2012-01-15 00:00:00.0 |
| 274                | 2012-05-30 00:00:00.0 | 70000.0      | 760CEF84-B980-417B-A667-7358C38857F0 | 2012-04-15 00:00:00.0 |
| ...                | ...                   | ...          | ...                                  | ...                   |
*/
CREATE TABLE SalesPersonQuotaHistory (
    "BusinessEntityID" INTEGER NOT NULL,
        -- <example>274</example>
        -- <fk> -> SalesPerson."BusinessEntityID"</fk>
    "QuotaDate" DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    "SalesQuota" REAL NOT NULL,
        -- <example>28000.000</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'00F2F9F8-5158-4436-B134-7E0C462289E5'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-04-16 00:00:00.0'</example>
    PRIMARY KEY ("BusinessEntityID", "QuotaDate"),
    FOREIGN KEY ("BusinessEntityID") REFERENCES SalesPerson("BusinessEntityID")
);

/*
Schema: NULL
Table: SalesReason
Rows: 10
All rows:
|   SalesReasonID | Name                      | ReasonType   | ModifiedDate          |
|-----------------|---------------------------|--------------|-----------------------|
|               1 | Price                     | Other        | 2008-04-30 00:00:00.0 |
|               2 | On Promotion              | Promotion    | 2008-04-30 00:00:00.0 |
|               3 | Magazine Advertisement    | Marketing    | 2008-04-30 00:00:00.0 |
|               4 | Television  Advertisement | Marketing    | 2008-04-30 00:00:00.0 |
|               5 | Manufacturer              | Other        | 2008-04-30 00:00:00.0 |
|               6 | Review                    | Other        | 2008-04-30 00:00:00.0 |
|               7 | Demo Event                | Marketing    | 2008-04-30 00:00:00.0 |
|               8 | Sponsorship               | Marketing    | 2008-04-30 00:00:00.0 |
|               9 | Quality                   | Other        | 2008-04-30 00:00:00.0 |
|              10 | Other                     | Other        | 2008-04-30 00:00:00.0 |
*/
CREATE TABLE SalesReason (
    "SalesReasonID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Name" TEXT NOT NULL,
        -- <values>{'Demo Event', 'Magazine Advertisement', 'Manufacturer', 'On Promotion', 'Other', 'Price', 'Quality', 'Review', 'Sponsorship', 'Television  Advertisement'}</values>
    "ReasonType" TEXT NOT NULL,
        -- <values>{'Marketing', 'Other', 'Promotion'}</values>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: SalesTaxRate
Rows: 29
Sample rows:
| SalesTaxRateID   | StateProvinceID   | TaxType   | TaxRate   | Name                                  | rowguid                              | ModifiedDate          |
|------------------|-------------------|-----------|-----------|---------------------------------------|--------------------------------------|-----------------------|
| 1                | 1                 | 1         | 14.0      | Canadian GST + Alberta Provincial Tax | 683DE5DD-521A-47D4-A573-06A3CDB1BC5D | 2008-04-30 00:00:00.0 |
| 2                | 57                | 1         | 14.25     | Canadian GST + Ontario Provincial Tax | 05C4FFDB-4F84-4CDF-ABE5-FDF3216EA74E | 2008-04-30 00:00:00.0 |
| 3                | 63                | 1         | 14.25     | Canadian GST + Quebec Provincial Tax  | D4EDB557-56D7-403C-B538-4DF5E7302588 | 2008-04-30 00:00:00.0 |
| 4                | 1                 | 2         | 7.0       | Canadian GST                          | F0D76907-B433-453F-B95E-16FCE73B807A | 2008-04-30 00:00:00.0 |
| 5                | 57                | 2         | 7.0       | Canadian GST                          | 7E0E97A2-878B-476F-A648-05A3DD4450ED | 2008-04-30 00:00:00.0 |
| ...              | ...               | ...       | ...       | ...                                   | ...                                  | ...                   |
*/
CREATE TABLE SalesTaxRate (
    "SalesTaxRateID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "StateProvinceID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> StateProvince."StateProvinceID"</fk>
    "TaxType" INTEGER NOT NULL,
        -- <example>1</example>
    "TaxRate" REAL NOT NULL,
        -- <example>14.000</example>
    "Name" TEXT NOT NULL,
        -- <example>'Canadian GST + Alberta Provincial Tax'</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'05C4FFDB-4F84-4CDF-ABE5-FDF3216EA74E'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2008-04-30 00:00:00.0'</example>
    FOREIGN KEY ("StateProvinceID") REFERENCES StateProvince("StateProvinceID")
);

/*
Schema: NULL
Table: SalesTerritory
Rows: 10
All rows:
|   TerritoryID | Name           | CountryRegionCode   | Group         |   SalesYTD |   SalesLastYear |   CostYTD |   CostLastYear | rowguid                              | ModifiedDate          |
|---------------|----------------|---------------------|---------------|------------|-----------------|-----------|----------------|--------------------------------------|-----------------------|
|             1 | Northwest      | US                  | North America |  7887186.8 |       3298694.5 |         0 |              0 | 43689A10-E30B-497F-B0DE-11DE20267FF7 | 2008-04-30 00:00:00.0 |
|             2 | Northeast      | US                  | North America |  2402176.8 |       3607148.9 |         0 |              0 | 00FB7309-96CC-49E2-8363-0A1BA72486F2 | 2008-04-30 00:00:00.0 |
|             3 | Central        | US                  | North America |  3072175.1 |       3205014.1 |         0 |              0 | DF6E7FD8-1A8D-468C-B103-ED8ADDB452C1 | 2008-04-30 00:00:00.0 |
|             4 | Southwest      | US                  | North America | 10510854   |       5366575.7 |         0 |              0 | DC3E9EA0-7950-4431-9428-99DBCBC33865 | 2008-04-30 00:00:00.0 |
|             5 | Southeast      | US                  | North America |  2538667.3 |       3925071.4 |         0 |              0 | 6DC4165A-5E4C-42D2-809D-4344E0AC75E7 | 2008-04-30 00:00:00.0 |
|             6 | Canada         | CA                  | North America |  6771829.1 |       5693988.9 |         0 |              0 | 06B4AF8A-1639-476E-9266-110461D66B00 | 2008-04-30 00:00:00.0 |
|             7 | France         | FR                  | Europe        |  4772398.3 |       2396539.8 |         0 |              0 | BF806804-9B4C-4B07-9D19-706F2E689552 | 2008-04-30 00:00:00.0 |
|             8 | Germany        | DE                  | Europe        |  3805202.3 |       1307949.8 |         0 |              0 | 6D2450DB-8159-414F-A917-E73EE91C38A9 | 2008-04-30 00:00:00.0 |
|             9 | Australia      | AU                  | Pacific       |  5977814.9 |       2278549   |         0 |              0 | 602E612E-DFE9-41D9-B894-27E489747885 | 2008-04-30 00:00:00.0 |
|            10 | United Kingdom | GB                  | Europe        |  5012905.4 |       1635823.4 |         0 |              0 | 05FC7E1F-2DEA-414E-9ECD-09D150516FB5 | 2008-04-30 00:00:00.0 |
*/
CREATE TABLE SalesTerritory (
    "TerritoryID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>2</example>
    "Name" TEXT NOT NULL,
        -- <values>{'Australia', 'Canada', 'Central', 'France', 'Germany', 'Northeast', 'Northwest', 'Southeast', 'Southwest', 'United Kingdom'}</values>
    "CountryRegionCode" TEXT NOT NULL,
        -- <values>{'AU', 'CA', 'DE', 'FR', 'GB', 'US'}</values>
        -- <fk> -> CountryRegion."CountryRegionCode"</fk>
    "Group" TEXT NOT NULL,
        -- <values>{'Europe', 'North America', 'Pacific'}</values>
    "SalesYTD" REAL NOT NULL,
        -- <example>7887186.788</example>
    "SalesLastYear" REAL NOT NULL,
        -- <example>3298694.494</example>
    "CostYTD" REAL NOT NULL,
        -- <example>0.000</example>
    "CostLastYear" REAL NOT NULL,
        -- <example>0.000</example>
    "rowguid" TEXT NOT NULL,
        -- <values>{'00FB7309-96CC-49E2-8363-0A1BA72486F2', '05FC7E1F-2DEA-414E-9ECD-09D150516FB5', '06B4AF8A-1639-476E-9266-110461D66B00', '43689A10-E30B-497F-B0DE-11DE20267FF7', '602E612E-DFE9-41D9-B894-27E489747885', '6D2450DB-8159-414F-A917-E73EE91C38A9', '6DC4165A-5E4C-42D2-809D-4344E0AC75E7', 'BF806804-9B4C-4B07-9D19-706F2E689552', 'DC3E9EA0-7950-4431-9428-99DBCBC33865', 'DF6E7FD8-1A8D-468C-B103-ED8ADDB452C1'}</values>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2008-04-30 00:00:00.0'</example>
    FOREIGN KEY ("CountryRegionCode") REFERENCES CountryRegion("CountryRegionCode")
);

/*
Schema: NULL
Table: SalesTerritoryHistory
Rows: 17
Sample rows:
| BusinessEntityID   | TerritoryID   | StartDate             | EndDate               | rowguid                              | ModifiedDate          |
|--------------------|---------------|-----------------------|-----------------------|--------------------------------------|-----------------------|
| 275                | 2             | 2011-05-31 00:00:00.0 | 2012-11-29 00:00:00.0 | 8563CE6A-00FF-47D7-BA4D-3C3E1CDEF531 | 2012-11-22 00:00:00.0 |
| 275                | 3             | 2012-11-30 00:00:00.0 | [NULL]                | 2F44304C-EE87-4C72-813E-CA75C5F61F4C | 2012-11-23 00:00:00.0 |
| 276                | 4             | 2011-05-31 00:00:00.0 | [NULL]                | 64BCB1B3-A793-40BA-9859-D90F78C3F167 | 2011-05-24 00:00:00.0 |
| 277                | 3             | 2011-05-31 00:00:00.0 | 2012-11-29 00:00:00.0 | 3E9F893D-5142-46C9-A76A-867D1E3D6F90 | 2012-11-22 00:00:00.0 |
| 277                | 2             | 2012-11-30 00:00:00.0 | [NULL]                | 132E4721-32DD-4A73-B556-1837F3A2B9AE | 2012-11-23 00:00:00.0 |
| ...                | ...           | ...                   | ...                   | ...                                  | ...                   |
*/
CREATE TABLE SalesTerritoryHistory (
    "BusinessEntityID" INTEGER NOT NULL,
        -- <example>275</example>
        -- <fk> -> SalesPerson."BusinessEntityID"</fk>
    "TerritoryID" INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> SalesTerritory."TerritoryID"</fk>
    "StartDate" DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    "EndDate" DATETIME NULL,
        -- <example>'2012-11-29 00:00:00.0'</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'009F7660-44A6-4ADF-BD4B-A5D1B79993F5'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2012-11-22 00:00:00.0'</example>
    PRIMARY KEY ("BusinessEntityID", "TerritoryID", "StartDate"),
    FOREIGN KEY ("BusinessEntityID") REFERENCES SalesPerson("BusinessEntityID"),
    FOREIGN KEY ("TerritoryID") REFERENCES SalesTerritory("TerritoryID")
);

/*
Schema: NULL
Table: ScrapReason
Rows: 16
Sample rows:
| ScrapReasonID   | Name                          | ModifiedDate          |
|-----------------|-------------------------------|-----------------------|
| 1               | Brake assembly not as ordered | 2008-04-30 00:00:00.0 |
| 2               | Color incorrect               | 2008-04-30 00:00:00.0 |
| 3               | Gouge in metal                | 2008-04-30 00:00:00.0 |
| 4               | Drill pattern incorrect       | 2008-04-30 00:00:00.0 |
| 5               | Drill size too large          | 2008-04-30 00:00:00.0 |
| ...             | ...                           | ...                   |
*/
CREATE TABLE ScrapReason (
    "ScrapReasonID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Name" TEXT NOT NULL,
        -- <example>'Brake assembly not as ordered'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: Shift
Rows: 3
All rows:
|   ShiftID | Name    | StartTime   | EndTime   | ModifiedDate          |
|-----------|---------|-------------|-----------|-----------------------|
|         1 | Day     | 07:00:00    | 15:00:00  | 2008-04-30 00:00:00.0 |
|         2 | Evening | 15:00:00    | 23:00:00  | 2008-04-30 00:00:00.0 |
|         3 | Night   | 23:00:00    | 07:00:00  | 2008-04-30 00:00:00.0 |
*/
CREATE TABLE Shift (
    "ShiftID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Name" TEXT NOT NULL,
        -- <values>{'Day', 'Evening', 'Night'}</values>
    "StartTime" TEXT NOT NULL,
        -- <values>{'07:00:00', '15:00:00', '23:00:00'}</values>
    "EndTime" TEXT NOT NULL,
        -- <values>{'07:00:00', '15:00:00', '23:00:00'}</values>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: ShipMethod
Rows: 5
All rows:
|   ShipMethodID | Name               |   ShipBase |   ShipRate | rowguid                              | ModifiedDate          |
|----------------|--------------------|------------|------------|--------------------------------------|-----------------------|
|              1 | XRQ - TRUCK GROUND |       3.95 |       0.99 | 6BE756D9-D7BE-4463-8F2C-AE60C710D606 | 2008-04-30 00:00:00.0 |
|              2 | ZY - EXPRESS       |       9.95 |       1.99 | 3455079B-F773-4DC6-8F1E-2A58649C4AB8 | 2008-04-30 00:00:00.0 |
|              3 | OVERSEAS - DELUXE  |      29.95 |       2.99 | 22F4E461-28CF-4ACE-A980-F686CF112EC8 | 2008-04-30 00:00:00.0 |
|              4 | OVERNIGHT J-FAST   |      21.95 |       1.29 | 107E8356-E7A8-463D-B60C-079FFF467F3F | 2008-04-30 00:00:00.0 |
|              5 | CARGO TRANSPORT 5  |       8.99 |       1.49 | B166019A-B134-4E76-B957-2B0490C610ED | 2008-04-30 00:00:00.0 |
*/
CREATE TABLE ShipMethod (
    "ShipMethodID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>4</example>
    "Name" TEXT NOT NULL,
        -- <values>{'CARGO TRANSPORT 5', 'OVERNIGHT J-FAST', 'OVERSEAS - DELUXE', 'XRQ - TRUCK GROUND', 'ZY - EXPRESS'}</values>
    "ShipBase" REAL NOT NULL,
        -- <example>3.950</example>
    "ShipRate" REAL NOT NULL,
        -- <example>0.990</example>
    "rowguid" TEXT NOT NULL,
        -- <values>{'107E8356-E7A8-463D-B60C-079FFF467F3F', '22F4E461-28CF-4ACE-A980-F686CF112EC8', '3455079B-F773-4DC6-8F1E-2A58649C4AB8', '6BE756D9-D7BE-4463-8F2C-AE60C710D606', 'B166019A-B134-4E76-B957-2B0490C610ED'}</values>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: ShoppingCartItem
Rows: 3
All rows:
|   ShoppingCartItemID |   ShoppingCartID |   Quantity |   ProductID | DateCreated           | ModifiedDate          |
|----------------------|------------------|------------|-------------|-----------------------|-----------------------|
|                    2 |            14951 |          3 |         862 | 2013-11-09 17:54:07.0 | 2013-11-09 17:54:07.0 |
|                    4 |            20621 |          4 |         881 | 2013-11-09 17:54:07.0 | 2013-11-09 17:54:07.0 |
|                    5 |            20621 |          7 |         874 | 2013-11-09 17:54:07.0 | 2013-11-09 17:54:07.0 |
*/
CREATE TABLE ShoppingCartItem (
    "ShoppingCartItemID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>2</example>
    "ShoppingCartID" TEXT NOT NULL,
        -- <values>{'14951', '20621'}</values>
    "Quantity" INTEGER NOT NULL,
        -- <example>3</example>
    "ProductID" INTEGER NOT NULL,
        -- <example>862</example>
        -- <fk> -> Product."ProductID"</fk>
    "DateCreated" DATETIME NOT NULL,
        -- <example>'2013-11-09 17:54:07.0'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2013-11-09 17:54:07.0'</example>
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID")
);

/*
Schema: NULL
Table: SpecialOffer
Rows: 16
Sample rows:
| SpecialOfferID   | Description              | DiscountPct   | Type            | Category    | StartDate             | EndDate               | MinQty   | MaxQty   | rowguid                              | ModifiedDate          |
|------------------|--------------------------|---------------|-----------------|-------------|-----------------------|-----------------------|----------|----------|--------------------------------------|-----------------------|
| 1                | No Discount              | 0.0           | No Discount     | No Discount | 2011-05-01 00:00:00.0 | 2014-11-30 00:00:00.0 | 0        | [NULL]   | 0290C4F5-191F-4337-AB6B-0A2DDE03CBF9 | 2011-04-01 00:00:00.0 |
| 2                | Volume Discount 11 to 14 | 0.0           | Volume Discount | Reseller    | 2011-05-31 00:00:00.0 | 2014-05-30 00:00:00.0 | 11       | 14.0     | D7542EE7-15DB-4541-985C-5CC27AEF26D6 | 2011-05-01 00:00:00.0 |
| 3                | Volume Discount 15 to 24 | 0.0           | Volume Discount | Reseller    | 2011-05-31 00:00:00.0 | 2014-05-30 00:00:00.0 | 15       | 24.0     | 4BDBCC01-8CF7-40A9-B643-40EC5B717491 | 2011-05-01 00:00:00.0 |
| 4                | Volume Discount 25 to 40 | 0.0           | Volume Discount | Reseller    | 2011-05-31 00:00:00.0 | 2014-05-30 00:00:00.0 | 25       | 40.0     | 504B5E85-8F3F-4EBC-9E1D-C1BC5DEA9AA8 | 2011-05-01 00:00:00.0 |
| 5                | Volume Discount 41 to 60 | 0.0           | Volume Discount | Reseller    | 2011-05-31 00:00:00.0 | 2014-05-30 00:00:00.0 | 41       | 60.0     | 677E1D9D-944F-4E81-90E8-47EB0A82D48C | 2011-05-01 00:00:00.0 |
| ...              | ...                      | ...           | ...             | ...         | ...                   | ...                   | ...      | ...      | ...                                  | ...                   |
*/
CREATE TABLE SpecialOffer (
    "SpecialOfferID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Description" TEXT NOT NULL,
        -- <example>'No Discount'</example>
    "DiscountPct" REAL NOT NULL,
        -- <example>0.000</example>
    "Type" TEXT NOT NULL,
        -- <values>{'Discontinued Product', 'Excess Inventory', 'New Product', 'No Discount', 'Seasonal Discount', 'Volume Discount'}</values>
    "Category" TEXT NOT NULL,
        -- <values>{'Customer', 'No Discount', 'Reseller'}</values>
    "StartDate" DATETIME NOT NULL,
        -- <example>'2011-05-01 00:00:00.0'</example>
    "EndDate" DATETIME NOT NULL,
        -- <example>'2014-11-30 00:00:00.0'</example>
    "MinQty" INTEGER NOT NULL,
        -- <example>0</example>
    "MaxQty" INTEGER NULL,
        -- <example>14</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'0290C4F5-191F-4337-AB6B-0A2DDE03CBF9'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2011-04-01 00:00:00.0'</example>
);

/*
Schema: NULL
Table: SpecialOfferProduct
Rows: 538
Sample rows:
| SpecialOfferID   | ProductID   | rowguid                              | ModifiedDate          |
|------------------|-------------|--------------------------------------|-----------------------|
| 1                | 680         | BB30B868-D86C-4557-8DB2-4B2D0A83A0FB | 2011-04-01 00:00:00.0 |
| 1                | 706         | B3C9A4B1-2AE6-4CBA-B552-1F206C9F4C1F | 2011-04-01 00:00:00.0 |
| 1                | 707         | 27B711FE-0B77-4EA4-AD1A-7C239956BEF4 | 2011-04-01 00:00:00.0 |
| 1                | 708         | 46CBB78B-246E-4D69-9BD6-E521277C1078 | 2011-04-01 00:00:00.0 |
| 1                | 709         | CF102AA0-055F-4D2B-8B98-04B161758EA8 | 2011-04-01 00:00:00.0 |
| ...              | ...         | ...                                  | ...                   |
*/
CREATE TABLE SpecialOfferProduct (
    "SpecialOfferID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> SpecialOffer."SpecialOfferID"</fk>
    "ProductID" INTEGER NOT NULL,
        -- <example>680</example>
        -- <fk> -> Product."ProductID"</fk>
    "rowguid" TEXT NOT NULL,
        -- <example>'0020931C-087C-42F8-B441-EBE3D3B5F51E'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-04-01 00:00:00.0'</example>
    PRIMARY KEY ("SpecialOfferID", "ProductID"),
    FOREIGN KEY ("SpecialOfferID") REFERENCES SpecialOffer("SpecialOfferID"),
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID")
);

/*
Schema: NULL
Table: StateProvince
Rows: 181
Sample rows:
| StateProvinceID   | StateProvinceCode   | CountryRegionCode   | IsOnlyStateProvinceFlag   | Name           | TerritoryID   | rowguid                              | ModifiedDate          |
|-------------------|---------------------|---------------------|---------------------------|----------------|---------------|--------------------------------------|-----------------------|
| 1                 | AB                  | CA                  | 0                         | Alberta        | 6             | 298C2880-AB1C-4982-A5AD-A36EB4BA0D34 | 2014-02-08 10:17:21.0 |
| 2                 | AK                  | US                  | 0                         | Alaska         | 1             | 5B7B8462-A888-4E0B-A3E1-7278F8AF107E | 2014-02-08 10:17:21.0 |
| 3                 | AL                  | US                  | 0                         | Alabama        | 5             | 41B328BE-21AE-45D0-841D-6F8DD71CE626 | 2014-02-08 10:17:21.0 |
| 4                 | AR                  | US                  | 0                         | Arkansas       | 3             | 54656A80-06F2-4C70-BA10-247179FC246E | 2014-02-08 10:17:21.0 |
| 5                 | AS                  | AS                  | 1                         | American Samoa | 1             | 255D15E1-9F6E-4CF8-9E5F-6B3858AD9B6A | 2014-02-08 10:17:21.0 |
| ...               | ...                 | ...                 | ...                       | ...            | ...           | ...                                  | ...                   |
*/
CREATE TABLE StateProvince (
    "StateProvinceID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>103</example>
    "StateProvinceCode" TEXT NOT NULL,
        -- <example>'01'</example>
    "CountryRegionCode" TEXT NOT NULL,
        -- <example>'FR'</example>
        -- <fk> -> CountryRegion."CountryRegionCode"</fk>
    "IsOnlyStateProvinceFlag" INTEGER NOT NULL,
        -- <example>0</example>
    "Name" TEXT NOT NULL,
        -- <example>'Ain'</example>
    "TerritoryID" INTEGER NOT NULL,
        -- <example>6</example>
        -- <fk> -> SalesTerritory."TerritoryID"</fk>
    "rowguid" TEXT NOT NULL,
        -- <example>'00723E00-C976-401D-A92B-E582DF3D6E01'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2014-02-08 10:17:21.0'</example>
    FOREIGN KEY ("TerritoryID") REFERENCES SalesTerritory("TerritoryID"),
    FOREIGN KEY ("CountryRegionCode") REFERENCES CountryRegion("CountryRegionCode")
);

/*
Schema: NULL
Table: Store
Rows: 701
Sample rows:
| BusinessEntityID   | Name                           | SalesPersonID   | Demographics                                                                                                                                                                                                | rowguid                              | ModifiedDate          |
|--------------------|--------------------------------|-----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|-----------------------|
| 292                | Next-Door Bike Store           | 279             | <StoreSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/StoreSurvey"><Ann...eFeet><Brands>2</Brands><Internet>ISDN</Internet><NumberEmployees>13</NumberEmployees></StoreSurvey> | A22517E3-848D-4EBE-B9D9-7437F3432304 | 2014-09-12 11:15:07.0 |
| 294                | Professional Sales and Service | 276             | <StoreSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/StoreSurvey"><Ann...reFeet><Brands>4+</Brands><Internet>T1</Internet><NumberEmployees>14</NumberEmployees></StoreSurvey> | B50CA50B-C601-4A13-B07E-2C63862D71B4 | 2014-09-12 11:15:07.0 |
| 296                | Riders Company                 | 277             | <StoreSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/StoreSurvey"><Ann...reFeet><Brands>2</Brands><Internet>DSL</Internet><NumberEmployees>15</NumberEmployees></StoreSurvey> | 337C3688-1339-4E1A-A08A-B54B23566E49 | 2014-09-12 11:15:07.0 |
| 298                | The Bike Mechanics             | 275             | <StoreSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/StoreSurvey"><Ann...reFeet><Brands>2</Brands><Internet>DSL</Internet><NumberEmployees>16</NumberEmployees></StoreSurvey> | 7894F278-F0C8-4D16-BD75-213FDBF13023 | 2014-09-12 11:15:07.0 |
| 300                | Nationwide Supply              | 286             | <StoreSurvey xmlns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/StoreSurvey"><Ann...eFeet><Brands>4+</Brands><Internet>DSL</Internet><NumberEmployees>17</NumberEmployees></StoreSurvey> | C3FC9705-A8C4-4F3A-9550-EB2FA4B7B64D | 2014-09-12 11:15:07.0 |
| ...                | ...                            | ...             | ...                                                                                                                                                                                                         | ...                                  | ...                   |
*/
CREATE TABLE Store (
    "BusinessEntityID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>630</example>
        -- <fk> -> BusinessEntity."BusinessEntityID"</fk>
    "Name" TEXT NOT NULL,
        -- <example>'Next-Door Bike Store'</example>
    "SalesPersonID" INTEGER NOT NULL,
        -- <example>279</example>
        -- <fk> -> SalesPerson."BusinessEntityID"</fk>
    "Demographics" TEXT NOT NULL,
        -- <example>'<StoreSurvey xmlns="http://schemas.microsoft.com/s...NumberEmployees>13</NumberEmployees></StoreSurvey>'</example>
    "rowguid" TEXT NOT NULL,
        -- <example>'004EA91C-FCD4-4973-87EF-9059C6E20BB5'</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2014-09-12 11:15:07.0'</example>
    FOREIGN KEY ("BusinessEntityID") REFERENCES BusinessEntity("BusinessEntityID"),
    FOREIGN KEY ("SalesPersonID") REFERENCES SalesPerson("BusinessEntityID")
);

/*
Schema: NULL
Table: TransactionHistory
Rows: 113443
Sample rows:
| TransactionID   | ProductID   | ReferenceOrderID   | ReferenceOrderLineID   | TransactionDate       | TransactionType   | Quantity   | ActualCost   | ModifiedDate          |
|-----------------|-------------|--------------------|------------------------|-----------------------|-------------------|------------|--------------|-----------------------|
| 100000          | 784         | 41590              | 0                      | 2013-07-31 00:00:00.0 | W                 | 2          | 0.0          | 2013-07-31 00:00:00.0 |
| 100001          | 794         | 41591              | 0                      | 2013-07-31 00:00:00.0 | W                 | 1          | 0.0          | 2013-07-31 00:00:00.0 |
| 100002          | 797         | 41592              | 0                      | 2013-07-31 00:00:00.0 | W                 | 1          | 0.0          | 2013-07-31 00:00:00.0 |
| 100003          | 798         | 41593              | 0                      | 2013-07-31 00:00:00.0 | W                 | 1          | 0.0          | 2013-07-31 00:00:00.0 |
| 100004          | 799         | 41594              | 0                      | 2013-07-31 00:00:00.0 | W                 | 1          | 0.0          | 2013-07-31 00:00:00.0 |
| ...             | ...         | ...                | ...                    | ...                   | ...               | ...        | ...          | ...                   |
*/
CREATE TABLE TransactionHistory (
    "TransactionID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>100000</example>
    "ProductID" INTEGER NOT NULL,
        -- <example>784</example>
        -- <fk> -> Product."ProductID"</fk>
    "ReferenceOrderID" INTEGER NOT NULL,
        -- <example>41590</example>
    "ReferenceOrderLineID" INTEGER NOT NULL,
        -- <example>0</example>
    "TransactionDate" DATETIME NOT NULL,
        -- <example>'2013-07-31 00:00:00.0'</example>
    "TransactionType" TEXT NOT NULL,
        -- <values>{'P', 'S', 'W'}</values>
    "Quantity" INTEGER NOT NULL,
        -- <example>2</example>
    "ActualCost" REAL NOT NULL,
        -- <example>0.000</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2013-07-31 00:00:00.0'</example>
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID")
);

/*
Schema: NULL
Table: TransactionHistoryArchive
Rows: 89253
Sample rows:
| TransactionID   | ProductID   | ReferenceOrderID   | ReferenceOrderLineID   | TransactionDate       | TransactionType   | Quantity   | ActualCost   | ModifiedDate          |
|-----------------|-------------|--------------------|------------------------|-----------------------|-------------------|------------|--------------|-----------------------|
| 1               | 1           | 1                  | 1                      | 2011-04-16 00:00:00.0 | P                 | 4          | 50.0         | 2011-04-16 00:00:00.0 |
| 2               | 359         | 2                  | 1                      | 2011-04-16 00:00:00.0 | P                 | 3          | 45.0         | 2011-04-16 00:00:00.0 |
| 3               | 360         | 2                  | 2                      | 2011-04-16 00:00:00.0 | P                 | 3          | 46.0         | 2011-04-16 00:00:00.0 |
| 4               | 530         | 3                  | 1                      | 2011-04-16 00:00:00.0 | P                 | 550        | 16.0         | 2011-04-16 00:00:00.0 |
| 5               | 4           | 4                  | 1                      | 2011-04-16 00:00:00.0 | P                 | 3          | 57.0         | 2011-04-16 00:00:00.0 |
| ...             | ...         | ...                | ...                    | ...                   | ...               | ...        | ...          | ...                   |
*/
CREATE TABLE TransactionHistoryArchive (
    "TransactionID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "ProductID" INTEGER NOT NULL,
        -- <example>1</example>
    "ReferenceOrderID" INTEGER NOT NULL,
        -- <example>1</example>
    "ReferenceOrderLineID" INTEGER NOT NULL,
        -- <example>1</example>
    "TransactionDate" DATETIME NOT NULL,
        -- <example>'2011-04-16 00:00:00.0'</example>
    "TransactionType" TEXT NOT NULL,
        -- <values>{'P', 'S', 'W'}</values>
    "Quantity" INTEGER NOT NULL,
        -- <example>4</example>
    "ActualCost" REAL NOT NULL,
        -- <example>50.000</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2011-04-16 00:00:00.0'</example>
);

/*
Schema: NULL
Table: UnitMeasure
Rows: 38
Sample rows:
| UnitMeasureCode   | Name     | ModifiedDate          |
|-------------------|----------|-----------------------|
| BOX               | Boxes    | 2008-04-30 00:00:00.0 |
| BTL               | Bottle   | 2008-04-30 00:00:00.0 |
| C                 | Celsius  | 2008-04-30 00:00:00.0 |
| CAN               | Canister | 2008-04-30 00:00:00.0 |
| CAR               | Carton   | 2008-04-30 00:00:00.0 |
| ...               | ...      | ...                   |
*/
CREATE TABLE UnitMeasure (
    "UnitMeasureCode" TEXT NOT NULL PRIMARY KEY,
        -- <example>'BOX'</example>
    "Name" TEXT NOT NULL,
        -- <example>'Bottle'</example>
    "ModifiedDate" DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

/*
Schema: NULL
Table: Vendor
Rows: 104
Sample rows:
| BusinessEntityID   | AccountNumber   | Name                    | CreditRating   | PreferredVendorStatus   | ActiveFlag   | PurchasingWebServiceURL   | ModifiedDate          |
|--------------------|-----------------|-------------------------|----------------|-------------------------|--------------|---------------------------|-----------------------|
| 1492               | AUSTRALI0001    | Australia Bike Retailer | 1              | 1                       | 1            | [NULL]                    | 2011-12-23 00:00:00.0 |
| 1494               | ALLENSON0001    | Allenson Cycles         | 2              | 1                       | 1            | [NULL]                    | 2011-04-25 00:00:00.0 |
| 1496               | ADVANCED0001    | Advanced Bicycles       | 1              | 1                       | 1            | [NULL]                    | 2011-04-25 00:00:00.0 |
| 1498               | TRIKES0001      | Trikes, Inc.            | 2              | 1                       | 1            | [NULL]                    | 2012-02-03 00:00:00.0 |
| 1500               | MORGANB0001     | Morgan Bike Accessories | 1              | 1                       | 1            | [NULL]                    | 2012-02-02 00:00:00.0 |
| ...                | ...             | ...                     | ...            | ...                     | ...          | ...                       | ...                   |
*/
CREATE TABLE Vendor (
    "BusinessEntityID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1596</example>
        -- <fk> -> BusinessEntity."BusinessEntityID"</fk>
    "AccountNumber" TEXT NOT NULL,
        -- <example>'ADATUM0001'</example>
    "Name" TEXT NOT NULL,
        -- <example>'Australia Bike Retailer'</example>
    "CreditRating" INTEGER NOT NULL,
        -- <example>1</example>
    "PreferredVendorStatus" INTEGER NOT NULL,
        -- <example>1</example>
    "ActiveFlag" INTEGER NOT NULL,
        -- <example>1</example>
    "PurchasingWebServiceURL" TEXT NULL,
        -- <values>{'www.adatum.com/', 'www.litwareinc.com/', 'www.northwindtraders.com/', 'www.proseware.com/', 'www.treyresearch.net/', 'www.wideworldimporters.com/'}</values>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-12-23 00:00:00.0'</example>
    FOREIGN KEY ("BusinessEntityID") REFERENCES BusinessEntity("BusinessEntityID")
);

/*
Schema: NULL
Table: WorkOrder
Rows: 72591
Sample rows:
| WorkOrderID   | ProductID   | OrderQty   | StockedQty   | ScrappedQty   | StartDate             | EndDate               | DueDate               | ScrapReasonID   | ModifiedDate          |
|---------------|-------------|------------|--------------|---------------|-----------------------|-----------------------|-----------------------|-----------------|-----------------------|
| 1             | 722         | 8          | 8            | 0             | 2011-06-03 00:00:00.0 | 2011-06-13 00:00:00.0 | 2011-06-14 00:00:00.0 | [NULL]          | 2011-06-13 00:00:00.0 |
| 2             | 725         | 15         | 15           | 0             | 2011-06-03 00:00:00.0 | 2011-06-13 00:00:00.0 | 2011-06-14 00:00:00.0 | [NULL]          | 2011-06-13 00:00:00.0 |
| 3             | 726         | 9          | 9            | 0             | 2011-06-03 00:00:00.0 | 2011-06-13 00:00:00.0 | 2011-06-14 00:00:00.0 | [NULL]          | 2011-06-13 00:00:00.0 |
| 4             | 729         | 16         | 16           | 0             | 2011-06-03 00:00:00.0 | 2011-06-13 00:00:00.0 | 2011-06-14 00:00:00.0 | [NULL]          | 2011-06-13 00:00:00.0 |
| 5             | 730         | 14         | 14           | 0             | 2011-06-03 00:00:00.0 | 2011-06-13 00:00:00.0 | 2011-06-14 00:00:00.0 | [NULL]          | 2011-06-13 00:00:00.0 |
| ...           | ...         | ...        | ...          | ...           | ...                   | ...                   | ...                   | ...             | ...                   |
*/
CREATE TABLE WorkOrder (
    "WorkOrderID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "ProductID" INTEGER NOT NULL,
        -- <example>722</example>
        -- <fk> -> Product."ProductID"</fk>
    "OrderQty" INTEGER NOT NULL,
        -- <example>8</example>
    "StockedQty" INTEGER NOT NULL,
        -- <example>8</example>
    "ScrappedQty" INTEGER NOT NULL,
        -- <example>0</example>
    "StartDate" DATETIME NOT NULL,
        -- <example>'2011-06-03 00:00:00.0'</example>
    "EndDate" DATETIME NOT NULL,
        -- <example>'2011-06-13 00:00:00.0'</example>
    "DueDate" DATETIME NOT NULL,
        -- <example>'2011-06-14 00:00:00.0'</example>
    "ScrapReasonID" INTEGER NULL,
        -- <example>7</example>
        -- <fk> -> ScrapReason."ScrapReasonID"</fk>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-06-13 00:00:00.0'</example>
    FOREIGN KEY ("ProductID") REFERENCES Product("ProductID"),
    FOREIGN KEY ("ScrapReasonID") REFERENCES ScrapReason("ScrapReasonID")
);

/*
Schema: NULL
Table: WorkOrderRouting
Rows: 67131
Sample rows:
| WorkOrderID   | ProductID   | OperationSequence   | LocationID   | ScheduledStartDate    | ScheduledEndDate      | ActualStartDate       | ActualEndDate         | ActualResourceHrs   | PlannedCost   | ActualCost   | ModifiedDate          |
|---------------|-------------|---------------------|--------------|-----------------------|-----------------------|-----------------------|-----------------------|---------------------|---------------|--------------|-----------------------|
| 13            | 747         | 1                   | 10           | 2011-06-03 00:00:00.0 | 2011-06-14 00:00:00.0 | 2011-06-03 00:00:00.0 | 2011-06-19 00:00:00.0 | 4.1                 | 92.25         | 92.25        | 2011-06-19 00:00:00.0 |
| 13            | 747         | 2                   | 20           | 2011-06-03 00:00:00.0 | 2011-06-14 00:00:00.0 | 2011-06-03 00:00:00.0 | 2011-06-19 00:00:00.0 | 3.5                 | 87.5          | 87.5         | 2011-06-19 00:00:00.0 |
| 13            | 747         | 3                   | 30           | 2011-06-03 00:00:00.0 | 2011-06-14 00:00:00.0 | 2011-06-03 00:00:00.0 | 2011-06-19 00:00:00.0 | 1.0                 | 14.5          | 14.5         | 2011-06-19 00:00:00.0 |
| 13            | 747         | 4                   | 40           | 2011-06-03 00:00:00.0 | 2011-06-14 00:00:00.0 | 2011-06-03 00:00:00.0 | 2011-06-19 00:00:00.0 | 2.0                 | 31.5          | 31.5         | 2011-06-19 00:00:00.0 |
| 13            | 747         | 6                   | 50           | 2011-06-03 00:00:00.0 | 2011-06-14 00:00:00.0 | 2011-06-03 00:00:00.0 | 2011-06-19 00:00:00.0 | 3.0                 | 36.75         | 36.75        | 2011-06-19 00:00:00.0 |
| ...           | ...         | ...                 | ...          | ...                   | ...                   | ...                   | ...                   | ...                 | ...           | ...          | ...                   |
*/
CREATE TABLE WorkOrderRouting (
    "WorkOrderID" INTEGER NOT NULL,
        -- <example>13</example>
        -- <fk> -> WorkOrder."WorkOrderID"</fk>
    "ProductID" INTEGER NOT NULL,
        -- <example>747</example>
    "OperationSequence" INTEGER NOT NULL,
        -- <example>1</example>
    "LocationID" INTEGER NOT NULL,
        -- <example>10</example>
        -- <fk> -> Location."LocationID"</fk>
    "ScheduledStartDate" DATETIME NOT NULL,
        -- <example>'2011-06-03 00:00:00.0'</example>
    "ScheduledEndDate" DATETIME NOT NULL,
        -- <example>'2011-06-14 00:00:00.0'</example>
    "ActualStartDate" DATETIME NOT NULL,
        -- <example>'2011-06-03 00:00:00.0'</example>
    "ActualEndDate" DATETIME NOT NULL,
        -- <example>'2011-06-19 00:00:00.0'</example>
    "ActualResourceHrs" REAL NOT NULL,
        -- <example>4.100</example>
    "PlannedCost" REAL NOT NULL,
        -- <example>92.250</example>
    "ActualCost" REAL NOT NULL,
        -- <example>92.250</example>
    "ModifiedDate" DATETIME NOT NULL,
        -- <example>'2011-06-19 00:00:00.0'</example>
    PRIMARY KEY ("WorkOrderID", "ProductID", "OperationSequence"),
    FOREIGN KEY ("WorkOrderID") REFERENCES WorkOrder("WorkOrderID"),
    FOREIGN KEY ("LocationID") REFERENCES Location("LocationID")
);
```