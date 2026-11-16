import asyncio
from types import SimpleNamespace

import pytest
from agent_server import corridor_context as context

REF = "corridor-0a1b2c3d"
LINE = {"type": "LineString", "coordinates": [[-100, 40], [-99.9, 40.1]]}
AREA = {"type": "Polygon", "coordinates": [[[-100, 40], [-99, 40], [-99, 41], [-100, 40]]]}


def _raw(**overrides):
    return {
        "corridor_ref": REF,
        "centerline": LINE,
        "buffer_distance": 100,
        "buffer_units": "feet",
        **overrides,
    }


def test_parse_valid_corridor_with_alternatives_and_staging():
    value = context.parse_active_corridor(_raw(alternatives=[LINE], indirect_geometry=AREA))
    assert value.alternatives == (LINE,)
    assert value.indirect_geometry == AREA


@pytest.mark.parametrize(
    "raw",
    [
        None,
        _raw(corridor_ref="bad"),
        _raw(centerline={"type": "LineString", "coordinates": [[0, 0]]}),
        _raw(centerline={"type": "Point", "coordinates": [0, 0]}),
        _raw(buffer_distance=0),
        _raw(buffer_distance=float("inf")),
        _raw(buffer_distance=True),
        _raw(buffer_units="yards"),
        _raw(alternatives=[LINE] * (context.MAX_ALTERNATIVES + 1)),
        _raw(indirect_geometry={"type": "Point", "coordinates": [0, 0]}),
    ],
)
def test_invalid_corridor_is_rejected(raw):
    with pytest.raises(context.InvalidCorridor):
        context.parse_active_corridor(raw)


def test_staging_vertex_limit_applies(monkeypatch):
    monkeypatch.setenv("GEO_MAX_VERTICES", "3")
    with pytest.raises(context.InvalidCorridor):
        context.parse_active_corridor(_raw(indirect_geometry=AREA))


def test_reader_ignores_invalid_and_handles_absent_context():
    assert context.read_active_corridor(SimpleNamespace(custom_inputs=None)) is None
    assert (
        context.read_active_corridor(
            SimpleNamespace(custom_inputs={"active_corridor": _raw(corridor_ref="bad")})
        )
        is None
    )
    assert context.read_active_corridor(SimpleNamespace(custom_inputs={"active_corridor": _raw()}))


def test_instruction_note_uses_reference_without_coordinates():
    note = context.instruction_note(context.parse_active_corridor(_raw()))
    assert REF in note and "100 feet on each side" in note
    assert "coordinates" not in note.replace("Do not write coordinates", "").lower()
    assert "-100" not in note


def test_substitution_is_tool_specific_and_deep_copied():
    corridor = context.parse_active_corridor(_raw(alternatives=[LINE], indirect_geometry=AREA))
    arguments = {"centerline": REF, "buffer_distance": 1, "custom": {"x": 1}}
    unrelated = context.substitute_arguments("other_tool", arguments, corridor)
    assert unrelated == arguments
    result = context.substitute_arguments(context.CORRIDOR_TOOL, arguments, corridor)
    assert result["centerline"] == LINE
    assert result["buffer_distance"] == 100
    assert result["buffer_units"] == "feet"
    assert result["alternatives"] == [LINE]
    assert result["indirect_geometry"] == AREA
    result["centerline"]["coordinates"].clear()
    assert corridor.centerline == LINE
    assert arguments["centerline"] == REF


def test_nonmatching_reference_and_missing_staging_remain_unmodified():
    corridor = context.parse_active_corridor(_raw())
    arguments = {"centerline": "corridor-ffffffff", "x": [1]}
    assert context.substitute_arguments(context.CORRIDOR_TOOL, arguments, corridor) == arguments


def test_bound_server_only_substitutes_corridor_call():
    class Server:
        def __init__(self):
            self.calls = []

        async def call_tool(self, name, arguments=None, **kwargs):
            self.calls.append((name, arguments, kwargs))

    server = context.bind_active_corridor(Server(), context.parse_active_corridor(_raw()))
    asyncio.run(server.call_tool(context.CORRIDOR_TOOL, {"centerline": REF}, meta={"x": 1}))
    asyncio.run(server.call_tool("other_tool", {"centerline": REF}))
    assert server.calls[0][1]["centerline"] == LINE
    assert server.calls[0][2] == {"meta": {"x": 1}}
    assert server.calls[1][1] == {"centerline": REF}
