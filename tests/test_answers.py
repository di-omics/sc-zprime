"""Recovering a submitted answer from a transcript, on small hand-built transcripts."""

import json

from sc_zprime import answers, trajectory

GRADER = {"type": "numeric_tolerance", "config": {"ground_truth": {"n": 10}, "tolerances": {"n": {"type": "absolute", "value": 2}}}}
PROMPT = "Return EXACTLY: <EVAL_ANSWER>{\"n\": <int>}</EVAL_ANSWER>"


def chat(tmp_path, steps, last_message=None):
    """A chat-style transcript from (command, output) pairs."""
    messages = [{"role": "user", "content": PROMPT}]
    for i, (command, output) in enumerate(steps):
        messages.append({"role": "assistant", "content": "", "tool_calls": [{"id": f"c{i}", "function": {"arguments": json.dumps({"command": command})}}]})
        messages.append({"role": "tool", "tool_call_id": f"c{i}", "content": json.dumps({"returncode": 0, "output": output})})
    if last_message:
        messages.append({"role": "assistant", "content": last_message})
    path = tmp_path / "trajectory.json"
    path.write_text(json.dumps({"messages": messages}))
    return path


def test_objects_are_found_in_json_and_in_python_form_and_never_evaluated():
    text = "result: {\"n\": 3} then {'m': [1, 2], 'k': 'x}y'} and {not an object} and {}"
    assert answers.objects_in(text) == [{"n": 3}, {"m": [1, 2], "k": "x}y"}]
    assert answers.objects_in("{'n': __import__('os').getcwd()}") == []


def test_fields_a_grader_reads_include_those_of_its_children():
    composite = {"type": "all_of", "config": {"children": [
        GRADER, {"type": "label_set_jaccard", "config": {"answer_field": "labels", "ground_truth_labels": ["a"]}},
        {"type": "multiple_choice", "config": {"correct_answer": "B"}}]}}
    assert answers.graded_fields(composite) == {"n", "labels", "answer"}


def test_the_last_answer_a_step_shows_is_taken(tmp_path):
    path = chat(tmp_path, [("python explore.py", "{'n': 4}"),
                           ("cat > /workspace/eval_answer.json << 'EOF'\n{\"n\": 9}\nEOF", ""),
                           ("cat /workspace/eval_answer.json", "{\"n\": 9}")])
    found = answers.recover(path, GRADER)
    assert found.answer == {"n": 9} and found.source == "printed" and len(found.shown) == 2


def test_a_literal_written_to_the_answer_file_counts_without_being_printed(tmp_path):
    path = chat(tmp_path, [("echo '{\"n\": 12}' > eval_answer.json", "")])
    found = answers.recover(path, GRADER)
    assert (found.answer, found.source) == ({"n": 12}, "written")


def test_the_template_in_the_prompt_is_not_an_answer(tmp_path):
    path = chat(tmp_path, [("echo \"<EVAL_ANSWER>{'n': '<int>'}</EVAL_ANSWER>\"", "{'n': '<int>'}")])
    assert answers.recover(path, GRADER).source == "none"


def test_a_tagged_answer_in_the_last_message_is_the_fallback(tmp_path):
    path = chat(tmp_path, [("python run.py", "wrote the answer file")], "Done. <EVAL_ANSWER>{\"n\": 11}</EVAL_ANSWER>")
    found = answers.recover(path, GRADER)
    assert (found.answer, found.source) == ({"n": 11}, "tagged")


def test_an_answer_that_is_never_shown_as_an_object_is_not_guessed(tmp_path):
    path = chat(tmp_path, [("python run.py", "n_degs: 11\nwrote /workspace/eval_answer.json")], "The count is 11.")
    found = answers.recover(path, GRADER)
    assert found.answer is None and found.source == "none"


def test_a_file_write_tool_call_is_read_in_two_stream_shapes(tmp_path):
    claude = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Write",
               "input": {"file_path": "/workspace/eval_answer.json", "content": "{\"n\": 8}"}}]}},
              {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "File created"}]}}]
    pi = [{"type": "tool_execution_start", "toolCallId": "a", "toolName": "bash", "args": {"command": "ls"}},
          {"type": "tool_execution_end", "toolCallId": "a", "result": {"content": [{"type": "text", "text": "data"}]}},
          {"type": "tool_execution_start", "toolCallId": "b", "toolName": "write", "args": {"path": "eval_answer.json", "content": "{\"n\": 8}"}},
          {"type": "tool_execution_end", "toolCallId": "b", "result": {"content": [{"type": "text", "text": "ok"}]}},
          {"type": "message_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "All done."}]}}]
    for name, doc in (("claude", claude), ("pi", pi)):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(doc))
        found = answers.recover(path, GRADER)
        assert (found.answer, found.source) == ({"n": 8}, "written"), name
    steps = trajectory.steps_from_document(pi)
    assert [s.command for s in steps][0] == "ls" and steps[0].output == "data"
    assert trajectory.assistant_texts(pi) == ["All done."]


def test_numpy_scalars_in_a_printed_dict_are_read_as_numbers():
    assert answers.objects_in("{'n': np.float64(11.5), 'k': np.int64(3)}") == [{"n": 11.5, "k": 3}]


def test_placeholders_are_whole_values_not_prefixes(tmp_path):
    for value in ("<int>", "float", "...", "TBD", "<your answer>"):
        assert not answers._is_answer({"n": value}, {"n"}), value
    assert answers._is_answer({"n": "number 12 of the list"}, {"n"}), "a real string that starts with a type word is kept"


def test_a_draft_in_a_notes_file_is_not_the_answer_but_a_script_that_writes_it_is(tmp_path):
    def tool(path, content, call):
        return [{"type": "tool_execution_start", "toolCallId": call, "toolName": "write", "args": {"path": path, "content": content}},
                {"type": "tool_execution_end", "toolCallId": call, "result": {"content": [{"type": "text", "text": "ok"}]}}]

    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps(tool("/workspace/NOTES.md", "draft for eval_answer.json: {\"n\": 4}", "a")))
    assert answers.recover(notes, GRADER).source == "none"
    script = tmp_path / "script.json"
    script.write_text(json.dumps(tool("/workspace/write_answer.py",
                                      "import json\nanswer = {\"n\": 9}\njson.dump(answer, open('/workspace/eval_answer.json', 'w'))", "a")))
    found = answers.recover(script, GRADER)
    assert (found.answer, found.source) == ({"n": 9}, "written")


def test_an_object_with_every_graded_field_is_preferred_over_a_partial_one(tmp_path):
    two = {"type": "numeric_tolerance", "config": {"ground_truth": {"n": 10, "m": 5}, "tolerances": {}}}
    path = chat(tmp_path, [("python a.py", "{'n': 9, 'm': 5}"), ("python b.py", "{'m': 7}")])
    assert answers.recover(path, two).answer == {"n": 9, "m": 5}


def test_a_later_write_that_shows_nothing_is_flagged(tmp_path):
    path = chat(tmp_path, [("cat /workspace/eval_answer.json", "{\"n\": 9}"),
                           ("python -c \"import json; json.dump(final, open('/workspace/eval_answer.json', 'w'))\"", "done")])
    found = answers.recover(path, GRADER)
    assert found.answer == {"n": 9} and found.written_again_unseen
    calm = chat(tmp_path, [("cat /workspace/eval_answer.json", "{\"n\": 9}"), ("ls /workspace", "eval_answer.json")])
    assert not answers.recover(calm, GRADER).written_again_unseen
