"""Request-led fictional practice simulation and portable relational schema."""

import calendar
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta

SEASONS = [1.26, 1.20, 1.10, 1.02, .98, .90, .82, .80, 1.02, 1.12, 1.20, 1.27]
PATHWAY_SEASONS = {
    "Same-day GP": [1.40,1.32,1.15,1.00,.91,.84,.80,.86,1.05,1.10,1.22,1.38],
    "Routine GP": [.92,1.00,1.18,1.14,1.10,1.03,.87,.83,1.20,1.15,1.02,.88],
    "Other service": [1.02,.98,1.04,.96,1.06,1.02,.96,1.04,1.10,1.08,.97,.94]
}
PATHWAY_BASE = {"Same-day GP":72,"Routine GP":39,"Other service":39}


def intake_schedule(open_days, seed, scale):
    """Independent pathway streams with distinct seasonal and weekday assumptions."""
    rng=random.Random(seed+201)
    monthly={}
    weekly={}
    latent={kind:0.0 for kind in PATHWAY_BASE}
    result={}
    for day in open_days:
        month=day.strftime("%Y-%m")
        week=day.isocalendar()[:2]
        row={}
        for kind,base in PATHWAY_BASE.items():
            if (month,kind) not in monthly:
                latent[kind]=.4*latent[kind]+rng.gauss(0,.10 if kind=="Same-day GP" else .13)
                monthly[(month,kind)]=math.exp(latent[kind])
            if (week,kind) not in weekly:
                weekly[(week,kind)]=max(.70,rng.gauss(1,.08))
            weekday=([1.22,1.02,.97,.98,.92] if kind=="Same-day GP" else
                     [1.00,1.08,1.08,1.00,.92] if kind=="Routine GP" else [1.10,1.02,1.00,.97,.95])[day.weekday()]
            mean=base*PATHWAY_SEASONS[kind][day.month-1]*monthly[(month,kind)]*weekly[(week,kind)]*weekday*scale
            row[kind]=max(0,round(rng.gauss(mean,math.sqrt(mean)+.06*mean)))
        result[day]=row
    return result

# Parent tables precede children. Definitions are shared by SQLite and MySQL.
TABLES = {
    "patients": """patient_id INTEGER PRIMARY KEY, nhs_number_hash VARCHAR(64) NOT NULL UNIQUE,
        sex VARCHAR(20) NOT NULL, date_of_birth DATE NOT NULL, age_band VARCHAR(20) NOT NULL,
        postcode_district VARCHAR(10) NOT NULL, registration_date DATE NOT NULL,
        is_active INTEGER NOT NULL CHECK(is_active IN (0,1))""",
    "clinicians": """clinician_id INTEGER PRIMARY KEY, clinician_name VARCHAR(100) NOT NULL,
        role VARCHAR(50) NOT NULL, fte REAL NOT NULL, working_pattern VARCHAR(100) NOT NULL,
        usual_session_minutes INTEGER NOT NULL, is_gp INTEGER NOT NULL,
        active_from DATE NOT NULL, active_to DATE""",
    "practice_calendar": """calendar_date DATE PRIMARY KEY, is_open INTEGER NOT NULL,
        closure_reason VARCHAR(100), seasonal_factor REAL NOT NULL""",
    "clinician_absences": """absence_id INTEGER PRIMARY KEY, clinician_id INTEGER NOT NULL,
        absence_date DATE NOT NULL, absence_reason VARCHAR(50) NOT NULL,
        FOREIGN KEY(clinician_id) REFERENCES clinicians(clinician_id)""",
    "clinic_sessions": """session_id INTEGER PRIMARY KEY, clinician_id INTEGER NOT NULL,
        session_date DATE NOT NULL, session_type VARCHAR(20) NOT NULL,
        start_time VARCHAR(8) NOT NULL, end_time VARCHAR(8) NOT NULL,
        planned_slots INTEGER NOT NULL, session_minutes INTEGER NOT NULL,
        delivery_mode VARCHAR(30) NOT NULL, FOREIGN KEY(clinician_id) REFERENCES clinicians(clinician_id)""",
    "appointment_slots": """slot_id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL,
        slot_start_datetime DATETIME NOT NULL, slot_end_datetime DATETIME NOT NULL,
        slot_type VARCHAR(30) NOT NULL, slot_status VARCHAR(30) NOT NULL,
        is_bookable INTEGER NOT NULL CHECK(is_bookable IN (0,1)),
        FOREIGN KEY(session_id) REFERENCES clinic_sessions(session_id)""",
    "appointment_requests": """request_id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL,
        requested_datetime DATETIME NOT NULL, original_contact_channel VARCHAR(30) NOT NULL,
        required_clinician_type VARCHAR(30) NOT NULL, required_appointment_type VARCHAR(30),
        required_by_datetime DATETIME, request_outcome VARCHAR(50) NOT NULL,
        non_allocation_reason VARCHAR(100), external_care_status VARCHAR(50) NOT NULL,
        external_appointment_datetime DATETIME, FOREIGN KEY(patient_id) REFERENCES patients(patient_id)""",
    "econsult_requests": """econsult_id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL UNIQUE,
        patient_id INTEGER NOT NULL, submitted_datetime DATETIME NOT NULL,
        original_contact_channel VARCHAR(30) NOT NULL, submitted_by_role VARCHAR(30) NOT NULL,
        category VARCHAR(50) NOT NULL, urgency_level VARCHAR(20) NOT NULL,
        triaged_datetime DATETIME NOT NULL, triage_outcome VARCHAR(50) NOT NULL,
        gp_appointment_recommended INTEGER NOT NULL, resolved_without_appointment INTEGER NOT NULL,
        signposting_reason VARCHAR(100), signposting_destination VARCHAR(80),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id)""",
    "appointments": """appointment_id INTEGER PRIMARY KEY, slot_id INTEGER NOT NULL UNIQUE,
        patient_id INTEGER NOT NULL, request_id INTEGER NOT NULL UNIQUE,
        booked_datetime DATETIME NOT NULL, booking_channel VARCHAR(40) NOT NULL,
        appointment_reason VARCHAR(50) NOT NULL, attendance_status VARCHAR(40) NOT NULL,
        outcome VARCHAR(80) NOT NULL, econsult_id INTEGER NOT NULL UNIQUE,
        cancelled_datetime DATETIME, FOREIGN KEY(slot_id) REFERENCES appointment_slots(slot_id),
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(econsult_id) REFERENCES econsult_requests(econsult_id)""",
    "incoming_call_volumes": """incoming_call_volume_id INTEGER PRIMARY KEY, call_date DATE NOT NULL,
        hour_start INTEGER NOT NULL, calls_offered INTEGER NOT NULL,
        calls_answered INTEGER NOT NULL, calls_abandoned INTEGER NOT NULL,
        average_wait_seconds REAL NOT NULL, UNIQUE(call_date,hour_start)""",
    "incoming_call_events": """incoming_call_event_id INTEGER PRIMARY KEY,
        incoming_call_volume_id INTEGER NOT NULL, patient_id INTEGER, request_id INTEGER,
        call_datetime DATETIME NOT NULL, queue_name VARCHAR(50) NOT NULL,
        call_reason VARCHAR(60) NOT NULL, call_outcome VARCHAR(20) NOT NULL,
        wait_seconds INTEGER NOT NULL, talk_seconds INTEGER NOT NULL,
        booking_intent INTEGER, appointment_booked INTEGER NOT NULL,
        allocation_status_at_call VARCHAR(50) NOT NULL, synthetic_call_reference VARCHAR(64) NOT NULL,
        FOREIGN KEY(incoming_call_volume_id) REFERENCES incoming_call_volumes(incoming_call_volume_id),
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id)""",
    "outgoing_call_attempts": """outgoing_call_attempt_id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL, request_id INTEGER NOT NULL, econsult_id INTEGER NOT NULL,
        appointment_id INTEGER, attempt_datetime DATETIME NOT NULL, attempt_number INTEGER NOT NULL,
        call_reason VARCHAR(60) NOT NULL, call_outcome VARCHAR(30) NOT NULL,
        appointment_booked_after_call INTEGER NOT NULL,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(econsult_id) REFERENCES econsult_requests(econsult_id),
        FOREIGN KEY(appointment_id) REFERENCES appointments(appointment_id)""",
    "patient_complaints": """complaint_id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL,
        request_id INTEGER NOT NULL, complaint_date DATE NOT NULL, complaint_category VARCHAR(50) NOT NULL,
        complaint_trigger VARCHAR(80) NOT NULL, trigger_datetime DATETIME NOT NULL,
        complaint_text_summary VARCHAR(255) NOT NULL, related_appointment_id INTEGER,
        related_econsult_id INTEGER NOT NULL, severity VARCHAR(20) NOT NULL, status VARCHAR(20) NOT NULL,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(related_appointment_id) REFERENCES appointments(appointment_id),
        FOREIGN KEY(related_econsult_id) REFERENCES econsult_requests(econsult_id)""",
    "appointment_activity_log": """appointment_activity_log_id INTEGER PRIMARY KEY,
        appointment_id INTEGER NOT NULL, event_datetime DATETIME NOT NULL,
        event_type VARCHAR(60) NOT NULL, event_channel VARCHAR(50) NOT NULL,
        event_actor VARCHAR(80) NOT NULL,
        FOREIGN KEY(appointment_id) REFERENCES appointments(appointment_id)""",
    "request_activity_log": """request_activity_log_id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL,
        event_datetime DATETIME NOT NULL, event_type VARCHAR(60) NOT NULL,
        event_actor VARCHAR(80) NOT NULL, event_payload TEXT NOT NULL,
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id)""",
}

KPI_FIELDS = {
    "kpi_month": "VARCHAR(7) PRIMARY KEY", "registered_patients": "INTEGER", "gp_sessions": "INTEGER",
    "gp_slots_total": "INTEGER", "gp_slots_bookable": "INTEGER", "gp_slots_booked": "INTEGER",
    "gp_slot_utilisation_pct": "REAL", "appointments_attended": "INTEGER", "appointments_dna": "INTEGER",
    "dna_rate_pct": "REAL", "appointments_cancelled": "INTEGER", "econsult_requests": "INTEGER",
    "econsults_gp_recommended": "INTEGER", "econsults_resolved_without_appointment": "INTEGER",
    "incoming_calls_offered": "INTEGER", "incoming_calls_answered": "INTEGER", "incoming_calls_abandoned": "INTEGER",
    "incoming_call_answer_rate_pct": "REAL", "average_wait_seconds": "REAL", "outgoing_call_attempts": "INTEGER",
    "outgoing_calls_answered": "INTEGER", "outgoing_call_answer_rate_pct": "REAL",
    "appointments_booked_after_outgoing_call": "INTEGER", "access_complaints": "INTEGER",
    "access_complaints_per_1000_patients": "REAL", "synthetic_data_label": "VARCHAR(100)",
    "gp_requests": "INTEGER", "same_day_gp_requests": "INTEGER", "routine_gp_requests": "INTEGER",
    "capacity_diverted_requests": "INTEGER", "capacity_diverted_patients": "INTEGER",
    "unmet_gp_requests": "INTEGER", "patients_without_appointment": "INTEGER", "pending_gp_requests": "INTEGER",
    "gp_requests_allocated_on_time_pct": "REAL", "appropriate_signposted_requests": "INTEGER",
    "confirmed_external_bookings": "INTEGER", "morning_call_gp_requests": "INTEGER",
    "morning_call_unallocated_patients": "INTEGER", "econsult_online_unallocated_patients": "INTEGER",
    "same_day_capacity_diverted": "INTEGER", "routine_capacity_diverted": "INTEGER"
}
TABLES["monthly_kpis"] = ",\n".join(f"{c} {t}" for c, t in KPI_FIELDS.items())

INDEXES = {
    "idx_slots_session": ("appointment_slots", "session_id"),
    "idx_slots_time_type": ("appointment_slots", "slot_type,slot_start_datetime"),
    "idx_sessions_date": ("clinic_sessions", "session_date"),
    "idx_requests_patient": ("appointment_requests", "patient_id"),
    "idx_requests_date": ("appointment_requests", "requested_datetime"),
    "idx_calls_request": ("incoming_call_events", "request_id"),
    "idx_calls_volume": ("incoming_call_events", "incoming_call_volume_id"),
    "idx_outgoing_request": ("outgoing_call_attempts", "request_id"),
    "idx_request_log_request": ("request_activity_log", "request_id"),
    "idx_appt_log_appt": ("appointment_activity_log", "appointment_id")
}


def schema_sql(dialect):
    head = "PRAGMA foreign_keys=ON;\n" if dialect == "sqlite" else (
        "CREATE DATABASE IF NOT EXISTS practicehub CHARACTER SET utf8mb4;\nUSE practicehub;\n")
    return head + "\n".join(f"CREATE TABLE {name} ({fields})" +
                            (" ENGINE=InnoDB" if dialect == "mysql" else "") + ";"
                            for name, fields in TABLES.items()) + "\n" + "\n".join(
        f"CREATE INDEX {n} ON {t} ({c});" for n,(t,c) in INDEXES.items())


# Aggregate each fact independently to prevent row multiplication across contacts.
KPI_SELECT = """
WITH months AS (
 SELECT DISTINCT SUBSTR(calendar_date,1,7) AS kpi_month FROM practice_calendar
), cap AS (
 SELECT SUBSTR(cs.session_date,1,7) AS kpi_month, COUNT(DISTINCT cs.session_id) AS gp_sessions,
 COUNT(s.slot_id) AS gp_slots_total, SUM(s.is_bookable) AS gp_slots_bookable,
 COUNT(a.appointment_id) AS gp_slots_booked,
 SUM(CASE WHEN a.attendance_status='Attended' THEN 1 ELSE 0 END) AS appointments_attended,
 SUM(CASE WHEN a.attendance_status='DNA' THEN 1 ELSE 0 END) AS appointments_dna,
 SUM(CASE WHEN a.cancelled_datetime IS NOT NULL THEN 1 ELSE 0 END) AS appointments_cancelled
 FROM clinic_sessions cs JOIN clinicians c ON c.clinician_id=cs.clinician_id
 JOIN appointment_slots s ON s.session_id=cs.session_id
 LEFT JOIN appointments a ON a.slot_id=s.slot_id
 WHERE c.is_gp=1 AND s.slot_type IN ('Same-day GP','Routine GP')
 GROUP BY SUBSTR(cs.session_date,1,7)
), req_base AS (
 SELECT r.*, e.resolved_without_appointment, a.attendance_status,
 CASE WHEN r.request_outcome='Signposted due to capacity'
      AND r.external_care_status<>'Confirmed external booking' THEN 1
      WHEN a.attendance_status='Cancelled by practice' THEN 1 ELSE 0 END AS unmet,
 CASE WHEN (a.appointment_id IS NOT NULL AND a.attendance_status<>'Cancelled by practice'
            AND a.booked_datetime<=r.required_by_datetime AND s.slot_start_datetime<=r.required_by_datetime)
      OR (r.external_care_status='Confirmed external booking'
            AND r.external_appointment_datetime<=r.required_by_datetime) THEN 1 ELSE 0 END AS on_time
 FROM appointment_requests r JOIN econsult_requests e ON e.request_id=r.request_id
 LEFT JOIN appointments a ON a.request_id=r.request_id
 LEFT JOIN appointment_slots s ON s.slot_id=a.slot_id
), req AS (
 SELECT SUBSTR(requested_datetime,1,7) AS kpi_month, COUNT(*) AS econsult_requests,
 SUM(CASE WHEN required_clinician_type='GP' THEN 1 ELSE 0 END) AS gp_requests,
 SUM(CASE WHEN required_appointment_type='Same-day GP' THEN 1 ELSE 0 END) AS same_day_gp_requests,
 SUM(CASE WHEN required_appointment_type='Routine GP' THEN 1 ELSE 0 END) AS routine_gp_requests,
 SUM(resolved_without_appointment) AS resolved_without_appointment,
 SUM(CASE WHEN request_outcome='Signposted due to capacity' THEN 1 ELSE 0 END) AS capacity_diverted_requests,
 COUNT(DISTINCT CASE WHEN request_outcome='Signposted due to capacity' THEN patient_id END) AS capacity_diverted_patients,
 SUM(unmet) AS unmet_gp_requests,
 COUNT(DISTINCT CASE WHEN unmet=1 THEN patient_id END) AS patients_without_appointment,
 SUM(CASE WHEN required_clinician_type='GP' AND request_outcome='Pending' THEN 1 ELSE 0 END) AS pending_gp_requests,
 SUM(on_time) AS on_time,
 SUM(CASE WHEN required_clinician_type='GP' AND request_outcome<>'Pending' THEN 1 ELSE 0 END) AS decided_gp_requests,
 SUM(CASE WHEN request_outcome='Appropriate signposting' THEN 1 ELSE 0 END) AS appropriate_signposted_requests,
 SUM(CASE WHEN external_care_status='Confirmed external booking' THEN 1 ELSE 0 END) AS confirmed_external_bookings,
 COUNT(DISTINCT CASE WHEN unmet=1 AND original_contact_channel='Online' THEN patient_id END) AS econsult_online_unallocated_patients,
 SUM(CASE WHEN request_outcome='Signposted due to capacity' AND required_appointment_type='Same-day GP' THEN 1 ELSE 0 END) AS same_day_capacity_diverted,
 SUM(CASE WHEN request_outcome='Signposted due to capacity' AND required_appointment_type='Routine GP' THEN 1 ELSE 0 END) AS routine_capacity_diverted
 FROM req_base GROUP BY SUBSTR(requested_datetime,1,7)
), tel AS (
 SELECT SUBSTR(call_datetime,1,7) AS kpi_month, COUNT(*) AS offered,
 SUM(CASE WHEN call_outcome='Answered' THEN 1 ELSE 0 END) AS answered,
 SUM(CASE WHEN call_outcome='Abandoned' THEN 1 ELSE 0 END) AS abandoned,
 AVG(wait_seconds) AS mean_wait
 FROM incoming_call_events GROUP BY SUBSTR(call_datetime,1,7)
), morning AS (
 SELECT SUBSTR(r.requested_datetime,1,7) AS kpi_month,
 COUNT(DISTINCT r.request_id) AS gp_requests,
 COUNT(DISTINCT CASE WHEN r.unmet=1 THEN r.patient_id END) AS unallocated_patients
 FROM req_base r JOIN incoming_call_events i ON i.request_id=r.request_id
 WHERE SUBSTR(i.call_datetime,12,5)>='08:00' AND SUBSTR(i.call_datetime,12,5)<'10:00'
 AND r.required_clinician_type='GP' AND i.booking_intent=1
 GROUP BY SUBSTR(r.requested_datetime,1,7)
), outgoing AS (
 SELECT SUBSTR(attempt_datetime,1,7) AS kpi_month, COUNT(*) AS attempts,
 SUM(CASE WHEN call_outcome='Answered' THEN 1 ELSE 0 END) AS answered,
 SUM(appointment_booked_after_call) AS booked
 FROM outgoing_call_attempts GROUP BY SUBSTR(attempt_datetime,1,7)
), complaints AS (
 SELECT SUBSTR(complaint_date,1,7) AS kpi_month, COUNT(*) AS access_complaints
 FROM patient_complaints WHERE complaint_category='Appointment access'
 GROUP BY SUBSTR(complaint_date,1,7)
), pop AS (SELECT COUNT(*) AS n FROM patients WHERE is_active=1)
SELECT m.kpi_month, pop.n AS registered_patients,
 COALESCE(c.gp_sessions,0) AS gp_sessions, COALESCE(c.gp_slots_total,0) AS gp_slots_total,
 COALESCE(c.gp_slots_bookable,0) AS gp_slots_bookable, COALESCE(c.gp_slots_booked,0) AS gp_slots_booked,
 ROUND(100.0*c.gp_slots_booked/NULLIF(c.gp_slots_bookable,0),2) AS gp_slot_utilisation_pct,
 COALESCE(c.appointments_attended,0) AS appointments_attended,
 COALESCE(c.appointments_dna,0) AS appointments_dna,
 ROUND(100.0*c.appointments_dna/NULLIF(c.gp_slots_booked,0),2) AS dna_rate_pct,
 COALESCE(c.appointments_cancelled,0) AS appointments_cancelled,
 COALESCE(r.econsult_requests,0) AS econsult_requests,
 COALESCE(r.gp_requests,0) AS econsults_gp_recommended,
 COALESCE(r.resolved_without_appointment,0) AS econsults_resolved_without_appointment,
 COALESCE(t.offered,0) AS incoming_calls_offered, COALESCE(t.answered,0) AS incoming_calls_answered,
 COALESCE(t.abandoned,0) AS incoming_calls_abandoned,
 ROUND(100.0*t.answered/NULLIF(t.offered,0),2) AS incoming_call_answer_rate_pct,
 ROUND(t.mean_wait,1) AS average_wait_seconds,
 COALESCE(o.attempts,0) AS outgoing_call_attempts, COALESCE(o.answered,0) AS outgoing_calls_answered,
 ROUND(100.0*o.answered/NULLIF(o.attempts,0),2) AS outgoing_call_answer_rate_pct,
 COALESCE(o.booked,0) AS appointments_booked_after_outgoing_call,
 COALESCE(p.access_complaints,0) AS access_complaints,
 ROUND(1000.0*COALESCE(p.access_complaints,0)/NULLIF(pop.n,0),2) AS access_complaints_per_1000_patients,
 'Synthetic PracticeHUB v2' AS synthetic_data_label,
 COALESCE(r.gp_requests,0) AS gp_requests, COALESCE(r.same_day_gp_requests,0) AS same_day_gp_requests,
 COALESCE(r.routine_gp_requests,0) AS routine_gp_requests,
 COALESCE(r.capacity_diverted_requests,0) AS capacity_diverted_requests,
 COALESCE(r.capacity_diverted_patients,0) AS capacity_diverted_patients,
 COALESCE(r.unmet_gp_requests,0) AS unmet_gp_requests,
 COALESCE(r.patients_without_appointment,0) AS patients_without_appointment,
 COALESCE(r.pending_gp_requests,0) AS pending_gp_requests,
 ROUND(100.0*r.on_time/NULLIF(r.decided_gp_requests,0),2) AS gp_requests_allocated_on_time_pct,
 COALESCE(r.appropriate_signposted_requests,0) AS appropriate_signposted_requests,
 COALESCE(r.confirmed_external_bookings,0) AS confirmed_external_bookings,
 COALESCE(mor.gp_requests,0) AS morning_call_gp_requests,
 COALESCE(mor.unallocated_patients,0) AS morning_call_unallocated_patients,
 COALESCE(r.econsult_online_unallocated_patients,0) AS econsult_online_unallocated_patients,
 COALESCE(r.same_day_capacity_diverted,0) AS same_day_capacity_diverted,
 COALESCE(r.routine_capacity_diverted,0) AS routine_capacity_diverted
FROM months m CROSS JOIN pop
LEFT JOIN cap c ON c.kpi_month=m.kpi_month LEFT JOIN req r ON r.kpi_month=m.kpi_month
LEFT JOIN tel t ON t.kpi_month=m.kpi_month LEFT JOIN outgoing o ON o.kpi_month=m.kpi_month
LEFT JOIN complaints p ON p.kpi_month=m.kpi_month LEFT JOIN morning mor ON mor.kpi_month=m.kpi_month
"""


VALIDATION_QUERIES = {
    "request_missing_intake": "SELECT COUNT(*) FROM appointment_requests r LEFT JOIN econsult_requests e ON e.request_id=r.request_id WHERE e.econsult_id IS NULL",
    "appointment_patient_mismatch": "SELECT COUNT(*) FROM appointments a JOIN appointment_requests r ON r.request_id=a.request_id JOIN econsult_requests e ON e.econsult_id=a.econsult_id WHERE a.patient_id<>r.patient_id OR a.patient_id<>e.patient_id OR a.request_id<>e.request_id",
    "booking_before_triage_or_after_slot": "SELECT COUNT(*) FROM appointments a JOIN econsult_requests e ON e.econsult_id=a.econsult_id JOIN appointment_slots s ON s.slot_id=a.slot_id WHERE a.booked_datetime<e.triaged_datetime OR a.booked_datetime>s.slot_start_datetime OR a.cancelled_datetime<a.booked_datetime",
    "wrong_slot_type_or_deadline": "SELECT COUNT(*) FROM appointments a JOIN appointment_requests r ON r.request_id=a.request_id JOIN appointment_slots s ON s.slot_id=a.slot_id WHERE s.slot_type<>r.required_appointment_type OR s.slot_start_datetime>r.required_by_datetime OR s.is_bookable=0",
    "calls_patient_mismatch": "SELECT COUNT(*) FROM incoming_call_events i JOIN appointment_requests r ON r.request_id=i.request_id WHERE i.patient_id<>r.patient_id OR i.patient_id IS NULL",
    "outbound_patient_or_time_mismatch": "SELECT COUNT(*) FROM outgoing_call_attempts o JOIN econsult_requests e ON e.econsult_id=o.econsult_id LEFT JOIN appointments a ON a.appointment_id=o.appointment_id WHERE o.patient_id<>e.patient_id OR o.request_id<>e.request_id OR o.attempt_datetime<e.triaged_datetime OR (a.appointment_id IS NOT NULL AND a.request_id<>o.request_id)",
    "complaint_patient_or_date_mismatch": "SELECT COUNT(*) FROM patient_complaints p JOIN appointment_requests r ON r.request_id=p.request_id JOIN econsult_requests e ON e.econsult_id=p.related_econsult_id LEFT JOIN appointments a ON a.appointment_id=p.related_appointment_id WHERE p.patient_id<>r.patient_id OR e.request_id<>r.request_id OR SUBSTR(r.requested_datetime,1,10)>p.complaint_date OR SUBSTR(p.trigger_datetime,1,10)>p.complaint_date OR p.trigger_datetime<r.requested_datetime OR (a.appointment_id IS NOT NULL AND a.patient_id<>p.patient_id)",
    "sessions_on_closed_days": "SELECT COUNT(*) FROM clinic_sessions s JOIN practice_calendar p ON p.calendar_date=s.session_date WHERE p.is_open=0",
    "sessions_on_leave": "SELECT COUNT(*) FROM clinic_sessions s JOIN clinician_absences a ON a.clinician_id=s.clinician_id AND a.absence_date=s.session_date",
    "invalid_patient_lifetime": "SELECT COUNT(*) FROM patients WHERE registration_date<date_of_birth",
    "request_before_registration": "SELECT COUNT(*) FROM appointment_requests r JOIN patients p ON p.patient_id=r.patient_id WHERE SUBSTR(r.requested_datetime,1,10)<p.registration_date",
    "inconsistent_triage_outcome": "SELECT COUNT(*) FROM econsult_requests e JOIN appointment_requests r ON r.request_id=e.request_id WHERE (e.signposting_reason='Practice capacity reached' AND r.request_outcome<>'Signposted due to capacity') OR (e.signposting_reason='Appropriate care pathway' AND r.required_clinician_type='GP')",
    "external_booking_after_deadline": "SELECT COUNT(*) FROM appointment_requests WHERE external_care_status='Confirmed external booking' AND (external_appointment_datetime IS NULL OR external_appointment_datetime>required_by_datetime)",
    "invalid_utilisation": "SELECT COUNT(*) FROM monthly_kpis WHERE gp_slot_utilisation_pct<0 OR gp_slot_utilisation_pct>100 OR gp_slots_booked>gp_slots_bookable",
    "invalid_unknown_intent": "SELECT COUNT(*) FROM incoming_call_events WHERE call_outcome='Abandoned' AND (booking_intent IS NOT NULL OR talk_seconds<>0)",
    "invalid_activity_chronology": "SELECT COUNT(*) FROM appointment_activity_log l JOIN appointments a ON a.appointment_id=l.appointment_id JOIN appointment_slots s ON s.slot_id=a.slot_id WHERE l.event_datetime<a.booked_datetime OR (l.event_type='Reminder sent' AND l.event_datetime>s.slot_start_datetime)",
    "incorrect_slot_state": "SELECT COUNT(*) FROM appointment_slots s LEFT JOIN appointments a ON a.slot_id=s.slot_id WHERE (a.appointment_id IS NULL AND s.slot_status IN ('Booked','Late cancellation')) OR (a.appointment_id IS NOT NULL AND (s.is_bookable=0 OR s.slot_status NOT IN ('Booked','Late cancellation')))",
    "patient_double_booking": "SELECT COUNT(*) FROM (SELECT a.patient_id,s.slot_start_datetime FROM appointments a JOIN appointment_slots s ON s.slot_id=a.slot_id GROUP BY a.patient_id,s.slot_start_datetime HAVING COUNT(*)>1) conflicts",
}


def validate(conn, meta):
    results = {name: conn.execute(sql).fetchone()[0] for name,sql in VALIDATION_QUERIES.items()}
    results["foreign_key_errors"]=len(conn.execute("PRAGMA foreign_key_check").fetchall())
    results["integrity_errors"]=int(conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok")
    results["population_error"]=int(conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]!=meta["population"])
    expected=36 if meta["profile"]=="final" else 3
    results["month_count_error"]=int(conn.execute("SELECT COUNT(*) FROM monthly_kpis").fetchone()[0]!=expected)
    results["call_rollup_mismatch"]=conn.execute("""SELECT COUNT(*) FROM incoming_call_volumes v JOIN
        (SELECT incoming_call_volume_id, COUNT(*) AS n, SUM(CASE WHEN call_outcome='Answered' THEN 1 ELSE 0 END) AS a,
         AVG(wait_seconds) AS w FROM incoming_call_events GROUP BY incoming_call_volume_id) e
        ON e.incoming_call_volume_id=v.incoming_call_volume_id
        WHERE v.calls_offered<>e.n OR v.calls_answered<>e.a OR v.calls_abandoned<>e.n-e.a
        OR ABS(v.average_wait_seconds-e.w)>.001""").fetchone()[0]
    results["session_slot_count_mismatch"]=conn.execute("""SELECT COUNT(*) FROM clinic_sessions c JOIN
        (SELECT session_id,COUNT(*) AS n FROM appointment_slots GROUP BY session_id) s ON s.session_id=c.session_id
        WHERE c.planned_slots<>s.n""").fetchone()[0]
    # Replay availability at allocation time: a diversion needs an actual suitable-slot shortfall.
    by_type_day=defaultdict(list)
    for sid,kind,when,bookable in conn.execute("SELECT slot_id,slot_type,slot_start_datetime,is_bookable FROM appointment_slots"):
        if bookable:
            by_type_day[(kind,when[:10])].append((sid,when))
    bookings=dict(conn.execute("SELECT slot_id,booked_datetime FROM appointments"))
    patient_bookings=defaultdict(dict)
    for patient,when,booked in conn.execute("SELECT a.patient_id,s.slot_start_datetime,a.booked_datetime FROM appointments a JOIN appointment_slots s ON s.slot_id=a.slot_id"):
        patient_bookings[patient][when]=booked
    results["diversion_with_suitable_capacity"]=0
    sql="""SELECT r.patient_id,r.required_appointment_type,r.requested_datetime,r.required_by_datetime,l.event_datetime
        FROM appointment_requests r JOIN request_activity_log l ON l.request_id=r.request_id
        WHERE r.request_outcome='Signposted due to capacity' AND l.event_type='Allocation decision'"""
    for patient,kind,requested,deadline,decided in conn.execute(sql):
        first=date.fromisoformat(requested[:10])
        search=[first] if kind=='Same-day GP' else [first+timedelta(days=i) for i in range(1,15)]
        earliest=iso(datetime.fromisoformat(decided)+timedelta(minutes=15))
        if any(when>=earliest and when<=deadline and (sid not in bookings or bookings[sid]>decided)
               and (when not in patient_bookings[patient] or patient_bookings[patient][when]>decided)
               for day in search for sid,when in by_type_day[(kind,iso(day))]):
            results["diversion_with_suitable_capacity"]+=1
    if meta["profile"]=="final":
        seasonal=conn.execute("""SELECT SUBSTR(kpi_month,1,4),
            AVG(CASE WHEN SUBSTR(kpi_month,6,2) IN ('12','01','02') THEN gp_requests END),
            AVG(CASE WHEN SUBSTR(kpi_month,6,2) IN ('06','07','08') THEN gp_requests END)
            FROM monthly_kpis GROUP BY SUBSTR(kpi_month,1,4)""").fetchall()
        results["winter_not_above_summer"]=sum(winter<=summer for _,winter,summer in seasonal)
    results["passed"]=all(v==0 for v in results.values())
    return results


def write_sql_assets(root):
    import sqlite3
    (root/"database/schema.sql").write_text("-- Generated from src/practicehub/dataset_v2.py\n"+schema_sql("sqlite")+"\n")
    old_views=["vw_executive_kpis_latest_month","vw_monthly_gp_capacity","vw_monthly_econsults",
               "vw_monthly_telephone","vw_monthly_access_complaints","vw_monthly_outgoing_calls","vw_monthly_core_kpis"]
    drops="\n".join("DROP VIEW IF EXISTS "+v+";" for v in old_views)
    reset="USE practicehub;\n"+drops+"\n"+"\n".join("DROP TABLE IF EXISTS "+n+";" for n in reversed(TABLES))+"\n"
    # Only the named PracticeHUB tables are replaced; foreign keys are dropped child-first.
    mysql_schema=schema_sql("mysql")
    head=mysql_schema[:mysql_schema.index("CREATE TABLE")]
    (root/"database/mysql_schema.sql").write_text("-- DESTRUCTIVE: rebuilds PracticeHUB v2 tables. Back up MySQL before running.\n"+head+reset+mysql_schema[mysql_schema.index("CREATE TABLE"):]+"\n")
    populate="START TRANSACTION;\nDELETE FROM monthly_kpis;\nINSERT INTO monthly_kpis SELECT * FROM vw_monthly_core_kpis;\nCOMMIT;\nSELECT COUNT(*) AS monthly_kpi_rows FROM monthly_kpis;\n"
    views="USE practicehub;\nCREATE OR REPLACE VIEW vw_monthly_core_kpis AS "+KPI_SELECT+";\n"
    helpers={"vw_monthly_gp_capacity":"kpi_month,gp_sessions,gp_slots_total,gp_slots_bookable,gp_slots_booked,gp_slot_utilisation_pct,appointments_attended,appointments_dna,dna_rate_pct,appointments_cancelled",
             "vw_monthly_econsults":"kpi_month,econsult_requests,econsults_gp_recommended,econsults_resolved_without_appointment,gp_requests,capacity_diverted_requests,appropriate_signposted_requests",
             "vw_monthly_telephone":"kpi_month,incoming_calls_offered,incoming_calls_answered,incoming_calls_abandoned,incoming_call_answer_rate_pct,average_wait_seconds,outgoing_call_attempts,outgoing_calls_answered,outgoing_call_answer_rate_pct,appointments_booked_after_outgoing_call",
             "vw_monthly_access_complaints":"kpi_month,access_complaints,access_complaints_per_1000_patients",
             "vw_monthly_outgoing_calls":"kpi_month,outgoing_call_attempts,outgoing_calls_answered,outgoing_call_answer_rate_pct,appointments_booked_after_outgoing_call"}
    for name,columns in helpers.items():
        views+=f"CREATE OR REPLACE VIEW {name} AS SELECT {columns} FROM vw_monthly_core_kpis;\n"
    views+="CREATE OR REPLACE VIEW vw_executive_kpis_latest_month AS SELECT * FROM vw_monthly_core_kpis WHERE kpi_month=(SELECT MAX(kpi_month) FROM vw_monthly_core_kpis);\n"
    (root/"database/mysql_kpi_views.sql").write_text("-- Rebuild v2 KPI views and refresh the physical KPI table.\n"+views+populate)
    (root/"database/mysql_populate_monthly_kpis.sql").write_text("USE practicehub;\n"+populate)
    conn=sqlite3.connect(":memory:")
    conn.executescript(schema_sql("sqlite"))
    dictionary=["# PracticeHUB V2 Data Dictionary", "", "Generated from the actual schema. IDs are synthetic; all activity is fictional.",
                "Nullable fields represent unknown or not-applicable values. Dates are historical 2023-2025; age_band is measured at the reporting cutoff.",
                "Read kpi_definitions_v2.md for derived measures and final_dataset_assumptions.md for sampling assumptions.", ""]
    erd=["# PracticeHUB V2 ERD", "", "Request-led schema. Each request has exactly one eConsult in the validated dataset; the unique foreign key enforces at most one, and validation checks completeness.",
         "Forecasts and model evaluations use result files, not database tables. Monthly KPIs are derived reporting data, not a transactional 3NF relation.", "", "```mermaid", "erDiagram", "    direction LR"]
    for table in TABLES:
        info=conn.execute(f"PRAGMA table_info({table})").fetchall()
        fks={r[3]:(r[2],r[4]) for r in conn.execute(f"PRAGMA foreign_key_list({table})")}
        dictionary.extend([f"## {table}", "", "| Field | Type | Required | Key / reference |", "|---|---|---|---|"])
        erd.append(f"    {table} {{")
        for _,name,kind,required,default,pk in info:
            ref="PK" if pk else f"FK to {fks[name][0]}.{fks[name][1]}" if name in fks else ""
            dictionary.append(f"| {name} | {kind} | {'Yes' if required or pk else 'No'} | {ref} |")
            erd.append(f"        {'int' if kind=='INTEGER' else 'float' if kind=='REAL' else 'date' if kind=='DATE' else 'datetime' if kind=='DATETIME' else 'string'} {name}"+
                       (" PK" if pk else " FK" if name in fks else ""))
        erd.append("    }")
        for name,(parent,parent_col) in fks.items():
            required=next(r[3] for r in info if r[1]==name)
            one=table in ('econsult_requests','appointments') and name in ('request_id','econsult_id','slot_id')
            erd.append(f"    {parent} {'||' if required else 'o|'}--{'o|' if one else 'o{'} {table} : {name}")
        dictionary.append("")
    erd.append("```")
    (root/"docs/data_dictionary.md").write_text("\n".join(dictionary)+"\n")
    (root/"docs/erd.md").write_text("\n".join(erd)+"\n")
    loads=["-- Run only after mysql_schema.sql (v2). Foreign keys remain enabled.\nUSE practicehub;"]
    for table in TABLES:
        if table=="monthly_kpis":
            continue
        info=conn.execute(f"PRAGMA table_info({table})").fetchall()
        path=str(root/"data/raw/final"/(table+".csv")).replace("'","''")
        columns=", ".join("@"+r[1] for r in info)
        setters=", ".join(r[1]+"=NULLIF(@"+r[1]+",'')" for r in info)
        loads.append(f"LOAD DATA LOCAL INFILE '{path}' INTO TABLE {table}\nCHARACTER SET utf8mb4\nFIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"'\nLINES TERMINATED BY '\\r\\n' IGNORE 1 LINES\n({columns}) SET {setters};\nSHOW COUNT(*) WARNINGS;")
    (root/"database/mysql_import_final.sql").write_text("\n\n".join(loads)+"\n")
    checks="USE practicehub;\n"+"\nUNION ALL\n".join(f"SELECT '{n}' AS check_name, ({q}) AS violations" for n,q in VALIDATION_QUERIES.items())+";\n"
    checks+="\n"+"\nUNION ALL\n".join(f"SELECT '{n}' AS table_name, COUNT(*) AS row_count FROM {n}" for n in TABLES)+";\n"
    (root/"database/mysql_validation.sql").write_text(checks)
    (root/"database/mysql_refresh_final.sql").write_text("-- DESTRUCTIVE rebuild of named PracticeHUB tables. Take a MySQL backup first.\n"+
        (root/"database/mysql_schema.sql").read_text()+"\n"+(root/"database/mysql_import_final.sql").read_text()+"\n"+
        (root/"database/mysql_kpi_views.sql").read_text()+"\n"+checks)
    conn.close()


def dt(d, hour=8, minute=0):
    return datetime.combine(d, time(hour, minute))


def iso(v):
    return v.isoformat(sep=" ") if isinstance(v, datetime) else v.isoformat()


def holidays(year):
    values = {2023: ["01-02", "04-07", "04-10", "05-01", "05-08", "05-29", "08-28", "12-25", "12-26"],
              2024: ["01-01", "03-29", "04-01", "05-06", "05-27", "08-26", "12-25", "12-26"],
              2025: ["01-01", "04-18", "04-21", "05-05", "05-26", "08-25", "12-25", "12-26"]}
    return {date.fromisoformat(f"{year}-{s}") for s in values[year]}


def build(profile, seed):
    rng = random.Random(seed)
    start, end, population = (date(2023, 1, 1), date(2025, 12, 31), 10_000) if profile == "final" else (
        date(2024, 1, 1), date(2024, 3, 31), 1000)
    asof = dt(end, 23, 59)
    days = [start + timedelta(days=i) for i in range((end-start).days + 1)]
    closures = set().union(*(holidays(y) for y in range(start.year, end.year+1)))
    open_days = [d for d in days if d.weekday() < 5 and d not in closures]
    t = {name: [] for name in TABLES}
    def add(table, **row):
        t[table].append(row)
        return row
    def audit(req, when, event, **payload):
        add("request_activity_log", request_activity_log_id=len(t["request_activity_log"])+1,
            request_id=req["request_id"], event_datetime=iso(when), event_type=event,
            event_actor="Reception" if event == "Intake recorded" else "Clinical triage team",
            event_payload=json.dumps(payload, sort_keys=True, separators=(",", ":")))
    for p in range(1, population+1):
        age = rng.choices([rng.randint(3,17), rng.randint(18,34), rng.randint(35,49), rng.randint(50,64),
                           rng.randint(65,79), rng.randint(80,95)], [20,21,20,19,14,6])[0]
        dob = date(end.year-age, rng.randint(1,12), rng.randint(1,28))
        age = end.year-dob.year-((end.month,end.day)<(dob.month,dob.day))
        band = next(label for low, high, label in [(0,17,"0-17"),(18,34,"18-34"),(35,49,"35-49"),
                                                  (50,64,"50-64"),(65,79,"65-79"),(80,120,"80+")]
                    if low <= age <= high)
        registered = max(dob, start-timedelta(days=rng.randint(10,3650)))
        add("patients", patient_id=p, nhs_number_hash=hashlib.sha256(f"{seed}-{p}".encode()).hexdigest(),
            sex=rng.choices(["Female","Male","Other"],[51,48,1])[0], date_of_birth=iso(dob), age_band=band,
            postcode_district=rng.choice(["CV1","CV2","CV3","CV4","CV5"]), registration_date=iso(registered), is_active=1)
    patterns = [[0,1,3,4],[0,1,2,3,4],[0,2,4],[1,2,3,4],[0,1,2]]
    names = ["Dr Asha Patel","Dr Ben Carter","Dr Chloe Hughes","Dr Daniel Green","Dr Elena Ahmed"]
    for i, (name, pattern) in enumerate(zip(names,patterns), 1):
        add("clinicians", clinician_id=i, clinician_name=name, role="GP", fte=len(pattern)/5,
            working_pattern=" ".join(calendar.day_abbr[w] for w in pattern), usual_session_minutes=210,
            is_gp=1, active_from="2020-01-01", active_to=None)
    for d in days:
        add("practice_calendar", calendar_date=iso(d), is_open=int(d in open_days),
            closure_reason=None if d in open_days else "Bank holiday" if d in closures else "Weekend",
            seasonal_factor=SEASONS[d.month-1])
    absent = set()
    for i, pattern in enumerate(patterns, 1):
        for year in range(start.year,end.year+1):
            eligible = [d for d in open_days if d.year==year and d.weekday() in pattern]
            count = min(len(eligible)//7, round(25*len(pattern)/5))
            weighted = sorted(eligible, key=lambda d: rng.random() / (1.6 if d.month in (7,8) else 1))
            for d in weighted[:count]:
                absent.add((i,d))
                add("clinician_absences", absence_id=len(t["clinician_absences"])+1, clinician_id=i,
                    absence_date=iso(d), absence_reason="Annual leave")
    slots_by_type = defaultdict(list)
    slots = {}
    for d in open_days:
        for i, pattern in enumerate(patterns,1):
            if d.weekday() not in pattern or (i,d) in absent:
                continue
            for period, h in [("AM",9),("PM",14)]:
                sid = len(t["clinic_sessions"])+1
                add("clinic_sessions", session_id=sid, clinician_id=i, session_date=iso(d), session_type=period,
                    start_time=f"{h:02d}:00", end_time=iso(dt(d,h)+timedelta(minutes=210))[11:16],
                    planned_slots=12, session_minutes=210, delivery_mode="Mixed")
                for j in range(12):
                    when = dt(d,h)+timedelta(minutes=15*j)
                    kind = "Same-day GP" if j < 7 else "Routine GP"
                    blocked = rng.random()<.015
                    slot = add("appointment_slots", slot_id=len(slots)+1, session_id=sid,
                               slot_start_datetime=iso(when), slot_end_datetime=iso(when+timedelta(minutes=15)),
                               slot_type=kind, slot_status="Blocked" if blocked else "Available", is_bookable=int(not blocked))
                    slots[slot["slot_id"]] = slot
                    if not blocked:
                        slots_by_type[(d,kind)].append(slot)
    for arr in slots_by_type.values():
        arr.sort(key=lambda s:s["slot_start_datetime"])
    calls = []
    def call(dtime, patient=None, req=None, outcome="Answered", intent=None, reason="General enquiry"):
        if dtime > asof:
            return
        calls.append(dict(patient_id=patient, request_id=req, call_datetime=iso(dtime), queue_name="Reception",
                          call_reason=reason, call_outcome=outcome, wait_seconds=rng.randint(90,900),
                          talk_seconds=rng.randint(80,360) if outcome=="Answered" else 0,
                          booking_intent=intent, appointment_booked=0,
                          allocation_status_at_call="Awaiting triage" if req else "Not established"))
    patient_pool = [p["patient_id"] for p in t["patients"]]
    weights = [2 if p["age_band"] in ("65-79","80+") else 1 for p in t["patients"]]
    available_pos = defaultdict(int)
    patient_reserved_times = defaultdict(set)
    scale = 1 if profile == "final" else .25
    schedule=intake_schedule(open_days,seed,scale)
    complaints_rng=random.Random(seed+701)
    complaint_month_factors={}
    complaint_latent=0.0
    for month in sorted({d.strftime('%Y-%m') for d in open_days}):
        complaint_latent=.35*complaint_latent+complaints_rng.gauss(0,.28)
        complaint_month_factors[month]=math.exp(complaint_latent)
    for d in open_days:
        factor = SEASONS[d.month-1] * (1.18 if d.weekday()==0 else .96)
        intakes=[]
        for pathway,count in schedule[d].items():
            patient_ids=rng.choices(patient_pool,weights=weights,k=count)
            intakes.extend((dt(d,8,5)+timedelta(minutes=rng.randint(0,135),seconds=rng.randint(0,59)),p,pathway)
                           for p in patient_ids)
        intakes.sort()
        daily = []
        for submitted, patient, pathway in intakes:
            rid = len(t["appointment_requests"])+1
            channel = rng.choices(["Telephone","Online","Reception"],[48,47,5])[0]
            needs_gp = pathway!='Other service'
            kind = pathway if needs_gp else None
            triaged = submitted+timedelta(minutes=rng.randint(10,35))
            deadline = dt(d,18) if kind=="Same-day GP" else dt(d+timedelta(days=14),18) if needs_gp else None
            req = add("appointment_requests", request_id=rid, patient_id=patient, requested_datetime=iso(submitted),
                      original_contact_channel=channel, required_clinician_type="GP" if needs_gp else "Other service",
                      required_appointment_type=kind, required_by_datetime=iso(deadline) if deadline else None,
                      request_outcome="Pending", non_allocation_reason=None, external_care_status="Not applicable",
                      external_appointment_datetime=None)
            ec = add("econsult_requests", econsult_id=rid, request_id=rid, patient_id=patient,
                     submitted_datetime=iso(submitted), original_contact_channel=channel,
                     submitted_by_role="Patient" if channel=="Online" else "Receptionist",
                     category=rng.choice(["Symptoms","Acute medication query","Mental health concern"] if kind=='Same-day GP'
                                         else ["Medication review","Follow-up","Long-term condition"] if needs_gp
                                         else ["Minor illness","Administrative request","Other service enquiry"]),
                     urgency_level="High" if kind=="Same-day GP" else "Medium" if needs_gp else "Low",
                     triaged_datetime=iso(triaged), triage_outcome="Pending allocation",
                     gp_appointment_recommended=int(needs_gp), resolved_without_appointment=0,
                     signposting_reason=None, signposting_destination=None)
            if channel=="Telephone":
                call(submitted-timedelta(minutes=4), patient, rid, intent=1, reason="Appointment request")
            audit(req, submitted, "Intake recorded", channel=channel, submitted_by=ec["submitted_by_role"], category=ec["category"])
            audit(req, triaged, "Clinical triage", gp_required=needs_gp, appointment_type=kind,
                  required_by=req["required_by_datetime"], triage_urgency=ec["urgency_level"])
            contact_attempts = []
            for i in range(3):
                at=triaged+timedelta(minutes=5+15*i)
                out=rng.choices(["Answered","Voicemail","No answer","Invalid number"],[65,15,19,1])[0]
                contact_attempts.append((at,out))
                if out=="Answered":
                    break
            daily.append((contact_attempts[-1][0]+timedelta(minutes=2),triaged,req,ec,contact_attempts))
        for decision_time, triaged, req, ec, call_outcomes in sorted(daily,key=lambda x:x[0]):
            rid, patient = req["request_id"], req["patient_id"]
            needs_gp = bool(ec["gp_appointment_recommended"])
            kind = req["required_appointment_type"]
            deadline = datetime.fromisoformat(req["required_by_datetime"]) if needs_gp else None
            selected = None
            searched = []
            if needs_gp:
                eligible_days = [d] if kind=="Same-day GP" else [d+timedelta(days=i) for i in range(1,15)]
                for candidate_day in eligible_days:
                    arr = slots_by_type[(candidate_day,kind)]
                    key = (candidate_day,kind)
                    pos = available_pos[key]
                    while pos<len(arr) and arr[pos]["slot_start_datetime"]<iso(decision_time+timedelta(minutes=15)):
                        pos+=1
                    available_pos[key] = pos
                    searched.append({"date":iso(candidate_day),"remaining":len(arr)-pos})
                    candidate = next((i for i in range(pos,len(arr))
                                      if arr[i]["slot_start_datetime"] not in patient_reserved_times[patient]),None)
                    if candidate is not None:
                        selected=arr.pop(candidate)
                        patient_reserved_times[patient].add(selected["slot_start_datetime"])
                        break
            apt = None
            if selected:
                req["request_outcome"]="Allocated internally"
                ec["triage_outcome"]="Book same-day appointment" if kind=="Same-day GP" else "Book routine appointment"
                when = datetime.fromisoformat(selected["slot_start_datetime"])
                status = rng.choices(["Attended","DNA","Cancelled by patient","Cancelled by practice"],[92,4,3,1])[0]
                cancelled = when-timedelta(minutes=rng.randint(1,10)) if status.startswith("Cancelled") else None
                selected["slot_status"]="Late cancellation" if cancelled else "Booked"
                apt = add("appointments", appointment_id=len(t["appointments"])+1, slot_id=selected["slot_id"],
                          patient_id=patient, request_id=rid, booked_datetime=iso(decision_time),
                          booking_channel="eConsult triage", appointment_reason=ec["category"], attendance_status=status,
                          outcome=rng.choice(["Advice given","Prescription issued","Follow-up planned","Referral made"]) if status=="Attended" else "No consultation",
                          econsult_id=rid, cancelled_datetime=iso(cancelled) if cancelled else None)
                events = [(decision_time,"Appointment allocated"), (when, "Consultation started" if status=="Attended" else "DNA" if status=="DNA" else "Slot not used")]
                reminder = max(decision_time,when-timedelta(days=1))
                if reminder<when:
                    events.append((reminder,"Reminder sent"))
                if cancelled:
                    events.append((cancelled,status))
                if status=="Attended":
                    events.append((when+timedelta(minutes=15),"Consultation completed"))
                for at, event in sorted(events):
                    add("appointment_activity_log", appointment_activity_log_id=len(t["appointment_activity_log"])+1,
                        appointment_id=apt["appointment_id"], event_datetime=iso(at), event_type=event,
                        event_channel="Clinical system" if at>=when else "SMS" if event=="Reminder sent" else "Reception",
                        event_actor="Clinician" if at>=when else "Reception")
            elif needs_gp and deadline>asof:
                req["request_outcome"]="Pending"
                req["non_allocation_reason"]="Deadline after reporting cutoff"
                ec["triage_outcome"]="Pending allocation"
            elif needs_gp:
                req["request_outcome"]="Signposted due to capacity"
                req["non_allocation_reason"]="No suitable capacity by required date"
                ec["triage_outcome"]="Signposted"
                ec["signposting_reason"]="Practice capacity reached"
                ec["signposting_destination"]=rng.choices(["PCN support appointments","NHS 111"],[65,35])[0]
                confirmed=ec["signposting_destination"]=="PCN support appointments" and rng.random()<.45
                req["external_care_status"]="Confirmed external booking" if confirmed else "Advised; receipt unknown"
                if confirmed:
                    req["external_appointment_datetime"]=iso(decision_time+timedelta(hours=2)) if kind=="Same-day GP" else iso(dt(d+timedelta(days=3),14))
            else:
                req["request_outcome"]="Appropriate signposting"
                ec["triage_outcome"]="Signposted"
                ec["signposting_reason"]="Appropriate care pathway"
                ec["signposting_destination"]=rng.choice(["Community pharmacy","Practice nurse","Self-care advice","NHS 111"])
                req["external_care_status"]="Advised; receipt unknown"
                ec["resolved_without_appointment"]=int(ec["signposting_destination"]=="Self-care advice")
            audit(req, decision_time, "Allocation decision", outcome=req["request_outcome"],
                  appointment_id=apt["appointment_id"] if apt else None, slot_id=selected["slot_id"] if selected else None,
                  non_allocation_reason=req["non_allocation_reason"], external_care_status=req["external_care_status"],
                  signposting_destination=ec["signposting_destination"], capacity_search=searched)
            for i,(at,out) in enumerate(call_outcomes,1):
                add("outgoing_call_attempts", outgoing_call_attempt_id=len(t["outgoing_call_attempts"])+1,
                    patient_id=patient, request_id=rid, econsult_id=rid, appointment_id=apt["appointment_id"] if apt else None,
                    attempt_datetime=iso(at), attempt_number=i, call_reason="Triage outcome follow-up",
                    call_outcome=out, appointment_booked_after_call=int(bool(apt) and out=="Answered"))
                audit(req, at, "Outbound contact attempt", attempt=i, outcome=out)
            audit(req, decision_time, "Outcome notification", outcome=req["request_outcome"],
                  channel="Telephone" if call_outcomes[-1][1]=="Answered" else "SMS",
                  confirmation="Communicated" if call_outcomes[-1][1]=="Answered" else "SMS sent; receipt unknown")
            repeat_prob=.28 if req["request_outcome"]=="Signposted due to capacity" else .05
            repeat_contact=rng.random()<repeat_prob
            if repeat_contact:
                at=decision_time+timedelta(minutes=rng.randint(20,120))
                call(at,patient,rid,intent=int(needs_gp),reason="Repeat contact about existing request")
                calls[-1]["allocation_status_at_call"]=req["request_outcome"]
            # Complaints follow documented experiences and reporting delays, not a fixed share of demand.
            triggers=[]
            if req['request_outcome']=='Signposted due to capacity':
                triggers.append(("Capacity-related signposting",decision_time,.030,"Appointment access"))
            if apt:
                if apt['attendance_status']=='Cancelled by practice':
                    triggers.append(("Practice cancellation",datetime.fromisoformat(apt['cancelled_datetime']),.13,"Appointment access"))
                waiting=(datetime.fromisoformat(selected['slot_start_datetime'])-decision_time).days
                if waiting>=7:
                    triggers.append(("Long routine wait",decision_time,.014 if waiting<11 else .025,"Appointment access"))
            if repeat_contact and needs_gp:
                triggers.append(("Repeated contact for access",at,.014,"Appointment access"))
            if call_outcomes[-1][1]!='Answered':
                triggers.append(("Difficulty receiving triage outcome",decision_time,.025,"Communication"))
            complaint=None
            multiplier=complaint_month_factors[d.strftime('%Y-%m')]
            for trigger,trigger_time,probability,category in triggers:
                if complaints_rng.random()<min(.3,probability*multiplier):
                    complaint=(trigger,trigger_time,category)
                    break
            if complaint:
                trigger,trigger_time,category=complaint
                complaint_day=trigger_time.date()+timedelta(days=complaints_rng.randint(1,35))
            if complaint and complaint_day<=end:
                add("patient_complaints", complaint_id=len(t["patient_complaints"])+1, patient_id=patient,
                    request_id=rid, complaint_date=iso(complaint_day), complaint_category=category,
                    complaint_trigger=trigger,trigger_datetime=iso(trigger_time),
                    complaint_text_summary=trigger+" linked to recorded request experience",
                    related_appointment_id=apt["appointment_id"] if apt else None, related_econsult_id=rid,
                    severity=complaints_rng.choices(["Low","Medium","High"],[25,65,10])[0], status="Open" if (end-complaint_day).days<14 else "Closed")
        additional=max(1,round(rng.gauss(240*factor*scale,18*scale)))
        for _ in range(additional):
            hour=rng.choices(list(range(8,18)),[22,18,12,10,8,7,7,6,6,4])[0]
            at=dt(d,hour,rng.randint(0,59))+timedelta(seconds=rng.randint(0,59))
            outcome="Abandoned" if rng.random() < (.30 if hour<10 else .15) else "Answered"
            call(at, rng.choice(patient_pool) if outcome=="Answered" else None, outcome=outcome,
                 intent=0 if outcome=="Answered" else None,
                 reason=rng.choice(["Prescription query","Test result enquiry","Administrative query"]) if outcome=="Answered" else "Unknown")
    groups=defaultdict(list)
    for row in sorted(calls,key=lambda r:r["call_datetime"]):
        groups[(row["call_datetime"][:10],int(row["call_datetime"][11:13]))].append(row)
    for (d,hour), arr in sorted(groups.items()):
        volume=len(t["incoming_call_volumes"])+1
        answered=sum(r["call_outcome"]=="Answered" for r in arr)
        add("incoming_call_volumes", incoming_call_volume_id=volume, call_date=d, hour_start=hour,
            calls_offered=len(arr), calls_answered=answered, calls_abandoned=len(arr)-answered,
            average_wait_seconds=round(sum(r["wait_seconds"] for r in arr)/len(arr),4))
        for row in arr:
            eid=len(t["incoming_call_events"])+1
            add("incoming_call_events", incoming_call_event_id=eid, incoming_call_volume_id=volume,
                **row, synthetic_call_reference=hashlib.sha256(f"{seed}-call-{eid}".encode()).hexdigest()[:24])
    return t, {"version":"2.1", "profile":profile, "seed":seed, "start_date":iso(start), "end_date":iso(end),
               "as_of_datetime":iso(asof), "population":population, "synthetic":True,
               "monthly_telephone_seasonal_factors":SEASONS, "request_pathway_factors":PATHWAY_SEASONS,
               "request_pathway_daily_bases":PATHWAY_BASE,
               "utilisation_assumption":"Capacity constrained; summer demand dip, no forced 60% utilisation target",
               "scenario":"Fictional eConsult-led practice, not an NHS-wide benchmark"}
