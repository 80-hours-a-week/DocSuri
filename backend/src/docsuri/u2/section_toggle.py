"""Session-scoped summary section collapse state."""

from __future__ import annotations

from docsuri.u0.ports import SessionPort

from .models import SectionKey, SectionToggleState, SummaryResult


class SectionToggleController:
    def __init__(self, session: SessionPort) -> None:
        self._session = session
        self._states: dict[str, SectionToggleState] = {}

    def toggle(self, section: SectionKey) -> SectionToggleState:
        state = self._state()
        state.collapsed[section] = not state.collapsed[section]
        return state.model_copy(deep=True)

    def defaults_for(self, _summary: SummaryResult) -> SectionToggleState:
        return self._state().model_copy(deep=True)

    def _state(self) -> SectionToggleState:
        anon_id = self._session.session().anon_id
        if anon_id not in self._states:
            self._states[anon_id] = SectionToggleState()
        return self._states[anon_id]
