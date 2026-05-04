"""Resources model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Resources:
    """Resources bag."""

    antimatter: float
    boost: float
    exotics: float
    fissiles: float
    influence: float
    metals: float
    mission_control: float
    money: float
    noble_metals: float
    operations: float
    volatiles: float
    water: float
