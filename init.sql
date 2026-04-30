-- ------------------------------------DDL-------------------------------------------------------------

-- CREATE DATABASE MedCare;
-- USE MedCare;
-- SHOW DATABASES;

-- 1. Facilities: Stores Practice and Pharmacy locations
CREATE TABLE FACILITIES (
    FacilityID INT PRIMARY KEY AUTO_INCREMENT,
    FacilityName VARCHAR(100) NOT NULL,
    Full_Address VARCHAR(255) NOT NULL
);

-- 2. Medications: The master drug catalog
CREATE TABLE MEDICATIONS (
    MedicationID INT PRIMARY KEY AUTO_INCREMENT,
    MedicationName VARCHAR(100) NOT NULL,
    Dosage VARCHAR(50),
    Form_Type VARCHAR(50)
);

-- 3. User Roles: Defines access levels (Admin, Researcher, etc.)
CREATE TABLE USER_ROLES (
    RoleID INT PRIMARY KEY AUTO_INCREMENT,
    RoleName VARCHAR(50) NOT NULL
);

-- 4. Patients: Stores demographic and clinical safety data
CREATE TABLE PATIENTS (
    PatientID INT PRIMARY KEY AUTO_INCREMENT,
    NHS_Number VARCHAR(10) UNIQUE NOT NULL,
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    DateOfBirth DATE NOT NULL,
    Address VARCHAR(255),
    Phone_Number VARCHAR(15),
    Allergies TEXT
);

-- Create the High-Security Partitioned Table
CREATE TABLE IF NOT EXISTS PATIENT_RECORDS_LOG (
    PatientID INT PRIMARY KEY,
    MedicalHistory LONGTEXT,
    BloodType VARCHAR(3),
    ChronicConditions TEXT,
    LastClinicalReview DATE,
    CONSTRAINT fk_patient_log FOREIGN KEY (PatientID) 
        REFERENCES PATIENTS(PatientID) 
        ON DELETE CASCADE
);

-- 5. Doctors: Linked to a primary Facility
CREATE TABLE DOCTORS (
    DoctorID INT PRIMARY KEY AUTO_INCREMENT,
    GMC_Number VARCHAR(7) UNIQUE NOT NULL,
    PrescriberName VARCHAR(100) NOT NULL,
    PrescriberSignature VARCHAR(255),
    FacilityID INT,
    FOREIGN KEY (FacilityID) REFERENCES FACILITIES(FacilityID)
);

-- 6. System Users: Linked to User Roles
CREATE TABLE SYSTEM_USERS (
    UserID INT PRIMARY KEY AUTO_INCREMENT,
    Username VARCHAR(50) UNIQUE NOT NULL,
    RoleID INT,
    FOREIGN KEY (RoleID) REFERENCES USER_ROLES(RoleID)
);

-- 7. Vaccinations: Tracks the vaccination events
CREATE TABLE VACCINATIONS (
    VaccinationID INT PRIMARY KEY AUTO_INCREMENT,
    PatientID INT NOT NULL,
    DoctorID INT NOT NULL,
    VaccineType VARCHAR(50) NOT NULL,
    DoseNumber INT NOT NULL,
    DateAdministered DATE NOT NULL,
    FOREIGN KEY (PatientID) REFERENCES PATIENTS(PatientID),
    FOREIGN KEY (DoctorID) REFERENCES DOCTORS(DoctorID)
);

-- 8. Prescriptions: List of prescriptions and acting as a central connection to all other tables
CREATE TABLE PRESCRIPTIONS (
    PrescriptionID INT PRIMARY KEY AUTO_INCREMENT,
    PatientID INT NOT NULL,
    DoctorID INT NOT NULL,
    MedicationID INT NOT NULL,
    FacilityID INT NOT NULL, -- (Also represents the Pharmacy Location)
    DatePrescribed DATE NOT NULL,
    DateDispensed DATE,
    Quantity INT NOT NULL,
    DirectionsForUse TEXT,
    NumberOfRepeats INT DEFAULT 0,
    DispensingPharmacist VARCHAR(100),
    Status VARCHAR(20) DEFAULT 'Pending',
    FOREIGN KEY (PatientID) REFERENCES PATIENTS(PatientID),
    FOREIGN KEY (DoctorID) REFERENCES DOCTORS(DoctorID),
    FOREIGN KEY (MedicationID) REFERENCES MEDICATIONS(MedicationID),
    FOREIGN KEY (FacilityID) REFERENCES FACILITIES(FacilityID)
);


SHOW TABLES;

DESCRIBE PRESCRIPTIONS;

DESCRIBE PATIENTS;


-- ------------------------------------DCL-------------------------------------------------------------


USE MedCare;

-- 1. CLEANUP (Optional but runs to clean any similar users or views)
DROP VIEW IF EXISTS Patient_Self_Service_View;
DROP USER IF EXISTS 'admin_user'@'%', 'pharmacist_user'@'%', 'manager_user'@'%', 'patient_user'@'%';

-- 2. CREATE SECURITY VIEW
-- Rule: "Patients can only view their own prescriptions"

CREATE VIEW Patient_Self_Service_View AS
SELECT 
    p.PrescriptionID, 
    m.MedicationName, 
    m.Dosage, 
    p.DatePrescribed, 
    p.Status, 
    p.DirectionsForUse
FROM PRESCRIPTIONS p
JOIN MEDICATIONS m ON p.MedicationID = m.MedicationID
WHERE p.PatientID = 1;

-- 3. CREATE USER ACCOUNTS
CREATE USER 'admin_user'@'%' IDENTIFIED BY 'AdminPass123';
CREATE USER 'pharmacist_user'@'%' IDENTIFIED BY 'PharmaPass123';
CREATE USER 'manager_user'@'%' IDENTIFIED BY 'ManagerPass123';
CREATE USER 'patient_user'@'%' IDENTIFIED BY 'PatientPass123';

-- 4. ASSIGN PRIVILEGES

-- Admin: Full System Access
GRANT ALL PRIVILEGES ON MedCare.* TO 'admin_user'@'%';

-- Pharmacist: Rule "Can dispense and update prescription status"
GRANT SELECT, INSERT, UPDATE ON MedCare.PRESCRIPTIONS TO 'pharmacist_user'@'%';
GRANT SELECT ON MedCare.PATIENTS TO 'pharmacist_user'@'%';
GRANT SELECT ON MedCare.MEDICATIONS TO 'pharmacist_user'@'%';
GRANT SELECT ON MedCare.FACILITIES TO 'pharmacist_user'@'%';

-- Manager: Rule "Can generate reports" (VIEW ONLY)
GRANT SELECT ON MedCare.* TO 'manager_user'@'%';

-- Patient: Rule "Can only view their own prescriptions"
-- Granting access ONLY to the View, not the base table.
GRANT SELECT ON MedCare.Patient_Self_Service_View TO 'patient_user'@'%';


FLUSH PRIVILEGES;

-- ------------------------------------DML-------------------------------------------------------------

USE MedCare;

-- ---------------------------------------------------------
-- Insert Commands
-- ---------------------------------------------------------

-- Facilities Data
INSERT INTO FACILITIES (FacilityName, Full_Address) VALUES 
('St. Jude’s General Practice', '12 High St, Lincoln, LN1 1PT'),
('Boots Pharmacy - Central', 'Unit 4, Waterside Shopping Centre, Lincoln, LN2 1AP'),
('Lincoln County Hospital', 'Greetwell Rd, Lincoln, LN2 5QY'),
('Well Pharmacy', '42 Newark Road, North Hykeham, LN6 8AU'),
('Nettleham Medical Centre', '14 Lodge Ln, Nettleham, LN2 2RS');

-- Medications Data
INSERT INTO MEDICATIONS (MedicationName, Dosage, Form_Type) VALUES 
('Amoxicillin', '500mg', 'Capsule'),
('Atorvastatin', '20mg', 'Tablet'),
('Salbutamol', '100mcg', 'Inhaler'),
('Metformin', '850mg', 'Tablet'),
('Sertraline', '50mg', 'Tablet'),
('Spikevax (Covid-19)', '0.5ml', 'Injection'),
('Fluad Quadrivalent', '0.5ml', 'Injection'),
('Prednisolone', '5mg', 'Tablet');

-- User Roles Data
INSERT INTO USER_ROLES (RoleName) VALUES 
('System Admin'), ('Pharmacist'), ('GP Manager'), ('Researcher'), ('Patient');    

-- Patients Data
INSERT INTO PATIENTS (NHS_Number, FirstName, LastName, DateOfBirth, Address, Phone_Number, Allergies) VALUES 
('4857293041', 'James', 'Wilson', '1955-03-12', '88 Yarborough Rd, Lincoln', '07712345678', 'Penicillin'),
('9928374650', 'Sarah', 'Ahmed', '1988-11-25', '12b Steep Hill, Lincoln', '07899112233', 'None'),
('1029384756', 'Robert', 'Taylor', '2010-06-05', '4 Ferrum Close, Hykeham', '07455667788', 'Peanuts, Sulfa Drugs'),
('5566778899', 'Elena', 'Petrova', '1992-01-30', 'Flat 4, 19 High St, Lincoln', '07900111222', 'Aspirin'),
('1234509876', 'David', 'Smith', '1942-09-14', 'The Laurels Care Home, LN6', '01522889900', 'None');

-- Patient Logs Data
INSERT INTO PATIENT_RECORDS_LOG (PatientID, MedicalHistory, BloodType, ChronicConditions, LastClinicalReview) VALUES 
(1, 'History of childhood asthma. Hospitalized in 1998.', 'A+', 'Hypertension', '2024-01-15'),
(2, 'No significant prior history. Routine prenatal care 2021.', 'O-', 'None', '2023-11-20'),
(4, 'Previous surgery for ACL repair. Family history of Type 2 Diabetes.', 'B+', 'Anxiety', '2024-02-10'),
(5, 'Elderly patient with declining mobility. Cognitive assessment required.', 'AB+', 'Arthritis, Early-stage Dementia', '2024-03-01');

-- Doctors Data
INSERT INTO DOCTORS (GMC_Number, PrescriberName, PrescriberSignature, FacilityID) VALUES 
('7012345', 'Dr. Alistair Cook', 'Sig_AC_701', 1),
('6123456', 'Dr. Meera Joshi', 'Sig_MJ_612', 5),
('5098765', 'Dr. Simon Vance', 'Sig_SV_509', 1),
('7443322', 'Dr. Sarah Jenkins', 'Sig_SJ_744', 3);

-- System Users Data
INSERT INTO SYSTEM_USERS (Username, RoleID) VALUES 
('admin_jclark', 1), ('pharma_kbrown', 2), ('mgr_rsmith', 3), ('res_ltaylor', 4);

-- Vaccinations Data
INSERT INTO VACCINATIONS (PatientID, DoctorID, VaccineType, DoseNumber, DateAdministered) VALUES 
(1, 1, 'Covid-19', 1, '2023-11-05'),
(1, 1, 'Covid-19', 2, '2024-02-10'),
(2, 2, 'Flu', 1, '2024-10-15'),
(5, 4, 'Covid-19', 3, '2024-01-20'),
(3, 2, 'MMR', 1, '2023-05-12');

-- Prescriptions Data
INSERT INTO PRESCRIPTIONS (PatientID, DoctorID, MedicationID, FacilityID, DatePrescribed, DateDispensed, Quantity, DirectionsForUse, NumberOfRepeats, DispensingPharmacist, Status) VALUES 
(1, 1, 2, 2, '2024-03-01', '2024-03-02', 28, 'One tablet at night', 5, 'K. Brown', 'Collected'),
(2, 2, 1, 2, '2024-03-10', '2024-03-10', 21, 'Take three times a day for 7 days', 0, 'K. Brown', 'Collected'),
(4, 3, 5, 4, '2024-03-15', NULL, 30, 'Take one daily', 2, NULL, 'Pending'),
(5, 4, 4, 2, '2024-02-20', '2024-02-21', 56, 'Twice daily with food', 3, 'K. Brown', 'Dispensed'),
(3, 2, 3, 4, '2024-03-18', NULL, 1, 'Use as required for shortness of breath', 1, NULL, 'Pending');


-- ---------------------------------------------------------
-- Data Manipulation Queries
-- ---------------------------------------------------------

-- 1. Create a new prescription record
-- Business Case: Dr. Cook (ID 1) prescribing Amoxicillin to Elena (ID 4)
INSERT INTO PRESCRIPTIONS (PatientID, DoctorID, MedicationID, FacilityID, DatePrescribed, Quantity, DirectionsForUse, Status) 
VALUES (4, 1, 1, 2, CURDATE(), 21, 'Take one three times daily for 7 days', 'Pending');

-- 2. Update a prescription status
-- Business Case: Pharmacist updating a pending script to 'Dispensed'
UPDATE PRESCRIPTIONS 
SET Status = 'Dispensed', 
    DateDispensed = CURDATE(), 
    DispensingPharmacist = 'K. Brown'
WHERE PrescriptionID = 3;

-- 3. Data Maintenance
-- Business Case: Removing a test or cancelled vaccination record
DELETE FROM VACCINATIONS WHERE VaccinationID = 999; -- Placeholder ID for deletion logic

-- 4. Search medications using wildcards
-- Business Case: Finding all variations of Penicillin or Flu-related meds
SELECT MedicationName, Dosage, Form_Type 
FROM MEDICATIONS 
WHERE MedicationName LIKE '%cillin%' OR MedicationName LIKE '%Flu%';

-- 5. Identify Clinical Risks
-- Business Case: Finding all patients who have documented allergies
SELECT FirstName, LastName, Allergies 
FROM PATIENTS 
WHERE Allergies IS NOT NULL AND Allergies != 'None';

-- 6. Filter by medication volume
-- Business Case: High-frequency prescriptions with multiple repeats
SELECT PrescriptionID, PatientID, NumberOfRepeats 
FROM PRESCRIPTIONS 
WHERE NumberOfRepeats >= 3 AND Status = 'Collected';

-- 7. Full Dispensing Audit
-- Business Case: Linking Patient, Medication, and Facility for a complete history
SELECT p.LastName AS Patient, m.MedicationName, f.FacilityName AS Pharmacy, pr.Status
FROM PRESCRIPTIONS pr
JOIN PATIENTS p ON pr.PatientID = p.PatientID
JOIN MEDICATIONS m ON pr.MedicationID = m.MedicationID
JOIN FACILITIES f ON pr.FacilityID = f.FacilityID;

-- 8. Vaccination Coverage Report
-- Business Case: Identifying which Doctors gave which vaccines to which Patients
SELECT p.FirstName, p.LastName, v.VaccineType, v.DoseNumber, d.PrescriberName
FROM VACCINATIONS v
JOIN PATIENTS p ON v.PatientID = p.PatientID
JOIN DOCTORS d ON v.DoctorID = d.DoctorID;

-- 9. Doctor Workload by Facility
-- Business Case: Managing staff resources by seeing how many scripts each doctor writes per clinic
SELECT f.FacilityName, d.PrescriberName, COUNT(pr.PrescriptionID) AS Scripts_Written
FROM DOCTORS d
JOIN FACILITIES f ON d.FacilityID = f.FacilityID
JOIN PRESCRIPTIONS pr ON d.DoctorID = pr.DoctorID
GROUP BY f.FacilityName, d.PrescriberName;

-- 10. Elderly Care Reporting
-- Business Case: Counting prescriptions for patients over the age of 65
SELECT COUNT(*) AS Elderly_Patient_Prescriptions
FROM PATIENTS p
JOIN PRESCRIPTIONS pr ON p.PatientID = pr.PatientID
WHERE TIMESTAMPDIFF(YEAR, p.DateOfBirth, CURDATE()) >= 65;

-- 11. Pharmacy Performance
-- Business Case: Tracking workload per Pharmacist at different locations
SELECT f.FacilityName, pr.DispensingPharmacist, COUNT(pr.PrescriptionID) AS Total_Filled
FROM PRESCRIPTIONS pr
JOIN FACILITIES f ON pr.FacilityID = f.FacilityID
WHERE pr.DispensingPharmacist IS NOT NULL
GROUP BY f.FacilityName, pr.DispensingPharmacist;

-- 12. Exception Reporting
-- Business Case: Finding patients who have NOT yet received any vaccinations
SELECT FirstName, LastName, NHS_Number 
FROM PATIENTS 
WHERE PatientID NOT IN (SELECT DISTINCT PatientID FROM VACCINATIONS);

-- 13. Multi-Dose Tracking
-- Business Case: Identifying patients who have received a Booster (Dose 2 or higher)
SELECT p.FirstName, p.LastName, v.VaccineType, COUNT(v.VaccinationID) AS Total_Doses
FROM VACCINATIONS v
JOIN PATIENTS p ON v.PatientID = p.PatientID
GROUP BY p.PatientID, v.VaccineType
HAVING Total_Doses >= 2;

-- 14. Authorized Clinical View
-- Business Case: Combining Patient Contact info with History
SELECT p.FirstName, p.LastName, l.BloodType, l.ChronicConditions
FROM PATIENTS p
JOIN PATIENT_RECORDS_LOG l ON p.PatientID = l.PatientID;