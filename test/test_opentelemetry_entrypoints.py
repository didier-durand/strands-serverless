import json
from contextvars import Context
from importlib.metadata import distributions

import importlib_metadata
from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext


def test_entry_points():
    print()
    entry_points: importlib_metadata.EntryPoints =  importlib_metadata.entry_points(group="opentelemetry_context")
    assert len(entry_points) == 1
    for entry_point in entry_points:
        print(str(entry_point))
        assert entry_point.name == "contextvars_context"
        assert entry_point.value == "opentelemetry.context.contextvars_context:ContextVarsRuntimeContext"
        assert entry_point.group == "opentelemetry_context"
        loaded = entry_point.load()
        print(f"loaded: {loaded}")
        assert loaded == ContextVarsRuntimeContext
        context = loaded()
        #assert isinstance(context, ContextVarsRuntimeContext)
        current: Context = context.get_current()
        assert current is not None
        assert len(current) == 0
        # check distributions
        count = 0
        for distribution in  distributions():
            count += 1
            print(distribution.name)
        assert count == 158
        # check entry points
        entry_points: list[dict] = []
        for entry_point in importlib_metadata.entry_points():
            entry_points.append({
                "name": entry_point.name,
                "value": entry_point.value,
                "group": entry_point.group
            })
        print("###")
        print(json.dumps(entry_points,indent=4))
        assert len(entry_points) == 95
