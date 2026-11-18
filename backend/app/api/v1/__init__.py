"""
v1 API router. Imports submodules via absolute import to avoid circular-import
issues during partial initialization of this package.
"""
from fastapi import APIRouter

import app.api.v1.auth as _auth
import app.api.v1.documents as _documents
import app.api.v1.health as _health
import app.api.v1.ml_debug as _ml_debug

api_router = APIRouter()
api_router.include_router(_health.router)
api_router.include_router(_auth.router)
api_router.include_router(_documents.router)
api_router.include_router(_ml_debug.router)
