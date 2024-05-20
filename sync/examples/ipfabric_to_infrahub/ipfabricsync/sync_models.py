from typing import Any, List, Optional

from infrahub_sync.adapters.ipfabricsync import IpfabricsyncModel

# -------------------------------------------------------
# AUTO-GENERATED FILE, DO NOT MODIFY
#  This file has been generated with the command `infrahub-sync generate`
#  All modifications will be lost the next time you reexecute this command
# -------------------------------------------------------

class BuiltinLocation(IpfabricsyncModel):
    _modelname = "BuiltinLocation"
    _identifiers = ("name",)
    _attributes = ("description", "type")
    name: str
    description: Optional[str] = None
    type: str
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class CoreOrganization(IpfabricsyncModel):
    _modelname = "CoreOrganization"
    _identifiers = ("name",)
    _attributes = ("type",)
    name: str
    type: Optional[str] = None
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class InfraDevice(IpfabricsyncModel):
    _modelname = "InfraDevice"
    _identifiers = ("hostname", "location")
    _attributes = ("platform", "model", "version", "serial_number", "hardware_serial_number", "fqdn")
    hostname: str
    serial_number: str
    hardware_serial_number: str
    fqdn: Optional[str] = None
    location: str
    platform: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class InfraNOSVersion(IpfabricsyncModel):
    _modelname = "InfraNOSVersion"
    _identifiers = ("manufacturer", "version")
    _attributes = ("platform", "model")
    version: str
    manufacturer: str
    platform: Optional[str] = None
    model: Optional[str] = None
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class InfraPartNumber(IpfabricsyncModel):
    _modelname = "InfraPartNumber"
    _identifiers = ("device", "name")
    _attributes = ("manufacturer", "model", "description", "part_id", "part_sn", "part_vid")
    name: Optional[str] = None
    description: Optional[str] = None
    part_id: Optional[str] = None
    part_sn: Optional[str] = None
    part_vid: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    device: Optional[str] = None
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class InfraPlatform(IpfabricsyncModel):
    _modelname = "InfraPlatform"
    _identifiers = ("name",)
    _attributes = ("description",)
    name: str
    description: Optional[str] = None
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class InfraVLAN(IpfabricsyncModel):
    _modelname = "InfraVLAN"
    _identifiers = ("location", "vlan_id")
    _attributes = ("description", "name")
    vlan_id: int
    description: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class InfraVRF(IpfabricsyncModel):
    _modelname = "InfraVRF"
    _identifiers = ("name",)
    _attributes = ("vrf_rd",)
    vrf_rd: Optional[str] = None
    name: str
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class TemplateDeviceType(IpfabricsyncModel):
    _modelname = "TemplateDeviceType"
    _identifiers = ("name", "manufacturer")
    _attributes = ("description",)
    name: str
    description: Optional[str] = None
    manufacturer: str
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class InfraInterfaceL3(IpfabricsyncModel):
    _modelname = "InfraInterfaceL3"
    _identifiers = ("device", "name")
    _attributes = ("mac_address", "mtu", "speed", "description")
    mac_address: Optional[str] = None
    mtu: Optional[int] = 2000
    speed: Optional[int] = None
    description: Optional[str] = None
    name: str
    device: str
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class InfraIPAddress(IpfabricsyncModel):
    _modelname = "InfraIPAddress"
    _identifiers = ("address",)
    _attributes = ("interface", "prefix", "description")
    description: Optional[str] = None
    address: str
    interface: Optional[str] = None
    prefix: Optional[str] = None
    local_id: Optional[str] = None
    local_data: Optional[Any] = None

class InfraPrefix(IpfabricsyncModel):
    _modelname = "InfraPrefix"
    _identifiers = ("prefix", "vrf")
    _attributes = ("location", "vlan")
    prefix: str
    vrf: Optional[str] = None
    location: Optional[str] = None
    vlan: Optional[str] = None
    local_id: Optional[str] = None
    local_data: Optional[Any] = None