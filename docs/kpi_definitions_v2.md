# V2 KPI Definitions

All figures are synthetic. The reporting cutoff is 31 December 2025, 23:59, not the computer's current date.

| Measure | Definition |
|---|---|
| gp_requests | Distinct requests clinically triaged as requiring GP care; one eConsult per request. |
| gp_slots_booked | Distinct slots allocated in the appointment's scheduled month, including DNAs and late cancellations. |
| gp_slot_utilisation_pct | Allocated slots / bookable patient-facing GP slots x 100. This is booking utilisation, not attended capacity. |
| capacity_diverted_requests | GP requests signposted because suitable internal capacity was exhausted; includes confirmed external bookings. |
| capacity_diverted_patients | Distinct patients with capacity-diverted requests in the request month. |
| unmet_gp_requests | Requests diverted without a confirmed external appointment, plus practice-cancelled bookings, as known at the cutoff. Other-service receipt can be unknown. |
| patients_without_appointment | Distinct patients associated with the unmet requests above, not the number of calls. |
| pending_gp_requests | Unallocated GP requests whose required-by date is after the cutoff. |
| gp_requests_allocated_on_time_pct | Eligible requests with suitable internal or confirmed external bookings by the deadline / decided GP requests x 100; pending requests excluded. Practice-cancelled bookings do not count as fulfilled. Patient cancellations are reported separately and count as an initially provided timely allocation. |
| appropriate_signposted_requests | Requests where another service was the appropriate pathway; excluded from GP demand. |
| confirmed_external_bookings | Confirmed PCN bookings, rather than advice to seek another service. |
| morning_call_gp_requests | Distinct GP request episodes with an identified appointment-intent call at 08:00 <= time < 10:00, grouped by request month. |
| morning_call_unallocated_patients | Distinct unmet-request patients linked to such morning calls, based on the final cutoff outcome, not necessarily the status during the call. |
| econsult_online_unallocated_patients | Distinct unmet-request patients whose original intake was Online; assisted telephone eConsults remain in their original channel. |
| average_wait_seconds | Mean wait per incoming call across answered and abandoned calls, calculated from individual events. It is not average speed of answer for answered calls only. |
| appointments_booked_after_outgoing_call | Internal allocations associated with successful follow-up calls. A booking notified by SMS after failed calls is excluded from this measure. |
| access_complaints | Count of appointment-access complaints by complaint month, separately from request and booking cohorts. |

The original 26 monthly KPI fields are retained for existing pandas scripts, with additional request and shortfall fields. The invalid sum of bookings, GP-recommended eConsults and complaints is removed.

Request measures use intake month; capacity and bookings use appointment/session month; calls and complaints use their event month. Do not subtract monthly bookings from monthly requests as if they were identical cohorts: routine bookings may cross months. Use the request outcomes and appropriate same-day/routine matching for shortfalls.

The full view and physical table have identical column order and calculations. Views reflect source-table changes immediately; the physical table/CSV requires refresh. Do not add unique patient counts across months or channels. Use COUNT(DISTINCT patient_id) over the desired period and request conditions.

For forecasting use clinically indicated request episodes, not all eConsults, contacts or complaints. Neither forecasts nor an additional-session recommendation has been generated. Compare suitable capacity by date and appointment type, consider redistributing slots, then assess additional sessions and cost under explicit assumptions.

## Chart Review v2.1

Chart 5 groups all received eConsult requests into internal GP bookings, appropriate signposting and capacity-related signposting. Pending requests are excluded from the three areas and disclosed below the plot. Signposting is a routing decision, not evidence that an external appointment was booked or attended. These three categories plus pending reconcile to received requests.

Chart 7 uses the combined all-channel distinct-patient unmet measure, not a sum of telephone and online unique-patient counts. Access complaints are shown by recorded trigger in complaint month. Shared causes can legitimately produce correlation; different curves are not an accuracy requirement.

Calendar features and appointment-type capacity/outcome breakdowns are exported alongside the charts. Capacity panels use scheduled appointment month; request trends use request month, so cross-month routine bookings must not be treated as a reconciliation error.
