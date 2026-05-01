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
    Form_Type VARCHAR(50),
    StockQuantity INT DEFAULT 0
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

-- 6. System Users: Linked to User Roles and optionally to a Patient record
CREATE TABLE SYSTEM_USERS (
    UserID INT PRIMARY KEY AUTO_INCREMENT,
    Username VARCHAR(50) UNIQUE NOT NULL,
    HashedPassword VARCHAR(255) NOT NULL, -- Added for JWT authentication security
    RoleID INT,
    PatientID INT NULL, -- Links a user to their clinical data if they are a patient
    FOREIGN KEY (RoleID) REFERENCES USER_ROLES(RoleID),
    FOREIGN KEY (PatientID) REFERENCES PATIENTS(PatientID) ON DELETE CASCADE
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
    p.PatientID, 
    m.MedicationName, 
    m.Dosage, 
    p.DatePrescribed, 
    p.Status, 
    p.DirectionsForUse
FROM PRESCRIPTIONS p
JOIN MEDICATIONS m ON p.MedicationID = m.MedicationID;

-- 3. CREATE USER ACCOUNTS
CREATE USER 'admin_user'@'%' IDENTIFIED BY 'AdminPass123';

-- 4. ASSIGN PRIVILEGES

-- Admin: Full System Access
GRANT ALL PRIVILEGES ON MedCare.* TO 'admin_user'@'%';

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
('Nettleham Medical Centre', '14 Lodge Ln, Nettleham, LN2 2RS'),
('Superdrug Pharmacy', 'Unit 12, High St, Lincoln, LN5 7ET'),
('University Health Centre', 'Brayford Pool, Lincoln, LN6 7TS');

-- Medications Data
INSERT INTO MEDICATIONS (MedicationName, Dosage, Form_Type, StockQuantity) VALUES 
('Amoxicillin', '500mg', 'Capsule', 252),
('Atorvastatin', '20mg', 'Tablet', 506),
('Salbutamol', '100mcg', 'Inhaler', 49),
('Metformin', '850mg', 'Tablet', 300),
('Sertraline', '50mg', 'Tablet', 120),
('Spikevax (Covid-19)', '0.5ml', 'Injection', 74),
('Fluad Quadrivalent', '0.5ml', 'Injection', 67),
('Prednisolone', '5mg', 'Tablet', 211);

-- User Roles Data
INSERT INTO USER_ROLES (RoleName) VALUES 
('System Admin'), ('Pharmacist'), ('GP Manager'), ('Researcher'), ('Patient');    

-- Patients Data
INSERT INTO PATIENTS (NHS_Number, FirstName, LastName, DateOfBirth, Address, Phone_Number, Allergies) VALUES 
('4857293041', 'James', 'Wilson', '1955-03-12', '88 Yarborough Rd, Lincoln', '07712345678', 'Penicillin'),
('9928374650', 'Sarah', 'Ahmed', '1988-11-25', '12b Steep Hill, Lincoln', '07899112233', 'None'),
('1029384756', 'Robert', 'Taylor', '2010-06-05', '4 Ferrum Close, Hykeham', '07455667788', 'Peanuts, Sulfa Drugs'),
('5566778899', 'Elena', 'Petrova', '1992-01-30', 'Flat 4, 19 High St, Lincoln', '07900111222', 'Aspirin'),
('1234509876', 'David', 'Smith', '1942-09-14', 'The Laurels Care Home, LN6', '01522889900', 'None'),
('1122334455', 'Sophie', 'Bennett', '1995-07-10', '14 Brayford Wharf, Lincoln', '07111222333', 'None'),
('6677889900', 'Marcus', 'Reed', '1972-12-01', '22 Outer Circle, Lincoln', '07444555666', 'Penicillin'),
('9988776655', 'Chloe', 'Fisher', '2001-04-20', 'Flat 10, Pavilions, Lincoln', '07888999000', 'Latex'),
('8877665544', 'Thomas', 'Brown', '1960-08-15', '56 Boultham Park Rd, Lincoln', '07222333444', 'None'),
('5544332211', 'Linda', 'Jones', '1958-11-02', '101 Monks Rd, Lincoln', '07333444555', 'Shellfish'),
('2233445566', 'William', 'Davies', '1990-02-14', '12 Newark Rd, Lincoln', '07555666777', 'None'),
('7788990011', 'Emily', 'White', '1985-06-30', '33 Carholme Rd, Lincoln', '07666777888', 'None'),
('1212121212', 'Arthur', 'Morgan', '1940-05-12', 'Lincoln Care East, LN2', '01522111222', 'Penicillin'),
('3434343434', 'Sadie', 'Adler', '1992-09-09', '45 West Parade, Lincoln', '07999888777', 'None'),
('5656565656', 'John', 'Marston', '1973-04-15', 'Beechwood Dr, Lincoln', '07888111999', 'Dust Mites');

-- Patient Logs Data
INSERT INTO PATIENT_RECORDS_LOG (PatientID, MedicalHistory, BloodType, ChronicConditions, LastClinicalReview) VALUES 
(1, 'History of childhood asthma. Hospitalized in 1998.', 'A+', 'Hypertension', '2024-01-15'),
(2, 'No significant prior history. Routine prenatal care 2021.', 'O-', 'None', '2023-11-20'),
(4, 'Previous surgery for ACL repair. Family history of Type 2 Diabetes.', 'B+', 'Anxiety', '2024-02-10'),
(5, 'Elderly patient with declining mobility. Cognitive assessment required.', 'AB+', 'Arthritis, Early-stage Dementia', '2024-03-01'),
(6, 'Post-viral fatigue syndrome 2022.', 'O+', 'None', '2024-04-01'),
(7, 'History of kidney stones.', 'A-', 'Gout', '2024-01-20'),
(13, 'Chronic obstructive pulmonary disease (COPD).', 'O+', 'COPD', '2024-03-15'),
(15, 'Recurring migraines since 2018.', 'B-', 'Migraines', '2024-02-28');

-- Doctors Data
INSERT INTO DOCTORS (GMC_Number, PrescriberName, PrescriberSignature, FacilityID) VALUES 
('7012345', 'Dr. Alistair Cook', 'Sig_AC_701', 1),
('6123456', 'Dr. Meera Joshi', 'Sig_MJ_612', 5),
('5098765', 'Dr. Simon Vance', 'Sig_SV_509', 1),
('7443322', 'Dr. Sarah Jenkins', 'Sig_SJ_744', 3),
('8899001', 'Dr. Robert Bell', 'Sig_RB_889', 7);

-- System Users: Admin and Staff
INSERT INTO SYSTEM_USERS (Username, HashedPassword, RoleID, PatientID) VALUES 
('admin_jclark', 'password123', 1, NULL),
('pharma_kbrown', 'password123', 2, NULL),
('mgr_rsmith', 'password123', 3, NULL),
('res_ltaylor', 'password123', 4, NULL);

-- System Users: Patient Accounts for all 15 entries
-- Logic: Username is patient_firstname, Password is NHSNumber+LastName
INSERT INTO SYSTEM_USERS (Username, HashedPassword, RoleID, PatientID) VALUES 
('james041',   '4857293041Wilson',  5, 1),
('sarah650',   '9928374650Ahmed',   5, 2),
('robert756',  '1029384756Taylor',  5, 3),
('elena899',   '5566778899Petrova', 5, 4),
('david876',   '1234509876Smith',   5, 5),
('sophie455',  '1122334455Bennett', 5, 6),
('marcus900',  '6677889900Reed',    5, 7),
('chloe655',   '9988776655Fisher',  5, 8),
('thomas544',  '8877665544Brown',   5, 9),
('linda211',   '5544332211Jones',   5, 10),
('william566', '2233445566Davies',  5, 11),
('emily011',   '7788990011White',   5, 12),
('arthur212',  '1212121212Morgan',  5, 13),
('sadie434',   '3434343434Adler',   5, 14),
('john656',    '5656565656Marston', 5, 15);

-- Vaccinations Data
INSERT INTO VACCINATIONS (PatientID, DoctorID, VaccineType, DoseNumber, DateAdministered) VALUES 
(1, 1, 'Covid-19', 1, '2023-11-05'),
(1, 1, 'Covid-19', 2, '2024-02-10'),
(2, 2, 'Flu', 1, '2024-10-15'),
(5, 4, 'Covid-19', 3, '2024-01-20'),
(3, 2, 'MMR', 1, '2023-05-12'),
(6, 1, 'Covid-19', 1, '2024-03-01'),
(6, 1, 'Covid-19', 2, '2024-04-01'),
(7, 3, 'Flu', 1, '2024-10-01'),
(13, 5, 'Pneumococcal', 1, '2024-02-15');

-- Prescriptions Data
INSERT INTO PRESCRIPTIONS (PatientID, DoctorID, MedicationID, FacilityID, DatePrescribed, DateDispensed, Quantity, DirectionsForUse, NumberOfRepeats, DispensingPharmacist, Status) VALUES 
(1, 1, 2, 2, '2024-03-01', '2024-03-02', 28, 'One tablet at night', 5, 'K. Brown', 'Collected'),
(2, 2, 1, 2, '2024-03-10', '2024-03-10', 21, 'Take three times a day for 7 days', 0, 'K. Brown', 'Collected'),
(4, 3, 5, 4, '2024-03-15', NULL, 30, 'Take one daily', 2, NULL, 'Pending'),
(5, 4, 4, 2, '2024-02-20', '2024-02-21', 56, 'Twice daily with food', 3, 'K. Brown', 'Dispensed'),
(3, 2, 3, 4, '2024-03-18', NULL, 1, 'Use as required for shortness of breath', 1, NULL, 'Pending'),
(6, 1, 5, 1, '2024-04-10', NULL, 30, 'Take one in the morning', 1, NULL, 'Pending'),
(7, 3, 2, 3, '2024-04-12', NULL, 28, 'One daily with evening meal', 6, NULL, 'Pending'),
(6, 2, 8, 5, '2024-04-15', '2024-04-16', 10, 'Five tablets daily for 2 days', 0, 'K. Brown', 'Dispensed'),
(13, 5, 4, 2, '2024-04-01', NULL, 56, 'Take twice daily', 0, NULL, 'Pending');