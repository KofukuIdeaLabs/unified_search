from fastapi import APIRouter

from app.api.routes import auth, users, utils,search,indexed_table,indexed_db,index_data,form_instance,form_template

api_router = APIRouter()
api_router.include_router(auth.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(indexed_table.router, prefix="/indexed_table", tags=["indexed_table"])
api_router.include_router(indexed_db.router, prefix="/indexed_db", tags=["indexed_db"])
api_router.include_router(index_data.router, prefix="/index_data", tags=["index_data"])
api_router.include_router(form_template.router,prefix="/form_template",tags=["form_template"])
api_router.include_router(form_instance.router,prefix="/form_instance",tags=["form_instance"])