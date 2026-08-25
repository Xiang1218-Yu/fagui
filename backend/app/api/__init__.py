from fastapi import APIRouter

from app.api import assessments, changes, notifications, regulations, runs, sources, subscriptions

api_router = APIRouter()
for module in (sources, runs, changes, regulations, assessments, subscriptions, notifications):
    api_router.include_router(module.router)
