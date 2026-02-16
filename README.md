# Final Year Project - TUDublin | Wissam Hadjarab | C21404706
# ZakaatIQ is a Flask-based web application designed to help Muslims manage their personal finances in a halal, secure, and intelligent way.
# The system predicts Zakat eligibility using a machine-learning model, logs encrypted financial inputs, provides AI-based future income forecasts, and allows users to make demo donations to verified charities.

## Project Features
# User Authentication - Secure login/register system
# Zakat Eligibility Predciton (AI + ML) - Uses a ML model, encryption with Fernet, results saved to database
# Encrypyed Finanical History - user inputs stored securely 
# Dashboard - user overview, full history, past zakat evaluations
# Income forecast module - AI forecast graph
# Donation module - demo simulates sending charity payments 
# Full responsice UI

## Requirememts 
# OS:
# macOS(Intel or silicon chip)
# Windows 10/11
# Linux (Ubuntu)
# Browser:
# Google chrome, Firefox, Safarti
# Software:
# Python 3.10-3.13

## Installation Steps
# 1. Clone repo 
git clone https://github.com/wissamhadjarab/Final-Year-Project.git
cd Final-Year-Project
# 2. Install dependencies
pip install -r requirements.txt
# 3. Run application
python3 app.py
# 4. Access browser from terminal 
http://127.0.0.1:5000/

## User credentials 
# Register new user from registration page; no default credentials required 
http://127.0.0.1:5000/register

## Use system
# 1. Start application 
python3 app.py

# 2. Open homepage 
http://127.0.0.1:5000/
# 3. Register -> create an account
# 4. Once logged in, redirected to dashboard 
# 5. Use main features; from navbar or dashboard
# Zakat eligibility, Dashboard (History), Forecast, Donation page, Logout

## Security notes
# User passwords hashed (Flask)
# Financial inputs stored and encrypted
# ML prediction uses secure local model
# SQLite database handled safely

## GitHub Repository 
https://github.com/wissamhadjarab/Final-Year-Project

## Author
# Wissam Hadjarab
# TU Dublin - International Computer Science | TU858/4