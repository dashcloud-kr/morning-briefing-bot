"""지역 → 기상청 격자·에어코리아 시도 매핑."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    label: str
    nx: int
    ny: int
    sido: str


REGIONS: dict[str, Region] = {
    "서울": Region("서울", 60, 127, "서울"),
    "부산": Region("부산", 98, 76, "부산"),
    "대구": Region("대구", 89, 90, "대구"),
    "인천": Region("인천", 55, 124, "인천"),
    "광주": Region("광주", 58, 74, "광주"),
    "대전": Region("대전", 67, 100, "대전"),
    "울산": Region("울산", 102, 84, "울산"),
    "세종": Region("세종", 66, 103, "세종"),
    "수원": Region("수원", 60, 121, "경기"),
    "춘천": Region("춘천", 73, 134, "강원"),
    "강릉": Region("강릉", 92, 131, "강원"),
    "청주": Region("청주", 69, 106, "충북"),
    "천안": Region("천안", 63, 110, "충남"),
    "전주": Region("전주", 63, 89, "전북"),
    "목포": Region("목포", 50, 67, "전남"),
    "여수": Region("여수", 73, 66, "전남"),
    "포항": Region("포항", 102, 94, "경북"),
    "창원": Region("창원", 91, 77, "경남"),
    "제주": Region("제주", 52, 38, "제주"),
}

DEFAULT_REGION = "서울"


def resolve_region(name: str) -> Region | None:
    return REGIONS.get(name.strip())


def region_names() -> str:
    return ", ".join(REGIONS.keys())
