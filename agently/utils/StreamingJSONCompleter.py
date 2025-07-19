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

class StreamingJSONCompleter:
    """
    StreamingJSONCompleter: A utility for streaming JSON strings that may arrive in fragments.
    It detects incomplete JSON objects/arrays/strings/comments and attempts to intelligently complete them.
    """

    def __init__(self) -> None:
        """Initialize an empty buffer."""
        self._buffer = ""

    def reset(self, data: str = "") -> None:
        """Replace the internal buffer with new data."""
        self._buffer = data

    def append(self, data: str) -> None:
        """Append data to the internal buffer."""
        self._buffer += data

    def complete(self) -> str:
        """
        Attempt to complete a partial JSON string by closing unclosed brackets, strings, or comments.
        Returns a completed JSON string.
        """
        buf = self._buffer
        stack = []
        i = 0
        in_string = False
        escape = False
        comment = None  # None, "//", or "/*"
        string_char = None  # Quote character to track string termination

        while i < len(buf):
            ch = buf[i]
            next_ch = buf[i + 1] if i + 1 < len(buf) else ""

            if comment is None:
                if in_string:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == string_char:
                        in_string = False
                        string_char = None
                elif ch in "\"'":
                    in_string = True
                    string_char = ch
                elif ch == "/" and next_ch == "/":
                    comment = "//"
                    i += 1
                elif ch == "/" and next_ch == "*":
                    comment = "/*"
                    i += 1
                elif ch in "{[":
                    stack.append(ch)
                elif ch in "}]":
                    if not stack:
                        # Ignore unmatched closing bracket
                        i += 1
                        continue
                    opener = stack[-1]
                    if (opener == "{" and ch == "}") or (opener == "[" and ch == "]"):
                        stack.pop()
                        if not stack and not in_string and comment is None:
                            # Complete JSON structure found
                            result = buf[: i + 1]
                            return result
                    else:
                        # Ignore mismatched closing bracket
                        i += 1
                        continue
            else:
                if comment == "//":
                    if ch in "\n\r":
                        comment = None
                elif comment == "/*":
                    if ch == "*" and next_ch == "/":
                        comment = None
                        i += 1

            i += 1

        # Attempt to complete unterminated structures

        # Close unterminated string
        if in_string and string_char is not None:
            buf += string_char
            in_string = False
            string_char = None

        # Close unterminated comment
        if comment == "//":
            # Assume end of line for single-line comment
            buf += "\n"
            comment = None
        elif comment == "/*":
            # Close multi-line comment
            buf += "*/"
            comment = None

        # Close unbalanced brackets
        if stack:
            closing = {"{": "}", "[": "]"}
            completion = "".join(closing[ch] for ch in reversed(stack))
            buf += completion
            stack.clear()

        return buf
