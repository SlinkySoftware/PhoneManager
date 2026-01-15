"""In-memory registry for device type renderers."""
from typing import Dict, List, Type

from .device_types.base import DeviceType
from .device_types.example_sip_phone import ExampleSIPPhone


REGISTERED_TYPES: Dict[str, Type[DeviceType]] = {
    ExampleSIPPhone.TypeID: ExampleSIPPhone,
}


def list_device_types() -> List[Type[DeviceType]]:
    return list(REGISTERED_TYPES.values())


def get_device_type(type_id: str) -> Type[DeviceType] | None:
    return REGISTERED_TYPES.get(type_id)
