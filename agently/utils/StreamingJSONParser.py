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

import json
import json5
from typing import Any, Dict, AsyncGenerator, List
import copy

from agently.utils import DataLocator, DataPathBuilder, StreamingJSONCompleter
from agently.types.data import StreamingData


class StreamingJSONParser:
    """
    AsyncStreamingJSONParser parses streamed JSON data chunk by chunk asynchronously, maintaining parsing state and emitting
    incremental ("delta") and completion ("done") events for each field as the structure is built up.

    This class is designed to process partial JSON data (e.g., from an LLM or network stream) and
    emit structured events as fields become available or finalized, allowing for responsive UI updates
    or downstream processing.

    Attributes:
        schema (Dict[str, Any]): The schema describing the expected JSON structure.
    """

    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize an AsyncStreamingJSONParser instance.

        Args:
            schema (Dict[str, Any]): The schema dict describing the expected JSON structure.
        """
        self.schema = schema
        self.completer = StreamingJSONCompleter()
        self.previous_data = {}
        self.current_data = {}
        self.field_completion_status = set()  # Tracks completed field paths
        self.string_values = {}  # Tracks current string values for fields
        self.last_complete_structure = {}  # Last complete structure for completion checks

        # Get the expected field parsing order and all possible paths
        self.expected_field_order = DataPathBuilder.extract_parsing_key_orders(schema, style="dot")
        self.all_possible_paths = DataPathBuilder.extract_possible_paths(schema, style="dot")

        self.current_parsing_position = 0  # Current position in parsing order

    async def _get_value_at_path(self, data: dict, path_keys: List[str | int]) -> Any:
        """
        Retrieve the value at the specified path from a nested dictionary/list structure.
        Args:
            data (dict): The data to search within.
            path_keys (List[str | int]): Path as a list of keys and indices.
        Returns:
            Any: The value at the path, or None if not found.
        """
        current = data
        for key in path_keys:
            if isinstance(key, int):
                if isinstance(current, list) and len(current) > key:
                    current = current[key]
                else:
                    return None
            elif isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    async def _set_value_at_path(self, data: dict, path_keys: List[str | int], value: Any):
        """
        Set the value at the specified path in a nested dictionary/list structure.
        Args:
            data (dict): The data to modify.
            path_keys (List[str | int]): Path as a list of keys/indices.
            value (Any): The value to set.
        """
        current = data
        for i, key in enumerate(path_keys[:-1]):
            if isinstance(key, int):
                if not isinstance(current, list):
                    return
                while len(current) <= key:
                    current.append({})
                current = current[key]
            else:
                if not isinstance(current, dict):
                    return
                if key not in current:
                    # Decide whether to create dict or list based on next key
                    next_key = path_keys[i + 1]
                    current[key] = [] if isinstance(next_key, int) else {}
                current = current[key]

        # Set final value at the path
        final_key = path_keys[-1]
        if isinstance(final_key, int):
            if isinstance(current, list):
                while len(current) <= final_key:
                    current.append(None)
                current[final_key] = value
        else:
            if isinstance(current, dict):
                current[final_key] = value

    async def _parse_path_keys(self, path: str) -> List[str | int]:
        """
        Parse a dot-style path string into a list of keys and indices.
        Args:
            path (str): The dot-style path (e.g., 'foo.bar[0].baz').
        Returns:
            List[str|int]: List of keys and indices.
        """
        if not path:
            return []

        keys = []
        parts = path.split('.')

        for part in parts:
            if '[' in part and ']' in part:
                # Handle array index
                base_part = part.split('[')[0]
                if base_part:
                    keys.append(base_part)

                # Extract all array indices
                import re

                indices = re.findall(r'\[(\d+)\]', part)
                for idx in indices:
                    keys.append(int(idx))
            else:
                keys.append(part)

        return keys

    async def _get_current_parsing_paths(self) -> set[str]:
        """
        Get the set of all currently parsed paths in the current_data structure.
        Returns:
            set[str]: Set of dot-style paths currently present in current_data.
        """
        current_paths = set()

        async def collect_paths(data: Any, path_keys: List[str | int] = []):
            path = DataPathBuilder.build_dot_path(path_keys)
            if path:
                current_paths.add(path)

            if isinstance(data, dict):
                for key, value in data.items():
                    await collect_paths(value, path_keys + [key])
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    await collect_paths(item, path_keys + [i])

        await collect_paths(self.current_data)
        return current_paths

    async def _should_mark_field_complete(self, path: str, current_value: Any, previous_value: Any) -> bool:
        """
        Determine whether a field/path should be marked as complete.
        Args:
            path (str): The field path.
            current_value (Any): The current value at this path.
            previous_value (Any): The previous value at this path.
        Returns:
            bool: True if the field should be marked as complete, False otherwise.
        """
        if path in self.field_completion_status:
            return False

        # Get all paths currently present in parsing
        current_parsing_paths = await self._get_current_parsing_paths()

        # Core logic: check the furthest path currently being parsed
        # If this path is before the furthest and value is stable, can mark as complete
        furthest_parsing_path = await self._get_furthest_parsing_path(current_parsing_paths)

        if furthest_parsing_path and await self._is_path_before(path, furthest_parsing_path):
            # This path is before the furthest one and value is stable
            if current_value == previous_value and current_value is not None:
                return True

        # Special case: leaf fields with stable value and newer paths
        if not isinstance(current_value, (dict, list)) and current_value is not None:
            for parsing_path in current_parsing_paths:
                if await self._is_path_before(path, parsing_path):
                    if current_value == previous_value:
                        return True
                    break

        return False

    async def _get_furthest_parsing_path(self, current_parsing_paths: set[str]) -> str | None:
        """
        Get the furthest (most advanced) path currently being parsed, according to expected order.
        Args:
            current_parsing_paths (set[str]): Set of paths currently present in the data.
        Returns:
            Optional[str]: The furthest path, or None if not found.
        """
        if not current_parsing_paths:
            return None

        # Find the last path being parsed according to expected order
        furthest_path = None
        furthest_index = -1

        for path in current_parsing_paths:
            try:
                index = self.expected_field_order.index(path)
                if index > furthest_index:
                    furthest_index = index
                    furthest_path = path
            except ValueError:
                # Path not in expected order (likely dynamic array)
                continue

        return furthest_path

    async def _is_path_before(self, path1: str, path2: str) -> bool:
        """
        Determine if path1 comes before path2 in the expected field order.
        Args:
            path1 (str): First path.
            path2 (str): Second path.
        Returns:
            bool: True if path1 is before path2, else False.
        """
        if not path2:
            return False

        try:
            index1 = self.expected_field_order.index(path1)
            index2 = self.expected_field_order.index(path2)
            return index1 < index2
        except ValueError:
            # special case: array path
            return await self._is_array_path_before(path1, path2)

    async def _is_array_path_before(self, path1: str, path2: str) -> bool:
        """
        Compare two array-type paths for order.
        Args:
            path1 (str): First path.
            path2 (str): Second path.
        Returns:
            bool: True if path1 is considered before path2.
        """
        # Simple string/length-based comparison; can be improved for more complex cases
        return len(path1) < len(path2) or path1 < path2

    async def _compare_and_generate_events(self) -> AsyncGenerator[StreamingData, None]:
        """
        Compare the current and previous data, and yield StreamingData events for
        incremental ("delta") updates and completions ("done").
        Yields:
            StreamingData: The event for each updated or completed field.
        """

        async def traverse_and_compare(current_data: Any, previous_data: Any, path_keys: List[str | int] = []):
            path = DataPathBuilder.build_dot_path(path_keys)

            # Handle incremental updates for string fields
            if isinstance(current_data, str):
                previous_str = previous_data if isinstance(previous_data, str) else ""

                # Emit delta if changed and computable
                if current_data != previous_str:
                    # Prefer suffix delta if previous_str is a prefix, else full current_data as delta
                    if previous_str and current_data.startswith(previous_str):
                        delta = current_data[len(previous_str) :]
                    else:
                        delta = current_data if previous_str == "" else current_data
                    if delta:
                        yield StreamingData(
                            path=path,
                            value=current_data,
                            delta=delta,
                            is_complete=False,
                            event_type="delta",
                            full_data=self.current_data,  # Pass the full current_data here
                        )
                        self.string_values[path] = current_data

                # Check if string field should be immediately marked complete
                if path and await self._should_mark_field_complete(path, current_data, previous_data):
                    self.field_completion_status.add(path)
                    yield StreamingData(
                        path=path,
                        value=current_data,
                        delta=None,
                        is_complete=True,
                        event_type="done",
                        full_data=self.current_data,  # Pass the full current_data here
                    )

            # Handle primitive (non-string) types
            elif not isinstance(current_data, (dict, list)) and current_data is not None:
                # Emit delta if value changed and previous_data exists
                if current_data != previous_data:
                    yield StreamingData(
                        path=path,
                        value=current_data,
                        delta=current_data,
                        is_complete=False,
                        event_type="delta",
                        full_data=self.current_data,  # Pass the full current_data here
                    )
                # Check if primitive field should be immediately marked complete
                if path and await self._should_mark_field_complete(path, current_data, previous_data):
                    self.field_completion_status.add(path)
                    yield StreamingData(
                        path=path,
                        value=current_data,
                        delta=None,
                        is_complete=True,
                        event_type="done",
                        full_data=self.current_data,  # Pass the full current_data here
                    )

            # Handle dictionary/object types
            elif isinstance(current_data, dict):
                previous_dict = previous_data if isinstance(previous_data, dict) else {}

                # Recursively process subfields
                for key, value in current_data.items():
                    child_path_keys = path_keys + [key]
                    previous_value = previous_dict.get(key)
                    async for event in traverse_and_compare(value, previous_value, child_path_keys):
                        yield event

                # Check if object should be marked complete
                if path and await self._should_mark_field_complete(path, current_data, previous_data):
                    self.field_completion_status.add(path)
                    yield StreamingData(
                        path=path,
                        value=current_data,
                        delta=None,
                        is_complete=True,
                        event_type="done",
                        full_data=self.current_data,  # Pass the full current_data here
                    )

            # Handle list/array types
            elif isinstance(current_data, list):
                previous_list = previous_data if isinstance(previous_data, list) else []

                # Recursively process elements
                for i, value in enumerate(current_data):
                    child_path_keys = path_keys + [i]
                    previous_value = previous_list[i] if i < len(previous_list) else None
                    async for event in traverse_and_compare(value, previous_value, child_path_keys):
                        yield event

                # Check if array should be marked complete
                if path and await self._should_mark_field_complete(path, current_data, previous_data):
                    self.field_completion_status.add(path)
                    yield StreamingData(
                        path=path,
                        value=current_data,
                        delta=None,
                        is_complete=True,
                        event_type="done",
                        full_data=self.current_data,  # Pass the full current_data here
                    )

        async for event in traverse_and_compare(self.current_data, self.previous_data):
            yield event

    async def _extract_array_index(self, path: str) -> int:
        """
        Extract the first array index from a dot-style path string.
        Args:
            path (str): The path string (e.g., 'foo.bar[2].baz').
        Returns:
            int: The first index found, or 0 if none.
        """
        import re

        match = re.search(r'\[(\d+)\]', path)
        return int(match.group(1)) if match else 0

    async def finalize(self) -> AsyncGenerator[StreamingData, None]:
        """
        Mark all remaining fields as complete and yield "done" events for every incomplete path.
        This should be called at the end of the stream to ensure all fields are finalized.
        Yields:
            StreamingData: The completion event for each remaining field.
        """

        async def mark_all_complete(data: Any, path_keys: List[str | int] = []):
            path = DataPathBuilder.build_dot_path(path_keys)

            if isinstance(data, dict):
                # Recursively mark all subfields
                for key, value in data.items():
                    child_path_keys = path_keys + [key]
                    async for event in mark_all_complete(value, child_path_keys):
                        yield event

                # Mark this object field as complete if not already done
                if path and path not in self.field_completion_status:
                    self.field_completion_status.add(path)
                    yield StreamingData(
                        path=path,
                        value=data,
                        delta=None,
                        is_complete=True,
                        event_type="done",
                        full_data=self.current_data,  # Pass the full current_data here
                    )

            elif isinstance(data, list):
                # Recursively mark all elements
                for i, item in enumerate(data):
                    child_path_keys = path_keys + [i]
                    async for event in mark_all_complete(item, child_path_keys):
                        yield event

                # Mark this array field as complete if not already done
                if path and path not in self.field_completion_status:
                    self.field_completion_status.add(path)
                    yield StreamingData(
                        path=path,
                        value=data,
                        delta=None,
                        is_complete=True,
                        event_type="done",
                        full_data=self.current_data,  # Pass the full current_data here
                    )

            else:
                # Mark primitive field as complete if not already done
                if path and path not in self.field_completion_status:
                    self.field_completion_status.add(path)
                    yield StreamingData(
                        path=path,
                        value=data,
                        delta=None,
                        is_complete=True,
                        event_type="done",
                        full_data=self.current_data,  # Pass the full current_data here
                    )

        async for event in mark_all_complete(self.current_data):
            yield event

    async def parse_chunk(self, chunk: str) -> AsyncGenerator[StreamingData, None]:
        """
        Parse a single chunk of streamed JSON data and yield StreamingData events for any
        detected incremental or completion updates.
        Args:
            chunk (str): A chunk of JSON text (possibly incomplete).
        Yields:
            StreamingData: The event for each detected update or completion.
        """
        self.completer.append(chunk)
        completed_json = self.completer.complete()
        located_json = DataLocator.locate_output_json(
            completed_json,
            self.schema,
        )
        if located_json:
            try:
                parsed_data = json5.loads(located_json)
                self.previous_data = copy.deepcopy(self.current_data)
                self.current_data = parsed_data

                async for event in self._compare_and_generate_events():
                    yield event
            except (json.JSONDecodeError, ValueError):
                # JSON parsing failed; wait for more data.
                pass

    async def parse_stream(self, chunk_stream: AsyncGenerator[str, None]) -> AsyncGenerator[StreamingData, None]:
        """
        Parse a stream of JSON chunks and yield StreamingData events.
        Args:
            chunk_stream (AsyncGenerator[str, None]): An async generator that yields JSON chunks.
        Yields:
            StreamingData: The event for each detected update or completion.
        """
        async for chunk in chunk_stream:
            async for event in self.parse_chunk(chunk):
                yield event

        # Finalize at the end of the stream
        async for event in self.finalize():
            yield event
