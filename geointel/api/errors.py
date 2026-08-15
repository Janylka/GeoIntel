from fastapi import HTTPException, status
from geointel.contracts.metrics import METRICS, ScopeTooFineError
from geointel.contracts.scope import Scope

def validate_metric_scope(metric_id: str, requested_scope: Scope) -> None:
    if metric_id not in METRICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown metric: {metric_id}"
        )
    
    metric_def = METRICS[metric_id]
    if requested_scope.is_finer_than(metric_def.min_scope):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "scope_too_fine",
                "metric": metric_id,
                "min_scope": metric_def.min_scope.value,
                "requested": requested_scope.value,
                "reason": f"Native resolution {metric_def.native_resolution_m} m is too coarse for {requested_scope.value}-level display"
            }
        )