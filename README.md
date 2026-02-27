# 🏥 Clinic Management System (CMS)

A **full-stack Clinic Management System** built using **Django, React,
and MySQL** to streamline hospital operations including patient
management, appointments, consultations, pharmacy inventory, laboratory
workflows, and billing.

This system digitizes day-to-day clinic activities through a secure
**role-based architecture**, improving efficiency, accuracy, and patient
experience.

------------------------------------------------------------------------

## 🚀 Project Overview

The Clinic Management System provides an integrated platform for
healthcare staff to manage clinical and administrative workflows in a
centralized environment.

The application supports multiple user roles:

-   👨‍💼 Administrator\
-   🧾 Receptionist\
-   👨‍⚕️ Doctor\
-   💊 Pharmacist\
-   🧪 Lab Technician

Each role has controlled access to features relevant to their
responsibilities.

------------------------------------------------------------------------

## ✨ Key Features

### 🔐 Role-Based Authentication

-   Secure login using JWT authentication
-   Access control based on user roles

### 📅 Appointment & Token Management

-   Smart appointment scheduling
-   Automatic daily token generation per doctor
-   Doctor-wise patient limits

### 🩺 Doctor Consultation System

-   Digital consultation notes
-   Medicine prescription management
-   Lab test requests
-   Patient medical history tracking

### 💊 Pharmacy & Inventory Management

-   Medicine stock tracking
-   Low-stock alerts
-   Dispensing workflow linked to prescriptions

### 🧪 Laboratory Module

-   Lab test prescriptions
-   Result entry and verification
-   Structured lab result tables for doctors and patients

### 💰 Billing System

-   One-time patient registration fee
-   Consultation billing
-   Lab billing integration
-   Payment tracking

------------------------------------------------------------------------

## 🏗 System Architecture

    React Frontend
          ↓
    Django REST API
          ↓
    MySQL Database

The backend follows **Django's MVT architecture** while exposing RESTful
APIs consumed by the React frontend.

------------------------------------------------------------------------

## 🛠 Tech Stack

### Backend

-   Django
-   Django REST Framework
-   MySQL

### Frontend

-   React.js
-   Bootstrap / CSS

### Tools

-   Git & GitHub
-   dbdiagram.io (ER Design)
-   Postman (API Testing)

------------------------------------------------------------------------

## 🔄 Workflow

    Patient Registration
            ↓
    Appointment Booking (Token Generated)
            ↓
    Doctor Consultation
            ↓
    Prescription / Lab Test
            ↓
    Medicine Dispense / Lab Result
            ↓
              Billing

------------------------------------------------------------------------

## ⭐ Project Goal

To provide a scalable and efficient digital solution for managing clinic
operations while ensuring secure access, accurate record keeping, and
improved healthcare workflow automation.
