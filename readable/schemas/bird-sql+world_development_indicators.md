```sql
-- Database: world_development_indicators

/*
Schema: NULLTable: Country
Rows: 247
Sample rows:
| CountryCode   | ShortName      | TableName      | LongName                                | Alpha2Code   | CurrencyUnit   | SpecialNotes                                                                                                                                                                                                | Region                     | IncomeGroup          | Wb2Code   | NationalAccountsBaseYear                           | NationalAccountsReferenceYear   | SnaPriceValuation                 | LendingCategory   | OtherGroups   | SystemOfNationalAccounts                                       | AlternativeConversionFactor   | PppSurveyYear                      | BalanceOfPaymentsManualInUse                 | ExternalDebtReportingStatus   | SystemOfTrade        | GovernmentAccountingConcept     | ImfDataDisseminationStandard             | LatestPopulationCensus                                        | LatestHouseholdSurvey                             | SourceOfMostRecentIncomeAndExpenditureData                | VitalRegistrationComplete   | LatestAgriculturalCensus   | LatestIndustrialData   | LatestTradeData   | LatestWaterWithdrawalData   |
|---------------|----------------|----------------|-----------------------------------------|--------------|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|----------------------|-----------|----------------------------------------------------|---------------------------------|-----------------------------------|-------------------|---------------|----------------------------------------------------------------|-------------------------------|------------------------------------|----------------------------------------------|-------------------------------|----------------------|---------------------------------|------------------------------------------|---------------------------------------------------------------|---------------------------------------------------|-----------------------------------------------------------|-----------------------------|----------------------------|------------------------|-------------------|-----------------------------|
| AFG           | Afghanistan    | Afghanistan    | Islamic State of Afghanistan            | AF           | Afghan afghani | Fiscal year end: March 20; reporting period for national accounts data: FY (from 2013 are CY). Natio...F and differ from the Central Statistics Organization numbers due to exclusion of the opium economy. | South Asia                 | Low income           | AF        | 2002/03                                            |                                 | Value added at basic prices (VAB) | IDA               | HIPC          | Country uses the 1993 System of National Accounts methodology. |                               |                                    |                                              | Actual                        | General trade system | Consolidated central government | General Data Dissemination System (GDDS) | 1979                                                          | Multiple Indicator Cluster Survey (MICS), 2010/11 | Integrated household survey (IHS), 2008                   |                             | 2013/14                    | [NULL]                 | 2013.0            | 2000.0                      |
| ALB           | Albania        | Albania        | Republic of Albania                     | AL           | Albanian lek   |                                                                                                                                                                                                             | Europe & Central Asia      | Upper middle income  | AL        | Original chained constant price data are rescaled. | 1996                            | Value added at basic prices (VAB) | IBRD              |               | Country uses the 1993 System of National Accounts methodology. |                               | Rolling                            | IMF Balance of Payments Manual, 6th edition. | Actual                        | General trade system | Budgetary central government    | General Data Dissemination System (GDDS) | 2011                                                          | Demographic and Health Survey (DHS), 2008/09      | Living Standards Measurement Study Survey (LSMS), 2011/12 | Yes                         | 2012                       | 2011.0                 | 2013.0            | 2006.0                      |
| DZA           | Algeria        | Algeria        | People's Democratic Republic of Algeria | DZ           | Algerian dinar |                                                                                                                                                                                                             | Middle East & North Africa | Upper middle income  | DZ        | 1980                                               |                                 | Value added at basic prices (VAB) | IBRD              |               | Country uses the 1968 System of National Accounts methodology. |                               | 2011                               | IMF Balance of Payments Manual, 6th edition. | Actual                        | Special trade system | Budgetary central government    | General Data Dissemination System (GDDS) | 2008                                                          | Multiple Indicator Cluster Survey (MICS), 2012    | Integrated household survey (IHS), 1995                   |                             |                            | 2010.0                 | 2013.0            | 2001.0                      |
| ASM           | American Samoa | American Samoa | American Samoa                          | AS           | U.S. dollar    |                                                                                                                                                                                                             | East Asia & Pacific        | Upper middle income  | AS        |                                                    |                                 |                                   |                   |               | Country uses the 1968 System of National Accounts methodology. |                               | 2011 (household consumption only). |                                              |                               | Special trade system |                                 |                                          | 2010                                                          |                                                   |                                                           | Yes                         | 2007                       | [NULL]                 | [NULL]            | [NULL]                      |
| ADO           | Andorra        | Andorra        | Principality of Andorra                 | AD           | Euro           |                                                                                                                                                                                                             | Europe & Central Asia      | High income: nonOECD | AD        | 2000                                               |                                 | Value added at basic prices (VAB) |                   |               | Country uses the 1968 System of National Accounts methodology. |                               |                                    |                                              |                               | Special trade system |                                 |                                          | 2011. Population data compiled from administrative registers. |                                                   |                                                           | Yes                         |                            | [NULL]                 | 2006.0            | [NULL]                      |
| ...           | ...            | ...            | ...                                     | ...          | ...            | ...                                                                                                                                                                                                         | ...                        | ...                  | ...       | ...                                                | ...                             | ...                               | ...               | ...           | ...                                                            | ...                           | ...                                | ...                                          | ...                           | ...                  | ...                             | ...                                      | ...                                                           | ...                                               | ...                                                       | ...                         | ...                        | ...                    | ...               | ...                         |
*/
CREATE TABLE Country (
    CountryCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'ABW'</example>
    ShortName TEXT NOT NULL,
        -- <example>'Afghanistan'</example>
    TableName TEXT NOT NULL,
        -- <example>'Afghanistan'</example>
    LongName TEXT NOT NULL,
        -- <example>'Islamic State of Afghanistan'</example>
    Alpha2Code TEXT NOT NULL,
        -- <example>'AF'</example>
    CurrencyUnit TEXT NOT NULL,
        -- <example>'Afghan afghani'</example>
    SpecialNotes TEXT NOT NULL,
        -- <example>'Fiscal year end: March 20; reporting period for na...ion numbers due to exclusion of the opium economy.'</example>
    Region TEXT NOT NULL,
        -- <values>{'', 'East Asia & Pacific', 'Europe & Central Asia', 'Latin America & Caribbean', 'Middle East & North Africa', 'North America', 'South Asia', 'Sub-Saharan Africa'}</values>
    IncomeGroup TEXT NOT NULL,
        -- <values>{'', 'High income: OECD', 'High income: nonOECD', 'Low income', 'Lower middle income', 'Upper middle income'}</values>
    Wb2Code TEXT NOT NULL,
        -- <example>'AF'</example>
    NationalAccountsBaseYear TEXT NOT NULL,
        -- <example>'2002/03'</example>
    NationalAccountsReferenceYear TEXT NOT NULL,
        -- <example>''</example>
    SnaPriceValuation TEXT NOT NULL,
        -- <values>{'', 'Value added at basic prices (VAB)', 'Value added at producer prices (VAP)'}</values>
    LendingCategory TEXT NOT NULL,
        -- <values>{'', 'Blend', 'IBRD', 'IDA'}</values>
    OtherGroups TEXT NOT NULL,
        -- <values>{'', 'Euro area', 'HIPC'}</values>
    SystemOfNationalAccounts TEXT NOT NULL,
        -- <values>{'', 'Country uses the 1968 System of National Accounts methodology.', 'Country uses the 1993 System of National Accounts methodology.', 'Country uses the 2008 System of National Accounts methodology.'}</values>
    AlternativeConversionFactor TEXT NOT NULL,
        -- <example>''</example>
    PppSurveyYear TEXT NOT NULL,
        -- <values>{'', '2011 (household consumption only).', '2011', 'Rolling'}</values>
    BalanceOfPaymentsManualInUse TEXT NOT NULL,
        -- <values>{'', 'IMF Balance of Payments Manual, 6th edition.'}</values>
    ExternalDebtReportingStatus TEXT NOT NULL,
        -- <values>{'', 'Actual', 'Estimate', 'Preliminary'}</values>
    SystemOfTrade TEXT NOT NULL,
        -- <values>{'', 'General trade system', 'Special trade system'}</values>
    GovernmentAccountingConcept TEXT NOT NULL,
        -- <values>{'', 'Budgetary central government', 'Consolidated central government'}</values>
    ImfDataDisseminationStandard TEXT NOT NULL,
        -- <values>{'', 'General Data Dissemination System (GDDS)', 'Special Data Dissemination Standard (SDDS)'}</values>
    LatestPopulationCensus TEXT NOT NULL,
        -- <example>'1979'</example>
    LatestHouseholdSurvey TEXT NOT NULL,
        -- <example>'Multiple Indicator Cluster Survey (MICS), 2010/11'</example>
    SourceOfMostRecentIncomeAndExpenditureData TEXT NOT NULL,
        -- <example>'Integrated household survey (IHS), 2008'</example>
    VitalRegistrationComplete TEXT NOT NULL,
        -- <values>{'', 'Yes', 'Yes. Vital registration for Guernsey and Jersey.'}</values>
    LatestAgriculturalCensus TEXT NOT NULL,
        -- <example>'2013/14'</example>
    LatestIndustrialData INTEGER NULL,
        -- <example>2011</example>
    LatestTradeData INTEGER NULL,
        -- <example>2013</example>
    LatestWaterWithdrawalData INTEGER NULL
        -- <example>2000</example>
);

/*
Schema: NULLTable: CountryNotes
Rows: 4857
Sample rows:
| Countrycode   | Seriescode        | Description                                                                                       |
|---------------|-------------------|---------------------------------------------------------------------------------------------------|
| ABW           | EG.EGY.PRIM.PP.KD | Sources: Estimated based on UN Energy Statistics (2014); World Development Indicators, WDI (2014) |
| ABW           | EG.ELC.RNEW.ZS    | Sources: UN Energy Statistics (2014)                                                              |
| ABW           | EG.FEC.RNEW.ZS    | Sources: UN Energy Statistics (2014)                                                              |
| ABW           | SM.POP.NETM       | Data sources : United Nations World Population Prospects                                          |
| ABW           | SM.POP.TOTL       | Estimates are derived from data on foreign-born population.                                       |
| ...           | ...               | ...                                                                                               |
*/
CREATE TABLE CountryNotes (
    Countrycode TEXT NOT NULL,
        -- <example>'ABW'</example>
        -- <fk> -> Country.CountryCode</fk>
    Seriescode TEXT NOT NULL,
        -- <example>'EG.EGY.PRIM.PP.KD'</example>
        -- <fk> -> Series.SeriesCode</fk>
    Description TEXT NOT NULL,
        -- <example>'Sources: Estimated based on UN Energy Statistics (2014); World Development Indicators, WDI (2014)'</example>
    PRIMARY KEY (Countrycode, Seriescode),
    FOREIGN KEY (Seriescode) REFERENCES Series(SeriesCode),
    FOREIGN KEY (Countrycode) REFERENCES Country(CountryCode)
);

/*
Schema: NULLTable: Footnotes
Rows: 532415
Sample rows:
| Countrycode   | Seriescode        | Year   | Description                                                                                            |
|---------------|-------------------|--------|--------------------------------------------------------------------------------------------------------|
| ABW           | AG.LND.FRST.K2    | YR1990 | Not specified                                                                                          |
| ABW           | AG.LND.FRST.K2    | YR2000 | Not specified                                                                                          |
| ABW           | AG.LND.FRST.K2    | YR2005 | Not specified                                                                                          |
| ABW           | BX.KLT.DINV.CD.WD | YR1987 | Source: United Nations Conference on Trade and Development, Foreign Direct Investment Online database. |
| ABW           | BX.KLT.DINV.CD.WD | YR1988 | Source: United Nations Conference on Trade and Development, Foreign Direct Investment Online database. |
| ...           | ...               | ...    | ...                                                                                                    |
*/
CREATE TABLE Footnotes (
    Countrycode TEXT NOT NULL,
        -- <example>'ABW'</example>
        -- <fk> -> Country.CountryCode</fk>
    Seriescode TEXT NOT NULL,
        -- <example>'AG.LND.FRST.K2'</example>
        -- <fk> -> Series.SeriesCode</fk>
    Year TEXT NOT NULL,
        -- <example>'YR1990'</example>
    Description TEXT NOT NULL,
        -- <example>'Not specified'</example>
    PRIMARY KEY (Countrycode, Seriescode, Year),
    FOREIGN KEY (Seriescode) REFERENCES Series(SeriesCode),
    FOREIGN KEY (Countrycode) REFERENCES Country(CountryCode)
);

/*
Schema: NULLTable: Indicators
Rows: 5656458
Sample rows:
| CountryName   | CountryCode   | IndicatorName                                                 | IndicatorCode   | Year   | Value   |
|---------------|---------------|---------------------------------------------------------------|-----------------|--------|---------|
| Arab World    | ARB           | Adolescent fertility rate (births per 1,000 women ages 15-19) | SP.ADO.TFRT     | 1960   | 133     |
| Arab World    | ARB           | Age dependency ratio (% of working-age population)            | SP.POP.DPND     | 1960   | 87      |
| Arab World    | ARB           | Age dependency ratio, old (% of working-age population)       | SP.POP.DPND.OL  | 1960   | 6       |
| Arab World    | ARB           | Age dependency ratio, young (% of working-age population)     | SP.POP.DPND.YG  | 1960   | 81      |
| Arab World    | ARB           | Arms exports (SIPRI trend indicator values)                   | MS.MIL.XPRT.KD  | 1960   | 3000000 |
| ...           | ...           | ...                                                           | ...             | ...    | ...     |
*/
CREATE TABLE Indicators (
    CountryName TEXT NOT NULL,
        -- <example>'Arab World'</example>
    CountryCode TEXT NOT NULL,
        -- <example>'ABW'</example>
        -- <fk> -> Country.CountryCode</fk>
    IndicatorName TEXT NOT NULL,
        -- <example>'Adolescent fertility rate (births per 1,000 women ages 15-19)'</example>
    IndicatorCode TEXT NOT NULL,
        -- <example>'AG.LND.AGRI.K2'</example>
    Year INTEGER NOT NULL,
        -- <example>1961</example>
    Value INTEGER NOT NULL,
        -- <example>133</example>
    PRIMARY KEY (CountryCode, IndicatorCode, Year),
    FOREIGN KEY (CountryCode) REFERENCES Country(CountryCode)
);

/*
Schema: NULLTable: Series
Rows: 1345
Sample rows:
| SeriesCode           | Topic                                                                    | IndicatorName                                             | ShortDefinition   | LongDefinition                                                                                                                                                                                              | UnitOfMeasure   | Periodicity   | BasePeriod   | OtherNotes   | AggregationMethod   | LimitationsAndExceptions                                                                                                                                                                                   | NotesFromOriginalSource   | GeneralComments                                                                                                                                                                                             | Source                                                                                                                                                                               | StatisticalConceptAndMethodology                                                                                                                                                                            | DevelopmentRelevance                                                                                                                                                                                        | RelatedSourceLinks   | OtherWebLinks   | RelatedIndicators   | LicenseType   |
|----------------------|--------------------------------------------------------------------------|-----------------------------------------------------------|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------|---------------|--------------|--------------|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|-----------------|---------------------|---------------|
| BN.KLT.DINV.CD       | Economic Policy & Debt: Balance of payments: Capital & financial account | Foreign direct investment, net (BoP, current US$)         |                   | Foreign direct investment are the net inflows of investment to acquire a lasting management interest...operating in an economy other than that of the investor. It is the sum of equity capital, reinvestme |                 | Annual        |              | [NULL]       |                     |                                                                                                                                                                                                            |                           | Note: Data are based on the sixth edition of the IMF's Balance of Payments Manual (BPM6) and are onl... the financial account have been changed from credits and debits to net acquisition of financial ass | International Monetary Fund, Balance of Payments Statistics Yearbook and data files.                                                                                                 |                                                                                                                                                                                                             |                                                                                                                                                                                                             |                      | [NULL]          | [NULL]              | Open          |
| BX.KLT.DINV.WD.GD.ZS | Economic Policy & Debt: Balance of payments: Capital & financial account | Foreign direct investment, net inflows (% of GDP)         |                   | Foreign direct investment are the net inflows of investment to acquire a lasting management interest...operating in an economy other than that of the investor. It is the sum of equity capital, reinvestme |                 | Annual        |              | [NULL]       | Weighted average    | FDI data do not give a complete picture of international investment in an economy. Balance of paymen...n important source of investment financing in some developing countries. In addition, FDI data omit |                           | Note: Data starting from 2005 are based on the sixth edition of the IMF's Balance of Payments Manual (BPM6).                                                                                                | International Monetary Fund, International Financial Statistics and Balance of Payments databases, World Bank, International Debt Statistics, and World Bank and OECD GDP estimates. | Data on equity flows are based on balance of payments data reported by the International Monetary Fu...lemented by the World Bank staff estimates using data from the United Nations Conference on Trade an | Private financial flows - equity and debt - account for the bulk of development finance. Equity flow...o equity. Debt flows are financing raised through bond issuance, bank lending, and supplier credits. |                      | [NULL]          | [NULL]              | Open          |
| BX.KLT.DINV.CD.WD    | Economic Policy & Debt: Balance of payments: Capital & financial account | Foreign direct investment, net inflows (BoP, current US$) |                   | Foreign direct investment refers to direct investment equity flows in the reporting economy. It is t... other capital. Direct investment is a category of cross-border investment associated with a residen |                 | Annual        |              | [NULL]       | Sum                 | FDI data do not give a complete picture of international investment in an economy. Balance of paymen...n important source of investment financing in some developing countries. In addition, FDI data omit |                           | Note: Data starting from 2005 are based on the sixth edition of the IMF's Balance of Payments Manual (BPM6).                                                                                                | International Monetary Fund, Balance of Payments database, supplemented by data from the United Nations Conference on Trade and Development and official national sources.           | Data on equity flows are based on balance of payments data reported by the International Monetary Fu...lemented by the World Bank staff estimates using data from the United Nations Conference on Trade an | Private financial flows - equity and debt - account for the bulk of development finance. Equity flow...o equity. Debt flows are financing raised through bond issuance, bank lending, and supplier credits. |                      | [NULL]          | [NULL]              | Open          |
| BM.KLT.DINV.GD.ZS    | Economic Policy & Debt: Balance of payments: Capital & financial account | Foreign direct investment, net outflows (% of GDP)        |                   | Foreign direct investment are the net inflows of investment to acquire a lasting management interest...operating in an economy other than that of the investor. It is the sum of equity capital, reinvestme |                 | Annual        |              | [NULL]       | Weighted average    |                                                                                                                                                                                                            |                           | Note: Data are based on the sixth edition of the IMF's Balance of Payments Manual (BPM6) and are only available from 2005 onwards.                                                                          | International Monetary Fund, International Financial Statistics and Balance of Payments databases, World Bank, International Debt Statistics, and World Bank and OECD GDP estimates. |                                                                                                                                                                                                             |                                                                                                                                                                                                             |                      | [NULL]          | [NULL]              | Open          |
| BN.TRF.KOGT.CD       | Economic Policy & Debt: Balance of payments: Capital & financial account | Net capital account (BoP, current US$)                    |                   | Net capital account records acquisitions and disposals of nonproduced nonfinancial assets, such as l... as well as capital transfers, including government debt forgiveness. The use of the term capital ac |                 | Annual        |              | [NULL]       |                     |                                                                                                                                                                                                            |                           | Note: Data are based on the sixth edition of the IMF's Balance of Payments Manual (BPM6) and are only available from 2005 onwards.                                                                          | International Monetary Fund, Balance of Payments Statistics Yearbook and data files.                                                                                                 |                                                                                                                                                                                                             |                                                                                                                                                                                                             |                      | [NULL]          | [NULL]              | Open          |
| ...                  | ...                                                                      | ...                                                       | ...               | ...                                                                                                                                                                                                         | ...             | ...           | ...          | ...          | ...                 | ...                                                                                                                                                                                                        | ...                       | ...                                                                                                                                                                                                         | ...                                                                                                                                                                                  | ...                                                                                                                                                                                                         | ...                                                                                                                                                                                                         | ...                  | ...             | ...                 | ...           |
*/
CREATE TABLE Series (
    SeriesCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'AG.AGR.TRAC.NO'</example>
    Topic TEXT NOT NULL,
        -- <example>'Economic Policy & Debt: Balance of payments: Capital & financial account'</example>
    IndicatorName TEXT NOT NULL,
        -- <example>'Foreign direct investment, net (BoP, current US$)'</example>
    ShortDefinition TEXT NOT NULL,
        -- <example>''</example>
    LongDefinition TEXT NOT NULL,
        -- <example>'Foreign direct investment are the net inflows of i...estor. It is the sum of equity capital, reinvestme'</example>
    UnitOfMeasure TEXT NOT NULL,
        -- <values>{'%', '', '2005 PPP $', '2011 PPP $', '`'}</values>
    Periodicity TEXT NOT NULL,
        -- <values>{'Annual'}</values>
    BasePeriod TEXT NOT NULL,
        -- <values>{'', '1990', '2000', '2004-06', '2005', '2010', '2011', 'varies by country'}</values>
    OtherNotes INTEGER NULL,
    AggregationMethod TEXT NOT NULL,
        -- <values>{'', 'Gap-filled total', 'Linear mixed-effect model estimates', 'Median', 'Sum', 'Unweighted average', 'Weighted average'}</values>
    LimitationsAndExceptions TEXT NOT NULL,
        -- <example>''</example>
    NotesFromOriginalSource TEXT NOT NULL,
        -- <values>{'', 'All surveys were administered using the Enterprise...which can be found from www.enterprisesurveys.org.', 'All the indicators refer to expenditures by financ...re the fiscal year begins in July, expenditure dat', 'Depending on the source and means of monitoring, d...s. See listed source for country-specific details.', 'Estimates are presented with uncertainty intervals...y produced by simulations). For more detailed info', 'Estimates of maternal mortality are presented alon...babilistic evaluation of the uncertainty attributa', 'In some cases, the sum of public and private expen...s a financing source. When the number is smaller t', 'Most surveys were administered using the Enterpris...he global Enterprise Surveys methodology, plus Afg', 'PPP series resulting from the 2005 International c...ors refer to expenditures by financing agent excep', 'SIPRI statistical data on arms transfers relates t...ends, SIPRI has developed a unique system to measu', 'The 2007-2011 refugee population category also inc...nd includes groups of persons who are outside thei'}</values>
    GeneralComments TEXT NOT NULL,
        -- <example>'Note: Data are based on the sixth edition of the I...its and debits to net acquisition of financial ass'</example>
    Source TEXT NOT NULL,
        -- <example>'International Monetary Fund, Balance of Payments Statistics Yearbook and data files.'</example>
    StatisticalConceptAndMethodology TEXT NOT NULL,
        -- <example>''</example>
    DevelopmentRelevance TEXT NOT NULL,
        -- <example>''</example>
    RelatedSourceLinks TEXT NOT NULL,
        -- <values>{'', 'World Bank, PovcalNet: an online poverty analysis ...http://iresearch.worldbank.org/PovcalNet/index.htm'}</values>
    OtherWebLinks INTEGER NULL,
    RelatedIndicators INTEGER NULL,
    LicenseType TEXT NOT NULL
        -- <values>{'Open', 'Restricted'}</values>
);

/*
Schema: NULLTable: SeriesNotes
Rows: 369
Sample rows:
| Seriescode        | Year   | Description                                                                                                 |
|-------------------|--------|-------------------------------------------------------------------------------------------------------------|
| SP.ADO.TFRT       | YR1960 | Interpolated using data for 1957 and 1962.                                                                  |
| SP.DYN.AMRT.FE    | YR1960 | Interpolated using data for 1957 and 1962, if the data source is United Nations World Population Prospects. |
| SP.DYN.AMRT.MA    | YR1960 | Interpolated using data for 1957 and 1962, if the data source is United Nations World Population Prospects. |
| SP.DYN.TO65.FE.ZS | YR1960 | Interpolated using data for 1957 and 1962.                                                                  |
| SP.DYN.TO65.MA.ZS | YR1960 | Interpolated using data for 1957 and 1962.                                                                  |
| ...               | ...    | ...                                                                                                         |
*/
CREATE TABLE SeriesNotes (
    Seriescode TEXT NOT NULL,
        -- <example>'DT.DOD.PVLX.CD'</example>
        -- <fk> -> Series.SeriesCode</fk>
    Year TEXT NOT NULL,
        -- <example>'YR2014'</example>
    Description TEXT NOT NULL,
        -- <example>'Interpolated using data for 1957 and 1962.'</example>
    PRIMARY KEY (Seriescode, Year),
    FOREIGN KEY (Seriescode) REFERENCES Series(SeriesCode)
);
```