"""Server grant models. Legacy worker recovery/configuration models remain closed."""

from typing import Literal, Self

from pydantic import Field, model_validator

from marketdata.session_recovery import RecoveryReceipt, RecoveryRequest, RecoveryStream

GrantStream = Literal[
    "candles",
    "quotes",
    "coverage",
    "status",
    "tsetmc_daily",
    "tsetmc_current",
    "tsetmc_coverage",
    "tsetmc_status",
]


class Grant(RecoveryStream):
    stream: GrantStream  # type: ignore[assignment]

    @model_validator(mode="after")
    def namespace(self) -> Self:
        if (self.provider == "tsetmc") != self.stream.startswith("tsetmc_"):
            raise ValueError("provider/stream namespace mismatch")
        return self


class GrantRecoveryRequest(RecoveryRequest):
    streams: list[Grant] = Field(min_length=1, max_length=1000)  # type: ignore[assignment]


class GrantRecoveryReceipt(RecoveryReceipt):
    streams: list[Grant]  # type: ignore[assignment]
