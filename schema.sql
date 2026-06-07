-- Run this once in MySQL to set up the database
-- mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS intern_ms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE intern_ms;

CREATE TABLE IF NOT EXISTS hr_credentials (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),
    full_name       VARCHAR(150),
    email           VARCHAR(150),
    phone           VARCHAR(50),
    department      VARCHAR(100),
    role            VARCHAR(100),
    avatar_initials VARCHAR(5),
    bio             TEXT,
    location        VARCHAR(150),
    gender          VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS intern (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(150),
    department     VARCHAR(100),
    attendance     FLOAT,
    tasks          FLOAT,
    communication  FLOAT,
    project        FLOAT,
    performance    VARCHAR(50),
    password_hash  VARCHAR(255),
    password_plain VARCHAR(100),
    email          VARCHAR(150),
    phone          VARCHAR(50),
    gender         VARCHAR(50),
    location       VARCHAR(150),
    position       VARCHAR(100),
    start_date     VARCHAR(20),
    end_date       VARCHAR(20),
    skills         TEXT,
    bio            TEXT,
    domain         VARCHAR(100)
);
select*from intern;
