from fastapi import APIRouter

import app.api.v1.auth as _auth
import app.api.v1.documents as _documents
import app.api.v1.health as _health
import app.api.v1.ml_debug as _ml_debug
import app.api.v1.search as _search

api_router = APIRouter()
api_router.include_router(_health.router)
api_router.include_router(_auth.router)
api_router.include_router(_documents.router)
api_router.include_router(_search.router)
api_router.include_router(_ml_debug.router)
