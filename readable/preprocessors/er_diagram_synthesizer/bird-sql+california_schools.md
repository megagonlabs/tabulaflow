```mermaid
erDiagram
    Institution {
        table schools "Core institution master data: identification, status, governance types, grades, contact, website, and geolocation."
    }
    FRPMSnapshot2014_2015 {
        table frpm "2014–2015 FRPM enrollment and eligibility metrics with some redundant identifying fields; one row per CDSCode."
    }
    SATResult {
        table satscores "SAT participation counts and average section scores; rtype indicates school ('S') vs district ('D') level; one row per CDSCode."
    }
    Institution |o--|| FRPMSnapshot2014_2015 : "InstitutionHasFRPMSnapshot2014_2015" %% FROM schools s JOIN frpm f ON f.CDSCode = s.CDSCode
    Institution |o--|| SATResult : "InstitutionHasSATResult" %% FROM schools s JOIN satscores sat ON sat.cds = s.CDSCode
```