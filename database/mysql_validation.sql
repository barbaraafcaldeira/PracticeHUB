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
