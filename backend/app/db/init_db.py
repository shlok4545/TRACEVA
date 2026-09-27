import os

from sqlalchemy import text

from app.core.security import get_password_hash
from app.db.database import Base, SessionLocal, engine

DEMO_PASSWORD = os.getenv("TRACEVA_DEMO_PASSWORD", "Traceva@2026")


def _ensure_legacy_schema(db) -> None:
    table_exists = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")).fetchone()
    if table_exists is None:
        return

    columns = {row[1] for row in db.execute(text("PRAGMA table_info(notifications)")).fetchall()}
    column_defs = {
        "severity": "ALTER TABLE notifications ADD COLUMN severity VARCHAR(30) NOT NULL DEFAULT 'INFO'",
        "related_passport_id": "ALTER TABLE notifications ADD COLUMN related_passport_id INTEGER",
        "related_pickup_id": "ALTER TABLE notifications ADD COLUMN related_pickup_id INTEGER",
        "related_incident_id": "ALTER TABLE notifications ADD COLUMN related_incident_id INTEGER",
        "is_read": "ALTER TABLE notifications ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0",
        "read_at": "ALTER TABLE notifications ADD COLUMN read_at VARCHAR(30)",
    }
    for column_name, alter_sql in column_defs.items():
        if column_name not in columns:
            try:
                db.execute(text(alter_sql))
            except Exception:
                pass
    db.commit()


def init_db() -> None:
    from app.models.facility import Facility
    from app.models.pickup import CollectorProfile
    from app.models.transport import TreatmentEvidence, TreatmentRecord, TransportEvent
    from app.models.user import User
    from app.models.ward import Ward
    from app.models.waste import WasteCategory, WasteRule

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _ensure_legacy_schema(db)
        facility_specs = [
            {
                "name": "City General Hospital",
                "type": "Hospital",
                "address": "Sector 12, Metro City",
                "contact": "+91 90000 10001",
                "status": "ACTIVE",
            },
            {
                "name": "Sunrise Medical Centre",
                "type": "Clinic",
                "address": "Green Avenue, North District",
                "contact": "+91 90000 10002",
                "status": "ACTIVE",
            },
            {
                "name": "Metro Diagnostic Lab",
                "type": "Laboratory",
                "address": "North Industrial Road",
                "contact": "+91 90000 10003",
                "status": "ACTIVE",
            },
            {
                "name": "GreenCare Treatment Facility",
                "type": "Treatment Facility",
                "address": "Eco Park, South Sector",
                "contact": "+91 90000 10004",
                "status": "ACTIVE",
            },
        ]

        existing_facilities = {facility.name: facility for facility in db.query(Facility).all()}
        for spec in facility_specs:
            if spec["name"] not in existing_facilities:
                facility = Facility(
                    name=spec["name"],
                    type=spec["type"],
                    address=spec["address"],
                    contact=spec["contact"],
                    status=spec["status"],
                )
                db.add(facility)
        db.commit()

        facilities = {facility.name: facility for facility in db.query(Facility).all()}

        ward_specs = [
            ("City General Hospital", "Emergency", "Emergency"),
            ("City General Hospital", "ICU", "Critical Care"),
            ("City General Hospital", "General Ward", "General"),
            ("City General Hospital", "Pathology", "Diagnostics"),
            ("Sunrise Medical Centre", "Emergency", "Emergency"),
            ("Sunrise Medical Centre", "General Ward", "General"),
            ("Sunrise Medical Centre", "Laboratory", "Diagnostics"),
            ("Metro Diagnostic Lab", "Laboratory", "Lab"),
            ("Metro Diagnostic Lab", "Sample Processing", "Processing"),
            ("GreenCare Treatment Facility", "Treatment Bay", "Treatment"),
        ]

        for facility_name, ward_name, department_type in ward_specs:
            facility = facilities.get(facility_name)
            if facility is None:
                continue
            existing = db.query(Ward).filter(Ward.facility_id == facility.id, Ward.name == ward_name).first()
            if existing is None:
                db.add(Ward(facility_id=facility.id, name=ward_name, department_type=department_type, manager_user_id=None))
        db.commit()

        category_specs = [
            {
                "name": "Infectious / Soiled Waste",
                "code": "INF-01",
                "description": "Demo category for blood, body-fluid, or soiled biomedical waste that requires controlled handling.",
                "segregation_group": "Yellow / infectious stream",
                "risk_level": "HIGH",
                "default_disposal_method": "Contained disposal and validated treatment pathway",
                "handling_guidance": "Use leak-proof secondary containment and keep the item away from general waste streams.",
                "warning_message": "This is a demo rule set for decision support only and should be confirmed by trained staff.",
            },
            {
                "name": "Sharps",
                "code": "SHR-01",
                "description": "Used needles, blades, and sharp clinical instruments.",
                "segregation_group": "Sharps container",
                "risk_level": "CRITICAL",
                "default_disposal_method": "Rigid sharps box with controlled disposal",
                "handling_guidance": "Do not bend or recap sharps. Place directly into the approved sharps container.",
                "warning_message": "Sharps require immediate protection from injury and should be escalated if damaged or exposed.",
            },
            {
                "name": "Contaminated Recyclable Plastic",
                "code": "REC-01",
                "description": "Plastic items contaminated with clinical waste but suitable for controlled recycling after validation.",
                "segregation_group": "Contaminated recyclable stream",
                "risk_level": "MEDIUM",
                "default_disposal_method": "Controlled handling and processing according to local segregation procedure",
                "handling_guidance": "Limit contact, seal the item, and confirm the contamination status before routing it.",
                "warning_message": "If contamination level is uncertain, escalate for manual review."
            },
            {
                "name": "Glass and Metal",
                "code": "GLA-01",
                "description": "Broken vials, ampoules, or metallic clinical disposables after cleaning and screening.",
                "segregation_group": "Glass / metal stream",
                "risk_level": "MEDIUM",
                "default_disposal_method": "Puncture-safe collection and controlled material handling",
                "handling_guidance": "Use cut-resistant handling and avoid direct contact if the item is chipped or leaking.",
                "warning_message": "Handle with care; damaged glass may puncture protective clothing.",
            },
            {
                "name": "Pharmaceutical Hazardous Waste",
                "code": "PHA-01",
                "description": "Expired, mixed, or hazardous medication waste requiring careful segregation.",
                "segregation_group": "Hazardous pharmaceutical stream",
                "risk_level": "CRITICAL",
                "default_disposal_method": "Controlled hazardous disposal channel",
                "handling_guidance": "Keep away from general biomedical waste and verify the container condition before movement.",
                "warning_message": "Pharmaceutical waste should be reviewed by trained staff when labels or storage conditions are unclear.",
            },
            {
                "name": "General Biomedical Waste",
                "code": "GEN-01",
                "description": "Low-risk biomedical material that does not match a higher-risk category in the demo rule set.",
                "segregation_group": "General biomedical stream",
                "risk_level": "LOW",
                "default_disposal_method": "Routine biomedical disposal under facility protocol",
                "handling_guidance": "Use standard PPE and verify that the item does not meet a higher-risk category before disposal.",
                "warning_message": "This category is a fallback and should be reviewed if the waste item is visibly contaminated or damaged.",
            },
        ]

        for spec in category_specs:
            existing = db.query(WasteCategory).filter(WasteCategory.code == spec["code"]).first()
            if existing is None:
                db.add(WasteCategory(**spec))
        db.commit()

        categories = {category.name: category for category in db.query(WasteCategory).all()}
        rule_specs = [
            ("Infectious / Soiled Waste", "used syringe", "used syringe", 0.96, 0.0, "Place in a sealed biohazard container and keep the item separated from general waste.", "Needle exposure risk — ensure safe handling and confirm contamination status."),
            ("Infectious / Soiled Waste", "blood contaminated dressing", "blood contaminated dressing", 0.94, 0.0, "Handle as infectious waste and contain leakage before transfer.", "Body fluid contamination present; use PPE and prevent cross-contact."),
            ("Sharps", "needle", "needle", 0.97, 0.1, "Place directly in a rigid sharps container without bending or recapping.", "Needlestick risk; do not handle with bare hands."),
            ("Sharps", "syringe", "syringe", 0.95, 0.1, "Use a sharps container and avoid puncture exposure.", "Sharps container must remain closed and stable."),
            ("Contaminated Recyclable Plastic", "contaminated plastic", "contaminated plastic", 0.85, 0.0, "Segregate into the contaminated recyclable stream and confirm contamination before transfer.", "If contamination is uncertain, escalate for manual verification."),
            ("Glass and Metal", "glass vial", "glass vial", 0.88, 0.0, "Collect in puncture-safe packaging and avoid direct contact with broken edges.", "Broken glass can cause injury; use gloves and protective handling."),
            ("Pharmaceutical Hazardous Waste", "pharmaceutical", "pharmaceutical", 0.9, 0.1, "Route to the hazardous pharmaceutical stream and verify container integrity.", "Medication waste should be reviewed when labels or storage status are unclear."),
            ("Pharmaceutical Hazardous Waste", "expired medicine", "expired medicine", 0.9, 0.1, "Store in a sealed hazardous container and confirm disposal instructions.", "Expired medicines should not be mixed with general biomedical waste."),
            ("General Biomedical Waste", "general waste", "general waste", 0.7, 0.0, "Use routine biomedical segregation and verify the item is not contaminated.", "Fallback category; review if the item appears contaminated or mixed."),
        ]

        for category_name, keyword, pattern, confidence, modifier, instruction, warning in rule_specs:
            category = categories.get(category_name)
            if category is None:
                continue
            exists = db.query(WasteRule).filter(WasteRule.category_id == category.id, WasteRule.item_pattern == pattern).first()
            if exists is None:
                db.add(WasteRule(category_id=category.id, item_keyword=keyword, item_pattern=pattern, confidence_level=confidence, risk_modifier=modifier, handling_instruction=instruction, warning=warning, active=True))
        db.commit()

        ward_map = {ward.name: ward for ward in db.query(Ward).all()}
        hospital_ward_ids = {ward.id for ward in db.query(Ward).filter(Ward.facility_id == facilities["City General Hospital"].id).all()}

        users = [
            {
                "name": "System Administrator",
                "email": "admin@traceva.demo",
                "role": "ADMIN",
                "facility_id": facilities["City General Hospital"].id,
                "ward_id": None,
            },
            {
                "name": "Nurse Supervisor",
                "email": "nurse@traceva.demo",
                "role": "WARD_STAFF",
                "facility_id": facilities["City General Hospital"].id,
                "ward_id": next(iter(hospital_ward_ids), None),
            },
            {
                "name": "Collection Lead",
                "email": "collector@traceva.demo",
                "role": "COLLECTOR",
                "facility_id": facilities["City General Hospital"].id,
                "ward_id": None,
            },
            {
                "name": "Treatment Operations",
                "email": "treatment@traceva.demo",
                "role": "TREATMENT_FACILITY",
                "facility_id": facilities["GreenCare Treatment Facility"].id,
                "ward_id": None,
            },
            {
                "name": "Compliance Regulator",
                "email": "regulator@traceva.demo",
                "role": "REGULATOR",
                "facility_id": facilities["City General Hospital"].id,
                "ward_id": None,
            },
        ]

        for payload in users:
            existing = db.query(User).filter(User.email == payload["email"]).first()
            if existing is None:
                db.add(
                    User(
                        name=payload["name"],
                        email=payload["email"],
                        password_hash=get_password_hash(DEMO_PASSWORD),
                        role=payload["role"],
                        facility_id=payload["facility_id"],
                        ward_id=payload["ward_id"],
                        status="ACTIVE",
                    )
                )
        db.commit()

        collector_user = db.query(User).filter(User.email == "collector@traceva.demo").first()
        if collector_user and db.query(CollectorProfile).filter(CollectorProfile.user_id == collector_user.id).first() is None:
            db.add(
                CollectorProfile(
                    user_id=collector_user.id,
                    facility_id=collector_user.facility_id,
                    employee_code="COL-001",
                    vehicle_number="MH-12-TRV-01",
                    phone="+91 90000 99999",
                    availability_status="AVAILABLE",
                    active=True,
                )
            )
        db.commit()
    finally:
        db.close()
