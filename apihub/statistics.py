from fastapi import APIRouter, Depends, Request

from apihub_users.common.db_session import create_session
from apihub_users.security.schemas import UserBase
from apihub_users.security.depends import require_token
from apihub_users.usage.queries import ActivityQuery

router = APIRouter()

STATISTICS_WINDOW = ["days", "weeks", "months", "quarters", "years"]


@router.get("/requests")
def count_requests(
    request: Request,
    user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    d = dict(request.query_params)
    if "time_range" not in request.query_params.keys():
        d["time_range"] = 7

    if "period" not in request.query_params.keys():
        d["period"] = "days"

    query = ActivityQuery(session)
    return {"count": query.get_activities_count(**d)}
