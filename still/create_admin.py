"""
Run this once to create or reset the admin account.
Usage: python create_admin.py
"""
from app import create_app
from extensions import db
from models.models import User, Role

app = create_app()
with app.app_context():
    role = Role.query.filter_by(name='System Administrator').first()
    if not role:
        print("ERROR: 'System Administrator' role not found. Run the app once first to seed roles.")
    else:
        admin = User.query.filter_by(employee_id='ADMIN001').first()
        if not admin:
            admin = User(
                employee_id='ADMIN001',
                full_name='System Administrator',
                email='admin@mzuni.ac.mw',
                post='System Administrator',
                grade='A1',
                role_id=role.id,
                is_active=True
            )
            db.session.add(admin)
            print("Admin user created.")
        else:
            print("Admin already exists — resetting password and ensuring active.")
            admin.is_active = True

        admin.set_password('Admin@1234')
        db.session.commit()
        print("Done. Login with Employee ID: ADMIN001 / Password: Admin@1234")
