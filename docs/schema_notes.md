# PracticeHUB Relational Schema Notes

V2 UPDATE: the current request-led schema and all fields are documented in data_dictionary.md and erd.md. The older descriptive notes below refer to v1 and are retained as design history. In v2 all bookings require a request and eConsult, signposting reasons are explicit, only five GP clinicians are included, and monthly_kpis is populated. The schema includes deliberate derived/audit reporting structures; it should not be presented as a strict 3NF design throughout without a functional-dependency review.

## Core Design

The schema separates appointment capacity, booked appointment activity, online consultation demand, telephone workload, and complaints. This matters because the assignment rules say these concepts must not be treated as identical measures of appointment demand.

## Main Tables

| Table | Purpose |
|---|---|
| `patients` | Synthetic registered patients used to support age-band and demographic analysis. |
| `clinicians` | GP and non-GP clinical staff, including working pattern metadata. |
| `clinic_sessions` | AM/PM/evening clinic sessions delivered by clinicians. |
| `appointment_slots` | Individual appointment slots created within clinic sessions. |
| `appointments` | Booking, attendance, cancellation, and DNA outcomes for slots. |
| `econsult_requests` | Online consultation requests submitted by patients. |
| `incoming_call_volumes` | Aggregated incoming telephone activity by date and hour. |
| `incoming_call_events` | Individual synthetic incoming call events used to support workload analysis and dataset scale. |
| `outgoing_call_attempts` | Individual outgoing call attempts, optionally linked to an eConsult or appointment. |
| `patient_complaints` | Appointment-access and other complaints. |
| `appointment_activity_log` | Synthetic EMIS-style appointment audit events such as booking, reminders, cancellations, and completion. |
| `monthly_kpis` | Derived monthly management KPI dataset for dashboard reporting. |

## Important Relationship Rules

The unused `forecast_results` and `model_evaluations` tables were removed on 18 October 2026. Forecast outputs and evaluation metrics remain in model-result files. Historical validation reports describe the earlier schema. MySQL includes separate monthly forecast input and correction tables in addition to the generated operational schema.

- A slot may exist without a booked appointment.
- An appointment must belong to a slot.
- An eConsult may lead to self-care advice, admin action, pharmacist/nurse triage, GP appointment recommendation, urgent escalation, or no further action.
- An eConsult is not automatically GP appointment demand.
- An outgoing call attempt may be linked to an eConsult, an appointment, both, or neither.
- Multiple outgoing attempts may occur before contact is made.
- A successful outgoing call does not automatically mean an appointment was booked.
- Complaints are indirect access-pressure signals, not direct demand observations.
- Operational event logs increase dataset size without inflating appointment demand.

## Monthly KPI Dataset

`monthly_kpis` is a derived dataset structure for the management overview dashboard. At this stage, the fields are created but the rows are left empty by default because the source tables are still being expanded.

When the raw data model is final, run the generator with `--populate-kpis` to calculate rows from the relational tables.

The KPI dataset includes:

- Registered patients.
- GP sessions, GP slots, bookable slots, booked slots, and slot utilisation.
- Attended, DNA, and cancelled GP appointments.
- eConsult requests, GP appointment recommendations, and requests resolved without appointment.
- Incoming call offered, answered, abandoned, answer rate, and average wait time.
- Outgoing call attempts, answered attempts, answer rate, and appointments booked after outgoing calls.
- Appointment-access complaints and complaints per 1,000 registered patients.

## Development Database

SQLite is the first implementation target because it is reproducible and easy to package with Streamlit. The table design uses simple relational patterns that can later be migrated to MySQL.

## Final Dataset Size

The small dataset is only for proving the data model. The final generator profile should produce at least 100MB across the SQLite database and/or CSV exports by scaling:

- Patient count to 10,000.
- History to 36 months.
- Appointment slots to realistic working-session volumes.
- Incoming call records to hourly daily observations.
- Outgoing call attempts to individual call-level records.
- Individual incoming call events and appointment activity logs to realistic operational-system detail.
