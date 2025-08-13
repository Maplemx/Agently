import pytest
from agently.utils.StreamingJSONParser import StreamingJSONParser, StreamingData


@pytest.mark.asyncio
async def test_streaming_json_parser_basic():
    schema = {
        "response": {
            "user": {
                "profile": {
                    "name": (str,),
                    "age": (int,),
                    "active": (bool,),
                },
                "preferences": {
                    "theme": (str,),
                    "notifications": (bool,),
                },
            },
            "data": {
                "items": [
                    {
                        "id": (int,),
                        "title": (str,),
                        "tags": [(str,)],
                    }
                ],
                "metadata": {
                    "total": (int,),
                    "page": (int,),
                },
            },
        }
    }

    def mock_llm_stream():
        chunks = [
            '{"response": {"user": {"profile": {"name": "J',
            'oh',
            'n", "age": 25, "active": true}, "preferences": {"theme": "dark", "notifications": true}}, "data": {"items": [{"id": 1, "title": "First',
            ' Item", "tags": ["tag1", "tag2"]}], "metadata": {"total": 1, "page": 1}}}}',
        ]
        for chunk in chunks:
            yield chunk

    parser = StreamingJSONParser(schema)
    events = []
    for chunk in mock_llm_stream():
        async for item in parser.parse_chunk(chunk):
            events.append(item)
    async for item in parser.finalize():
        events.append(item)

    # Extract delta and done events
    deltas = [e for e in events if e.event_type == "delta"]
    dones = [e for e in events if e.event_type == "done"]

    assert any("response.user.profile.name" in e.path and e.delta for e in deltas)
    assert any(e.path == "response.user.profile.name" and e.is_complete for e in dones)
    assert any(e.path == "response.data.items[0].tags" and e.value == ["tag1", "tag2"] for e in dones)
    assert events[-1].path == "response"  # Final completion of root


@pytest.mark.asyncio
async def test_streaming_json_parser_edge_cases():
    schema = {
        "profile": {
            "username": (str,),
            "age": (int,),
            "emails": [(str,)],
            "preferences": {
                "notifications": (bool,),
                "languages": [(str,)],
            },
            "optional_field": (str,),  # optional, may be missing
        }
    }

    # Simulate streaming chunks:
    # - username comes in three parts (testing delta aggregation)
    # - age completed in one chunk
    # - emails array built incrementally
    # - preferences.languages array partially missing one delta (simulate missing fragment)
    chunks = [
        '{"profile": {"username": "A',
        'l',
        'ice", "age": 30, "emails": ["alice@example.com"',
        ', "alice.work@example.com"], "preferences": {"notifications": true, "languages": ["English"',
        # missing next chunk for languages array (simulate missing delta)
        ', "Spanish"]}, "optional_field": "optional_value"}}',
    ]

    parser = StreamingJSONParser(schema)
    events = []
    for chunk in chunks:
        async for item in parser.parse_chunk(chunk):
            events.append(item)
    async for item in parser.finalize():
        events.append(item)

    # Collect done events by path
    done_events = [e for e in events if e.event_type == "done"]
    delta_events = [e for e in events if e.event_type == "delta"]

    # Check final values correctness
    # username final value
    username_done = next((e for e in done_events if e.path == "profile.username"), None)
    assert username_done is not None
    assert username_done.value == "Alice"

    # age final value
    age_done = next((e for e in done_events if e.path == "profile.age"), None)
    assert age_done is not None
    assert age_done.value == 30

    # emails final value
    emails_done = next((e for e in done_events if e.path == "profile.emails"), None)
    assert emails_done is not None
    assert emails_done.value == ["alice@example.com", "alice.work@example.com"]

    # preferences.notifications final value
    notifications_done = next((e for e in done_events if e.path == "profile.preferences.notifications"), None)
    assert notifications_done is not None
    assert notifications_done.value is True

    # preferences.languages final value
    languages_done = next((e for e in done_events if e.path == "profile.preferences.languages"), None)
    assert languages_done is not None
    # Because one delta chunk was missing, the final value should still be complete and correct
    assert languages_done.value == ["English", "Spanish"]

    # optional_field final value
    optional_done = next((e for e in done_events if e.path == "profile.optional_field"), None)
    assert optional_done is not None
    assert optional_done.value == "optional_value"

    # Check that username deltas appear as expected (3 parts)
    username_deltas = [e for e in delta_events if e.path == "profile.username"]
    assert len(username_deltas) >= 3
    aggregated_username = "".join(e.delta for e in username_deltas)
    assert aggregated_username == "Alice"

    # age done should appear after age delta(s) if any delta exist
    age_deltas = [e for e in delta_events if e.path == "profile.age"]
    if age_deltas:
        assert events.index(age_deltas[-1]) < events.index(age_done)
    # else: no delta for age is expected and acceptable

    # emails done after all email items deltas
    emails_deltas = [e for e in delta_events if e.path.startswith("profile.emails")]
    assert emails_deltas
    assert events.index(emails_deltas[-1]) < events.index(emails_done)

    # languages done after all language items deltas (including missing delta simulated)
    languages_deltas = [e for e in delta_events if e.path.startswith("profile.preferences.languages")]
    assert languages_deltas
    assert events.index(languages_deltas[-1]) < events.index(languages_done)
