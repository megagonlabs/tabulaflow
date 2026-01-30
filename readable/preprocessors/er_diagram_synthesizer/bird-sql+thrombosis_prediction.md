```mermaid
erDiagram
    Patient {
        table Patient "One row per patient with sex, birthdate, admission status, and diagnosis summary."
    }
    Examination {
        table Examination "One row per patient examination with examination date and various examination results/flags."
    }
    LabResult {
        table Laboratory "One row per patient per date holding a lab panel; composite primary key (ID, Date)."
    }
    Patient }o--o| Examination : "PatientHasExaminations"
    Patient }o--|| LabResult : "PatientHasLabResults"
    Examination |o--o{ LabResult : "SameDayAssessment"
```