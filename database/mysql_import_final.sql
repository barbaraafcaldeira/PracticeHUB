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
