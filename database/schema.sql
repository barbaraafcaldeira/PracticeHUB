-- Generated from src/practicehub/dataset_v2.py
PRAGMA foreign_keys=ON;
CREATE TABLE patients (patient_id INTEGER PRIMARY KEY, nhs_number_hash VARCHAR(64) NOT NULL UNIQUE,
        sex VARCHAR(20) NOT NULL, date_of_birth DATE NOT NULL, age_band VARCHAR(20) NOT NULL,
        postcode_district VARCHAR(10) NOT NULL, registration_date DATE NOT NULL,
        is_active INTEGER NOT NULL CHECK(is_active IN (0,1)));
CREATE TABLE clinicians (clinician_id INTEGER PRIMARY KEY, clinician_name VARCHAR(100) NOT NULL,
        role VARCHAR(50) NOT NULL, fte REAL NOT NULL, working_pattern VARCHAR(100) NOT NULL,
        usual_session_minutes INTEGER NOT NULL, is_gp INTEGER NOT NULL,
        active_from DATE NOT NULL, active_to DATE);
CREATE TABLE practice_calendar (calendar_date DATE PRIMARY KEY, is_open INTEGER NOT NULL,
        closure_reason VARCHAR(100), seasonal_factor REAL NOT NULL);
CREATE TABLE clinician_absences (absence_id INTEGER PRIMARY KEY, clinician_id INTEGER NOT NULL,
        absence_date DATE NOT NULL, absence_reason VARCHAR(50) NOT NULL,
        FOREIGN KEY(clinician_id) REFERENCES clinicians(clinician_id));
CREATE TABLE clinic_sessions (session_id INTEGER PRIMARY KEY, clinician_id INTEGER NOT NULL,
        session_date DATE NOT NULL, session_type VARCHAR(20) NOT NULL,
        start_time VARCHAR(8) NOT NULL, end_time VARCHAR(8) NOT NULL,
        planned_slots INTEGER NOT NULL, session_minutes INTEGER NOT NULL,
        delivery_mode VARCHAR(30) NOT NULL, FOREIGN KEY(clinician_id) REFERENCES clinicians(clinician_id));
CREATE TABLE appointment_slots (slot_id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL,
        slot_start_datetime DATETIME NOT NULL, slot_end_datetime DATETIME NOT NULL,
        slot_type VARCHAR(30) NOT NULL, slot_status VARCHAR(30) NOT NULL,
        is_bookable INTEGER NOT NULL CHECK(is_bookable IN (0,1)),
        FOREIGN KEY(session_id) REFERENCES clinic_sessions(session_id));
CREATE TABLE appointment_requests (request_id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL,
        requested_datetime DATETIME NOT NULL, original_contact_channel VARCHAR(30) NOT NULL,
        required_clinician_type VARCHAR(30) NOT NULL, required_appointment_type VARCHAR(30),
        required_by_datetime DATETIME, request_outcome VARCHAR(50) NOT NULL,
        non_allocation_reason VARCHAR(100), external_care_status VARCHAR(50) NOT NULL,
        external_appointment_datetime DATETIME, FOREIGN KEY(patient_id) REFERENCES patients(patient_id));
CREATE TABLE econsult_requests (econsult_id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL UNIQUE,
        patient_id INTEGER NOT NULL, submitted_datetime DATETIME NOT NULL,
        original_contact_channel VARCHAR(30) NOT NULL, submitted_by_role VARCHAR(30) NOT NULL,
        category VARCHAR(50) NOT NULL, urgency_level VARCHAR(20) NOT NULL,
        triaged_datetime DATETIME NOT NULL, triage_outcome VARCHAR(50) NOT NULL,
        gp_appointment_recommended INTEGER NOT NULL, resolved_without_appointment INTEGER NOT NULL,
        signposting_reason VARCHAR(100), signposting_destination VARCHAR(80),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id));
CREATE TABLE appointments (appointment_id INTEGER PRIMARY KEY, slot_id INTEGER NOT NULL UNIQUE,
        patient_id INTEGER NOT NULL, request_id INTEGER NOT NULL UNIQUE,
        booked_datetime DATETIME NOT NULL, booking_channel VARCHAR(40) NOT NULL,
        appointment_reason VARCHAR(50) NOT NULL, attendance_status VARCHAR(40) NOT NULL,
        outcome VARCHAR(80) NOT NULL, econsult_id INTEGER NOT NULL UNIQUE,
        cancelled_datetime DATETIME, FOREIGN KEY(slot_id) REFERENCES appointment_slots(slot_id),
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(econsult_id) REFERENCES econsult_requests(econsult_id));
CREATE TABLE incoming_call_volumes (incoming_call_volume_id INTEGER PRIMARY KEY, call_date DATE NOT NULL,
        hour_start INTEGER NOT NULL, calls_offered INTEGER NOT NULL,
        calls_answered INTEGER NOT NULL, calls_abandoned INTEGER NOT NULL,
        average_wait_seconds REAL NOT NULL, UNIQUE(call_date,hour_start));
CREATE TABLE incoming_call_events (incoming_call_event_id INTEGER PRIMARY KEY,
        incoming_call_volume_id INTEGER NOT NULL, patient_id INTEGER, request_id INTEGER,
        call_datetime DATETIME NOT NULL, queue_name VARCHAR(50) NOT NULL,
        call_reason VARCHAR(60) NOT NULL, call_outcome VARCHAR(20) NOT NULL,
        wait_seconds INTEGER NOT NULL, talk_seconds INTEGER NOT NULL,
        booking_intent INTEGER, appointment_booked INTEGER NOT NULL,
        allocation_status_at_call VARCHAR(50) NOT NULL, synthetic_call_reference VARCHAR(64) NOT NULL,
        FOREIGN KEY(incoming_call_volume_id) REFERENCES incoming_call_volumes(incoming_call_volume_id),
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id));
CREATE TABLE outgoing_call_attempts (outgoing_call_attempt_id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL, request_id INTEGER NOT NULL, econsult_id INTEGER NOT NULL,
        appointment_id INTEGER, attempt_datetime DATETIME NOT NULL, attempt_number INTEGER NOT NULL,
        call_reason VARCHAR(60) NOT NULL, call_outcome VARCHAR(30) NOT NULL,
        appointment_booked_after_call INTEGER NOT NULL,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(econsult_id) REFERENCES econsult_requests(econsult_id),
        FOREIGN KEY(appointment_id) REFERENCES appointments(appointment_id));
CREATE TABLE patient_complaints (complaint_id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL,
        request_id INTEGER NOT NULL, complaint_date DATE NOT NULL, complaint_category VARCHAR(50) NOT NULL,
        complaint_trigger VARCHAR(80) NOT NULL, trigger_datetime DATETIME NOT NULL,
        complaint_text_summary VARCHAR(255) NOT NULL, related_appointment_id INTEGER,
        related_econsult_id INTEGER NOT NULL, severity VARCHAR(20) NOT NULL, status VARCHAR(20) NOT NULL,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id),
        FOREIGN KEY(related_appointment_id) REFERENCES appointments(appointment_id),
        FOREIGN KEY(related_econsult_id) REFERENCES econsult_requests(econsult_id));
CREATE TABLE appointment_activity_log (appointment_activity_log_id INTEGER PRIMARY KEY,
        appointment_id INTEGER NOT NULL, event_datetime DATETIME NOT NULL,
        event_type VARCHAR(60) NOT NULL, event_channel VARCHAR(50) NOT NULL,
        event_actor VARCHAR(80) NOT NULL,
        FOREIGN KEY(appointment_id) REFERENCES appointments(appointment_id));
CREATE TABLE request_activity_log (request_activity_log_id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL,
        event_datetime DATETIME NOT NULL, event_type VARCHAR(60) NOT NULL,
        event_actor VARCHAR(80) NOT NULL, event_payload TEXT NOT NULL,
        FOREIGN KEY(request_id) REFERENCES appointment_requests(request_id));
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
routine_capacity_diverted INTEGER);
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
