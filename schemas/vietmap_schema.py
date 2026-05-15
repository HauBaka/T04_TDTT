from pydantic import BaseModel

from schemas.response_schema import GPSCoordinates


class VietMapAutocompleteRequest(BaseModel):
    text: str
    focus: GPSCoordinates | None = None


class AutoCompleteResult(BaseModel):
    name: str
    address: str
    display: str
    ref_id: str
    distance: float | None = None
    gps: GPSCoordinates | None = None


class VietMapAutocompleteResponse(BaseModel):
    data: list[AutoCompleteResult] | None = None


class VietMapPlaceDetailRequest(BaseModel):
    ref_id: str


class VietMapPlaceResult(BaseModel):
    name: str
    address: str
    display: str
    gps_coordinates: GPSCoordinates


class VietMapPlaceDetailResponse(BaseModel):
    result: VietMapPlaceResult | None = None
