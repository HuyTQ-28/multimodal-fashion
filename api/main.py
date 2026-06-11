"""FastAPI application entrypoint."""

from fastapi import FastAPI

from api.routes import router


app = FastAPI(title="FREEDOM-RT")
app.include_router(router)
