"""Turntable camera list. Safe to import outside Blender."""

from __future__ import annotations


def view_specs(*, quick: bool) -> list[dict[str, object]]:
    if quick:
        azimuths = list(range(0, 360, 45))
        elevations = (12,)
        holdout_az = {90, 270}
    else:
        azimuths = list(range(0, 360, 30))
        elevations = (8, 22)
        holdout_az = {45, 135, 225, 315}
    rows: list[dict[str, object]] = []
    for el in elevations:
        for az in azimuths:
            rows.append(
                {
                    "id": f"az{az:03d}_el{el:02d}",
                    "azimuth": az,
                    "elevation": el,
                    "holdout": az in holdout_az and el == elevations[-1],
                }
            )
    return rows
