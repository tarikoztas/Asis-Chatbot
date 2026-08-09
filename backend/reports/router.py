"""Rapor API'si: GET /api/reports/{report_id}

Örnek: /api/reports/dolum-hakedis?start=2026-06-01&end=2026-06-30&bolge=Kadıköy
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Request

from backend.reports import mock_data, service
from backend.reports.registry import REPORTS

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{report_id}")
def get_report(report_id: str, request: Request,
               start: date | None = None, end: date | None = None,
               limit: int = service.KART_SATIR_LIMITI) -> dict:
    meta = REPORTS.get(report_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Bilinmeyen rapor: {report_id}")

    # Enum filtreleri sorgu parametrelerinden topla ve kayıt defterine göre doğrula
    enum_filters = {}
    for anahtar, tanim in meta["enum_filters"].items():
        deger = request.query_params.get(anahtar)
        if deger is None:
            continue
        if deger not in tanim["values"]:
            raise HTTPException(
                status_code=422,
                detail=f"Geçersiz {anahtar} değeri: {deger!r}. "
                       f"İzin verilenler: {tanim['values']}",
            )
        enum_filters[anahtar] = deger

    # Tek uç verildiyse diğerini veri ufkuyla tamamla
    bugun = date.today()
    if start is not None and end is None:
        end = bugun
    elif end is not None and start is None:
        start = mock_data.data_start(bugun)

    return service.get_report(report_id, start, end, enum_filters,
                              limit=max(1, min(limit, 500)))
