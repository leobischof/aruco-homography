"""Seiten- und Kachelgeometrie."""

from __future__ import annotations

import math

import pytest

from app import config
from app.notices import AppError
from app.pdf.layout import single_page, strip_height, tile_layout


def test_seite_ist_objekt_plus_rand_plus_streifen():
    page = single_page(400.0, 250.0, 5.0, strip_height())

    assert page.page_w == pytest.approx(410.0)
    assert page.page_h == pytest.approx(250.0 + 10.0 + config.STRIP_H_MM)
    assert page.image.as_tuple() == pytest.approx((5.0, 5.0 + config.STRIP_H_MM, 400.0, 250.0))


def test_streifen_ist_immer_da():
    """Er traegt das Markenzeichen, und das gehoert auf jedes Blatt."""
    assert strip_height() == config.STRIP_H_MM


def test_randlos_belegt_das_bild_trotzdem_exakt_den_zuschnitt():
    """Der Streifen vergroessert die SEITE, nie das Bild - die Invariante bleibt."""
    page = single_page(400.0, 250.0, 0.0, strip_height())

    assert page.image.as_tuple() == pytest.approx((0.0, config.STRIP_H_MM, 400.0, 250.0))
    assert (page.page_w, page.page_h) == pytest.approx((400.0, 250.0 + config.STRIP_H_MM))


def test_leerer_zuschnitt_wird_abgelehnt():
    with pytest.raises(AppError) as error:
        single_page(0.0, 250.0, 5.0, 0.0)
    assert error.value.code == "empty_crop"


def test_kachelzahl_folgt_der_formel():
    strip = strip_height()
    plan = tile_layout(700.0, 500.0, "A4", "portrait", 5.0, 10.0, strip)

    usable_w = 210.0 - 10.0
    usable_h = 297.0 - 10.0 - config.STRIP_H_MM
    assert plan.n_cols == max(1, math.ceil((700.0 - 10.0) / (usable_w - 10.0)))
    assert plan.n_rows == max(1, math.ceil((500.0 - 10.0) / (usable_h - 10.0)))
    assert plan.page_count == plan.n_cols * plan.n_rows


def test_kacheln_decken_den_ganzen_zuschnitt_ab():
    """Jeder Millimeter des Zuschnitts muss auf mindestens einem Blatt liegen."""
    crop_w, crop_h = 700.0, 500.0
    plan = tile_layout(crop_w, crop_h, "A4", "portrait", 5.0, 10.0, strip_height())

    for position in [0.0, 123.4, 349.9, crop_w - 0.01]:
        assert any(t.crop_x <= position <= t.crop_x + t.src_w for t in plan.tiles), position
    for position in [0.0, 88.8, 251.0, crop_h - 0.01]:
        assert any(t.crop_y <= position <= t.crop_y + t.src_h for t in plan.tiles), position


def test_ueberlappung_wird_eingehalten():
    plan = tile_layout(700.0, 500.0, "A4", "portrait", 5.0, 10.0, 0.0)
    assert plan.step_w == pytest.approx(plan.usable_w - plan.overlap_mm)
    assert plan.step_h == pytest.approx(plan.usable_h - plan.overlap_mm)


def test_letzte_kachel_laeuft_nicht_ueber_den_zuschnitt_hinaus():
    plan = tile_layout(700.0, 500.0, "A4", "portrait", 5.0, 10.0, 0.0)
    for tile in plan.tiles:
        assert tile.crop_x + tile.src_w <= 700.0 + 1e-9
        assert tile.crop_y + tile.src_h <= 500.0 + 1e-9
        assert tile.src_w > 0.0 and tile.src_h > 0.0


def test_auto_ausrichtung_waehlt_die_seitensparende_variante():
    breit = tile_layout(900.0, 200.0, "A4", "auto", 5.0, 10.0, 0.0)
    quer = tile_layout(900.0, 200.0, "A4", "landscape", 5.0, 10.0, 0.0)
    hoch = tile_layout(900.0, 200.0, "A4", "portrait", 5.0, 10.0, 0.0)

    assert breit.page_count == min(quer.page_count, hoch.page_count)


def test_zu_grosse_ueberlappung_bricht_ab():
    with pytest.raises(AppError) as error:
        tile_layout(700.0, 500.0, "A4", "portrait", 5.0, 250.0, 0.0)
    assert error.value.code == "overlap_too_large"


def test_a3_braucht_weniger_blaetter_als_a4():
    a4 = tile_layout(700.0, 500.0, "A4", "auto", 5.0, 10.0, 0.0)
    a3 = tile_layout(700.0, 500.0, "A3", "auto", 5.0, 10.0, 0.0)
    assert a3.page_count < a4.page_count
