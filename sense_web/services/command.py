from enum import IntEnum


class CommandType(IntEnum):
    NONE_AVAILABLE = 0
    SET_POLL_RATE = 1
    SET_RAIL_STATE = 2


class CommandSensor(IntEnum):
    ADCS = 0
    LIS3MDL = 1
    LSM6DSO = 2
    SHT4X = 3


class CommandRail(IntEnum):
    RAIL_5VH = 0


# Human-readable labels
CMD_TYPE_MAP = {
    CommandType.NONE_AVAILABLE: "None Available",
    CommandType.SET_POLL_RATE: "Set Poll Rate",
    CommandType.SET_RAIL_STATE: "Set Rail State",
}

CMD_SENSOR_MAP = {
    CommandSensor.ADCS: "ADCS",
    CommandSensor.LIS3MDL: "LIS3MDL",
    CommandSensor.LSM6DSO: "LSM6DSO",
    CommandSensor.SHT4X: "SHT4X",
}

CMD_RAIL_MAP = {
    CommandRail.RAIL_5VH: "5VH Rail",
}
