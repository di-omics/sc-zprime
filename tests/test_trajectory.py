import json

from sc_zprime import trajectory as tj


def test_chat_style_transcript():
    doc = {"messages": [
        {"role": "system", "content": "s"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "function": {"arguments": json.dumps({"command": "echo 5"})}}]},
        {"role": "tool", "tool_call_id": "c1", "content": json.dumps({"returncode": 0, "output": "5\n"})},
    ]}
    steps = tj.steps_from_document(doc)
    assert [(s.command, s.output.strip()) for s in steps] == [("echo 5", "5")]


def test_responses_style_transcript():
    doc = {"messages": [
        {"output": [{"type": "reasoning"}, {"type": "function_call", "call_id": "k", "arguments": json.dumps({"command": "ls"})}]},
        {"type": "function_call_output", "call_id": "k", "output": json.dumps({"returncode": 0, "output": "data"})},
    ]}
    steps = tj.steps_from_document(doc)
    assert steps[0].command == "ls" and steps[0].output == "data"


def test_claude_code_stream():
    doc = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t", "input": {"command": "pwd"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "content": [{"type": "text", "text": "/workspace"}]}]}},
    ]
    steps = tj.steps_from_document(doc)
    assert steps[0].command == "pwd" and steps[0].output == "/workspace"


def test_codex_stream_unwraps_the_shell():
    doc = [{"type": "item.completed", "item": {"type": "command_execution",
            "command": "/bin/bash -lc \"python -c 'print(1)'\"", "aggregated_output": "1\n"}}]
    steps = tj.steps_from_document(doc)
    assert steps[0].command == "python -c 'print(1)'" and steps[0].output == "1\n"


def test_unwrap_single_quoted_wrapper_restores_inner_quotes():
    wrapped = "bash -lc 'f(flavor='\"'\"'seurat_v3'\"'\"')'"
    assert tj.unwrap_shell(wrapped) == "f(flavor='seurat_v3')"


def test_integer_pattern_is_a_standalone_token():
    pat = tj.number_pattern(4242)
    assert pat.search("Number of DEGs: 4242")
    assert pat.search("n = 4,242 genes")
    assert pat.search("4242.0")
    assert not pat.search("24242") and not pat.search("42420") and not pat.search("4242.7")


def test_decimal_pattern_allows_more_printed_digits():
    pat = tj.number_pattern(0.612)
    assert pat.search("corr=0.61234")
    assert not pat.search("10.612") and not pat.search("0.613")


def test_first_step_printing_respects_the_filter():
    steps = [tj.Step(0, "cat notes", "777"), tj.Step(1, "python de.py", "n 777")]
    import re
    assert tj.first_step_printing(steps, 777).index == 0
    assert tj.first_step_printing(steps, 777, re.compile("python")).index == 1
    assert tj.first_step_printing(steps, 999) is None
