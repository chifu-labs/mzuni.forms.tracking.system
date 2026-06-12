def seed_data():
    from extensions import db
    from models.models import Role, Department, User, FormType, WorkflowStep

    # ── Roles ──────────────────────────────────────────────────────
    for rname in [
        'Sender', 'Department Officer', 'Head of Department',
        'Registry Officer', 'Finance Officer', 'Human Resource Officer',
        'ICT Administrator', 'System Administrator', 'Vice Chancellor',
        'Director of Finance', 'Dean/Principal Officer', 'Transport Officer',
        'Chief Procurement Officer'
    ]:
        if not Role.query.filter_by(name=rname).first():
            db.session.add(Role(name=rname))
    db.session.commit()

    # ── Departments ────────────────────────────────────────────────
    for dname, dcode in [
        ('Registry', 'REG'), ('Finance', 'FIN'), ('Human Resources', 'HR'),
        ('ICT', 'ICT'), ('Transport', 'TRANS'), ('Vice Chancellor Office', 'VCO'),
        ('Procurement', 'PROC'), ('Administration', 'ADM'),
        ('Water and Sanitation - PEER PROJECT', 'WSP'),
    ]:
        if not Department.query.filter_by(code=dcode).first():
            db.session.add(Department(name=dname, code=dcode))
    db.session.commit()

    # ── Form Types ─────────────────────────────────────────────────
    for fdata in [
        {'name': 'REQUEST FOR USE OF FUNDS FOR INTERNAL TRAVEL AND SUBSISTENCE',
         'ref_number': 'ADM/02/11/13', 'template_name': 'travel_subsistence',
         'description': 'Request for use of funds for internal travel and subsistence (To be completed and submitted 48 hours before travel)'},
        {'name': 'REQUEST FOR USE OF FUNDS FOR PROCUREMENT',
         'ref_number': 'ADM/08/11/13', 'template_name': 'procurement',
         'description': 'Request for use of funds for procurement of goods and services'},
        {'name': 'STAFF BOOKING TRANSPORT FORM',
         'ref_number': 'TRANS/01/08/13', 'template_name': 'transport_booking',
         'description': 'Staff booking transport form (Booking must be made at least 48 hours in advance)'},
        {'name': 'FUEL REQUISITION',
         'ref_number': 'FUEL/01', 'template_name': 'fuel_requisition',
         'description': 'Fuel requisition form'},
    ]:
        if not FormType.query.filter_by(ref_number=fdata['ref_number']).first():
            db.session.add(FormType(**fdata))
    db.session.commit()

    # ── Workflow Steps ─────────────────────────────────────────────
    # Travel & Subsistence — 6 steps (C→D→E→F→G→H)
    ts = FormType.query.filter_by(ref_number='ADM/02/11/13').first()
    if ts and not WorkflowStep.query.filter_by(form_type_id=ts.id).first():
        for step_order, step_name in [
            (1, 'COMMENTS BY HEAD OF DEPARTMENT/COST CENTRE MANAGER'),
            (2, 'RECOMMENDATION BY DEAN/PRINCIPAL OFFICER'),
            (3, 'AVAILABILITY OF BUDGET AND FUNDS'),
            (4, 'COMMENTS BY UNIVERSITY REGISTRAR'),
            (5, 'APPROVAL BY VICE-CHANCELLOR'),
            (6, 'AUTHORIZATION OF PAYMENT BY DIRECTOR OF FINANCE'),
        ]:
            db.session.add(WorkflowStep(
                form_type_id=ts.id, step_order=step_order, step_name=step_name
            ))

    # Procurement — 7 steps (C→D→E→F→G→H→I)
    pf = FormType.query.filter_by(ref_number='ADM/08/11/13').first()
    if pf and not WorkflowStep.query.filter_by(form_type_id=pf.id).first():
        for step_order, step_name in [
            (1, 'COMMENTS BY HEAD OF DEPARTMENT/COST CENTRE MANAGER'),
            (2, 'RECOMMENDATION BY DEAN/PRINCIPAL OFFICER'),
            (3, 'AVAILABILITY OF BUDGET AND FUNDS'),
            (4, 'COMMENTS BY UNIVERSITY REGISTRAR'),
            (5, 'APPROVAL BY VICE-CHANCELLOR'),
            (6, 'RECOMMENDATION OF PAYMENT BY CHIEF PROCUREMENT OFFICER'),
            (7, 'AUTHORIZATION OF PAYMENT BY DIRECTOR OF FINANCE'),
        ]:
            db.session.add(WorkflowStep(
                form_type_id=pf.id, step_order=step_order, step_name=step_name
            ))

    # Transport Booking — 3 steps (B→C→D)
    tb = FormType.query.filter_by(ref_number='TRANS/01/08/13').first()
    if tb and not WorkflowStep.query.filter_by(form_type_id=tb.id).first():
        for step_order, step_name in [
            (1, 'Endorsement of Head of Department'),
            (2, 'Section C – Transport Officer'),
            (3, 'Section D – University Registrar'),
        ]:
            db.session.add(WorkflowStep(
                form_type_id=tb.id, step_order=step_order, step_name=step_name
            ))

    # Fuel Requisition — 4 steps (B→C→D→E)
    fuel = FormType.query.filter_by(ref_number='FUEL/01').first()
    if fuel and not WorkflowStep.query.filter_by(form_type_id=fuel.id).first():
        for step_order, step_name in [
            (1, 'SECTION B – Transport Officer'),
            (2, 'SECTION C – Head of Department'),
            (3, 'SECTION D – University Registrar'),
            (4, 'SECTION E – Director of Finance'),
        ]:
            db.session.add(WorkflowStep(
                form_type_id=fuel.id, step_order=step_order, step_name=step_name
            ))

    db.session.commit()

    # ── Default Admin User ─────────────────────────────────────────
    admin_role = Role.query.filter_by(name='System Administrator').first()
    if admin_role and not User.query.filter_by(employee_id='ADMIN001').first():
        admin = User(
            employee_id='ADMIN001', full_name='System Administrator',
            email='admin@mzuni.ac.mw', post='System Administrator',
            grade='A1', role_id=admin_role.id
        )
        admin.set_password('Admin@1234')
        db.session.add(admin)
        db.session.commit()
