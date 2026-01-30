```mermaid
erDiagram
    Member {
        table member "Core member profile, contact info, officer position, shirt size, and references to major and ZIP code."
    }
    Event {
        table event "Event master record including name, schedule, type, location, notes, and lifecycle status."
    }
    Budget {
        table budget "Per-event budget categories with amounts, spend, remaining, and event linkage."
    }
    Expense {
        table expense "Expense details including description, date, cost, approval flag, and links to submitting member and funded budget."
    }
    Income {
        table income "Income entries with date received, amount, source, notes, and recording member."
    }
    Major {
        table major "Lookup of academic majors and their affiliated department and college."
    }
    ZipCode {
        table zip_code "ZIP code directory with type, city, county, state, and abbreviation."
    }
    Event }o--o{ Member : "EventAttendance" %% FROM event JOIN attendance ON attendance.link_to_event = event.event_id JOIN member ON member.member_id = attendance.link_to_member
    Event |o--|{ Budget : "EventBudgeting" %% FROM event JOIN budget ON budget.link_to_event = event.event_id
    Budget |o--|{ Expense : "BudgetExpenses" %% FROM budget JOIN expense ON expense.link_to_budget = budget.budget_id
    Member |o--|{ Expense : "MemberExpenseSubmission" %% FROM member JOIN expense ON expense.link_to_member = member.member_id
    Member |o--|{ Income : "MemberIncomeCollection" %% FROM member JOIN income ON income.link_to_member = member.member_id
    Major |o--o{ Member : "MemberMajor" %% FROM member JOIN major ON major.major_id = member.link_to_major
    ZipCode |o--o{ Member : "MemberLocation" %% FROM member JOIN zip_code ON zip_code.zip_code = member.zip
```