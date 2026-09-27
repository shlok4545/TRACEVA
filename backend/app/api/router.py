from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.facilities import router as facilities_router
from app.api.routes.facility import router as facility_router
from app.api.routes.health import router as health_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.passports import qr_router, router as passports_router
from app.api.routes.pickups import router as pickups_router
from app.api.routes.reports import router as reports_router
from app.api.routes.treatment import router as treatment_router
from app.api.routes.transport import router as transport_router
from app.api.routes.users import router as users_router
from app.api.routes.wards import router as wards_router
from app.api.routes.waste import router as waste_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health")
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(users_router, prefix="/users")
api_router.include_router(facilities_router, prefix="/facilities")
api_router.include_router(facility_router, prefix="/facility")
api_router.include_router(wards_router, prefix="/wards")
api_router.include_router(waste_router)
api_router.include_router(passports_router, prefix="/passports")
api_router.include_router(qr_router, prefix="/qr")
api_router.include_router(pickups_router, prefix="/pickups")
api_router.include_router(pickups_router, prefix="/collector")
api_router.include_router(transport_router, prefix="/transport")
api_router.include_router(treatment_router, prefix="/treatment")
api_router.include_router(incidents_router, prefix="/incidents")
api_router.include_router(notifications_router, prefix="/notifications")
api_router.include_router(dashboard_router, prefix="/dashboard")
api_router.include_router(reports_router, prefix="/reports")
