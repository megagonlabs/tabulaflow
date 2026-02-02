```sql
-- Database: world_development_indicators

-- Table: Country (247 rows)
CREATE TABLE Country (
    CountryCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'ABW'</example>
    ShortName TEXT NULL,
        -- <example>'Afghanistan'</example>
    TableName TEXT NULL,
        -- <example>'Afghanistan'</example>
    LongName TEXT NULL,
        -- <example>'Islamic State of Afghanistan'</example>
    Alpha2Code TEXT NULL,
        -- <example>'AF'</example>
    CurrencyUnit TEXT NULL,
        -- <example>'Afghan afghani'</example>
    SpecialNotes TEXT NULL,
        -- <example>'Fiscal year end: March 20; reporting period for na...ion numbers due to exclusion of the opium economy.'</example>
    Region TEXT NULL,
        -- <values>{'', 'East Asia & Pacific', 'Europe & Central Asia', 'Latin America & Caribbean', 'Middle East & North Africa', 'North America', 'South Asia', 'Sub-Saharan Africa'}</values>
    IncomeGroup TEXT NULL,
        -- <values>{'', 'High income: OECD', 'High income: nonOECD', 'Low income', 'Lower middle income', 'Upper middle income'}</values>
    Wb2Code TEXT NULL,
        -- <example>'AF'</example>
    NationalAccountsBaseYear TEXT NULL,
        -- <example>'2002/03'</example>
    NationalAccountsReferenceYear TEXT NULL,
        -- <example>''</example>
    SnaPriceValuation TEXT NULL,
        -- <values>{'', 'Value added at basic prices (VAB)', 'Value added at producer prices (VAP)'}</values>
    LendingCategory TEXT NULL,
        -- <values>{'', 'Blend', 'IBRD', 'IDA'}</values>
    OtherGroups TEXT NULL,
        -- <values>{'', 'Euro area', 'HIPC'}</values>
    SystemOfNationalAccounts TEXT NULL,
        -- <values>{'', 'Country uses the 1968 System of National Accounts methodology.', 'Country uses the 1993 System of National Accounts methodology.', 'Country uses the 2008 System of National Accounts methodology.'}</values>
    AlternativeConversionFactor TEXT NULL,
        -- <example>''</example>
    PppSurveyYear TEXT NULL,
        -- <values>{'', '2011 (household consumption only).', '2011', 'Rolling'}</values>
    BalanceOfPaymentsManualInUse TEXT NULL,
        -- <values>{'', 'IMF Balance of Payments Manual, 6th edition.'}</values>
    ExternalDebtReportingStatus TEXT NULL,
        -- <values>{'', 'Actual', 'Estimate', 'Preliminary'}</values>
    SystemOfTrade TEXT NULL,
        -- <values>{'', 'General trade system', 'Special trade system'}</values>
    GovernmentAccountingConcept TEXT NULL,
        -- <values>{'', 'Budgetary central government', 'Consolidated central government'}</values>
    ImfDataDisseminationStandard TEXT NULL,
        -- <values>{'', 'General Data Dissemination System (GDDS)', 'Special Data Dissemination Standard (SDDS)'}</values>
    LatestPopulationCensus TEXT NULL,
        -- <example>'1979'</example>
    LatestHouseholdSurvey TEXT NULL,
        -- <example>'Multiple Indicator Cluster Survey (MICS), 2010/11'</example>
    SourceOfMostRecentIncomeAndExpenditureData TEXT NULL,
        -- <example>'Integrated household survey (IHS), 2008'</example>
    VitalRegistrationComplete TEXT NULL,
        -- <values>{'', 'Yes', 'Yes. Vital registration for Guernsey and Jersey.'}</values>
    LatestAgriculturalCensus TEXT NULL,
        -- <example>'2013/14'</example>
    LatestIndustrialData INTEGER NULL,
        -- <example>2011</example>
    LatestTradeData INTEGER NULL,
        -- <example>2013</example>
    LatestWaterWithdrawalData INTEGER NULL
        -- <example>2000</example>
);

-- Table: CountryNotes (4857 rows)
CREATE TABLE CountryNotes (
    Countrycode TEXT NOT NULL,
        -- <example>'ABW'</example>
        -- <fk> -> Country.CountryCode</fk>
    Seriescode TEXT NOT NULL,
        -- <example>'EG.EGY.PRIM.PP.KD'</example>
        -- <fk> -> Series.SeriesCode</fk>
    Description TEXT NULL,
        -- <example>'Sources: Estimated based on UN Energy Statistics (2014); World Development Indicators, WDI (2014)'</example>
    PRIMARY KEY (Countrycode, Seriescode),
    FOREIGN KEY (Seriescode) REFERENCES Series(SeriesCode),
    FOREIGN KEY (Countrycode) REFERENCES Country(CountryCode)
);

-- Table: Footnotes (532415 rows)
CREATE TABLE Footnotes (
    Countrycode TEXT NOT NULL,
        -- <example>'ABW'</example>
        -- <fk> -> Country.CountryCode</fk>
    Seriescode TEXT NOT NULL,
        -- <example>'AG.LND.FRST.K2'</example>
        -- <fk> -> Series.SeriesCode</fk>
    Year TEXT NULL,
        -- <example>'YR1990'</example>
    Description TEXT NULL,
        -- <example>'Not specified'</example>
    PRIMARY KEY (Countrycode, Seriescode, Year),
    FOREIGN KEY (Seriescode) REFERENCES Series(SeriesCode),
    FOREIGN KEY (Countrycode) REFERENCES Country(CountryCode)
);

-- Table: Indicators (5656458 rows)
CREATE TABLE Indicators (
    CountryName TEXT NULL,
        -- <example>'Arab World'</example>
    CountryCode TEXT NOT NULL,
        -- <example>'ABW'</example>
        -- <fk> -> Country.CountryCode</fk>
    IndicatorName TEXT NULL,
        -- <example>'Adolescent fertility rate (births per 1,000 women ages 15-19)'</example>
    IndicatorCode TEXT NOT NULL,
        -- <example>'AG.LND.AGRI.K2'</example>
    Year INTEGER NOT NULL,
        -- <example>1961</example>
    Value INTEGER NULL,
        -- <example>133</example>
    PRIMARY KEY (CountryCode, IndicatorCode, Year),
    FOREIGN KEY (CountryCode) REFERENCES Country(CountryCode)
);

-- Table: Series (1345 rows)
CREATE TABLE Series (
    SeriesCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'AG.AGR.TRAC.NO'</example>
    Topic TEXT NULL,
        -- <example>'Economic Policy & Debt: Balance of payments: Capital & financial account'</example>
    IndicatorName TEXT NULL,
        -- <example>'Foreign direct investment, net (BoP, current US$)'</example>
    ShortDefinition TEXT NULL,
        -- <example>''</example>
    LongDefinition TEXT NULL,
        -- <example>'Foreign direct investment are the net inflows of i...estor. It is the sum of equity capital, reinvestme'</example>
    UnitOfMeasure TEXT NULL,
        -- <values>{'%', '', '2005 PPP $', '2011 PPP $', '`'}</values>
    Periodicity TEXT NULL,
        -- <values>{'Annual'}</values>
    BasePeriod TEXT NULL,
        -- <values>{'', '1990', '2000', '2004-06', '2005', '2010', '2011', 'varies by country'}</values>
    OtherNotes INTEGER NULL,
    AggregationMethod TEXT NULL,
        -- <values>{'', 'Gap-filled total', 'Linear mixed-effect model estimates', 'Median', 'Sum', 'Unweighted average', 'Weighted average'}</values>
    LimitationsAndExceptions TEXT NULL,
        -- <example>''</example>
    NotesFromOriginalSource TEXT NULL,
        -- <values>{'', 'All surveys were administered using the Enterprise...which can be found from www.enterprisesurveys.org.', 'All the indicators refer to expenditures by financ...re the fiscal year begins in July, expenditure dat', 'Depending on the source and means of monitoring, d...s. See listed source for country-specific details.', 'Estimates are presented with uncertainty intervals...y produced by simulations). For more detailed info', 'Estimates of maternal mortality are presented alon...babilistic evaluation of the uncertainty attributa', 'In some cases, the sum of public and private expen...s a financing source. When the number is smaller t', 'Most surveys were administered using the Enterpris...he global Enterprise Surveys methodology, plus Afg', 'PPP series resulting from the 2005 International c...ors refer to expenditures by financing agent excep', 'SIPRI statistical data on arms transfers relates t...ends, SIPRI has developed a unique system to measu', 'The 2007-2011 refugee population category also inc...nd includes groups of persons who are outside thei'}</values>
    GeneralComments TEXT NULL,
        -- <example>'Note: Data are based on the sixth edition of the I...its and debits to net acquisition of financial ass'</example>
    Source TEXT NULL,
        -- <example>'International Monetary Fund, Balance of Payments Statistics Yearbook and data files.'</example>
    StatisticalConceptAndMethodology TEXT NULL,
        -- <example>''</example>
    DevelopmentRelevance TEXT NULL,
        -- <example>''</example>
    RelatedSourceLinks TEXT NULL,
        -- <values>{'', 'World Bank, PovcalNet: an online poverty analysis ...http://iresearch.worldbank.org/PovcalNet/index.htm'}</values>
    OtherWebLinks INTEGER NULL,
    RelatedIndicators INTEGER NULL,
    LicenseType TEXT NULL
        -- <values>{'Open', 'Restricted'}</values>
);

-- Table: SeriesNotes (369 rows)
CREATE TABLE SeriesNotes (
    Seriescode TEXT NOT NULL,
        -- <example>'DT.DOD.PVLX.CD'</example>
        -- <fk> -> Series.SeriesCode</fk>
    Year TEXT NOT NULL,
        -- <example>'YR2014'</example>
    Description TEXT NULL,
        -- <example>'Interpolated using data for 1957 and 1962.'</example>
    PRIMARY KEY (Seriescode, Year),
    FOREIGN KEY (Seriescode) REFERENCES Series(SeriesCode)
);
```