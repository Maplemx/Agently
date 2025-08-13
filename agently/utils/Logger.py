# Copyright 2023-2025 AgentEra(Agently.Tech)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from logging.config import dictConfig
from typing import cast
import importlib.util


LEVEL_PREFIXES = {
    "DEBUG": "[DEBUG]",
    "INFO": "[INFO]",
    "WARNING": "[WARNING]",
    "ERROR": "[ERROR]",
    "CRITICAL": "[CRITICAL]",
}


class AgentlyFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.levelprefix = LEVEL_PREFIXES.get(record.levelname, f"[{record.levelname}]")
        return super().format(record)


class AgentlyLogger(logging.Logger):
    def raise_error(self, error: Exception | str):
        from agently import Agently

        if isinstance(error, str):
            error = RuntimeError(error)
        self.error(error)
        if Agently.settings.get("runtime.raise_error"):
            raise error


logging.setLoggerClass(AgentlyLogger)


def create_logger(app_name: str = "Agently", log_level: str = "INFO") -> AgentlyLogger:
    _inspect_uvicorn = importlib.util.find_spec("uvicorn")

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": (
                {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(asctime)s | %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
                if _inspect_uvicorn
                else {
                    "()": AgentlyFormatter,
                    "fmt": "%(levelprefix)s %(asctime)s | %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            )
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": log_level,
            },
            "uvicorn.error": {
                "level": log_level,
                "handlers": ["default"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": log_level,
                "handlers": ["default"],
                "propagate": False,
            },
        },
    }

    dictConfig(logging_config)
    return cast(AgentlyLogger, logging.getLogger(app_name))
