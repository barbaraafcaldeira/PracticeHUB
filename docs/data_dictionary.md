# PracticeHUB V2 Data Dictionary

Generated from the actual schema. IDs are synthetic; all activity is fictional.
Nullable fields represent unknown or not-applicable values. Dates are historical 2023-2025; age_band is measured at the reporting cutoff.
Read kpi_definitions_v2.md for derived measures and final_dataset_assumptions.md for sampling assumptions.

## patients

| Field | Type | Required | Key / reference |
|---|---|---|---|
| patient_id | INTEGER | Yes | PK |
| nhs_number_hash | VARCHAR(64) | Yes |  |
| sex | VARCHAR(20) | Yes |  |
| date_of_birth | DATE | Yes |  |
| age_band | VARCHAR(20) | Yes |  |
| postcode_district | VARCHAR(10) | Yes |  |
| registration_date | DATE | Yes |  |
| is_active | INTEGER | Yes |  |

## clinicians

| Field | Type | Required | Key / reference |
|---|---|---|---|
| clinician_id | INTEGER | Yes | PK |
| clinician_name | VARCHAR(100) | Yes |  |
| role | VARCHAR(50) | Yes |  |
| fte | REAL | Yes |  |
| working_pattern | VARCHAR(100) | Yes |  |
| usual_session_minutes | INTEGER | Yes |  |
| is_gp | INTEGER | Yes |  |
| active_from | DATE | Yes |  |
| active_to | DATE | No |  |

## practice_calendar

| Field | Type | Required | Key / reference |
|---|---|---|---|
| calendar_date | DATE | Yes | PK |
| is_open | INTEGER | Yes |  |
| closure_reason | VARCHAR(100) | No |  |
| seasonal_factor | REAL | Yes |  |

## clinician_absences

| Field | Type | Required | Key / reference |
|---|---|---|---|
| absence_id | INTEGER | Yes | PK |
| clinician_id | INTEGER | Yes | FK to clinicians.clinician_id |
| absence_date | DATE | Yes |  |
| absence_reason | VARCHAR(50) | Yes |  |

## clinic_sessions

| Field | Type | Required | Key / reference |
|---|---|---|---|
| session_id | INTEGER | Yes | PK |
| clinician_id | INTEGER | Yes | FK to clinicians.clinician_id |
| session_date | DATE | Yes |  |
| session_type | VARCHAR(20) | Yes |  |
| start_time | VARCHAR(8) | Yes |  |
| end_time | VARCHAR(8) | Yes |  |
| planned_slots | INTEGER | Yes |  |
| session_minutes | INTEGER | Yes |  |
| delivery_mode | VARCHAR(30) | Yes |  |

## appointment_slots

| Field | Type | Required | Key / reference |
|---|---|---|---|
| slot_id | INTEGER | Yes | PK |
| session_id | INTEGER | Yes | FK to clinic_sessions.session_id |
| slot_start_datetime | DATETIME | Yes |  |
| slot_end_datetime | DATETIME | Yes |  |
| slot_type | VARCHAR(30) | Yes |  |
| slot_status | VARCHAR(30) | Yes |  |
| is_bookable | INTEGER | Yes |  |

## appointment_requests

| Field | Type | Required | Key / reference |
|---|---|---|---|
| request_id | INTEGER | Yes | PK |
| patient_id | INTEGER | Yes | FK to patients.patient_id |
| requested_datetime | DATETIME | Yes |  |
| original_contact_channel | VARCHAR(30) | Yes |  |
| required_clinician_type | VARCHAR(30) | Yes |  |
| required_appointment_type | VARCHAR(30) | No |  |
| required_by_datetime | DATETIME | No |  |
| request_outcome | VARCHAR(50) | Yes |  |
| non_allocation_reason | VARCHAR(100) | No |  |
| external_care_status | VARCHAR(50) | Yes |  |
| external_appointment_datetime | DATETIME | No |  |

## econsult_requests

| Field | Type | Required | Key / reference |
|---|---|---|---|
| econsult_id | INTEGER | Yes | PK |
| request_id | INTEGER | Yes | FK to appointment_requests.request_id |
| patient_id | INTEGER | Yes | FK to patients.patient_id |
| submitted_datetime | DATETIME | Yes |  |
| original_contact_channel | VARCHAR(30) | Yes |  |
| submitted_by_role | VARCHAR(30) | Yes |  |
| category | VARCHAR(50) | Yes |  |
| urgency_level | VARCHAR(20) | Yes |  |
| triaged_datetime | DATETIME | Yes |  |
| triage_outcome | VARCHAR(50) | Yes |  |
| gp_appointment_recommended | INTEGER | Yes |  |
| resolved_without_appointment | INTEGER | Yes |  |
| signposting_reason | VARCHAR(100) | No |  |
| signposting_destination | VARCHAR(80) | No |  |

## appointments

| Field | Type | Required | Key / reference |
|---|---|---|---|
| appointment_id | INTEGER | Yes | PK |
| slot_id | INTEGER | Yes | FK to appointment_slots.slot_id |
| patient_id | INTEGER | Yes | FK to patients.patient_id |
| request_id | INTEGER | Yes | FK to appointment_requests.request_id |
| booked_datetime | DATETIME | Yes |  |
| booking_channel | VARCHAR(40) | Yes |  |
| appointment_reason | VARCHAR(50) | Yes |  |
| attendance_status | VARCHAR(40) | Yes |  |
| outcome | VARCHAR(80) | Yes |  |
| econsult_id | INTEGER | Yes | FK to econsult_requests.econsult_id |
| cancelled_datetime | DATETIME | No |  |

## incoming_call_volumes

| Field | Type | Required | Key / reference |
|---|---|---|---|
| incoming_call_volume_id | INTEGER | Yes | PK |
| call_date | DATE | Yes |  |
| hour_start | INTEGER | Yes |  |
| calls_offered | INTEGER | Yes |  |
| calls_answered | INTEGER | Yes |  |
| calls_abandoned | INTEGER | Yes |  |
| average_wait_seconds | REAL | Yes |  |

## incoming_call_events

| Field | Type | Required | Key / reference |
|---|---|---|---|
| incoming_call_event_id | INTEGER | Yes | PK |
| incoming_call_volume_id | INTEGER | Yes | FK to incoming_call_volumes.incoming_call_volume_id |
| patient_id | INTEGER | No | FK to patients.patient_id |
| request_id | INTEGER | No | FK to appointment_requests.request_id |
| call_datetime | DATETIME | Yes |  |
| queue_name | VARCHAR(50) | Yes |  |
| call_reason | VARCHAR(60) | Yes |  |
| call_outcome | VARCHAR(20) | Yes |  |
| wait_seconds | INTEGER | Yes |  |
| talk_seconds | INTEGER | Yes |  |
| booking_intent | INTEGER | No |  |
| appointment_booked | INTEGER | Yes |  |
| allocation_status_at_call | VARCHAR(50) | Yes |  |
| synthetic_call_reference | VARCHAR(64) | Yes |  |

## outgoing_call_attempts

| Field | Type | Required | Key / reference |
|---|---|---|---|
| outgoing_call_attempt_id | INTEGER | Yes | PK |
| patient_id | INTEGER | Yes | FK to patients.patient_id |
| request_id | INTEGER | Yes | FK to appointment_requests.request_id |
| econsult_id | INTEGER | Yes | FK to econsult_requests.econsult_id |
| appointment_id | INTEGER | No | FK to appointments.appointment_id |
| attempt_datetime | DATETIME | Yes |  |
| attempt_number | INTEGER | Yes |  |
| call_reason | VARCHAR(60) | Yes |  |
| call_outcome | VARCHAR(30) | Yes |  |
| appointment_booked_after_call | INTEGER | Yes |  |

## patient_complaints

| Field | Type | Required | Key / reference |
|---|---|---|---|
| complaint_id | INTEGER | Yes | PK |
| patient_id | INTEGER | Yes | FK to patients.patient_id |
| request_id | INTEGER | Yes | FK to appointment_requests.request_id |
| complaint_date | DATE | Yes |  |
| complaint_category | VARCHAR(50) | Yes |  |
| complaint_trigger | VARCHAR(80) | Yes |  |
| trigger_datetime | DATETIME | Yes |  |
| complaint_text_summary | VARCHAR(255) | Yes |  |
| related_appointment_id | INTEGER | No | FK to appointments.appointment_id |
| related_econsult_id | INTEGER | Yes | FK to econsult_requests.econsult_id |
| severity | VARCHAR(20) | Yes |  |
| status | VARCHAR(20) | Yes |  |

## appointment_activity_log

| Field | Type | Required | Key / reference |
|---|---|---|---|
| appointment_activity_log_id | INTEGER | Yes | PK |
| appointment_id | INTEGER | Yes | FK to appointments.appointment_id |
| event_datetime | DATETIME | Yes |  |
| event_type | VARCHAR(60) | Yes |  |
| event_channel | VARCHAR(50) | Yes |  |
| event_actor | VARCHAR(80) | Yes |  |

## request_activity_log

| Field | Type | Required | Key / reference |
|---|---|---|---|
| request_activity_log_id | INTEGER | Yes | PK |
| request_id | INTEGER | Yes | FK to appointment_requests.request_id |
| event_datetime | DATETIME | Yes |  |
| event_type | VARCHAR(60) | Yes |  |
| event_actor | VARCHAR(80) | Yes |  |
| event_payload | TEXT | Yes |  |

## monthly_kpis

| Field | Type | Required | Key / reference |
|---|---|---|---|
| kpi_month | VARCHAR(7) | Yes | PK |
| registered_patients | INTEGER | No |  |
| gp_sessions | INTEGER | No |  |
| gp_slots_total | INTEGER | No |  |
| gp_slots_bookable | INTEGER | No |  |
| gp_slots_booked | INTEGER | No |  |
| gp_slot_utilisation_pct | REAL | No |  |
| appointments_attended | INTEGER | No |  |
| appointments_dna | INTEGER | No |  |
| dna_rate_pct | REAL | No |  |
| appointments_cancelled | INTEGER | No |  |
| econsult_requests | INTEGER | No |  |
| econsults_gp_recommended | INTEGER | No |  |
| econsults_resolved_without_appointment | INTEGER | No |  |
| incoming_calls_offered | INTEGER | No |  |
| incoming_calls_answered | INTEGER | No |  |
| incoming_calls_abandoned | INTEGER | No |  |
| incoming_call_answer_rate_pct | REAL | No |  |
| average_wait_seconds | REAL | No |  |
| outgoing_call_attempts | INTEGER | No |  |
| outgoing_calls_answered | INTEGER | No |  |
| outgoing_call_answer_rate_pct | REAL | No |  |
| appointments_booked_after_outgoing_call | INTEGER | No |  |
| access_complaints | INTEGER | No |  |
| access_complaints_per_1000_patients | REAL | No |  |
| synthetic_data_label | VARCHAR(100) | No |  |
| gp_requests | INTEGER | No |  |
| same_day_gp_requests | INTEGER | No |  |
| routine_gp_requests | INTEGER | No |  |
| capacity_diverted_requests | INTEGER | No |  |
| capacity_diverted_patients | INTEGER | No |  |
| unmet_gp_requests | INTEGER | No |  |
| patients_without_appointment | INTEGER | No |  |
| pending_gp_requests | INTEGER | No |  |
| gp_requests_allocated_on_time_pct | REAL | No |  |
| appropriate_signposted_requests | INTEGER | No |  |
| confirmed_external_bookings | INTEGER | No |  |
| morning_call_gp_requests | INTEGER | No |  |
| morning_call_unallocated_patients | INTEGER | No |  |
| econsult_online_unallocated_patients | INTEGER | No |  |
| same_day_capacity_diverted | INTEGER | No |  |
| routine_capacity_diverted | INTEGER | No |  |

