"""
Retirement scenario persistence service.

CRUD operations for retirement calculator scenarios.
Config is stored as a JSON blob; results are not persisted.
"""

import json
import logging
from typing import List, Optional

from db.models import RetirementScenario
from services.base_service import SessionMixin

logger = logging.getLogger(__name__)


class RetirementScenarioService(SessionMixin):
    """CRUD service for retirement scenarios."""

    def list_scenarios(self) -> List[RetirementScenario]:
        """Return all scenarios ordered by id (creation order)."""
        return (
            self.session.query(RetirementScenario)
            .order_by(RetirementScenario.id)
            .all()
        )

    def get_scenario(self, scenario_id: int) -> Optional[RetirementScenario]:
        """Return a single scenario by id, or None."""
        return self.session.get(RetirementScenario, scenario_id)

    def create_scenario(self, name: str, config: dict) -> RetirementScenario:
        """Create a new scenario. Returns the created row."""
        scenario = RetirementScenario(
            name=name,
            config=json.dumps(config),
        )
        self.session.add(scenario)
        self.session.commit()
        self.session.refresh(scenario)
        logger.info("Created retirement scenario %d: %s", scenario.id, name)
        return scenario

    def update_scenario(
        self,
        scenario_id: int,
        *,
        name: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> Optional[RetirementScenario]:
        """Partial update. Returns updated row, or None if not found."""
        scenario = self.get_scenario(scenario_id)
        if scenario is None:
            return None
        if name is not None:
            scenario.name = name
        if config is not None:
            scenario.config = json.dumps(config)
        self.session.commit()
        self.session.refresh(scenario)
        return scenario

    def delete_scenario(self, scenario_id: int) -> bool:
        """Delete a scenario. Returns True if deleted, False if not found."""
        scenario = self.get_scenario(scenario_id)
        if scenario is None:
            return False
        self.session.delete(scenario)
        self.session.commit()
        logger.info("Deleted retirement scenario %d", scenario_id)
        return True
