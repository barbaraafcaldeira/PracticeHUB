# Final Dataset Assumptions

The v2.1 dataset represents a fictional capacity-constrained English GP practice. Its parameters are disclosed modelling assumptions, not measured NHS-wide benchmarks. The previous dataset is retained in dated data/archives folders.

## Scale

- Registered patients: 10,000.
- Historical period: 36 months, from January 2023 to December 2025.
- Clinical workforce: 5 GPs, 3.8 total FTE, with weekday patterns consistent with FTE.
- The 36 monthly KPI rows are recalculated from source records.
- Reporting cutoff: 31 December 2025, 23:59. This is a historical position, not current live demand.
- Fixed cohort: 10,000 patients already registered at the start; ages are measured at the reporting cutoff. Births, deaths and list turnover are not simulated.

## Realism Principles

- Every request has one eConsult, including reception-assisted telephone requests. Original contact channels remain available.
- Intake routes: 48% telephone, 47% online, 5% reception (sampling probabilities, not exact quotas).
- Intake is generated in three separate streams, with baseline means per open weekday of 72 same-day GP, 39 routine GP and 39 other-service requests. GP share and same-day/routine proportions are not fixed quotas.
- Same-day monthly multipliers, January through December: 1.40, 1.32, 1.15, 1.00, 0.91, 0.84, 0.80, 0.86, 1.05, 1.10, 1.22, 1.38. These represent acute winter pressure.
- Routine monthly multipliers: 0.92, 1.00, 1.18, 1.14, 1.10, 1.03, 0.87, 0.83, 1.20, 1.15, 1.02, 0.88. These represent spring/autumn review and follow-up cycles rather than a copy of acute demand.
- Other-service monthly multipliers: 1.02, 0.98, 1.04, 0.96, 1.06, 1.02, 0.96, 1.04, 1.10, 1.08, 0.97, 0.94. Each pathway also has independent year/month, weekly and daily stochastic variation. Same-day demand has a stronger Monday effect; routine requests have a modest Tuesday/Wednesday effect. All draws are reproducible from the seed, not edited monthly totals.
- The latest capacity-constrained scenario supersedes the earlier forced 60% summer utilisation requirement. Summer request demand falls; utilisation is calculated from allocation rather than assigned percentages.
- Sessions: 09:00-12:30 and 14:00-17:30; 12 patient slots of 15 minutes and 30 minutes non-slot time per session. Seven slots are same-day and five routine. Approximately 1.5% are blocked.
- Weekends and England bank holidays in 2023-2025 are closed, including the 2023 coronation holiday. Explicit annual leave reduces sessions. Leave allowance is 25 days per year prorated to scheduled weekdays; no locum cover or sickness is modelled.
- Same-day requests require a slot that day; routine requests require a slot on one of the next 14 calendar days. Allocation searches suitable slots in timestamp order after triage/contact, with at least 15 minutes before the slot starts. Routine/same-day slots are not automatically interchangeable. A patient cannot hold two simultaneous appointments.
- Diversions require a genuine shortage of suitable slots at the decision time. Replay validation checks this. Spare routine slots can coexist with same-day shortfalls; the separate appointment-type figures expose this mismatch.
- Capacity destinations: PCN support (65%) or NHS 111 (35%). PCN booking is confirmed in 45% of sampled PCN diversions; other external receipt is unknown. These are fictional pathway assumptions, not clinical referral advice.
- Appropriate signposting is separate from capacity diversion. Self-care advice is the only automatically marked resolved-without-appointment outcome; external advice does not prove care was received.
- Routine requests whose deadlines exceed the reporting cutoff and have no available in-window booking remain pending, not overdue unmet need. The simulation does not claim later outcomes.
- Outbound contact: up to three attempts, 15 minutes apart after triage. Answered calls may communicate any outcome. If contact fails, an SMS notification is recorded, with receipt unknown.
- Attendance sampling: 92% attended, 4% DNA, 3% patient cancellation, 1% practice cancellation. Cancellations occur 1-10 minutes before the slot and are explicitly late, with no simulated refill. Early cancellations/rebooking and requests following a cancellation are outside this version.
- Booked-slot utilisation means slots allocated at least once / eligible bookable slots. It includes late cancellations and DNAs and must not be interpreted as delivered consultations. Attendance and cancellation measures are shown separately.
- Other telephone workload has mean 240 calls per open weekday before seasonal effects; morning call volume is higher. Abandoned callers have unknown appointment intent and patient identity. Hourly volumes and waits are derived from individual events, not generated independently.
- Repeat contact probabilities: 28% following capacity diversion, 5% otherwise. Repeated contacts retain the original request ID.
- Complaints have recorded trigger types and timestamps. Eligible triggers are capacity-related signposting (base probability 3%), practice cancellation (13%), routine waits of at least seven days (1.4%, rising to 2.5% at eleven days), repeat GP contact (1.4%), and unsuccessful outbound contact (2.5%, classified as communication rather than appointment access). A request can produce at most one complaint. Trigger eligibility is assessed against actual generated events.
- Complaint propensities vary independently by month, with a reporting delay of 1-35 days after the trigger. Reports after the historical cutoff are not included. Complaints therefore need not follow the request curve in the same month, but remain related to actual problems. These probabilities and delays are fictional assumptions, not NHS prevalence estimates or measured behavioural effects.
- Request audit logs contain intake facts, triage, suitable-capacity searches, contact attempts and notification evidence. Size is derived from these event records; repeated filler labels/notes have been removed.
- Forecasts and evaluation tables remain empty for the user's later analysis. Model scores have not been used to tune these parameters.

## Validation and Limitations

The JSON validation reports contain row counts, CSV SHA-256 hashes, byte sizes and zero-violation checks for keys, identity consistency, chronology, slot suitability, deadlines, holidays, leave, aggregates and diversion-time capacity. Winter GP requests must exceed summer GP requests on average within each year. Missing values mean not applicable or genuinely unknown; they are not blindly replaced with zero.

Unmet GP need counts recorded requests lacking a suitable internal or confirmed external booking, plus practice-cancelled appointments. It does not establish that the patient received no care elsewhere. Pending requests are separate. Monthly distinct patient counts must not be summed to obtain annual unique patients. Only people who contact the surgery are observable.

Session-cost assumptions, triage-team staffing, uncertainty estimates and forecasting are not yet implemented. Extra-capacity recommendations must follow the user's analysis and account for possible redistribution between same-day and routine slots before purchasing extra sessions.
