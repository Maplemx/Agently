import json5
import pytest
from typing import Any, cast
from agently.utils import StreamingJSONCompleter


def run_case(fragments, expected_keys=None, should_be_valid_json=True, description=""):
    """Generic test runner for JSON completion."""
    completer = StreamingJSONCompleter()
    for frag in fragments:
        completer.append(frag)
    completed = completer.complete()
    print(f"Test: {description}")
    print(f"Input fragments: {fragments}")
    print(f"Completed JSON: {completed}")

    parsed = None
    if should_be_valid_json:
        try:
            parsed = json5.loads(completed)
            if expected_keys and isinstance(parsed, dict):
                for key in expected_keys:
                    assert key in parsed, f"Expected key '{key}' not found in {parsed}"
            elif expected_keys and isinstance(parsed, list):
                assert isinstance(parsed, list), f"Expected list but got {type(parsed)}"
        except Exception as e:
            pytest.fail(f"Invalid JSON generated: {completed}, Error: {e}")

    return completed, parsed if should_be_valid_json else None


class TestStreamingJSONCompleterBasic:
    """Basic functionality tests"""

    def test_complete_simple_object(self):
        """Test a complete simple JSON object"""
        run_case(['{"a": 1}'], ["a"], description="Test a complete simple JSON object")

    def test_incomplete_object_closing_brace(self):
        """Test object missing closing brace"""
        run_case(['{"a": 1'], ["a"], description="Test object missing closing brace")

    def test_only_opening_brace(self):
        """Test object with only opening brace"""
        run_case(['{'], [], description="Test object with only opening brace")

    def test_empty_object(self):
        """Test empty object"""
        run_case(['{}'], [], description="Test empty object")

    def test_empty_array(self):
        """Test empty array"""
        run_case(['[]'], [], description="Test empty array")


class TestStreamingJSONCompleterNested:
    """Nested structure tests"""

    def test_nested_structure_unclosed_array(self):
        """Test unclosed array in nested structure"""
        run_case(['{"a": {"b": [1, 2'], ["a"], description="Test unclosed array in nested structure")

    def test_nested_structure_closed_array(self):
        """Test closed array in nested structure"""
        run_case(['{"a": {"b": [1, 2]}'], ["a"], description="Test closed array in nested structure")

    def test_deeply_nested_objects(self):
        """Test deeply nested objects"""
        run_case(['{"a": {"b": {"c": {"d": "value"'], ["a"], description="Test deeply nested objects")

    def test_deeply_nested_arrays(self):
        """Test deeply nested arrays"""
        run_case(['[[[["inner"'], [], description="Test deeply nested arrays")

    def test_mixed_nested_structures(self):
        """Test mixed nested structures"""
        run_case(['{"arr": [{"nested": [1, 2'], ["arr"], description="Test mixed nested structures")

    def test_multiple_nested_levels(self):
        """Test multiple levels of nesting"""
        run_case(
            ['{"level1": {"level2": {"level3": {"level4": "deep"'],
            ["level1"],
            description="Test multiple levels of nesting",
        )


class TestStreamingJSONCompleterDataTypes:
    """Data type tests"""

    def test_string_values(self):
        """Test string values"""
        run_case(['{"str": "hello world"'], ["str"], description="Test string values")

    def test_number_values(self):
        """Test numeric values"""
        run_case(['{"int": 42, "float": 3.14, "exp": 1e5'], ["int", "float", "exp"], description="Test numeric values")

    def test_boolean_values(self):
        """Test boolean values"""
        run_case(
            ['{"true_val": true, "false_val": false'], ["true_val", "false_val"], description="Test boolean values"
        )

    def test_null_values(self):
        """Test null values"""
        run_case(['{"null_val": null'], ["null_val"], description="Test null values")

    def test_mixed_data_types(self):
        """Test mixed data types"""
        run_case(
            ['{"str": "text", "num": 123, "bool": true, "null": null, "arr": [1, "a"], "obj": {"nested": true'],
            ["str", "num", "bool", "null", "arr", "obj"],
            description="Test mixed data types",
        )


class TestStreamingJSONCompleterStrings:
    """String handling tests"""

    def test_unclosed_string_value(self):
        """Test unclosed string value"""
        run_case(['{"a": "incomplete'], ["a"], description="Test unclosed string value")

    def test_unclosed_string_with_escape(self):
        """Test unclosed string with escape character"""
        run_case([r'{"msg": "hello'], ["msg"], description="Test unclosed string with escape character")

    def test_escaped_quote_in_string(self):
        """Test escaped quote in string"""
        run_case([r'{"a": "abc\\\"def'], ["a"], description="Test escaped quote in string")

    def test_escaped_newline_in_string(self):
        """Test escaped newline in string"""
        run_case([r'{"a": "line\\n'], ["a"], description="Test escaped newline in string")

    def test_escaped_backslash_in_string(self):
        """Test escaped backslash in string"""
        run_case([r'{"path": "C:\\\\Users\\\\'], ["path"], description="Test escaped backslash in string")

    def test_escaped_tab_in_string(self):
        """Test escaped tab in string"""
        run_case([r'{"tab": "hello\\t'], ["tab"], description="Test escaped tab in string")

    def test_unicode_in_string(self):
        """Test Unicode characters in string"""
        run_case(['{"unicode": "\\u4e2d\\u6587'], ["unicode"], description="Test Unicode characters in string")

    def test_single_quote_string(self):
        """Test single-quoted string"""
        run_case(["{'single': 'value'"], ["single"], description="Test single-quoted string")

    def test_string_with_double_slash(self):
        """Test double slashes in string (e.g., URLs)"""
        run_case(['{ "a": "http://example.com'], ["a"], description="Test double slashes in string (e.g., URLs)")

    def test_string_with_multiline_comment_inside(self):
        """Test multiline comment markers inside string"""
        run_case(['{ "a": "some/*text*/inside"'], ["a"], description="Test multiline comment markers inside string")

    def test_empty_string(self):
        """Test empty string"""
        run_case(['{"empty": ""'], ["empty"], description="Test empty string")

    def test_string_with_json_content(self):
        """Test string containing JSON content"""
        run_case(
            ['{"json_str": "{\\"nested\\": \\"value\\"'],
            ["json_str"],
            description="Test string containing JSON content",
        )


class TestStreamingJSONCompleterComments:
    """Comment handling tests"""

    def test_single_line_comment_eof(self):
        """Test single-line comment at end of input"""
        run_case(['{ "a": 1, // some comment'], ["a"], description="Test single-line comment at end of input")

    def test_single_line_comment_no_newline(self):
        """Test single-line comment without newline"""
        run_case(['{ "a": 1 // comment'], ["a"], description="Test single-line comment without newline")

    def test_multiline_comment_unclosed(self):
        """Test unclosed multiline comment"""
        run_case(['{ "a": 1, /* comment'], ["a"], description="Test unclosed multiline comment")

    def test_multiline_comment_closed(self):
        """Test properly closed multiline comment"""
        run_case(['{ "a": 1, /* comment */ "b": 2'], ["a", "b"], description="Test properly closed multiline comment")

    def test_nested_comments(self):
        """Test nested comments"""
        run_case(['{ "a": 1 // comment /* nested'], ["a"], description="Test nested comments")

    def test_comment_between_fields(self):
        """Test comment between object fields"""
        run_case(['{ "a": 1, /* between */ "b": 2'], ["a", "b"], description="Test comment between object fields")

    def test_comment_in_array(self):
        """Test comment inside array"""
        run_case(['[1, /* comment */ 2'], [], description="Test comment inside array")

    def test_multiple_single_line_comments(self):
        """Test multiple single-line comments"""
        run_case(
            ['{ "a": 1, // first\n "b": 2 // second'], ["a", "b"], description="Test multiple single-line comments"
        )


class TestStreamingJSONCompleterArrays:
    """Array handling tests"""

    def test_unclosed_array(self):
        """Test unclosed array"""
        run_case(['[1, 2, 3'], [], description="Test unclosed array")

    def test_array_with_objects(self):
        """Test array containing objects"""
        run_case(['[{"a": 1}, {"b": 2'], [], description="Test array containing objects")

    def test_array_with_mixed_types(self):
        """Test array with mixed data types"""
        run_case(['[1, "string", true, null, {"obj": true'], [], description="Test array with mixed data types")

    def test_nested_arrays(self):
        """Test nested arrays"""
        run_case(['[[1, 2], [3, 4'], [], description="Test nested arrays")

    def test_array_with_trailing_comma(self):
        """Test array with trailing comma"""
        run_case(['[1, 2, 3,'], [], description="Test array with trailing comma")


class TestStreamingJSONCompleterStreaming:
    """Streaming data tests"""

    def test_multiple_fields_streamed(self):
        """Test fragmented transmission of multiple fields"""
        run_case(
            ['{ "a": "abc"', ', "b": [1, 2]', ', "c": {"d": "e" }'],
            ["a", "b", "c"],
            description="Test fragmented transmission of multiple fields",
        )

    def test_single_character_streaming(self):
        """Test streaming one character at a time"""
        fragments = list('{"key": "value"}')
        run_case(fragments, ["key"], description="Test streaming one character at a time")

    def test_irregular_fragment_sizes(self):
        """Test irregular fragment sizes"""
        run_case(
            ['{', '"a":', ' "val', 'ue",', ' "b": [1,', ' 2]'], ["a", "b"], description="Test irregular fragment sizes"
        )

    def test_streaming_with_comments(self):
        """Test streaming with comments"""
        run_case(['{ "a": 1, //', ' comment\n "b":', ' 2'], ["a", "b"], description="Test streaming with comments")

    def test_streaming_nested_structure(self):
        """Test streaming with nested structures"""
        run_case(
            ['{ "data": {', ' "users": [', '   {"id": 1,', '    "name": "Alice"', '   },', '   {"id": 2'],
            ["data"],
            description="Test streaming with nested structures",
        )


class TestStreamingJSONCompleterEdgeCases:
    """Edge case tests"""

    def test_empty_input(self):
        """Test empty input"""
        completer = StreamingJSONCompleter()
        result = completer.complete()
        assert result == "", "Empty input should return an empty string"

    def test_whitespace_only(self):
        """Test input with only whitespace"""
        run_case(['   \n\t  '], [], should_be_valid_json=False, description="Test input with only whitespace")

    def test_only_comments(self):
        """Test input containing only comments"""
        run_case(
            ['// just a comment'], [], should_be_valid_json=False, description="Test input containing only comments"
        )
        run_case(
            ['/* only multiline comment */'],
            [],
            should_be_valid_json=False,
            description="Test input containing only comments",
        )

    def test_malformed_json_recovery(self):
        """Test recovery from malformed JSON"""
        # Mismatched brackets - tool will generate syntactically invalid JSON, this is expected
        completed, _ = run_case(['{"a": [}'], [], should_be_valid_json=False, description="Mismatched brackets")
        # Verify tool attempted to fix, even if result is not valid JSON
        assert '{"a": [}]}' == completed

        # Trailing comma - tool can handle this case
        run_case(['{"a": 1,}'], ["a"], description="Trailing comma")

    def test_large_nesting_level(self):
        """Test deeply nested structure"""
        deep_json = '{"level": ' * 30 + '"deep"' + '}' * 28
        run_case([deep_json], ["level"], description="30 levels")
        with pytest.raises(RecursionError, match="recursion"):
            # too many levels will cause maximum recursion
            # this case is acceptable
            deep_json = '{"level": ' * 50 + '"deep"' + '}' * 49
            completer = StreamingJSONCompleter()
            completer.append(deep_json)
            completed = completer.complete()
            print(completed)  # completed should be correct
            json5.loads(completed)  # but json5 can not load

    def test_very_long_string(self):
        """Test very long string"""
        long_string = '{"long": "' + 'x' * 1000
        run_case([long_string], ["long"], description="Test very long string")

    def test_multiple_root_objects(self):
        """Test multiple root JSON objects"""
        completed, _ = run_case(
            ['{"a": 1} {"b": 2}'], ["a"], should_be_valid_json=True, description="Test multiple root JSON objects"
        )
        # Should complete only the first object
        assert '{"a": 1}' in completed


class TestStreamingJSONCompleterReset:
    """Reset method tests"""

    def test_reset_functionality(self):
        """Test functionality of reset method"""
        completer = StreamingJSONCompleter()
        completer.append('{"old": "data"')

        # Reset and add new data
        completer.reset('{"new": "data"')
        result = completer.complete()

        parsed = cast(dict[str, Any], json5.loads(result))
        assert "new" in parsed
        assert "old" not in parsed

    def test_reset_with_empty_string(self):
        """Test reset with empty string"""
        completer = StreamingJSONCompleter()
        completer.append('{"old": "data"}')
        completer.reset('')

        result = completer.complete()
        assert result == ""

    def test_reset_after_append(self):
        """Test reset after appending"""
        completer = StreamingJSONCompleter()
        completer.append('{"first": ')
        completer.append('"value"}')

        # Reset and add new incomplete data
        completer.reset('{"second": "val')
        result = completer.complete()

        parsed = cast(dict[str, Any], json5.loads(result))
        assert "second" in parsed
        assert "first" not in parsed


class TestStreamingJSONCompleterSpecialCharacters:
    """Special character tests"""

    def test_special_characters_in_strings(self):
        """Test special characters in strings"""
        run_case(['{"special": "\\n\\r\\t\\b\\f'], ["special"], description="Test special characters in strings")

    def test_unicode_escape_sequences(self):
        """Test Unicode escape sequences"""
        run_case(['{"unicode": "\\u0041\\u0042'], ["unicode"], description="Test Unicode escape sequences")

    def test_control_characters(self):
        """Test control characters"""
        run_case(['{"ctrl": "\\u0000\\u001f'], ["ctrl"], description="Test control characters")

    def test_emoji_in_strings(self):
        """Test emojis in strings"""
        run_case(['{"emoji": "😀🎉'], ["emoji"], description="Test emojis in strings")


class TestStreamingJSONCompleterPerformance:
    """Performance related tests"""

    def test_large_array(self):
        """Test large array"""
        large_array = '{"data": [' + ', '.join(str(i) for i in range(1000))
        run_case([large_array], ["data"], description="Test large array")

    def test_many_fields(self):
        """Test object with many fields"""
        many_fields = '{' + ', '.join(f'"field{i}": {i}' for i in range(100))
        expected_keys = [f"field{i}" for i in range(100)]
        run_case([many_fields], expected_keys, description="Test object with many fields")


if __name__ == "__main__":
    # Run all tests
    import sys

    test_classes = [
        TestStreamingJSONCompleterBasic,
        TestStreamingJSONCompleterNested,
        TestStreamingJSONCompleterDataTypes,
        TestStreamingJSONCompleterStrings,
        TestStreamingJSONCompleterComments,
        TestStreamingJSONCompleterArrays,
        TestStreamingJSONCompleterStreaming,
        TestStreamingJSONCompleterEdgeCases,
        TestStreamingJSONCompleterReset,
        TestStreamingJSONCompleterSpecialCharacters,
        TestStreamingJSONCompleterPerformance,
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running test class: {test_class.__name__}")
        print(f"{'='*60}")

        instance = test_class()
        test_methods = [method for method in dir(instance) if method.startswith('test_')]

        for test_method in test_methods:
            total_tests += 1
            try:
                print(f"\nRunning test: {test_method}")
                getattr(instance, test_method)()
                print(f"✅ {test_method} passed")
                passed_tests += 1
            except Exception as e:
                print(f"❌ {test_method} failed: {e}")

    print(f"\n{'='*60}")
    print(f"Test summary: {passed_tests}/{total_tests} passed")
    print(f"{'='*60}")

    if passed_tests != total_tests:
        sys.exit(1)
