from datetime import date
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from warehouse_backend.application.use_cases.ingest_records import (
    IngestionResult,
    IngestTableflowRecordsUseCase,
)
from warehouse_backend.domain.exceptions import MissingPlayerIdError
from warehouse_backend.domain.models import FormRecord
from warehouse_backend.presentation.api.dependencies import get_ingest_use_case

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


class TableflowRecordItem(BaseModel):
    record_id: UUID | None = None
    player_id: UUID
    category_id: UUID | None = None
    metric_date: date
    data: dict[str, Any] = Field(default_factory=dict)


class TableflowWebhookPayload(BaseModel):
    club_id: UUID
    department_id: str
    form_name: str
    category_id: UUID
    records: list[TableflowRecordItem]


class IngestionResponse(BaseModel):
    status: str
    records_processed: int
    records_inserted: int
    players_provisioned: int


@router.post("/tableflow", response_model=IngestionResponse, status_code=status.HTTP_200_OK)
async def ingest_tableflow(
    payload: TableflowWebhookPayload,
    use_case: Annotated[IngestTableflowRecordsUseCase, Depends(get_ingest_use_case)],
) -> IngestionResponse:
    domain_records: list[FormRecord] = []
    for item in payload.records:
        if not item.player_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Form record rejected: 'player_id' is required.",
            )
        domain_records.append(
            FormRecord(
                record_id=item.record_id or uuid4(),
                club_id=payload.club_id,
                department_id=payload.department_id,
                form_name=payload.form_name,
                player_id=item.player_id,
                category_id=item.category_id or payload.category_id,
                metric_date=item.metric_date,
                raw_data=item.data,
            )
        )

    try:
        result: IngestionResult = await use_case.execute(
            records=domain_records,
            default_category_id=payload.category_id,
        )
    except MissingPlayerIdError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err

    return IngestionResponse(
        status="success",
        records_processed=result.records_processed,
        records_inserted=result.records_inserted,
        players_provisioned=result.players_provisioned,
    )
