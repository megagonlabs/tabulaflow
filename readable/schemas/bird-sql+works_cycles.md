```sql
-- Database: works_cycles

-- Table: Address (19614 rows)
CREATE TABLE Address (
    AddressID INTEGER NULL PRIMARY KEY,
        -- <example>18089</example>
    AddressLine1 TEXT NOT NULL,
        -- <example>'#500-75 O'Connor Street'</example>
    AddressLine2 TEXT NULL,
        -- <example>'Space 55'</example>
    City TEXT NOT NULL,
        -- <example>'Ottawa'</example>
    StateProvinceID INTEGER NOT NULL,
        -- <example>57</example>
        -- <fk> -> StateProvince.StateProvinceID</fk>
    PostalCode TEXT NOT NULL,
        -- <example>'K4B 1S2'</example>
    SpatialLocation TEXT NULL,
        -- <example>'0x00000000010100000067A89189898A5EC0AE8BFC28BCE44740'</example>
    rowguid TEXT NOT NULL,
        -- <example>'00093F9C-0487-4723-B376-D90FF565AD6F'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2007-12-04 00:00:00.0'</example>
    FOREIGN KEY (StateProvinceID) REFERENCES StateProvince(StateProvinceID)
);

-- Table: AddressType (6 rows)
CREATE TABLE AddressType (
    AddressTypeID INTEGER NULL PRIMARY KEY,
        -- <example>4</example>
    Name TEXT NOT NULL,
        -- <values>{'Archive', 'Billing', 'Home', 'Main Office', 'Primary', 'Shipping'}</values>
    rowguid TEXT NOT NULL,
        -- <values>{'24CB3088-4345-47C4-86C5-17B535133D1E', '41BC2FF6-F0FC-475F-8EB9-CEC0805AA0F2', '8EEEC28C-07A2-4FB9-AD0A-42D4A0BBC575', 'A67F238A-5BA2-444B-966C-0467ED9C427F', 'B29DA3F8-19A3-47DA-9DAA-15C84F4A83A5', 'B84F78B1-4EFE-4A0E-8CB7-70E9F112F886'}</values>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: BillOfMaterials (2679 rows)
CREATE TABLE BillOfMaterials (
    BillOfMaterialsID INTEGER NULL PRIMARY KEY,
        -- <example>893</example>
    ProductAssemblyID INTEGER NULL,
        -- <example>3</example>
        -- <fk> -> Product.ProductID</fk>
    ComponentID INTEGER NOT NULL,
        -- <example>749</example>
        -- <fk> -> Product.ProductID</fk>
    StartDate DATETIME NOT NULL,
        -- <example>'2010-05-26 00:00:00.0'</example>
    EndDate DATETIME NULL,
        -- <example>'2010-05-03 00:00:00.0'</example>
    UnitMeasureCode TEXT NOT NULL,
        -- <values>{'EA', 'IN', 'OZ'}</values>
        -- <fk> -> UnitMeasure.UnitMeasureCode</fk>
    BOMLevel INTEGER NOT NULL,
        -- <example>2</example>
    PerAssemblyQty REAL NOT NULL,
        -- <example>1.000</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2010-02-18 00:00:00.0'</example>
    FOREIGN KEY (UnitMeasureCode) REFERENCES UnitMeasure(UnitMeasureCode),
    FOREIGN KEY (ComponentID) REFERENCES Product(ProductID),
    FOREIGN KEY (ProductAssemblyID) REFERENCES Product(ProductID)
);

-- Table: BusinessEntity (20777 rows)
CREATE TABLE BusinessEntity (
    BusinessEntityID INTEGER NULL PRIMARY KEY,
        -- <example>8722</example>
    rowguid TEXT NOT NULL,
        -- <example>'00021813-91EF-4A97-9682-0D2AC8C9EA97'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2017-12-13 13:20:24.0'</example>
);

-- Table: BusinessEntityAddress (19614 rows)
CREATE TABLE BusinessEntityAddress (
    BusinessEntityID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> BusinessEntity.BusinessEntityID</fk>
    AddressID INTEGER NOT NULL,
        -- <example>249</example>
        -- <fk> -> Address.AddressID</fk>
    AddressTypeID INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> AddressType.AddressTypeID</fk>
    rowguid TEXT NOT NULL,
        -- <example>'00013363-E32F-4615-9439-AFF156D480AE'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2014-09-12 11:15:06.0'</example>
    PRIMARY KEY (BusinessEntityID, AddressID, AddressTypeID),
    FOREIGN KEY (AddressID) REFERENCES Address(AddressID),
    FOREIGN KEY (AddressTypeID) REFERENCES AddressType(AddressTypeID),
    FOREIGN KEY (BusinessEntityID) REFERENCES BusinessEntity(BusinessEntityID)
);

-- Table: BusinessEntityContact (909 rows)
CREATE TABLE BusinessEntityContact (
    BusinessEntityID INTEGER NOT NULL,
        -- <example>292</example>
        -- <fk> -> BusinessEntity.BusinessEntityID</fk>
    PersonID INTEGER NOT NULL,
        -- <example>291</example>
        -- <fk> -> Person.BusinessEntityID</fk>
    ContactTypeID INTEGER NOT NULL,
        -- <example>11</example>
        -- <fk> -> ContactType.ContactTypeID</fk>
    rowguid TEXT NOT NULL,
        -- <example>'0022434C-E325-47B0-92A0-7302FFA5046F'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2017-12-13 13:21:02.0'</example>
    PRIMARY KEY (BusinessEntityID, PersonID, ContactTypeID),
    FOREIGN KEY (BusinessEntityID) REFERENCES BusinessEntity(BusinessEntityID),
    FOREIGN KEY (ContactTypeID) REFERENCES ContactType(ContactTypeID),
    FOREIGN KEY (PersonID) REFERENCES Person(BusinessEntityID)
);

-- Table: ContactType (20 rows)
CREATE TABLE ContactType (
    ContactTypeID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NOT NULL,
        -- <example>'Accounting Manager'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: CountryRegion (239 rows)
CREATE TABLE CountryRegion (
    CountryRegionCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'AD'</example>
    Name TEXT NOT NULL,
        -- <example>'Afghanistan'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'ModifiedDate'</example>
);

-- Table: CountryRegionCurrency (109 rows)
CREATE TABLE CountryRegionCurrency (
    CountryRegionCode TEXT NOT NULL,
        -- <example>'AE'</example>
        -- <fk> -> CountryRegion.CountryRegionCode</fk>
    CurrencyCode TEXT NOT NULL,
        -- <example>'AED'</example>
        -- <fk> -> Currency.CurrencyCode</fk>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2014-02-08 10:17:21.0'</example>
    PRIMARY KEY (CountryRegionCode, CurrencyCode),
    FOREIGN KEY (CountryRegionCode) REFERENCES CountryRegion(CountryRegionCode),
    FOREIGN KEY (CurrencyCode) REFERENCES Currency(CurrencyCode)
);

-- Table: CreditCard (19118 rows)
CREATE TABLE CreditCard (
    CreditCardID INTEGER NULL PRIMARY KEY,
        -- <example>11935</example>
    CardType TEXT NOT NULL,
        -- <values>{'ColonialVoice', 'Distinguish', 'SuperiorCard', 'Vista'}</values>
    CardNumber TEXT NOT NULL,
        -- <example>'11111000471254'</example>
    ExpMonth INTEGER NOT NULL,
        -- <example>11</example>
    ExpYear INTEGER NOT NULL,
        -- <example>2006</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2013-07-29 00:00:00.0'</example>
);

-- Table: Culture (8 rows)
CREATE TABLE Culture (
    CultureID TEXT NOT NULL PRIMARY KEY,
        -- <values>{'', 'ar', 'en', 'es', 'fr', 'he', 'th', 'zh-cht'}</values>
    Name TEXT NOT NULL,
        -- <values>{'Arabic', 'Chinese', 'English', 'French', 'Hebrew', 'Invariant Language (Invariant Country)', 'Spanish', 'Thai'}</values>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: Currency (105 rows)
CREATE TABLE Currency (
    CurrencyCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'AED'</example>
    Name TEXT NOT NULL,
        -- <example>'Afghani'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: CurrencyRate (13532 rows)
CREATE TABLE CurrencyRate (
    CurrencyRateID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    CurrencyRateDate DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    FromCurrencyCode TEXT NOT NULL,
        -- <values>{'USD'}</values>
        -- <fk> -> Currency.CurrencyCode</fk>
    ToCurrencyCode TEXT NOT NULL,
        -- <values>{'ARS', 'AUD', 'BRL', 'CAD', 'CNY', 'DEM', 'EUR', 'FRF', 'GBP', 'JPY', 'MXN', 'SAR', 'USD', 'VEB'}</values>
        -- <fk> -> Currency.CurrencyCode</fk>
    AverageRate REAL NOT NULL,
        -- <example>1.000</example>
    EndOfDayRate REAL NOT NULL,
        -- <example>1.000</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    FOREIGN KEY (ToCurrencyCode) REFERENCES Currency(CurrencyCode),
    FOREIGN KEY (FromCurrencyCode) REFERENCES Currency(CurrencyCode)
);

-- Table: Customer (0 rows)
CREATE TABLE Customer (
    CustomerID INTEGER NULL PRIMARY KEY,
    PersonID INTEGER NULL,
        -- <fk> -> Person.BusinessEntityID</fk>
    StoreID INTEGER NULL,
        -- <fk> -> Store.BusinessEntityID</fk>
    TerritoryID INTEGER NULL,
        -- <fk> -> SalesTerritory.TerritoryID</fk>
    AccountNumber TEXT NOT NULL,
    rowguid TEXT NOT NULL,
    ModifiedDate DATETIME NOT NULL,
    FOREIGN KEY (PersonID) REFERENCES Person(BusinessEntityID),
    FOREIGN KEY (TerritoryID) REFERENCES SalesTerritory(TerritoryID),
    FOREIGN KEY (StoreID) REFERENCES Store(BusinessEntityID)
);

-- Table: Department (16 rows)
CREATE TABLE Department (
    DepartmentID INTEGER NULL PRIMARY KEY,
        -- <example>12</example>
    Name TEXT NOT NULL,
        -- <example>'Document Control'</example>
    GroupName TEXT NOT NULL,
        -- <values>{'Executive General and Administration', 'Inventory Management', 'Manufacturing', 'Quality Assurance', 'Research and Development', 'Sales and Marketing'}</values>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: Document (13 rows)
CREATE TABLE Document (
    DocumentNode TEXT NOT NULL PRIMARY KEY,
        -- <example>'/'</example>
    DocumentLevel INTEGER NULL,
        -- <example>0</example>
    Title TEXT NOT NULL,
        -- <example>'Documents'</example>
    Owner INTEGER NOT NULL,
        -- <example>217</example>
        -- <fk> -> Employee.BusinessEntityID</fk>
    FolderFlag INTEGER NOT NULL,
        -- <example>1</example>
    FileName TEXT NOT NULL,
        -- <example>'Documents'</example>
    FileExtension TEXT NOT NULL,
        -- <values>{'', '.doc'}</values>
    Revision TEXT NOT NULL,
        -- <values>{'0', '1', '2', '3', '4', '8'}</values>
    ChangeNumber INTEGER NOT NULL,
        -- <example>0</example>
    Status INTEGER NOT NULL,
        -- <example>2</example>
    DocumentSummary TEXT NULL,
        -- <values>{'Detailed instructions for replacing pedals with Ad... parts when replacing worn or broken components. 
', 'Guidelines and recommendations for lubricating the...quency at which oil or grease should be applied. 
', 'It is important that you maintain your bicycle and... adjusting the tightness of the suspension fork.

', 'Reflectors are vital safety components of your bic... bracket of your Adventure Works Cycles bicycle.

', 'Worn or damaged seats can be easily replaced follo...parts when replacing worn or broken components. 

'}</values>
    Document BLOB NULL,
        -- <example>'0xD0CF11E0A1B11AE100000000000000000000000000000000...00000000000000000000000000000000000000000000000000'</example>
    rowguid TEXT NOT NULL,
        -- <example>'26A266F1-1D23-40E2-AF48-6AB8D954FE37'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2017-12-13 13:58:03.0'</example>
    FOREIGN KEY (Owner) REFERENCES Employee(BusinessEntityID)
);

-- Table: EmailAddress (19972 rows)
CREATE TABLE EmailAddress (
    BusinessEntityID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Person.BusinessEntityID</fk>
    EmailAddressID INTEGER NULL,
        -- <example>1</example>
    EmailAddress TEXT NULL,
        -- <example>'ken0@adventure-works.com'</example>
    rowguid TEXT NOT NULL,
        -- <example>'8A1901E4-671B-431A-871C-EADB2942E9EE'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2009-01-07 00:00:00.0'</example>
    PRIMARY KEY (BusinessEntityID, EmailAddressID),
    FOREIGN KEY (BusinessEntityID) REFERENCES Person(BusinessEntityID)
);

-- Table: Employee (290 rows)
CREATE TABLE Employee (
    BusinessEntityID INTEGER NOT NULL PRIMARY KEY,
        -- <example>151</example>
        -- <fk> -> Person.BusinessEntityID</fk>
    NationalIDNumber TEXT NOT NULL,
        -- <example>'10708100'</example>
    LoginID TEXT NOT NULL,
        -- <example>'adventure-works\alan0'</example>
    OrganizationNode TEXT NULL,
        -- <example>'/1/'</example>
    OrganizationLevel INTEGER NULL,
        -- <example>1</example>
    JobTitle TEXT NOT NULL,
        -- <example>'Chief Executive Officer'</example>
    BirthDate DATE NOT NULL,
        -- <example>'1969-01-29'</example>
    MaritalStatus TEXT NOT NULL,
        -- <values>{'M', 'S'}</values>
    Gender TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    HireDate DATE NOT NULL,
        -- <example>'2009-01-14'</example>
    SalariedFlag INTEGER NOT NULL,
        -- <example>1</example>
    VacationHours INTEGER NOT NULL,
        -- <example>99</example>
    SickLeaveHours INTEGER NOT NULL,
        -- <example>69</example>
    CurrentFlag INTEGER NOT NULL,
        -- <example>1</example>
    rowguid TEXT NOT NULL,
        -- <example>'00027A8C-C2F8-4A31-ABA8-8A203638B8F1'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2014-06-30 00:00:00.0'</example>
    FOREIGN KEY (BusinessEntityID) REFERENCES Person(BusinessEntityID)
);

-- Table: EmployeeDepartmentHistory (296 rows)
CREATE TABLE EmployeeDepartmentHistory (
    BusinessEntityID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Employee.BusinessEntityID</fk>
    DepartmentID INTEGER NOT NULL,
        -- <example>16</example>
        -- <fk> -> Department.DepartmentID</fk>
    ShiftID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Shift.ShiftID</fk>
    StartDate DATE NOT NULL,
        -- <example>'2009-01-14'</example>
    EndDate DATE NULL,
        -- <example>'2010-05-30'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2009-01-13 00:00:00.0'</example>
    PRIMARY KEY (BusinessEntityID, DepartmentID, ShiftID, StartDate),
    FOREIGN KEY (ShiftID) REFERENCES Shift(ShiftID),
    FOREIGN KEY (DepartmentID) REFERENCES Department(DepartmentID),
    FOREIGN KEY (BusinessEntityID) REFERENCES Employee(BusinessEntityID)
);

-- Table: EmployeePayHistory (316 rows)
CREATE TABLE EmployeePayHistory (
    BusinessEntityID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Employee.BusinessEntityID</fk>
    RateChangeDate DATETIME NOT NULL,
        -- <example>'2009-01-14 00:00:00.0'</example>
    Rate REAL NOT NULL,
        -- <example>125.500</example>
    PayFrequency INTEGER NOT NULL,
        -- <example>2</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2014-06-30 00:00:00.0'</example>
    PRIMARY KEY (BusinessEntityID, RateChangeDate),
    FOREIGN KEY (BusinessEntityID) REFERENCES Employee(BusinessEntityID)
);

-- Table: JobCandidate (12 rows)
CREATE TABLE JobCandidate (
    JobCandidateID INTEGER NULL PRIMARY KEY,
        -- <example>2</example>
    BusinessEntityID INTEGER NULL,
        -- <example>274</example>
        -- <fk> -> Employee.BusinessEntityID</fk>
    Resume TEXT NULL,
        -- <example>'<ns:Resume xmlns:ns="http://schemas.microsoft.com/...ttp://www.Wingtiptoys.com</ns:WebSite></ns:Resume>'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2007-06-23 00:00:00.0'</example>
    FOREIGN KEY (BusinessEntityID) REFERENCES Employee(BusinessEntityID)
);

-- Table: Location (14 rows)
CREATE TABLE Location (
    LocationID INTEGER NULL PRIMARY KEY,
        -- <example>30</example>
    Name TEXT NOT NULL,
        -- <example>'Debur and Polish'</example>
    CostRate REAL NOT NULL,
        -- <example>0.000</example>
    Availability REAL NOT NULL,
        -- <example>0.000</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: Password (19972 rows)
CREATE TABLE Password (
    BusinessEntityID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> Person.BusinessEntityID</fk>
    PasswordHash TEXT NOT NULL,
        -- <example>'pbFwXWE99vobT6g+vPWFy93NtUU/orrIWafF01hccfM='</example>
    PasswordSalt TEXT NOT NULL,
        -- <example>'bE3XiWw='</example>
    rowguid TEXT NOT NULL,
        -- <example>'329EACBE-C883-4F48-B8B6-17AA4627EFFF'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2009-01-07 00:00:00.0'</example>
    FOREIGN KEY (BusinessEntityID) REFERENCES Person(BusinessEntityID)
);

-- Table: Person (19972 rows)
CREATE TABLE Person (
    BusinessEntityID INTEGER NOT NULL PRIMARY KEY,
        -- <example>14617</example>
        -- <fk> -> BusinessEntity.BusinessEntityID</fk>
    PersonType TEXT NOT NULL,
        -- <values>{'EM', 'GC', 'IN', 'SC', 'SP', 'VC'}</values>
    NameStyle INTEGER NOT NULL,
        -- <example>0</example>
    Title TEXT NULL,
        -- <values>{'Mr.', 'Mrs.', 'Ms', 'Ms.', 'Sr.', 'Sra.'}</values>
    FirstName TEXT NOT NULL,
        -- <example>'Ken'</example>
    MiddleName TEXT NULL,
        -- <example>'J'</example>
    LastName TEXT NOT NULL,
        -- <example>'Sánchez'</example>
    Suffix TEXT NULL,
        -- <values>{'II', 'III', 'IV', 'Jr.', 'PhD', 'Sr.'}</values>
    EmailPromotion INTEGER NOT NULL,
        -- <example>0</example>
    AdditionalContactInfo TEXT NULL,
        -- <values>{'<AdditionalContactInfo xmlns="http://schemas.micro...</act:number></act:mobile></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...</act:number></act:mobile></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...icing.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...is up.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...obile></crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...obile></crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...odels.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...reach.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...sales.</crm:ContactRecord></AdditionalContactInfo>', '<AdditionalContactInfo xmlns="http://schemas.micro...tract.</crm:ContactRecord></AdditionalContactInfo>'}</values>
    Demographics TEXT NULL,
        -- <example>'<IndividualSurvey xmlns="http://schemas.microsoft....urchaseYTD>0</TotalPurchaseYTD></IndividualSurvey>'</example>
    rowguid TEXT NOT NULL,
        -- <example>'000191EF-7424-4A5F-AB19-0852B1F0B78D'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2009-01-07 00:00:00.0'</example>
    FOREIGN KEY (BusinessEntityID) REFERENCES BusinessEntity(BusinessEntityID)
);

-- Table: PersonCreditCard (19118 rows)
CREATE TABLE PersonCreditCard (
    BusinessEntityID INTEGER NOT NULL,
        -- <example>293</example>
        -- <fk> -> Person.BusinessEntityID</fk>
    CreditCardID INTEGER NOT NULL,
        -- <example>17038</example>
        -- <fk> -> CreditCard.CreditCardID</fk>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2013-07-31 00:00:00.0'</example>
    PRIMARY KEY (BusinessEntityID, CreditCardID),
    FOREIGN KEY (CreditCardID) REFERENCES CreditCard(CreditCardID),
    FOREIGN KEY (BusinessEntityID) REFERENCES Person(BusinessEntityID)
);

-- Table: PhoneNumberType (3 rows)
CREATE TABLE PhoneNumberType (
    PhoneNumberTypeID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NOT NULL,
        -- <values>{'Cell', 'Home', 'Work'}</values>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2017-12-13 13:19:22.0'</example>
);

-- Table: Product (504 rows)
CREATE TABLE Product (
    ProductID INTEGER NULL PRIMARY KEY,
        -- <example>921</example>
    Name TEXT NOT NULL,
        -- <example>'AWC Logo Cap'</example>
    ProductNumber TEXT NOT NULL,
        -- <example>'AR-5381'</example>
    MakeFlag INTEGER NOT NULL,
        -- <example>0</example>
    FinishedGoodsFlag INTEGER NOT NULL,
        -- <example>0</example>
    Color TEXT NULL,
        -- <values>{'Black', 'Blue', 'Grey', 'Multi', 'Red', 'Silver', 'Silver/Black', 'White', 'Yellow'}</values>
    SafetyStockLevel INTEGER NOT NULL,
        -- <example>1000</example>
    ReorderPoint INTEGER NOT NULL,
        -- <example>750</example>
    StandardCost REAL NOT NULL,
        -- <example>0.000</example>
    ListPrice REAL NOT NULL,
        -- <example>0.000</example>
    Size TEXT NULL,
        -- <example>'58'</example>
    SizeUnitMeasureCode TEXT NULL,
        -- <values>{'CM'}</values>
        -- <fk> -> UnitMeasure.UnitMeasureCode</fk>
    WeightUnitMeasureCode TEXT NULL,
        -- <values>{'G', 'LB'}</values>
        -- <fk> -> UnitMeasure.UnitMeasureCode</fk>
    Weight REAL NULL,
        -- <example>435.000</example>
    DaysToManufacture INTEGER NOT NULL,
        -- <example>0</example>
    ProductLine TEXT NULL,
        -- <values>{'M', 'R', 'S', 'T'}</values>
    Class TEXT NULL,
        -- <values>{'H', 'L', 'M'}</values>
    Style TEXT NULL,
        -- <values>{'M', 'U', 'W'}</values>
    ProductSubcategoryID INTEGER NULL,
        -- <example>14</example>
        -- <fk> -> ProductSubcategory.ProductSubcategoryID</fk>
    ProductModelID INTEGER NULL,
        -- <example>6</example>
        -- <fk> -> ProductModel.ProductModelID</fk>
    SellStartDate DATETIME NOT NULL,
        -- <example>'2008-04-30 00:00:00.0'</example>
    SellEndDate DATETIME NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    DiscontinuedDate DATETIME NULL,
    rowguid TEXT NOT NULL,
        -- <example>'01A8C3FC-ED52-458E-A634-D5B6E2ACCFED'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2014-02-08 10:01:36.0'</example>
    FOREIGN KEY (ProductModelID) REFERENCES ProductModel(ProductModelID),
    FOREIGN KEY (ProductSubcategoryID) REFERENCES ProductSubcategory(ProductSubcategoryID),
    FOREIGN KEY (WeightUnitMeasureCode) REFERENCES UnitMeasure(UnitMeasureCode),
    FOREIGN KEY (SizeUnitMeasureCode) REFERENCES UnitMeasure(UnitMeasureCode)
);

-- Table: ProductCategory (4 rows)
CREATE TABLE ProductCategory (
    ProductCategoryID INTEGER NULL PRIMARY KEY,
        -- <example>3</example>
    Name TEXT NOT NULL,
        -- <values>{'Accessories', 'Bikes', 'Clothing', 'Components'}</values>
    rowguid TEXT NOT NULL,
        -- <values>{'10A7C342-CA82-48D4-8A38-46A2EB089B74', '2BE3BE36-D9A2-4EEE-B593-ED895D97C2A6', 'C657828D-D808-4ABA-91A3-AF2CE02300E9', 'CFBDA25C-DF71-47A7-B81B-64EE161AA37C'}</values>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: ProductCostHistory (395 rows)
CREATE TABLE ProductCostHistory (
    ProductID INTEGER NOT NULL,
        -- <example>707</example>
        -- <fk> -> Product.ProductID</fk>
    StartDate DATE NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    EndDate DATE NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    StandardCost REAL NOT NULL,
        -- <example>12.028</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    PRIMARY KEY (ProductID, StartDate),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
);

-- Table: ProductDescription (762 rows)
CREATE TABLE ProductDescription (
    ProductDescriptionID INTEGER NULL PRIMARY KEY,
        -- <example>1954</example>
    Description TEXT NOT NULL,
        -- <example>'Chromoly steel.'</example>
    rowguid TEXT NOT NULL,
        -- <example>'00FFDFAC-0207-4DF0-8051-7D3C884816F3'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2013-04-30 00:00:00.0'</example>
);

-- Table: ProductDocument (32 rows)
CREATE TABLE ProductDocument (
    ProductID INTEGER NOT NULL,
        -- <example>317</example>
        -- <fk> -> Product.ProductID</fk>
    DocumentNode TEXT NOT NULL,
        -- <values>{'/1/1/', '/2/1/', '/3/1/', '/3/2/', '/3/3/', '/3/4/'}</values>
        -- <fk> -> Document.DocumentNode</fk>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2013-12-29 13:51:58.0'</example>
    PRIMARY KEY (ProductID, DocumentNode),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID),
    FOREIGN KEY (DocumentNode) REFERENCES Document(DocumentNode)
);

-- Table: ProductInventory (1069 rows)
CREATE TABLE ProductInventory (
    ProductID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Product.ProductID</fk>
    LocationID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Location.LocationID</fk>
    Shelf TEXT NOT NULL,
        -- <example>'A'</example>
    Bin INTEGER NOT NULL,
        -- <example>1</example>
    Quantity INTEGER NOT NULL,
        -- <example>408</example>
    rowguid TEXT NOT NULL,
        -- <example>'47A24246-6C43-48EB-968F-025738A8A410'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2014-08-08 00:00:00.0'</example>
    PRIMARY KEY (ProductID, LocationID),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID),
    FOREIGN KEY (LocationID) REFERENCES Location(LocationID)
);

-- Table: ProductListPriceHistory (395 rows)
CREATE TABLE ProductListPriceHistory (
    ProductID INTEGER NOT NULL,
        -- <example>707</example>
        -- <fk> -> Product.ProductID</fk>
    StartDate DATE NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    EndDate DATE NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    ListPrice REAL NOT NULL,
        -- <example>33.644</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2012-05-29 00:00:00.0'</example>
    PRIMARY KEY (ProductID, StartDate),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
);

-- Table: ProductModel (128 rows)
CREATE TABLE ProductModel (
    ProductModelID INTEGER NULL PRIMARY KEY,
        -- <example>82</example>
    Name TEXT NOT NULL,
        -- <example>'All-Purpose Bike Stand'</example>
    CatalogDescription TEXT NULL,
        -- <values>{'<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>', '<?xml-stylesheet href="ProductDescription.xsl" typ...ience></p1:Specifications></p1:ProductDescription>'}</values>
    Instructions TEXT NULL,
        -- <values>{'<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...cs>.
                    </step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...flate the tube to 35 PSI.</step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...lustration <diag>7</diag></step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...p><step>Move to shipping.</step></Location></root>', '<root xmlns="http://schemas.microsoft.com/sqlserve...p><step>Move to shipping.</step></Location></root>'}</values>
    rowguid TEXT NOT NULL,
        -- <example>'00CE9171-8944-4D49-BA37-485C1D122F5C'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2013-04-30 00:00:00.0'</example>
);

-- Table: ProductModelProductDescriptionCulture (762 rows)
CREATE TABLE ProductModelProductDescriptionCulture (
    ProductModelID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ProductModel.ProductModelID</fk>
    ProductDescriptionID INTEGER NOT NULL,
        -- <example>1199</example>
        -- <fk> -> ProductDescription.ProductDescriptionID</fk>
    CultureID TEXT NOT NULL,
        -- <values>{'ar', 'en', 'fr', 'he', 'th', 'zh-cht'}</values>
        -- <fk> -> Culture.CultureID</fk>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2013-04-30 00:00:00.0'</example>
    PRIMARY KEY (ProductModelID, ProductDescriptionID, CultureID),
    FOREIGN KEY (ProductModelID) REFERENCES ProductModel(ProductModelID),
    FOREIGN KEY (ProductDescriptionID) REFERENCES ProductDescription(ProductDescriptionID),
    FOREIGN KEY (CultureID) REFERENCES Culture(CultureID)
);

-- Table: ProductPhoto (100 rows)
CREATE TABLE ProductPhoto (
    ProductPhotoID INTEGER NULL PRIMARY KEY,
        -- <example>69</example>
    ThumbNailPhoto BLOB NULL,
        -- <example>'0x47494638396150003100F70000E3E3FCA6ACB3F5F6FE303D...B10653A210B9C00FDA2026E4C00F1299108D3811010100003B'</example>
    ThumbnailPhotoFileName TEXT NULL,
        -- <example>'racer02_black_f_small.gif'</example>
    LargePhoto BLOB NULL,
        -- <example>'0x474946383961F0009500F70000D3D3FEE2E3FE86878ADBDC...2ECA61C0785440D755E992B335FC5561171648172B2000003B'</example>
    LargePhotoFileName TEXT NULL,
        -- <example>'racer02_black_f_large.gif'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: ProductProductPhoto (504 rows)
CREATE TABLE ProductProductPhoto (
    ProductID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Product.ProductID</fk>
    ProductPhotoID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ProductPhoto.ProductPhotoID</fk>
    Primary INTEGER NOT NULL,
        -- <example>1</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2008-03-31 00:00:00.0'</example>
    PRIMARY KEY (ProductID, ProductPhotoID),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID),
    FOREIGN KEY (ProductPhotoID) REFERENCES ProductPhoto(ProductPhotoID)
);

-- Table: ProductReview (4 rows)
CREATE TABLE ProductReview (
    ProductReviewID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    ProductID INTEGER NOT NULL,
        -- <example>709</example>
        -- <fk> -> Product.ProductID</fk>
    ReviewerName TEXT NOT NULL,
        -- <values>{'David', 'Jill', 'John Smith', 'Laura Norman'}</values>
    ReviewDate DATETIME NOT NULL,
        -- <example>'2013-09-18 00:00:00.0'</example>
    EmailAddress TEXT NOT NULL,
        -- <values>{'david@graphicdesigninstitute.com', 'jill@margiestravel.com', 'john@fourthcoffee.com', 'laura@treyresearch.net'}</values>
    Rating INTEGER NOT NULL,
        -- <example>5</example>
    Comments TEXT NULL,
        -- <values>{'A little on the heavy side, but overall the entry/.... I would like 
them even better if there was a we', 'I can't believe I'm singing the praises of a pair ...feet all day. 
The reinforced toe is nearly bullet', 'Maybe it's just because I'm new to mountain biking... the pedals, or is it just a learning curve thing?', 'The Road-550-W from Adventure Works Cycles is ever... is shorter, the suspension is weight-tuned and th'}</values>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2013-09-18 00:00:00.0'</example>
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
);

-- Table: ProductSubcategory (37 rows)
CREATE TABLE ProductSubcategory (
    ProductSubcategoryID INTEGER NULL PRIMARY KEY,
        -- <example>2</example>
    ProductCategoryID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ProductCategory.ProductCategoryID</fk>
    Name TEXT NOT NULL,
        -- <example>'Bib-Shorts'</example>
    rowguid TEXT NOT NULL,
        -- <example>'000310C0-BCC8-42C4-B0C3-45AE611AF06B'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2008-04-30 00:00:00.0'</example>
    FOREIGN KEY (ProductCategoryID) REFERENCES ProductCategory(ProductCategoryID)
);

-- Table: ProductVendor (460 rows)
CREATE TABLE ProductVendor (
    ProductID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Product.ProductID</fk>
    BusinessEntityID INTEGER NOT NULL,
        -- <example>1580</example>
        -- <fk> -> Vendor.BusinessEntityID</fk>
    AverageLeadTime INTEGER NOT NULL,
        -- <example>17</example>
    StandardPrice REAL NOT NULL,
        -- <example>47.870</example>
    LastReceiptCost REAL NULL,
        -- <example>50.264</example>
    LastReceiptDate DATETIME NULL,
        -- <example>'2011-08-29 00:00:00.0'</example>
    MinOrderQty INTEGER NOT NULL,
        -- <example>1</example>
    MaxOrderQty INTEGER NOT NULL,
        -- <example>5</example>
    OnOrderQty INTEGER NULL,
        -- <example>3</example>
    UnitMeasureCode TEXT NOT NULL,
        -- <values>{'CAN', 'CS', 'CTN', 'DZ', 'EA', 'GAL', 'PAK'}</values>
        -- <fk> -> UnitMeasure.UnitMeasureCode</fk>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-08-29 00:00:00.0'</example>
    PRIMARY KEY (ProductID, BusinessEntityID),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID),
    FOREIGN KEY (BusinessEntityID) REFERENCES Vendor(BusinessEntityID),
    FOREIGN KEY (UnitMeasureCode) REFERENCES UnitMeasure(UnitMeasureCode)
);

-- Table: PurchaseOrderDetail (8845 rows)
CREATE TABLE PurchaseOrderDetail (
    PurchaseOrderID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> PurchaseOrderHeader.PurchaseOrderID</fk>
    PurchaseOrderDetailID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    DueDate DATETIME NOT NULL,
        -- <example>'2011-04-30 00:00:00.0'</example>
    OrderQty INTEGER NOT NULL,
        -- <example>4</example>
    ProductID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Product.ProductID</fk>
    UnitPrice REAL NOT NULL,
        -- <example>50.000</example>
    LineTotal REAL NOT NULL,
        -- <example>201.000</example>
    ReceivedQty REAL NOT NULL,
        -- <example>3.000</example>
    RejectedQty REAL NOT NULL,
        -- <example>0.000</example>
    StockedQty REAL NOT NULL,
        -- <example>3.000</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-04-23 00:00:00.0'</example>
    FOREIGN KEY (PurchaseOrderID) REFERENCES PurchaseOrderHeader(PurchaseOrderID),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
);

-- Table: PurchaseOrderHeader (4012 rows)
CREATE TABLE PurchaseOrderHeader (
    PurchaseOrderID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    RevisionNumber INTEGER NOT NULL,
        -- <example>4</example>
    Status INTEGER NOT NULL,
        -- <example>4</example>
    EmployeeID INTEGER NOT NULL,
        -- <example>258</example>
        -- <fk> -> Employee.BusinessEntityID</fk>
    VendorID INTEGER NOT NULL,
        -- <example>1580</example>
        -- <fk> -> Vendor.BusinessEntityID</fk>
    ShipMethodID INTEGER NOT NULL,
        -- <example>3</example>
        -- <fk> -> ShipMethod.ShipMethodID</fk>
    OrderDate DATETIME NOT NULL,
        -- <example>'2011-04-16 00:00:00.0'</example>
    ShipDate DATETIME NULL,
        -- <example>'2011-04-25 00:00:00.0'</example>
    SubTotal REAL NOT NULL,
        -- <example>201.040</example>
    TaxAmt REAL NOT NULL,
        -- <example>16.083</example>
    Freight REAL NOT NULL,
        -- <example>5.026</example>
    TotalDue REAL NOT NULL,
        -- <example>222.149</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-04-25 00:00:00.0'</example>
    FOREIGN KEY (EmployeeID) REFERENCES Employee(BusinessEntityID),
    FOREIGN KEY (VendorID) REFERENCES Vendor(BusinessEntityID),
    FOREIGN KEY (ShipMethodID) REFERENCES ShipMethod(ShipMethodID)
);

-- Table: SalesOrderDetail (121317 rows)
CREATE TABLE SalesOrderDetail (
    SalesOrderID INTEGER NOT NULL,
        -- <example>43659</example>
        -- <fk> -> SalesOrderHeader.SalesOrderID</fk>
    SalesOrderDetailID INTEGER NULL PRIMARY KEY,
        -- <example>54351</example>
    CarrierTrackingNumber TEXT NULL,
        -- <example>'4911-403C-98'</example>
    OrderQty INTEGER NOT NULL,
        -- <example>1</example>
    ProductID INTEGER NOT NULL,
        -- <example>776</example>
        -- <fk>composite</fk>
    SpecialOfferID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk>composite</fk>
    UnitPrice REAL NOT NULL,
        -- <example>2025.000</example>
    UnitPriceDiscount REAL NOT NULL,
        -- <example>0.000</example>
    LineTotal REAL NOT NULL,
        -- <example>2025.000</example>
    rowguid TEXT NOT NULL,
        -- <example>'0000C99C-2B71-4885-B976-C1CCAE896EF2'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    FOREIGN KEY (SalesOrderID) REFERENCES SalesOrderHeader(SalesOrderID),
    FOREIGN KEY (SpecialOfferID, ProductID) REFERENCES SpecialOfferProduct(SpecialOfferID, ProductID)
);

-- Table: SalesOrderHeader (31465 rows)
CREATE TABLE SalesOrderHeader (
    SalesOrderID INTEGER NULL PRIMARY KEY,
        -- <example>71821</example>
    RevisionNumber INTEGER NOT NULL,
        -- <example>8</example>
    OrderDate DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    DueDate DATETIME NOT NULL,
        -- <example>'2011-06-12 00:00:00.0'</example>
    ShipDate DATETIME NULL,
        -- <example>'2011-06-07 00:00:00.0'</example>
    Status INTEGER NOT NULL,
        -- <example>5</example>
    OnlineOrderFlag INTEGER NOT NULL,
        -- <example>0</example>
    SalesOrderNumber TEXT NOT NULL,
        -- <example>'SO43659'</example>
    PurchaseOrderNumber TEXT NULL,
        -- <example>'PO522145787'</example>
    AccountNumber TEXT NULL,
        -- <example>'10-4020-000676'</example>
    CustomerID INTEGER NOT NULL,
        -- <example>29825</example>
        -- <fk> -> Customer.CustomerID</fk>
    SalesPersonID INTEGER NULL,
        -- <example>279</example>
        -- <fk> -> SalesPerson.BusinessEntityID</fk>
    TerritoryID INTEGER NULL,
        -- <example>5</example>
        -- <fk> -> SalesTerritory.TerritoryID</fk>
    BillToAddressID INTEGER NOT NULL,
        -- <example>985</example>
        -- <fk> -> Address.AddressID</fk>
    ShipToAddressID INTEGER NOT NULL,
        -- <example>985</example>
        -- <fk> -> Address.AddressID</fk>
    ShipMethodID INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> Address.AddressID</fk>
    CreditCardID INTEGER NULL,
        -- <example>16281</example>
        -- <fk> -> CreditCard.CreditCardID</fk>
    CreditCardApprovalCode TEXT NULL,
        -- <example>'105041Vi84182'</example>
    CurrencyRateID INTEGER NULL,
        -- <example>4</example>
        -- <fk> -> CurrencyRate.CurrencyRateID</fk>
    SubTotal REAL NOT NULL,
        -- <example>20565.621</example>
    TaxAmt REAL NOT NULL,
        -- <example>1971.515</example>
    Freight REAL NOT NULL,
        -- <example>616.098</example>
    TotalDue REAL NOT NULL,
        -- <example>23153.234</example>
    Comment TEXT NULL,
    rowguid TEXT NOT NULL,
        -- <example>'0000DE87-AB3F-4920-AC46-C404834241A0'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-06-07 00:00:00.0'</example>
    FOREIGN KEY (CurrencyRateID) REFERENCES CurrencyRate(CurrencyRateID),
    FOREIGN KEY (CreditCardID) REFERENCES CreditCard(CreditCardID),
    FOREIGN KEY (ShipMethodID) REFERENCES Address(AddressID),
    FOREIGN KEY (ShipToAddressID) REFERENCES Address(AddressID),
    FOREIGN KEY (BillToAddressID) REFERENCES Address(AddressID),
    FOREIGN KEY (TerritoryID) REFERENCES SalesTerritory(TerritoryID),
    FOREIGN KEY (SalesPersonID) REFERENCES SalesPerson(BusinessEntityID),
    FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID)
);

-- Table: SalesOrderHeaderSalesReason (27647 rows)
CREATE TABLE SalesOrderHeaderSalesReason (
    SalesOrderID INTEGER NOT NULL,
        -- <example>43697</example>
        -- <fk> -> SalesOrderHeader.SalesOrderID</fk>
    SalesReasonID INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> SalesReason.SalesReasonID</fk>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    PRIMARY KEY (SalesOrderID, SalesReasonID),
    FOREIGN KEY (SalesOrderID) REFERENCES SalesOrderHeader(SalesOrderID),
    FOREIGN KEY (SalesReasonID) REFERENCES SalesReason(SalesReasonID)
);

-- Table: SalesPerson (17 rows)
CREATE TABLE SalesPerson (
    BusinessEntityID INTEGER NOT NULL PRIMARY KEY,
        -- <example>287</example>
        -- <fk> -> Employee.BusinessEntityID</fk>
    TerritoryID INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> SalesTerritory.TerritoryID</fk>
    SalesQuota REAL NULL,
        -- <example>300000.000</example>
    Bonus REAL NOT NULL,
        -- <example>0.000</example>
    CommissionPct REAL NOT NULL,
        -- <example>0.000</example>
    SalesYTD REAL NOT NULL,
        -- <example>559697.564</example>
    SalesLastYear REAL NOT NULL,
        -- <example>0.000</example>
    rowguid TEXT NOT NULL,
        -- <example>'1DD1F689-DF74-4149-8600-59555EEF154B'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2010-12-28 00:00:00.0'</example>
    FOREIGN KEY (BusinessEntityID) REFERENCES Employee(BusinessEntityID),
    FOREIGN KEY (TerritoryID) REFERENCES SalesTerritory(TerritoryID)
);

-- Table: SalesPersonQuotaHistory (163 rows)
CREATE TABLE SalesPersonQuotaHistory (
    BusinessEntityID INTEGER NOT NULL,
        -- <example>274</example>
        -- <fk> -> SalesPerson.BusinessEntityID</fk>
    QuotaDate DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    SalesQuota REAL NOT NULL,
        -- <example>28000.000</example>
    rowguid TEXT NOT NULL,
        -- <example>'00F2F9F8-5158-4436-B134-7E0C462289E5'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-04-16 00:00:00.0'</example>
    PRIMARY KEY (BusinessEntityID, QuotaDate),
    FOREIGN KEY (BusinessEntityID) REFERENCES SalesPerson(BusinessEntityID)
);

-- Table: SalesReason (10 rows)
CREATE TABLE SalesReason (
    SalesReasonID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NOT NULL,
        -- <values>{'Demo Event', 'Magazine Advertisement', 'Manufacturer', 'On Promotion', 'Other', 'Price', 'Quality', 'Review', 'Sponsorship', 'Television  Advertisement'}</values>
    ReasonType TEXT NOT NULL,
        -- <values>{'Marketing', 'Other', 'Promotion'}</values>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: SalesTaxRate (29 rows)
CREATE TABLE SalesTaxRate (
    SalesTaxRateID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    StateProvinceID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> StateProvince.StateProvinceID</fk>
    TaxType INTEGER NOT NULL,
        -- <example>1</example>
    TaxRate REAL NOT NULL,
        -- <example>14.000</example>
    Name TEXT NOT NULL,
        -- <example>'Canadian GST + Alberta Provincial Tax'</example>
    rowguid TEXT NOT NULL,
        -- <example>'05C4FFDB-4F84-4CDF-ABE5-FDF3216EA74E'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2008-04-30 00:00:00.0'</example>
    FOREIGN KEY (StateProvinceID) REFERENCES StateProvince(StateProvinceID)
);

-- Table: SalesTerritory (10 rows)
CREATE TABLE SalesTerritory (
    TerritoryID INTEGER NULL PRIMARY KEY,
        -- <example>2</example>
    Name TEXT NOT NULL,
        -- <values>{'Australia', 'Canada', 'Central', 'France', 'Germany', 'Northeast', 'Northwest', 'Southeast', 'Southwest', 'United Kingdom'}</values>
    CountryRegionCode TEXT NOT NULL,
        -- <values>{'AU', 'CA', 'DE', 'FR', 'GB', 'US'}</values>
        -- <fk> -> CountryRegion.CountryRegionCode</fk>
    Group TEXT NOT NULL,
        -- <values>{'Europe', 'North America', 'Pacific'}</values>
    SalesYTD REAL NOT NULL,
        -- <example>7887186.788</example>
    SalesLastYear REAL NOT NULL,
        -- <example>3298694.494</example>
    CostYTD REAL NOT NULL,
        -- <example>0.000</example>
    CostLastYear REAL NOT NULL,
        -- <example>0.000</example>
    rowguid TEXT NOT NULL,
        -- <values>{'00FB7309-96CC-49E2-8363-0A1BA72486F2', '05FC7E1F-2DEA-414E-9ECD-09D150516FB5', '06B4AF8A-1639-476E-9266-110461D66B00', '43689A10-E30B-497F-B0DE-11DE20267FF7', '602E612E-DFE9-41D9-B894-27E489747885', '6D2450DB-8159-414F-A917-E73EE91C38A9', '6DC4165A-5E4C-42D2-809D-4344E0AC75E7', 'BF806804-9B4C-4B07-9D19-706F2E689552', 'DC3E9EA0-7950-4431-9428-99DBCBC33865', 'DF6E7FD8-1A8D-468C-B103-ED8ADDB452C1'}</values>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2008-04-30 00:00:00.0'</example>
    FOREIGN KEY (CountryRegionCode) REFERENCES CountryRegion(CountryRegionCode)
);

-- Table: SalesTerritoryHistory (17 rows)
CREATE TABLE SalesTerritoryHistory (
    BusinessEntityID INTEGER NOT NULL,
        -- <example>275</example>
        -- <fk> -> SalesPerson.BusinessEntityID</fk>
    TerritoryID INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> SalesTerritory.TerritoryID</fk>
    StartDate DATETIME NOT NULL,
        -- <example>'2011-05-31 00:00:00.0'</example>
    EndDate DATETIME NULL,
        -- <example>'2012-11-29 00:00:00.0'</example>
    rowguid TEXT NOT NULL,
        -- <example>'009F7660-44A6-4ADF-BD4B-A5D1B79993F5'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2012-11-22 00:00:00.0'</example>
    PRIMARY KEY (BusinessEntityID, TerritoryID, StartDate),
    FOREIGN KEY (BusinessEntityID) REFERENCES SalesPerson(BusinessEntityID),
    FOREIGN KEY (TerritoryID) REFERENCES SalesTerritory(TerritoryID)
);

-- Table: ScrapReason (16 rows)
CREATE TABLE ScrapReason (
    ScrapReasonID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NOT NULL,
        -- <example>'Brake assembly not as ordered'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: Shift (3 rows)
CREATE TABLE Shift (
    ShiftID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NOT NULL,
        -- <values>{'Day', 'Evening', 'Night'}</values>
    StartTime TEXT NOT NULL,
        -- <values>{'07:00:00', '15:00:00', '23:00:00'}</values>
    EndTime TEXT NOT NULL,
        -- <values>{'07:00:00', '15:00:00', '23:00:00'}</values>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: ShipMethod (5 rows)
CREATE TABLE ShipMethod (
    ShipMethodID INTEGER NULL PRIMARY KEY,
        -- <example>4</example>
    Name TEXT NOT NULL,
        -- <values>{'CARGO TRANSPORT 5', 'OVERNIGHT J-FAST', 'OVERSEAS - DELUXE', 'XRQ - TRUCK GROUND', 'ZY - EXPRESS'}</values>
    ShipBase REAL NOT NULL,
        -- <example>3.950</example>
    ShipRate REAL NOT NULL,
        -- <example>0.990</example>
    rowguid TEXT NOT NULL,
        -- <values>{'107E8356-E7A8-463D-B60C-079FFF467F3F', '22F4E461-28CF-4ACE-A980-F686CF112EC8', '3455079B-F773-4DC6-8F1E-2A58649C4AB8', '6BE756D9-D7BE-4463-8F2C-AE60C710D606', 'B166019A-B134-4E76-B957-2B0490C610ED'}</values>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: ShoppingCartItem (3 rows)
CREATE TABLE ShoppingCartItem (
    ShoppingCartItemID INTEGER NULL PRIMARY KEY,
        -- <example>2</example>
    ShoppingCartID TEXT NOT NULL,
        -- <values>{'14951', '20621'}</values>
    Quantity INTEGER NOT NULL,
        -- <example>3</example>
    ProductID INTEGER NOT NULL,
        -- <example>862</example>
        -- <fk> -> Product.ProductID</fk>
    DateCreated DATETIME NOT NULL,
        -- <example>'2013-11-09 17:54:07.0'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2013-11-09 17:54:07.0'</example>
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
);

-- Table: SpecialOffer (16 rows)
CREATE TABLE SpecialOffer (
    SpecialOfferID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Description TEXT NOT NULL,
        -- <example>'No Discount'</example>
    DiscountPct REAL NOT NULL,
        -- <example>0.000</example>
    Type TEXT NOT NULL,
        -- <values>{'Discontinued Product', 'Excess Inventory', 'New Product', 'No Discount', 'Seasonal Discount', 'Volume Discount'}</values>
    Category TEXT NOT NULL,
        -- <values>{'Customer', 'No Discount', 'Reseller'}</values>
    StartDate DATETIME NOT NULL,
        -- <example>'2011-05-01 00:00:00.0'</example>
    EndDate DATETIME NOT NULL,
        -- <example>'2014-11-30 00:00:00.0'</example>
    MinQty INTEGER NOT NULL,
        -- <example>0</example>
    MaxQty INTEGER NULL,
        -- <example>14</example>
    rowguid TEXT NOT NULL,
        -- <example>'0290C4F5-191F-4337-AB6B-0A2DDE03CBF9'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2011-04-01 00:00:00.0'</example>
);

-- Table: SpecialOfferProduct (538 rows)
CREATE TABLE SpecialOfferProduct (
    SpecialOfferID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> SpecialOffer.SpecialOfferID</fk>
    ProductID INTEGER NOT NULL,
        -- <example>680</example>
        -- <fk> -> Product.ProductID</fk>
    rowguid TEXT NOT NULL,
        -- <example>'0020931C-087C-42F8-B441-EBE3D3B5F51E'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-04-01 00:00:00.0'</example>
    PRIMARY KEY (SpecialOfferID, ProductID),
    FOREIGN KEY (SpecialOfferID) REFERENCES SpecialOffer(SpecialOfferID),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
);

-- Table: StateProvince (181 rows)
CREATE TABLE StateProvince (
    StateProvinceID INTEGER NULL PRIMARY KEY,
        -- <example>103</example>
    StateProvinceCode TEXT NOT NULL,
        -- <example>'01'</example>
    CountryRegionCode TEXT NOT NULL,
        -- <example>'FR'</example>
        -- <fk> -> CountryRegion.CountryRegionCode</fk>
    IsOnlyStateProvinceFlag INTEGER NOT NULL,
        -- <example>0</example>
    Name TEXT NOT NULL,
        -- <example>'Ain'</example>
    TerritoryID INTEGER NOT NULL,
        -- <example>6</example>
        -- <fk> -> SalesTerritory.TerritoryID</fk>
    rowguid TEXT NOT NULL,
        -- <example>'00723E00-C976-401D-A92B-E582DF3D6E01'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2014-02-08 10:17:21.0'</example>
    FOREIGN KEY (TerritoryID) REFERENCES SalesTerritory(TerritoryID),
    FOREIGN KEY (CountryRegionCode) REFERENCES CountryRegion(CountryRegionCode)
);

-- Table: Store (701 rows)
CREATE TABLE Store (
    BusinessEntityID INTEGER NOT NULL PRIMARY KEY,
        -- <example>630</example>
        -- <fk> -> BusinessEntity.BusinessEntityID</fk>
    Name TEXT NOT NULL,
        -- <example>'Next-Door Bike Store'</example>
    SalesPersonID INTEGER NULL,
        -- <example>279</example>
        -- <fk> -> SalesPerson.BusinessEntityID</fk>
    Demographics TEXT NULL,
        -- <example>'<StoreSurvey xmlns="http://schemas.microsoft.com/s...NumberEmployees>13</NumberEmployees></StoreSurvey>'</example>
    rowguid TEXT NOT NULL,
        -- <example>'004EA91C-FCD4-4973-87EF-9059C6E20BB5'</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2014-09-12 11:15:07.0'</example>
    FOREIGN KEY (BusinessEntityID) REFERENCES BusinessEntity(BusinessEntityID),
    FOREIGN KEY (SalesPersonID) REFERENCES SalesPerson(BusinessEntityID)
);

-- Table: TransactionHistory (113443 rows)
CREATE TABLE TransactionHistory (
    TransactionID INTEGER NULL PRIMARY KEY,
        -- <example>100000</example>
    ProductID INTEGER NOT NULL,
        -- <example>784</example>
        -- <fk> -> Product.ProductID</fk>
    ReferenceOrderID INTEGER NOT NULL,
        -- <example>41590</example>
    ReferenceOrderLineID INTEGER NOT NULL,
        -- <example>0</example>
    TransactionDate DATETIME NOT NULL,
        -- <example>'2013-07-31 00:00:00.0'</example>
    TransactionType TEXT NOT NULL,
        -- <values>{'P', 'S', 'W'}</values>
    Quantity INTEGER NOT NULL,
        -- <example>2</example>
    ActualCost REAL NOT NULL,
        -- <example>0.000</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2013-07-31 00:00:00.0'</example>
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
);

-- Table: TransactionHistoryArchive (89253 rows)
CREATE TABLE TransactionHistoryArchive (
    TransactionID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    ProductID INTEGER NOT NULL,
        -- <example>1</example>
    ReferenceOrderID INTEGER NOT NULL,
        -- <example>1</example>
    ReferenceOrderLineID INTEGER NOT NULL,
        -- <example>1</example>
    TransactionDate DATETIME NOT NULL,
        -- <example>'2011-04-16 00:00:00.0'</example>
    TransactionType TEXT NOT NULL,
        -- <values>{'P', 'S', 'W'}</values>
    Quantity INTEGER NOT NULL,
        -- <example>4</example>
    ActualCost REAL NOT NULL,
        -- <example>50.000</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2011-04-16 00:00:00.0'</example>
);

-- Table: UnitMeasure (38 rows)
CREATE TABLE UnitMeasure (
    UnitMeasureCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'BOX'</example>
    Name TEXT NOT NULL,
        -- <example>'Bottle'</example>
    ModifiedDate DATETIME NOT NULL
        -- <example>'2008-04-30 00:00:00.0'</example>
);

-- Table: Vendor (104 rows)
CREATE TABLE Vendor (
    BusinessEntityID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1596</example>
        -- <fk> -> BusinessEntity.BusinessEntityID</fk>
    AccountNumber TEXT NOT NULL,
        -- <example>'ADATUM0001'</example>
    Name TEXT NOT NULL,
        -- <example>'Australia Bike Retailer'</example>
    CreditRating INTEGER NOT NULL,
        -- <example>1</example>
    PreferredVendorStatus INTEGER NOT NULL,
        -- <example>1</example>
    ActiveFlag INTEGER NOT NULL,
        -- <example>1</example>
    PurchasingWebServiceURL TEXT NULL,
        -- <values>{'www.adatum.com/', 'www.litwareinc.com/', 'www.northwindtraders.com/', 'www.proseware.com/', 'www.treyresearch.net/', 'www.wideworldimporters.com/'}</values>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-12-23 00:00:00.0'</example>
    FOREIGN KEY (BusinessEntityID) REFERENCES BusinessEntity(BusinessEntityID)
);

-- Table: WorkOrder (72591 rows)
CREATE TABLE WorkOrder (
    WorkOrderID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    ProductID INTEGER NOT NULL,
        -- <example>722</example>
        -- <fk> -> Product.ProductID</fk>
    OrderQty INTEGER NOT NULL,
        -- <example>8</example>
    StockedQty INTEGER NOT NULL,
        -- <example>8</example>
    ScrappedQty INTEGER NOT NULL,
        -- <example>0</example>
    StartDate DATETIME NOT NULL,
        -- <example>'2011-06-03 00:00:00.0'</example>
    EndDate DATETIME NULL,
        -- <example>'2011-06-13 00:00:00.0'</example>
    DueDate DATETIME NOT NULL,
        -- <example>'2011-06-14 00:00:00.0'</example>
    ScrapReasonID INTEGER NULL,
        -- <example>7</example>
        -- <fk> -> ScrapReason.ScrapReasonID</fk>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-06-13 00:00:00.0'</example>
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID),
    FOREIGN KEY (ScrapReasonID) REFERENCES ScrapReason(ScrapReasonID)
);

-- Table: WorkOrderRouting (67131 rows)
CREATE TABLE WorkOrderRouting (
    WorkOrderID INTEGER NOT NULL,
        -- <example>13</example>
        -- <fk> -> WorkOrder.WorkOrderID</fk>
    ProductID INTEGER NOT NULL,
        -- <example>747</example>
    OperationSequence INTEGER NOT NULL,
        -- <example>1</example>
    LocationID INTEGER NOT NULL,
        -- <example>10</example>
        -- <fk> -> Location.LocationID</fk>
    ScheduledStartDate DATETIME NOT NULL,
        -- <example>'2011-06-03 00:00:00.0'</example>
    ScheduledEndDate DATETIME NOT NULL,
        -- <example>'2011-06-14 00:00:00.0'</example>
    ActualStartDate DATETIME NULL,
        -- <example>'2011-06-03 00:00:00.0'</example>
    ActualEndDate DATETIME NULL,
        -- <example>'2011-06-19 00:00:00.0'</example>
    ActualResourceHrs REAL NULL,
        -- <example>4.100</example>
    PlannedCost REAL NOT NULL,
        -- <example>92.250</example>
    ActualCost REAL NULL,
        -- <example>92.250</example>
    ModifiedDate DATETIME NOT NULL,
        -- <example>'2011-06-19 00:00:00.0'</example>
    PRIMARY KEY (WorkOrderID, ProductID, OperationSequence),
    FOREIGN KEY (WorkOrderID) REFERENCES WorkOrder(WorkOrderID),
    FOREIGN KEY (LocationID) REFERENCES Location(LocationID)
);
```