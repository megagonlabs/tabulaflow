```mermaid
erDiagram
    EducationOrganization {
        table schools "Master reference of organizations; includes both district/COE rows (School is NULL) and school sites with detailed profile and contact fields."
    }
    FRPMStatistics {
        table frpm "Per-organization FRPM metrics for a given academic year; contains enrollment, free meal counts, FRPM counts, and provision/charter indicators."
    }
    SATScoreSummary {
        table satscores "Per-organization SAT summary (one row per CDS code in this dataset) including participants, average Reading/Math/Writing scores, and count scoring ≥1500."
    }

    %% FROM frpm JOIN schools ON frpm.CDSCode = schools.CDSCode
    EducationOrganization |o--|{ FRPMStatistics : "OrganizationHasFRPMStatistics"

    %% FROM satscores JOIN schools ON satscores.cds = schools.CDSCode
    EducationOrganization |o--|| SATScoreSummary : "OrganizationHasSATScoreSummary"
```