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

import datetime
import warnings
from typing import (
    Any,
    Literal,
    Mapping,
    Union,
    get_origin,
    get_args,
    overload,
    TYPE_CHECKING,
    TypeVar,
)
from pydantic import BaseModel

if TYPE_CHECKING:
    from agently.types.data import SerializableValue, KwargsType

T = TypeVar("T")


class DataFormatter:
    @staticmethod
    def sanitize(value: Any, *, remain_type: bool = False) -> Any:
        from .RuntimeData import RuntimeData, RuntimeDataNamespace

        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.isoformat()

        if issubclass(type(value), RuntimeData) or issubclass(type(value), RuntimeDataNamespace):
            return DataFormatter.sanitize(value.data, remain_type=remain_type)

        if isinstance(value, type):
            if issubclass(value, BaseModel):
                extracted_value = {}
                for name, field in value.model_fields.items():
                    extracted_value.update(
                        {
                            name: (
                                (
                                    DataFormatter.sanitize(field.annotation, remain_type=remain_type),
                                    field.description,
                                )
                                if field.description
                                else (DataFormatter.sanitize(field.annotation, remain_type=remain_type),)
                            )
                        }
                    )
                return extracted_value
            else:
                if remain_type:
                    return value
                return value.__name__ if hasattr(value, "__name__") else str(value)
        if get_origin(value) is not None:
            if remain_type:
                return value
            original_text = get_origin(value)
            args = get_args(value)
            if original_text is list:
                return f"list[{DataFormatter.sanitize(args[0], remain_type=remain_type)}]"
            if original_text is dict:
                return f"dict[{DataFormatter.sanitize(args[0], remain_type=remain_type)}, {DataFormatter.sanitize(args[1], remain_type=remain_type)}]"
            if original_text is tuple:
                return f"tuple[{', '.join(DataFormatter.sanitize(a, remain_type=remain_type) for a in args)}]"
            if original_text is Union:
                return " | ".join(str(DataFormatter.sanitize(a, remain_type=remain_type)) for a in args)
            if original_text is Literal:
                return f"Literal[{ ', '.join(str(DataFormatter.sanitize(a, remain_type=remain_type)) for a in args) }]"
            if isinstance(value, type) and hasattr(value, "__name__"):
                return value.__name__
            return str(value)

        if isinstance(value, dict):
            return {str(k): DataFormatter.sanitize(v, remain_type=remain_type) for k, v in value.items()}
        if isinstance(value, list):
            return [DataFormatter.sanitize(v, remain_type=remain_type) for v in value]
        if isinstance(value, set):
            return {DataFormatter.sanitize(v, remain_type=remain_type) for v in value}
        if isinstance(value, tuple):
            return tuple(DataFormatter.sanitize(v, remain_type=remain_type) for v in value)

        return str(value)

    @overload
    @staticmethod
    def to_str_key_dict(
        value: Any,
        *,
        value_format: None = None,
        default_key: str,
        default_value: T = None,
        inconvertible_warning: bool = False,
    ) -> dict[str, Any | T]: ...

    @overload
    @staticmethod
    def to_str_key_dict(
        value: Any,
        *,
        value_format: Literal["serializable"],
        default_key: str,
        default_value: T = None,
        inconvertible_warning: bool = False,
    ) -> dict[str, "SerializableValue" | T]: ...

    @overload
    @staticmethod
    def to_str_key_dict(
        value: Any,
        *,
        value_format: Literal["str"],
        default_key: str,
        default_value: T = None,
        inconvertible_warning: bool = False,
    ) -> dict[str, str | T]: ...

    @overload
    @staticmethod
    def to_str_key_dict(
        value: Any,
        *,
        value_format: None = None,
        default_key: None,
        default_value: T = None,
        inconvertible_warning: bool = False,
    ) -> dict[str, Any] | T: ...

    @overload
    @staticmethod
    def to_str_key_dict(
        value: Any,
        *,
        value_format: Literal["serializable"],
        default_key: None,
        default_value: T = None,
        inconvertible_warning: bool = False,
    ) -> dict[str, "SerializableValue"] | T: ...

    @overload
    @staticmethod
    def to_str_key_dict(
        value: Any,
        *,
        value_format: Literal["str"],
        default_key: None,
        default_value: T = None,
        inconvertible_warning: bool = False,
    ) -> dict[str, str | T] | T: ...

    @overload
    @staticmethod
    def to_str_key_dict(
        value: Any,
        *,
        value_format: Literal['serializable', 'str'] | None = None,
        default_key: str | None = None,
        default_value: T = None,
        inconvertible_warning: bool = False,
    ) -> dict[str, Any] | T: ...

    @staticmethod
    def to_str_key_dict(
        value: Any,
        *,
        value_format: Literal["serializable", "str"] | None = None,
        default_key: str | None = None,
        default_value: T = None,
        inconvertible_warning: bool = False,
    ) -> dict[str, Any] | T:
        if isinstance(value, Mapping):
            if value_format is None:
                return {str(DataFormatter.sanitize(k)): v for k, v in value.items()}
            elif value_format == "serializable":
                return {str(DataFormatter.sanitize(k)): DataFormatter.sanitize(v) for k, v in value.items()}
            elif value_format == "str":
                return {str(DataFormatter.sanitize(k)): str(DataFormatter.sanitize(v)) for k, v in value.items()}
        else:
            if inconvertible_warning:
                warnings.warn(
                    f"Error: Non-dictionary value cannot be convert to a string key dictionary.\n"
                    f"Value: { value }\n"
                    "Tips: You can provide parameter 'default_key' to allow DataFormatter.to_str_key_dict() convert non-dictionary value to a dictionary { default_key: value } automatically."
                )
            # restructure value to {default_key: value}
            if default_key is not None:
                return DataFormatter.to_str_key_dict(
                    {default_key: value},
                    value_format=value_format,
                    default_value=default_value,
                )
            return default_value

    @staticmethod
    def to_str(value: Any) -> str:
        return str(DataFormatter.sanitize(value))

    @staticmethod
    def from_schema_to_kwargs_format(input_schema: dict[str, Any] | None) -> "KwargsType | None":
        if input_schema and len(input_schema.keys()) > 0:
            if "type" not in input_schema:
                raise KeyError(f"Cannot find key 'type' in input schema: { input_schema }")
            if input_schema["type"] != "object":
                raise TypeError(f"Input schema type is not 'object' but: { input_schema['type'] }")
            if "properties" not in input_schema:
                raise KeyError(f"Cannot find key 'properties' in input schema: { input_schema }")
            properties = input_schema["properties"]
            kwargs_format: "KwargsType" = {}
            for kwarg_name, kwarg_schema in properties.items():
                if "type" in kwarg_schema:
                    kwarg_type = kwarg_schema["type"]
                    del kwarg_schema["type"]
                else:
                    kwarg_type = any
                if "title" in kwarg_schema:
                    del kwarg_schema["title"]
                kwarg_desc = None
                if kwarg_schema.keys():
                    kwarg_desc = ";".join([f"{ key }: { value }" for key, value in kwarg_schema.items()])
                kwargs_format.update({kwarg_name: (kwarg_type, kwarg_desc)})
            return kwargs_format if len(kwargs_format.keys()) > 0 else None
        return None
