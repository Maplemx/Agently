from typing import TypeAlias

ArgumentDesc: TypeAlias = type | str | tuple[str | type, str]
KwargsType: TypeAlias = dict[str, ArgumentDesc]
ReturnType: TypeAlias = ArgumentDesc | dict[str, "ReturnType"] | list["ReturnType"]
