from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any


@dataclass(frozen=True, slots=True)
class CameraGeoTransform:
    camera_code: str
    origin_lat: float
    origin_lng: float
    lat_per_world_y: float
    lng_per_world_x: float


@dataclass(frozen=True, slots=True)
class SpatialCellConfig:
    zoom: int
    cell_size_degrees: float
    spatial_ref: str = "EPSG:4326"


@dataclass(frozen=True, slots=True)
class GeoPoint:
    lat: float
    lng: float


def world_xy_to_geo(point: tuple[float, float], transform: CameraGeoTransform) -> GeoPoint:
    x, y = point
    return GeoPoint(
        lat=transform.origin_lat + (y * transform.lat_per_world_y),
        lng=transform.origin_lng + (x * transform.lng_per_world_x),
    )


def cell_id_for_geo(camera_code: str, point: GeoPoint, config: SpatialCellConfig) -> str:
    lat_bucket = floor(point.lat / config.cell_size_degrees)
    lng_bucket = floor(point.lng / config.cell_size_degrees)
    return f"{camera_code}:{config.zoom}:{lat_bucket}:{lng_bucket}"


def cell_centroid_from_id(cell_id: str, config: SpatialCellConfig) -> GeoPoint:
    parts = cell_id.split(":")
    if len(parts) != 4:
        raise ValueError("cell_id must be camera:zoom:lat_bucket:lng_bucket")
    lat_bucket = int(parts[2])
    lng_bucket = int(parts[3])
    return GeoPoint(
        lat=(lat_bucket + 0.5) * config.cell_size_degrees,
        lng=(lng_bucket + 0.5) * config.cell_size_degrees,
    )


def extract_xy_points(value: Any) -> tuple[tuple[float, float], ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return ()
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(
        (float(point[0]), float(point[1]))
        for point in value
        if isinstance(point, (list, tuple)) and len(point) >= 2
    )
