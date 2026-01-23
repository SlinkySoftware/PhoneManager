# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""In-memory registry for device type renderers."""
from typing import Dict, List, Type


from .device_types.base import DeviceType
from .device_types.example_sip_phone import ExampleSIPPhone
from .device_types.grandstream_ht812 import GrandstreamHT812
from .device_types.yealink_sip_t33g import YealinkSIPT33G
from .device_types.yealink_w70b_dect import YealinkW70BDECT


REGISTERED_TYPES: Dict[str, Type[DeviceType]] = {
    ExampleSIPPhone.TypeID: ExampleSIPPhone,
    GrandstreamHT812.TypeID: GrandstreamHT812,
    YealinkSIPT33G.TypeID: YealinkSIPT33G,
    YealinkW70BDECT.TypeID: YealinkW70BDECT,
}


def list_device_types() -> List[Type[DeviceType]]:
    return list(REGISTERED_TYPES.values())


def get_device_type(type_id: str) -> Type[DeviceType] | None:
    return REGISTERED_TYPES.get(type_id)
