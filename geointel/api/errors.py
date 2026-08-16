from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from geointel.contracts.metrics import ScopeTooFineError, UnknownMetricError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ScopeTooFineError)
    async def scope_too_fine_handler(request: Request, exc: ScopeTooFineError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "ScopeTooFineError",
                "message": str(exc),
                "metric_id": exc.metric_id,
                "min_scope": exc.min_scope.value,
                "requested_scope": exc.requested.value,
            },
        )

    @app.exception_handler(UnknownMetricError)
    async def unknown_metric_handler(request: Request, exc: UnknownMetricError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": "UnknownMetricError",
                "message": str(exc),
                "metric_id": exc.metric_id,
            },
        )
