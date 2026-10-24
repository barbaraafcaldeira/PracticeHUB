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
