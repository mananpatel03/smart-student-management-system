import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ssms-super-secret-key-2026-production-salt')
    
    # Dual database support: SQLite for instant local execution, or MySQL via environment variable
    # Example for MySQL: mysql+pymysql://root:password@localhost:3306/ssms_db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{BASE_DIR / 'ssms.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Institutional Academic Rules
    ATTENDANCE_THRESHOLD = 75.0  # Percentage below which students are flagged as defaulters
    PASS_PERCENTAGE = 40.0       # Passing percentage for individual subjects and total
    INSTITUTE_NAME = "Apex Institute of Technology & Engineering"
    INSTITUTE_CODE = "AITE-ENG-2026"
    INSTITUTE_ADDRESS = "Knowledge City, Institutional Area, Sector 12"
    INSTITUTE_PHONE = "+91 98765 43210"
    INSTITUTE_EMAIL = "academic@aite-edu.in"
