#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Definicion de listings, filtros de dormitorios, conteo de unidades
y disponibilidad manual extra.

Este archivo es puramente datos/configuracion. No contiene logica.
"""

# ================== LISTA PRINCIPAL (FULL SYNC) ==================
PRIMARY_LISTINGS = [
    {"listing_id": 401039, "resort_code": "MRP"},
    {"listing_id": 400411, "resort_code": "WMH"},
    {"listing_id": 400413, "resort_code": "WMH"},
    {"listing_id": 400415, "resort_code": "WKV"},
    {"listing_id": 400458, "resort_code": "WRB"},
    {"listing_id": 400459, "resort_code": "MRD"},
    {"listing_id": 400579, "resort_code": "MGC"},
    {"listing_id": 400581, "resort_code": "MSE"},
    {"listing_id": 400586, "resort_code": "MHB"},
    {"listing_id": 400419, "resort_code": "MPB"},
    {"listing_id": 400426, "resort_code": "RFR"},
    {"listing_id": 400457, "resort_code": "MVF"},
    {"listing_id": 400587, "resort_code": "MBP"},
    {"listing_id": 401016, "resort_code": "MBP"},
    {"listing_id": 401017, "resort_code": "MOU"},
    {"listing_id": 401019, "resort_code": "MVD"},
    {"listing_id": 401020, "resort_code": "MBY"},
    {"listing_id": 401021, "resort_code": "MFV"},
    {"listing_id": 401024, "resort_code": "MGQ"},
    {"listing_id": 401026, "resort_code": "MOW"},
    {"listing_id": 401027, "resort_code": "VTA"},
    {"listing_id": 401029, "resort_code": "NCV"},
    {"listing_id": 401033, "resort_code": "HSC"},
    {"listing_id": 401037, "resort_code": "MMS"},
    {"listing_id": 401038, "resort_code": "WKV"},
    {"listing_id": 401050, "resort_code": "SRM"},
    {"listing_id": 401053, "resort_code": "MVB"},
    {"listing_id": 401057, "resort_code": "MHH"},
    {"listing_id": 401058, "resort_code": "MSW"},
    {"listing_id": 401061, "resort_code": "MSW"},
    {"listing_id": 401065, "resort_code": "WSJ"},
    {"listing_id": 401070, "resort_code": "MMI"},
    {"listing_id": 401076, "resort_code": "MEV"},
    {"listing_id": 401077, "resort_code": "MIP"},
    {"listing_id": 401078, "resort_code": "MVL"},
    {"listing_id": 401079, "resort_code": "MVL"},
    {"listing_id": 401080, "resort_code": "MLE"},
    {"listing_id": 401028, "resort_code": "MGA"},
    {"listing_id": 405457, "resort_code": "HEC"},
    {"listing_id": 401032, "resort_code": "MGA"},
    {"listing_id": 400284, "resort_code": "MGV"},
    {"listing_id": 400359, "resort_code": "MPD"},
    {"listing_id": 400389, "resort_code": "MHB"},
    {"listing_id": 400413, "resort_code": "WMH"},
    {"listing_id": 400421, "resort_code": "SVV"},
    {"listing_id": 400571, "resort_code": "MCV"},
    {"listing_id": 400572, "resort_code": "MCV"},
    {"listing_id": 400578, "resort_code": "MGC"},
    {"listing_id": 400580, "resort_code": "MSE"},
    {"listing_id": 400582, "resort_code": "MRD"},
    {"listing_id": 400584, "resort_code": "MHB"},
    {"listing_id": 400585, "resort_code": "MSE"},
    {"listing_id": 401015, "resort_code": "MML"},
    {"listing_id": 401018, "resort_code": "MML"},
    {"listing_id": 401034, "resort_code": "MSP"},
    {"listing_id": 401064, "resort_code": "MPD"},
    {"listing_id": 401066, "resort_code": "MCP"},
    {"listing_id": 401069, "resort_code": "MDO"},
    {"listing_id": 401073, "resort_code": "MRD"},
    {"listing_id": 401074, "resort_code": "MGK"},
    {"listing_id": 401075, "resort_code": "MGK"},
    {"listing_id": 401081, "resort_code": "FAP"},
    {"listing_id": 401315, "resort_code": "MGV"},
    {"listing_id": 402468, "resort_code": "RGT"},
    {"listing_id": 453542, "resort_code": "VIT"},
]

PRIMARY_BEDROOM_FILTER = {
    401039: "2", 400411: "2", 400413: "1", 400415: "2", 400458: "1", 400459: "2", 400579: "2", 400581: "2", 400586: "2",
    400419: "0", 400426: "0", 400457: "2", 400587: "1", 401016: "0", 401017: "0", 401019: "2", 401020: "2",
    401021: "2", 401024: "0", 401026: "2", 401027: "1", 401029: "2", 401033: "0", 401037: "2", 401038: "1",
    401050: "0", 401053: "0", 401057: "2", 401058: "0", 401061: "1", 401065: "0", 401070: "2", 401076: "2",
    401077: "3", 401078: "0", 401079: "1", 401080: "2", 401028: "0", 405457: "0", 401032: "1", 400284: "0",
    400359: "0", 400389: "0", 400421: "1", 400571: "0", 400572: "1", 400578: "0", 400580: "0", 400582: "0",
    400584: "1", 400585: "1", 401015: "1", 401018: "0", 401034: "2", 401064: "1", 401066: "2", 401069: "1",
    401073: "1", 401074: "1", 401075: "2", 401081: "0", 401315: "2", 402468: "0", 453542: "2",
}

# ================== LISTA SECUNDARIA (SOLO DISPONIBILIDAD) ==================
SECONDARY_BEDROOM_FILTER = {
    400459: "2",
    400581: "2",
    401032: "1",
    401028: "0",
    400284: "0",
    400359: "0",
    400580: "0",
    400582: "0",
    400585: "1",
    401064: "1",
    401069: "1",
    401076: "2",
    401315: "2",
    402468: "0",
}

AVAILABILITY_ONLY_LISTINGS = [
    {"listing_id": 400459, "resort_code": "MR2"},
    {"listing_id": 400581, "resort_code": "MMC"},
    {"listing_id": 401032, "resort_code": "MG1"},
    {"listing_id": 401032, "resort_code": "MG3"},
    {"listing_id": 401032, "resort_code": "MG5"},
    {"listing_id": 401028, "resort_code": "MG1"},
    {"listing_id": 401028, "resort_code": "MG3"},
    {"listing_id": 401028, "resort_code": "MG5"},
    {"listing_id": 400284, "resort_code": "MGR"},
    {"listing_id": 400359, "resort_code": "MDS"},
    {"listing_id": 400580, "resort_code": "MMC"},
    {"listing_id": 400582, "resort_code": "MR2"},
    {"listing_id": 400585, "resort_code": "MMC"},
    {"listing_id": 401064, "resort_code": "MDS"},
    {"listing_id": 401069, "resort_code": "MVB"},
    {"listing_id": 401069, "resort_code": "MEV"},
    {"listing_id": 401076, "resort_code": "MVB"},
    {"listing_id": 401076, "resort_code": "MDO"},
    {"listing_id": 401315, "resort_code": "MGR"},
    {"listing_id": 402468, "resort_code": "RT2"},
    {"listing_id": 402468, "resort_code": "RT1"},
]

# ================== CONTEO DE UNIDADES ==================
ALL_UNIT_COUNTS = {
    # Multi-units
    400284: 4,
    400359: 5,
    400389: 2,
    401034: 2,
    401060: 3,
    401066: 2,
    # Single-units
    400411: 1, 400413: 1, 400415: 1, 400419: 1, 400421: 1, 400426: 1,
    400457: 1, 400458: 1, 400459: 1, 400571: 1, 400572: 1, 400578: 1,
    400579: 1, 400580: 1, 400581: 1, 400582: 1, 400584: 1, 400585: 1,
    400586: 1, 400587: 1, 401015: 1, 401016: 1, 401017: 1, 401018: 1,
    401019: 1, 401020: 1, 401021: 1, 401024: 1, 401026: 1, 401027: 1,
    401028: 1, 401029: 1, 401032: 1, 401033: 1, 401037: 1, 401038: 1,
    401039: 1, 401050: 1, 401053: 1, 401057: 1, 401058: 1, 401061: 1,
    401064: 1, 401065: 1, 401069: 1, 401070: 1, 401073: 1, 401074: 1,
    401075: 1, 401076: 1, 401077: 1, 401078: 1, 401079: 1, 401080: 1,
    401081: 1, 401315: 1, 402468: 1, 405457: 1, 453542: 1,
}

# ================== DISPONIBILIDAD MANUAL EXTRA ==================
# Rangos estilo check-in / check-out.
# Fechas interpretadas como noches desde startDate hasta el dia anterior a endDate.
MANUAL_EXTRA_AVAIL = {
    400359: [
        ("2026-04-03", "2026-04-10"),
    ],
    "1348054833142358701": [
        ("2026-04-04", "2026-04-12"),
    ],
}
