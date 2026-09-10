"""CrewAI trading application package.

The state export is lazy so pure contracts and deterministic policies can be
imported without initializing the optional CrewAI runtime.
"""

__all__ = ["TelegramSignalState"]


def __getattr__(name: str):
    if name == "TelegramSignalState":
        from crewai_app.flows.states import TelegramSignalState

        return TelegramSignalState
    raise AttributeError(name)
