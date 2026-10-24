-- DESTRUCTIVE rebuild of named PracticeHUB tables. Take a MySQL backup first.
-- DESTRUCTIVE: rebuilds PracticeHUB v2 tables. Back up MySQL before running.
CREATE DATABASE IF NOT EXISTS practicehub CHARACTER SET utf8mb4;
USE practicehub;
USE practicehub;
DROP VIEW IF EXISTS vw_executive_kpis_latest_month;
DROP VIEW IF EXISTS vw_monthly_gp_capacity;
DROP VIEW IF EXISTS vw_monthly_econsults;
DROP VIEW IF EXISTS vw_monthly_telephone;
DROP VIEW IF EXISTS vw_monthly_access_complaints;
DROP VIEW IF EXISTS vw_monthly_outgoing_calls;
DROP VIEW IF EXISTS vw_monthly_core_kpis;
DROP TABLE IF EXISTS monthly_kpis;
DROP TABLE IF EXISTS request_activity_log;
DROP TABLE IF EXISTS appointment_activity_log;
DROP TABLE IF EXISTS patient_complaints;
DROP TABLE IF EXISTS outgoing_call_attempts;
DROP TABLE IF EXISTS incoming_call_events;
DROP TABLE IF EXISTS incoming_call_volumes;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS econsult_requests;
DROP TABLE IF EXISTS appointment_requests;
DROP TABLE IF EXISTS appointment_slots;
DROP TABLE IF EXISTS clinic_sessions;
DROP TABLE IF EXISTS clinician_absences;
DROP TABLE IF EXISTS practice_calendar;
DROP TABLE IF EXISTS clinicians;
DROP TABLE IF EXISTS patients;
CREATE TABLE patients (patient_id INTEGER PRIMARY KEY, nhs_number_hash VARCHAR(64) NOT NULL UNIQUE,
        sex VARCHAR(20) NOT NULL, date_of_birth DATE NOT NULL, age_band VARCHAR(20) NOT NULL,
        postcode_district VARCHAR(10) NOT NULL, registration_date DATE NOT NULL,
        is_active INTEGER NOT NULL CHECK(is_active IN (0,1))) ENGINE=InnoDB;
CREATE TABLE clinicians (clinician_id INTEGER PRIMARY KEY, clinician_name VARCHAR(100) NOT NULL,
        role VARCHAR(50) NOT NULL, fte REAL NOT NULL, working_pattern VARCHAR(100) NOT NULL,
        usual_session_minutes INTEGER NOT NULL, is_gp INTEGER NOT NULL,
        active_from DATE NOT NULL, active_to DATE) ENGINE=InnoDB;
CREATE TABLE practice_calendar (calendar_date DATE PRIMARY KEY, is_open INTEGER NOT NULL,
        closure_reason VARCHAR(100), seasonal_factor REAL NOT NULL) ENGINE=InnoDB;
CREATE TABLE clinician_absences (absence_id INTEGER PRIMARY KEY, clinician_id INTEGER NOT NULL,
        absence_date DATE NOT NULL, absence_reason VARCHAR(50) NOT NULL,
        FOREIGN KEY(clinician_id) REFERENCES clinicians(clinician_id)) ENGINE=InnoDB;
CREATE TABLE clinic_sessions (session_id INTEGER PRIMARY KEY, clinician_id INTEGER NOT NULL,
        session_date DATE NOT NULL, session_type VARCHAR(20) NOT NULL,
        start_time VARCHAR(8) NOT NULL, end_time VARCHAR(8) NOT NULL,
        planned_slots INTEGER NOT NULL, session_minutes INTEGER NOT NULL,
        delivery_mode VARCHAR(30) NOT NULL, FOREIGN KEY(clinician_id) REFERENCES clinicians(clinician_id)) ENGINE=InnoDB;
CREATE TABLE appointment_slots (slot_id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL,
        slot_start_datetime DATETIME NOT NULL, slot_end_datetime DATETIME NOT NULL,
        slot_type VARCHAR(30) NOT NULL, slot_status VARCHAR(30) NOT NULL,
        is_bookable INTEGER NOT NULL CHECK(is_bookable IN (0,1)),
        FOREIGN KEY(session_id) REFERENCES clinic_sessions(session_id)) ENGINE=InnoDB;
CREATE TABLE appointment_requests (request_id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL,
        requested_datetime DATETIME NOT NULL, original_contact_channel VARCHAR(30) NOT NULL,
        required_clinician_type VARCHAR(30) NOT NULL, required_appointment_type VARCHAR(30),
        required_by_datetime DATETIME, request_outcome VARCHAR(50) NOT NULL,
        non_allocation_reason VARCHAR(100), external_care_status VARCHAR(50) NOT NULL,
        external_appointment_datetime DATETIME, FOREIGN KEY(patient_id) REFERENCES patients(patient_id)) ENGINE=InnoDB;
CREATE TABLE econsult_requests (econsult_id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL UNIQUE,
        patient_id INTEGER NOT NULL, submitted_datetime DATETIME NOT NULL,
        original_contact_channel VARCHAR(30) NOT NULL, submitted_by_role VARCHAR(30) NOT NULL,
        category VARCHAR(50) NOT NULL, urgency_level VARCHAR(20) NOT NULL,
        triaged_datetime DATETIME NOT NULL, triage_outcome VARCHAR(50) NOT NULL,
        gp_appointment_recommended INTEGER NOT NULL, resolved_without_appointment INTEGER NOT NULL,
        signposting_reason VARCHAR(100), signposting_destination VARCHAR(80),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id)) ENGINE=InnoDB;
CREATE TABLE appointments (appointment_id INTEGER PRIMARY KEY, slot_id INTEGER NOT NULL UNIQUE,
        patient_id INTEGER NOT NULL, request_id INTEGER NOT NULL UNIQUE,
        booked_datetime DATETIME NOT NULL, booking_channel VARCHAR(40) NOT NULL,
        appointment_reason VARCHAR(50) NOT NULL, attendance_status VARCHAR(40) NOT NULL,
        outcome VARCHAR(80) NOT NULL, econsult_id INTEGER NOT NULL UNIQUE,
        cancelled_datetime DATETIME, FOREIGN KEY(slot_id) REFERENCES appointment_slots(slot_id),
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(econsult_id) REFERENCES econsult_requests(econsult_id)) ENGINE=InnoDB;
CREATE TABLE incoming_call_volumes (incoming_call_volume_id INTEGER PRIMARY KEY, call_date DATE NOT NULL,
        hour_start INTEGER NOT NULL, calls_offered INTEGER NOT NULL,
        calls_answered INTEGER NOT NULL, calls_abandoned INTEGER NOT NULL,
        average_wait_seconds REAL NOT NULL, UNIQUE(call_date,hour_start)) ENGINE=InnoDB;
CREATE TABLE incoming_call_events (incoming_call_event_id INTEGER PRIMARY KEY,
        incoming_call_volume_id INTEGER NOT NULL, patient_id INTEGER, request_id INTEGER,
        call_datetime DATETIME NOT NULL, queue_name VARCHAR(50) NOT NULL,
        call_reason VARCHAR(60) NOT NULL, call_outcome VARCHAR(20) NOT NULL,
        wait_seconds INTEGER NOT NULL, talk_seconds INTEGER NOT NULL,
        booking_intent INTEGER, appointment_booked INTEGER NOT NULL,
        allocation_status_at_call VARCHAR(50) NOT NULL, synthetic_call_reference VARCHAR(64) NOT NULL,
        FOREIGN KEY(incoming_call_volume_id) REFERENCES incoming_call_volumes(incoming_call_volume_id),
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id)) ENGINE=InnoDB;
CREATE TABLE outgoing_call_attempts (outgoing_call_attempt_id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL, request_id INTEGER NOT NULL, econsult_id INTEGER NOT NULL,
        appointment_id INTEGER, attempt_datetime DATETIME NOT NULL, attempt_number INTEGER NOT NULL,
        call_reason VARCHAR(60) NOT NULL, call_outcome VARCHAR(30) NOT NULL,
        appointment_booked_after_call INTEGER NOT NULL,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(econsult_id) REFERENCES econsult_requests(econsult_id),
        FOREIGN KEY(appointment_id) REFERENCES appointments(appointment_id)) ENGINE=InnoDB;
CREATE TABLE patient_complaints (complaint_id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL,
        request_id INTEGER NOT NULL, complaint_date DATE NOT NULL, complaint_category VARCHAR(50) NOT NULL,
        complaint_trigger VARCHAR(80) NOT NULL, trigger_datetime DATETIME NOT NULL,
        complaint_text_summary VARCHAR(255) NOT NULL, related_appointment_id INTEGER,
        related_econsult_id INTEGER NOT NULL, severity VARCHAR(20) NOT NULL, status VARCHAR(20) NOT NULL,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(related_appointment_id) REFERENCES appointments(appointment_id),
        FOREIGN KEY(related_econsult_id) REFERENCES econsult_requests(econsult_id)) ENGINE=InnoDB;
CREATE TABLE appointment_activity_log (appointment_activity_log_id INTEGER PRIMARY KEY,
        appointment_id INTEGER NOT NULL, event_datetime DATETIME NOT NULL,
        event_type VARCHAR(60) NOT NULL, event_channel VARCHAR(50) NOT NULL,
        event_actor VARCHAR(80) NOT NULL,
        FOREIGN KEY(appointment_id) REFERENCES appointments(appointment_id)) ENGINE=InnoDB;
CREATE TABLE request_activity_log (request_activity_log_id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL,
        event_datetime DATETIME NOT NULL, event_type VARCHAR(60) NOT NULL,
        event_actor VARCHAR(80) NOT NULL, event_payload TEXT NOT NULL,
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id)) ENGINE=InnoDB;
CREATE TABLE monthly_kpis (kpi_month VARCHAR(7) PRIMARY KEY,
registered_patients INTEGER,
gp_sessions INTEGER,
gp_slots_total INTEGER,
gp_slots_bookable INTEGER,
gp_slots_booked INTEGER,
gp_slot_utilisation_pct REAL,
appointments_attended INTEGER,
appointments_dna INTEGER,
dna_rate_pct REAL,
appointments_cancelled INTEGER,
econsult_requests INTEGER,
econsults_gp_recommended INTEGER,
econsults_resolved_without_appointment INTEGER,
incoming_calls_offered INTEGER,
incoming_calls_answered INTEGER,
incoming_calls_abandoned INTEGER,
incoming_call_answer_rate_pct REAL,
average_wait_seconds REAL,
outgoing_call_attempts INTEGER,
outgoing_calls_answered INTEGER,
outgoing_call_answer_rate_pct REAL,
appointments_booked_after_outgoing_call INTEGER,
access_complaints INTEGER,
access_complaints_per_1000_patients REAL,
synthetic_data_label VARCHAR(100),
gp_requests INTEGER,
same_day_gp_requests INTEGER,
routine_gp_requests INTEGER,
capacity_diverted_requests INTEGER,
capacity_diverted_patients INTEGER,
unmet_gp_requests INTEGER,
patients_without_appointment INTEGER,
pending_gp_requests INTEGER,
gp_requests_allocated_on_time_pct REAL,
appropriate_signposted_requests INTEGER,
confirmed_external_bookings INTEGER,
morning_call_gp_requests INTEGER,
morning_call_unallocated_patients INTEGER,
econsult_online_unallocated_patients INTEGER,
same_day_capacity_diverted INTEGER,
routine_capacity_diverted INTEGER) ENGINE=InnoDB;
CREATE INDEX idx_slots_session ON appointment_slots (session_id);
CREATE INDEX idx_slots_time_type ON appointment_slots (slot_type,slot_start_datetime);
CREATE INDEX idx_sessions_date ON clinic_sessions (session_date);
CREATE INDEX idx_requests_patient ON appointment_requests (patient_id);
CREATE INDEX idx_requests_date ON appointment_requests (requested_datetime);
CREATE INDEX idx_calls_request ON incoming_call_events (request_id);
CREATE INDEX idx_calls_volume ON incoming_call_events (incoming_call_volume_id);
CREATE INDEX idx_outgoing_request ON outgoing_call_attempts (request_id);
CREATE INDEX idx_request_log_request ON request_activity_log (request_id);
CREATE INDEX idx_appt_log_appt ON appointment_activity_log (appointment_id);

-- Run only after mysql_schema.sql (v2). Foreign keys remain enabled.
USE practicehub;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/patients.csv' INTO TABLE patients
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@patient_id, @nhs_number_hash, @sex, @date_of_birth, @age_band, @postcode_district, @registration_date, @is_active) SET patient_id=NULLIF(@patient_id,''), nhs_number_hash=NULLIF(@nhs_number_hash,''), sex=NULLIF(@sex,''), date_of_birth=NULLIF(@date_of_birth,''), age_band=NULLIF(@age_band,''), postcode_district=NULLIF(@postcode_district,''), registration_date=NULLIF(@registration_date,''), is_active=NULLIF(@is_active,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/clinicians.csv' INTO TABLE clinicians
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@clinician_id, @clinician_name, @role, @fte, @working_pattern, @usual_session_minutes, @is_gp, @active_from, @active_to) SET clinician_id=NULLIF(@clinician_id,''), clinician_name=NULLIF(@clinician_name,''), role=NULLIF(@role,''), fte=NULLIF(@fte,''), working_pattern=NULLIF(@working_pattern,''), usual_session_minutes=NULLIF(@usual_session_minutes,''), is_gp=NULLIF(@is_gp,''), active_from=NULLIF(@active_from,''), active_to=NULLIF(@active_to,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/practice_calendar.csv' INTO TABLE practice_calendar
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@calendar_date, @is_open, @closure_reason, @seasonal_factor) SET calendar_date=NULLIF(@calendar_date,''), is_open=NULLIF(@is_open,''), closure_reason=NULLIF(@closure_reason,''), seasonal_factor=NULLIF(@seasonal_factor,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/clinician_absences.csv' INTO TABLE clinician_absences
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@absence_id, @clinician_id, @absence_date, @absence_reason) SET absence_id=NULLIF(@absence_id,''), clinician_id=NULLIF(@clinician_id,''), absence_date=NULLIF(@absence_date,''), absence_reason=NULLIF(@absence_reason,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/clinic_sessions.csv' INTO TABLE clinic_sessions
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@session_id, @clinician_id, @session_date, @session_type, @start_time, @end_time, @planned_slots, @session_minutes, @delivery_mode) SET session_id=NULLIF(@session_id,''), clinician_id=NULLIF(@clinician_id,''), session_date=NULLIF(@session_date,''), session_type=NULLIF(@session_type,''), start_time=NULLIF(@start_time,''), end_time=NULLIF(@end_time,''), planned_slots=NULLIF(@planned_slots,''), session_minutes=NULLIF(@session_minutes,''), delivery_mode=NULLIF(@delivery_mode,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/appointment_slots.csv' INTO TABLE appointment_slots
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@slot_id, @session_id, @slot_start_datetime, @slot_end_datetime, @slot_type, @slot_status, @is_bookable) SET slot_id=NULLIF(@slot_id,''), session_id=NULLIF(@session_id,''), slot_start_datetime=NULLIF(@slot_start_datetime,''), slot_end_datetime=NULLIF(@slot_end_datetime,''), slot_type=NULLIF(@slot_type,''), slot_status=NULLIF(@slot_status,''), is_bookable=NULLIF(@is_bookable,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/appointment_requests.csv' INTO TABLE appointment_requests
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@request_id, @patient_id, @requested_datetime, @original_contact_channel, @required_clinician_type, @required_appointment_type, @required_by_datetime, @request_outcome, @non_allocation_reason, @external_care_status, @external_appointment_datetime) SET request_id=NULLIF(@request_id,''), patient_id=NULLIF(@patient_id,''), requested_datetime=NULLIF(@requested_datetime,''), original_contact_channel=NULLIF(@original_contact_channel,''), required_clinician_type=NULLIF(@required_clinician_type,''), required_appointment_type=NULLIF(@required_appointment_type,''), required_by_datetime=NULLIF(@required_by_datetime,''), request_outcome=NULLIF(@request_outcome,''), non_allocation_reason=NULLIF(@non_allocation_reason,''), external_care_status=NULLIF(@external_care_status,''), external_appointment_datetime=NULLIF(@external_appointment_datetime,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/econsult_requests.csv' INTO TABLE econsult_requests
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@econsult_id, @request_id, @patient_id, @submitted_datetime, @original_contact_channel, @submitted_by_role, @category, @urgency_level, @triaged_datetime, @triage_outcome, @gp_appointment_recommended, @resolved_without_appointment, @signposting_reason, @signposting_destination) SET econsult_id=NULLIF(@econsult_id,''), request_id=NULLIF(@request_id,''), patient_id=NULLIF(@patient_id,''), submitted_datetime=NULLIF(@submitted_datetime,''), original_contact_channel=NULLIF(@original_contact_channel,''), submitted_by_role=NULLIF(@submitted_by_role,''), category=NULLIF(@category,''), urgency_level=NULLIF(@urgency_level,''), triaged_datetime=NULLIF(@triaged_datetime,''), triage_outcome=NULLIF(@triage_outcome,''), gp_appointment_recommended=NULLIF(@gp_appointment_recommended,''), resolved_without_appointment=NULLIF(@resolved_without_appointment,''), signposting_reason=NULLIF(@signposting_reason,''), signposting_destination=NULLIF(@signposting_destination,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/appointments.csv' INTO TABLE appointments
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@appointment_id, @slot_id, @patient_id, @request_id, @booked_datetime, @booking_channel, @appointment_reason, @attendance_status, @outcome, @econsult_id, @cancelled_datetime) SET appointment_id=NULLIF(@appointment_id,''), slot_id=NULLIF(@slot_id,''), patient_id=NULLIF(@patient_id,''), request_id=NULLIF(@request_id,''), booked_datetime=NULLIF(@booked_datetime,''), booking_channel=NULLIF(@booking_channel,''), appointment_reason=NULLIF(@appointment_reason,''), attendance_status=NULLIF(@attendance_status,''), outcome=NULLIF(@outcome,''), econsult_id=NULLIF(@econsult_id,''), cancelled_datetime=NULLIF(@cancelled_datetime,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/incoming_call_volumes.csv' INTO TABLE incoming_call_volumes
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@incoming_call_volume_id, @call_date, @hour_start, @calls_offered, @calls_answered, @calls_abandoned, @average_wait_seconds) SET incoming_call_volume_id=NULLIF(@incoming_call_volume_id,''), call_date=NULLIF(@call_date,''), hour_start=NULLIF(@hour_start,''), calls_offered=NULLIF(@calls_offered,''), calls_answered=NULLIF(@calls_answered,''), calls_abandoned=NULLIF(@calls_abandoned,''), average_wait_seconds=NULLIF(@average_wait_seconds,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/incoming_call_events.csv' INTO TABLE incoming_call_events
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@incoming_call_event_id, @incoming_call_volume_id, @patient_id, @request_id, @call_datetime, @queue_name, @call_reason, @call_outcome, @wait_seconds, @talk_seconds, @booking_intent, @appointment_booked, @allocation_status_at_call, @synthetic_call_reference) SET incoming_call_event_id=NULLIF(@incoming_call_event_id,''), incoming_call_volume_id=NULLIF(@incoming_call_volume_id,''), patient_id=NULLIF(@patient_id,''), request_id=NULLIF(@request_id,''), call_datetime=NULLIF(@call_datetime,''), queue_name=NULLIF(@queue_name,''), call_reason=NULLIF(@call_reason,''), call_outcome=NULLIF(@call_outcome,''), wait_seconds=NULLIF(@wait_seconds,''), talk_seconds=NULLIF(@talk_seconds,''), booking_intent=NULLIF(@booking_intent,''), appointment_booked=NULLIF(@appointment_booked,''), allocation_status_at_call=NULLIF(@allocation_status_at_call,''), synthetic_call_reference=NULLIF(@synthetic_call_reference,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/outgoing_call_attempts.csv' INTO TABLE outgoing_call_attempts
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@outgoing_call_attempt_id, @patient_id, @request_id, @econsult_id, @appointment_id, @attempt_datetime, @attempt_number, @call_reason, @call_outcome, @appointment_booked_after_call) SET outgoing_call_attempt_id=NULLIF(@outgoing_call_attempt_id,''), patient_id=NULLIF(@patient_id,''), request_id=NULLIF(@request_id,''), econsult_id=NULLIF(@econsult_id,''), appointment_id=NULLIF(@appointment_id,''), attempt_datetime=NULLIF(@attempt_datetime,''), attempt_number=NULLIF(@attempt_number,''), call_reason=NULLIF(@call_reason,''), call_outcome=NULLIF(@call_outcome,''), appointment_booked_after_call=NULLIF(@appointment_booked_after_call,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/patient_complaints.csv' INTO TABLE patient_complaints
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@complaint_id, @patient_id, @request_id, @complaint_date, @complaint_category, @complaint_trigger, @trigger_datetime, @complaint_text_summary, @related_appointment_id, @related_econsult_id, @severity, @status) SET complaint_id=NULLIF(@complaint_id,''), patient_id=NULLIF(@patient_id,''), request_id=NULLIF(@request_id,''), complaint_date=NULLIF(@complaint_date,''), complaint_category=NULLIF(@complaint_category,''), complaint_trigger=NULLIF(@complaint_trigger,''), trigger_datetime=NULLIF(@trigger_datetime,''), complaint_text_summary=NULLIF(@complaint_text_summary,''), related_appointment_id=NULLIF(@related_appointment_id,''), related_econsult_id=NULLIF(@related_econsult_id,''), severity=NULLIF(@severity,''), status=NULLIF(@status,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/appointment_activity_log.csv' INTO TABLE appointment_activity_log
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@appointment_activity_log_id, @appointment_id, @event_datetime, @event_type, @event_channel, @event_actor) SET appointment_activity_log_id=NULLIF(@appointment_activity_log_id,''), appointment_id=NULLIF(@appointment_id,''), event_datetime=NULLIF(@event_datetime,''), event_type=NULLIF(@event_type,''), event_channel=NULLIF(@event_channel,''), event_actor=NULLIF(@event_actor,'');
SHOW COUNT(*) WARNINGS;

LOAD DATA LOCAL INFILE '/Users/barbaraafcaldeira/Documents/Big data module/data/raw/final/request_activity_log.csv' INTO TABLE request_activity_log
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(@request_activity_log_id, @request_id, @event_datetime, @event_type, @event_actor, @event_payload) SET request_activity_log_id=NULLIF(@request_activity_log_id,''), request_id=NULLIF(@request_id,''), event_datetime=NULLIF(@event_datetime,''), event_type=NULLIF(@event_type,''), event_actor=NULLIF(@event_actor,''), event_payload=NULLIF(@event_payload,'');
SHOW COUNT(*) WARNINGS;

-- Rebuild v2 KPI views and refresh the physical KPI table.
USE practicehub;
CREATE OR REPLACE VIEW vw_monthly_core_kpis AS 
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
;
CREATE OR REPLACE VIEW vw_monthly_gp_capacity AS SELECT kpi_month,gp_sessions,gp_slots_total,gp_slots_bookable,gp_slots_booked,gp_slot_utilisation_pct,appointments_attended,appointments_dna,dna_rate_pct,appointments_cancelled FROM vw_monthly_core_kpis;
CREATE OR REPLACE VIEW vw_monthly_econsults AS SELECT kpi_month,econsult_requests,econsults_gp_recommended,econsults_resolved_without_appointment,gp_requests,capacity_diverted_requests,appropriate_signposted_requests FROM vw_monthly_core_kpis;
CREATE OR REPLACE VIEW vw_monthly_telephone AS SELECT kpi_month,incoming_calls_offered,incoming_calls_answered,incoming_calls_abandoned,incoming_call_answer_rate_pct,average_wait_seconds,outgoing_call_attempts,outgoing_calls_answered,outgoing_call_answer_rate_pct,appointments_booked_after_outgoing_call FROM vw_monthly_core_kpis;
CREATE OR REPLACE VIEW vw_monthly_access_complaints AS SELECT kpi_month,access_complaints,access_complaints_per_1000_patients FROM vw_monthly_core_kpis;
CREATE OR REPLACE VIEW vw_monthly_outgoing_calls AS SELECT kpi_month,outgoing_call_attempts,outgoing_calls_answered,outgoing_call_answer_rate_pct,appointments_booked_after_outgoing_call FROM vw_monthly_core_kpis;
CREATE OR REPLACE VIEW vw_executive_kpis_latest_month AS SELECT * FROM vw_monthly_core_kpis WHERE kpi_month=(SELECT MAX(kpi_month) FROM vw_monthly_core_kpis);
START TRANSACTION;
DELETE FROM monthly_kpis;
INSERT INTO monthly_kpis SELECT * FROM vw_monthly_core_kpis;
COMMIT;
SELECT COUNT(*) AS monthly_kpi_rows FROM monthly_kpis;

USE practicehub;
SELECT 'request_missing_intake' AS check_name, (SELECT COUNT(*) FROM appointment_requests r LEFT JOIN econsult_requests e ON e.request_id=r.request_id WHERE e.econsult_id IS NULL) AS violations
UNION ALL
SELECT 'appointment_patient_mismatch' AS check_name, (SELECT COUNT(*) FROM appointments a JOIN appointment_requests r ON r.request_id=a.request_id JOIN econsult_requests e ON e.econsult_id=a.econsult_id WHERE a.patient_id<>r.patient_id OR a.patient_id<>e.patient_id OR a.request_id<>e.request_id) AS violations
UNION ALL
SELECT 'booking_before_triage_or_after_slot' AS check_name, (SELECT COUNT(*) FROM appointments a JOIN econsult_requests e ON e.econsult_id=a.econsult_id JOIN appointment_slots s ON s.slot_id=a.slot_id WHERE a.booked_datetime<e.triaged_datetime OR a.booked_datetime>s.slot_start_datetime OR a.cancelled_datetime<a.booked_datetime) AS violations
UNION ALL
SELECT 'wrong_slot_type_or_deadline' AS check_name, (SELECT COUNT(*) FROM appointments a JOIN appointment_requests r ON r.request_id=a.request_id JOIN appointment_slots s ON s.slot_id=a.slot_id WHERE s.slot_type<>r.required_appointment_type OR s.slot_start_datetime>r.required_by_datetime OR s.is_bookable=0) AS violations
UNION ALL
SELECT 'calls_patient_mismatch' AS check_name, (SELECT COUNT(*) FROM incoming_call_events i JOIN appointment_requests r ON r.request_id=i.request_id WHERE i.patient_id<>r.patient_id OR i.patient_id IS NULL) AS violations
UNION ALL
SELECT 'outbound_patient_or_time_mismatch' AS check_name, (SELECT COUNT(*) FROM outgoing_call_attempts o JOIN econsult_requests e ON e.econsult_id=o.econsult_id LEFT JOIN appointments a ON a.appointment_id=o.appointment_id WHERE o.patient_id<>e.patient_id OR o.request_id<>e.request_id OR o.attempt_datetime<e.triaged_datetime OR (a.appointment_id IS NOT NULL AND a.request_id<>o.request_id)) AS violations
UNION ALL
SELECT 'complaint_patient_or_date_mismatch' AS check_name, (SELECT COUNT(*) FROM patient_complaints p JOIN appointment_requests r ON r.request_id=p.request_id JOIN econsult_requests e ON e.econsult_id=p.related_econsult_id LEFT JOIN appointments a ON a.appointment_id=p.related_appointment_id WHERE p.patient_id<>r.patient_id OR e.request_id<>r.request_id OR SUBSTR(r.requested_datetime,1,10)>p.complaint_date OR SUBSTR(p.trigger_datetime,1,10)>p.complaint_date OR p.trigger_datetime<r.requested_datetime OR (a.appointment_id IS NOT NULL AND a.patient_id<>p.patient_id)) AS violations
UNION ALL
SELECT 'sessions_on_closed_days' AS check_name, (SELECT COUNT(*) FROM clinic_sessions s JOIN practice_calendar p ON p.calendar_date=s.session_date WHERE p.is_open=0) AS violations
UNION ALL
SELECT 'sessions_on_leave' AS check_name, (SELECT COUNT(*) FROM clinic_sessions s JOIN clinician_absences a ON a.clinician_id=s.clinician_id AND a.absence_date=s.session_date) AS violations
UNION ALL
SELECT 'invalid_patient_lifetime' AS check_name, (SELECT COUNT(*) FROM patients WHERE registration_date<date_of_birth) AS violations
UNION ALL
SELECT 'request_before_registration' AS check_name, (SELECT COUNT(*) FROM appointment_requests r JOIN patients p ON p.patient_id=r.patient_id WHERE SUBSTR(r.requested_datetime,1,10)<p.registration_date) AS violations
UNION ALL
SELECT 'inconsistent_triage_outcome' AS check_name, (SELECT COUNT(*) FROM econsult_requests e JOIN appointment_requests r ON r.request_id=e.request_id WHERE (e.signposting_reason='Practice capacity reached' AND r.request_outcome<>'Signposted due to capacity') OR (e.signposting_reason='Appropriate care pathway' AND r.required_clinician_type='GP')) AS violations
UNION ALL
SELECT 'external_booking_after_deadline' AS check_name, (SELECT COUNT(*) FROM appointment_requests WHERE external_care_status='Confirmed external booking' AND (external_appointment_datetime IS NULL OR external_appointment_datetime>required_by_datetime)) AS violations
UNION ALL
SELECT 'invalid_utilisation' AS check_name, (SELECT COUNT(*) FROM monthly_kpis WHERE gp_slot_utilisation_pct<0 OR gp_slot_utilisation_pct>100 OR gp_slots_booked>gp_slots_bookable) AS violations
UNION ALL
SELECT 'invalid_unknown_intent' AS check_name, (SELECT COUNT(*) FROM incoming_call_events WHERE call_outcome='Abandoned' AND (booking_intent IS NOT NULL OR talk_seconds<>0)) AS violations
UNION ALL
SELECT 'invalid_activity_chronology' AS check_name, (SELECT COUNT(*) FROM appointment_activity_log l JOIN appointments a ON a.appointment_id=l.appointment_id JOIN appointment_slots s ON s.slot_id=a.slot_id WHERE l.event_datetime<a.booked_datetime OR (l.event_type='Reminder sent' AND l.event_datetime>s.slot_start_datetime)) AS violations
UNION ALL
SELECT 'incorrect_slot_state' AS check_name, (SELECT COUNT(*) FROM appointment_slots s LEFT JOIN appointments a ON a.slot_id=s.slot_id WHERE (a.appointment_id IS NULL AND s.slot_status IN ('Booked','Late cancellation')) OR (a.appointment_id IS NOT NULL AND (s.is_bookable=0 OR s.slot_status NOT IN ('Booked','Late cancellation')))) AS violations
UNION ALL
SELECT 'patient_double_booking' AS check_name, (SELECT COUNT(*) FROM (SELECT a.patient_id,s.slot_start_datetime FROM appointments a JOIN appointment_slots s ON s.slot_id=a.slot_id GROUP BY a.patient_id,s.slot_start_datetime HAVING COUNT(*)>1) conflicts) AS violations;

SELECT 'patients' AS table_name, COUNT(*) AS row_count FROM patients
UNION ALL
SELECT 'clinicians' AS table_name, COUNT(*) AS row_count FROM clinicians
UNION ALL
SELECT 'practice_calendar' AS table_name, COUNT(*) AS row_count FROM practice_calendar
UNION ALL
SELECT 'clinician_absences' AS table_name, COUNT(*) AS row_count FROM clinician_absences
UNION ALL
SELECT 'clinic_sessions' AS table_name, COUNT(*) AS row_count FROM clinic_sessions
UNION ALL
SELECT 'appointment_slots' AS table_name, COUNT(*) AS row_count FROM appointment_slots
UNION ALL
SELECT 'appointment_requests' AS table_name, COUNT(*) AS row_count FROM appointment_requests
UNION ALL
SELECT 'econsult_requests' AS table_name, COUNT(*) AS row_count FROM econsult_requests
UNION ALL
SELECT 'appointments' AS table_name, COUNT(*) AS row_count FROM appointments
UNION ALL
SELECT 'incoming_call_volumes' AS table_name, COUNT(*) AS row_count FROM incoming_call_volumes
UNION ALL
SELECT 'incoming_call_events' AS table_name, COUNT(*) AS row_count FROM incoming_call_events
UNION ALL
SELECT 'outgoing_call_attempts' AS table_name, COUNT(*) AS row_count FROM outgoing_call_attempts
UNION ALL
SELECT 'patient_complaints' AS table_name, COUNT(*) AS row_count FROM patient_complaints
UNION ALL
SELECT 'appointment_activity_log' AS table_name, COUNT(*) AS row_count FROM appointment_activity_log
UNION ALL
SELECT 'request_activity_log' AS table_name, COUNT(*) AS row_count FROM request_activity_log
UNION ALL
SELECT 'monthly_kpis' AS table_name, COUNT(*) AS row_count FROM monthly_kpis;
