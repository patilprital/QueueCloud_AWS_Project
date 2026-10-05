CREATE DATABASE IF NOT EXISTS queuecloud;
USE queuecloud;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'patient',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    available_from VARCHAR(10) DEFAULT '09:00',
    available_to VARCHAR(10) DEFAULT '17:00',
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR(10) NOT NULL,
    token INT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Waiting',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_appointment_patient FOREIGN KEY (patient_id) REFERENCES users(id),
    CONSTRAINT fk_appointment_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id),
    CONSTRAINT uq_appointment_doctor_date_token UNIQUE (doctor_id, appointment_date, token),
    INDEX ix_appointment_queue (appointment_date, doctor_id, status, appointment_time, token)
);

INSERT INTO doctors (name, specialization, department, available_from, available_to)
SELECT 'Dr. Anjali Sharma', 'General Physician', 'General Medicine', '09:00', '17:00'
WHERE NOT EXISTS (SELECT 1 FROM doctors WHERE name = 'Dr. Anjali Sharma');

INSERT INTO doctors (name, specialization, department, available_from, available_to)
SELECT 'Dr. Rahul Patil', 'Orthopedic', 'Orthopedics', '10:00', '16:00'
WHERE NOT EXISTS (SELECT 1 FROM doctors WHERE name = 'Dr. Rahul Patil');

INSERT INTO doctors (name, specialization, department, available_from, available_to)
SELECT 'Dr. Neha Joshi', 'Dermatologist', 'Dermatology', '11:00', '18:00'
WHERE NOT EXISTS (SELECT 1 FROM doctors WHERE name = 'Dr. Neha Joshi');
