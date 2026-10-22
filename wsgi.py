from app import create_app
from models import db
from seed_data import seed_database

# Create application instance for WSGI servers (Gunicorn, uWSGI, PythonAnywhere)
app = create_app()

# Auto-initialize database tables and demo seed data on startup if not present
with app.app_context():
    db.create_all()
    seed_database()

if __name__ == "__main__":
    app.run()
