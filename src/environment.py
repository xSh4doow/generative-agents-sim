"""Ambiente da simulação: Village + Location + TimeManager."""

from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import HOURS_PER_DAY, LOCATIONS, NUM_DAYS


@dataclass
class Location:
    name: str
    description: str
    occupants: list[str] = field(default_factory=list)


class Village:
    """Conjunto de locais e quem está em cada um."""

    def __init__(self):
        self.locations: dict[str, Location] = {
            name: Location(name=name, description=desc)
            for name, desc in LOCATIONS.items()
        }

    def list_locations(self) -> list[str]:
        return list(self.locations.keys())

    def place_agent(self, agent_name: str, location: str) -> None:
        """Coloca o agente num local sem checar se já está em outro."""
        if location not in self.locations:
            raise KeyError(f"Local inexistente: {location}")
        if agent_name not in self.locations[location].occupants:
            self.locations[location].occupants.append(agent_name)

    def remove_agent_everywhere(self, agent_name: str) -> None:
        for loc in self.locations.values():
            if agent_name in loc.occupants:
                loc.occupants.remove(agent_name)

    def move_agent(self, agent_name: str, to_loc: str) -> bool:
        """Move o agente. Retorna True se mudou, False se já estava lá ou local inválido."""
        if to_loc not in self.locations:
            return False
        current = self.get_location_of(agent_name)
        if current == to_loc:
            return False
        self.remove_agent_everywhere(agent_name)
        self.place_agent(agent_name, to_loc)
        return True

    def get_agents_at(self, location: str) -> list[str]:
        if location not in self.locations:
            return []
        return list(self.locations[location].occupants)

    def get_location_of(self, agent_name: str) -> str | None:
        for name, loc in self.locations.items():
            if agent_name in loc.occupants:
                return name
        return None

    def describe(self, location: str) -> str:
        if location not in self.locations:
            return ""
        return self.locations[location].description


class TimeManager:
    """Tempo discreto: dias 1..num_days, horas em HOURS_PER_DAY."""

    def __init__(self, num_days: int = NUM_DAYS):
        self.num_days = num_days
        self.day = 1
        self._hour_idx = 0
        self.hour = HOURS_PER_DAY[0]

    def current_time(self) -> tuple:
        return (self.day, self.hour)

    def is_new_day(self) -> bool:
        return self._hour_idx == 0

    def advance(self) -> bool:
        """Avança 1 hora. Retorna False quando a simulação terminou."""
        self._hour_idx += 1
        if self._hour_idx >= len(HOURS_PER_DAY):
            self._hour_idx = 0
            self.day += 1
            if self.day > self.num_days:
                return False
        self.hour = HOURS_PER_DAY[self._hour_idx]
        return True

    def total_hours_elapsed(self) -> int:
        return (self.day - 1) * len(HOURS_PER_DAY) + self._hour_idx
