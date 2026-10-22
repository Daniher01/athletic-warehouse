class DomainError(Exception):
    """Base domain exception."""


class PlayerNotFoundError(DomainError):
    """Raised when a player is not found."""

    def __init__(self, player_id: str) -> None:
        super().__init__(f"Player with ID '{player_id}' was not found.")
        self.player_id = player_id


class MissingPlayerIdError(DomainError):
    """Raised when a form record lacks the required player_id column."""

    def __init__(self, record_index: int | None = None) -> None:
        msg = (
            f"Record at index {record_index} is missing required 'player_id'."
            if record_index is not None
            else "Form record is missing required 'player_id'."
        )
        super().__init__(msg)
        self.record_index = record_index


class InvalidRecordError(DomainError):
    """Raised when a form record fails invariant validation."""
