import json5
from agently.utils import StreamingJSONCompleter


def run_case(fragments, expected_keys):
    completer = StreamingJSONCompleter()
    for frag in fragments:
        completer.append(frag)
    completed = completer.complete()
    print("Completed JSON:", completed)
    parsed = json5.loads(completed)
    if isinstance(parsed, dict):
        for key in expected_keys:
            assert key in parsed
    elif isinstance(parsed, list):
        assert isinstance(parsed, list)


# Test a simple complete JSON object with one key-value pair.
def test_complete_simple_object():
    run_case(['{"a": 1}'], ["a"])


# Test an object missing the closing brace to check if completion handles it.
def test_incomplete_object_closing_brace():
    run_case(['{"a": 1'], ["a"])


# Test with only an opening brace to verify behavior on minimal input.
def test_only_opening_brace():
    run_case(['{'], [])


# Test nested object with an unclosed array to check nested structure completion.
def test_nested_structure_unclosed_array():
    run_case(['{"a": {"b": [1, 2'], ["a"])


# Test nested object with a properly closed array inside.
def test_nested_structure_closed_array():
    run_case(['{"a": {"b": [1, 2]}'], ["a"])


# Test unclosed string value to verify string completion handling.
def test_unclosed_string_value():
    run_case(['{"a": "incomplete'], ["a"])


# Test unclosed string with an escape character to check escape handling.
def test_unclosed_string_with_escape():
    run_case([r'{"msg": "hello'], ["msg"])


# Test string containing an escaped quote to verify correct parsing.
def test_escaped_quote_in_string():
    run_case([r'{"a": "abc\\\"def'], ["a"])


# Test string containing an escaped newline character.
def test_escaped_newline_in_string():
    run_case([r'{"a": "line\\n'], ["a"])


# Test JSON with a single-line comment at the end of input.
def test_single_line_comment_eof():
    run_case(['{ "a": 1, // some comment'], ["a"])


# Test JSON with a single-line comment without a newline at the end.
def test_single_line_comment_no_newline():
    run_case(['{ "a": 1 // comment'], ["a"])


# Test JSON with an unclosed multiline comment to check comment handling.
def test_multiline_comment_unclosed():
    run_case(['{ "a": 1, /* comment'], ["a"])


# Test string containing a double slash sequence (like a URL).
def test_string_with_double_slash():
    run_case(['{ "a": "http://example.com'], ["a"])


# Test string containing what looks like a multiline comment inside the string.
def test_string_with_multiline_comment_inside():
    run_case(['{ "a": "some/*text*/inside"'], ["a"])


# Test an unclosed array to check array completion.
def test_unclosed_array():
    run_case(['[1, 2, 3'], [])


# Test multiple fields streamed in separate fragments to verify incremental parsing.
def test_multiple_fields_streamed():
    run_case(['{ "a": "abc"', ', "b": [1, 2]', ', "c": {"d": "e" }'], ["a", "b", "c"])
