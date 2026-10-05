-- Run this ONLY if you already created QueueCloud before the updated project.
-- If you are creating the database from scratch, use database/schema.sql instead.
USE queuecloud;

-- Add the unique token constraint required by the updated application.
-- If this statement fails because the constraint/index already exists, skip it.
ALTER TABLE appointments
    ADD CONSTRAINT uq_appointment_doctor_date_token
    UNIQUE (doctor_id, appointment_date, token);

CREATE INDEX ix_appointment_queue
    ON appointments (appointment_date, doctor_id, status, appointment_time, token);
