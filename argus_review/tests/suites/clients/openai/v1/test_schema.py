from argus_review.clients.openai.v1.schema import (
    OpenAIUsageSchema,
    OpenAIMessageSchema,
    OpenAIChoiceSchema,
    OpenAIChatRequestSchema,
    OpenAIChatResponseSchema,
    OpenAIToolCallSchema,
    OpenAIToolFunctionSchema,
    OpenAIChatToolSchema,
    OpenAIChatToolFunctionDefSchema,
)


# ---------- OpenAIChatResponseSchema ----------

def test_first_text_returns_text():
    resp = OpenAIChatResponseSchema(
        usage=OpenAIUsageSchema(total_tokens=5, prompt_tokens=2, completion_tokens=3),
        choices=[
            OpenAIChoiceSchema(
                message=OpenAIMessageSchema(role="assistant", content=" hello world ")
            )
        ],
    )
    assert resp.first_text == "hello world"


def test_first_text_empty_if_no_choices():
    resp = OpenAIChatResponseSchema(
        usage=OpenAIUsageSchema(total_tokens=1, prompt_tokens=1, completion_tokens=0),
        choices=[],
    )
    assert resp.first_text == ""


def test_first_text_strips_and_handles_empty_content():
    resp = OpenAIChatResponseSchema(
        usage=OpenAIUsageSchema(total_tokens=1, prompt_tokens=1, completion_tokens=0),
        choices=[OpenAIChoiceSchema(message=OpenAIMessageSchema(role="assistant", content="   "))],
    )
    assert resp.first_text == ""


def test_first_tool_call_returns_first_tool_call():
    tool_call = OpenAIToolCallSchema(
        id="call_1",
        type="function",
        function=OpenAIToolFunctionSchema(
            name="read_shell_command",
            arguments='{"command":"git diff --name-only"}',
        ),
    )
    resp = OpenAIChatResponseSchema(
        usage=OpenAIUsageSchema(total_tokens=5, prompt_tokens=2, completion_tokens=3),
        choices=[
            OpenAIChoiceSchema(
                message=OpenAIMessageSchema(
                    role="assistant",
                    content=None,
                    tool_calls=[tool_call],
                )
            )
        ],
    )

    assert resp.first_tool_call == tool_call


def test_first_tool_call_none_when_absent():
    resp = OpenAIChatResponseSchema(
        usage=OpenAIUsageSchema(total_tokens=1, prompt_tokens=1, completion_tokens=0),
        choices=[OpenAIChoiceSchema(message=OpenAIMessageSchema(role="assistant", content="ok"))],
    )

    assert resp.first_tool_call is None


# ---------- OpenAIChatRequestSchema ----------

def test_chat_request_schema_builds_ok():
    msg = OpenAIMessageSchema(role="user", content="hello")
    req = OpenAIChatRequestSchema(
        model="gpt-4o-mini",
        messages=[msg],
        max_tokens=100,
        temperature=0.3,
    )
    assert req.model == "gpt-4o-mini"
    assert req.messages[0].content == "hello"
    assert req.max_tokens == 100
    assert req.temperature == 0.3


def test_chat_request_schema_stream_defaults_to_false():
    msg = OpenAIMessageSchema(role="user", content="hi")
    req = OpenAIChatRequestSchema(model="gpt-4o-mini", messages=[msg])
    assert req.stream is False


def test_chat_request_schema_stream_included_in_payload():
    msg = OpenAIMessageSchema(role="user", content="hi")
    req = OpenAIChatRequestSchema(model="gpt-4o-mini", messages=[msg])
    payload = req.model_dump(exclude_none=True)
    assert payload["stream"] is False


def test_chat_request_schema_includes_tools_when_provided():
    msg = OpenAIMessageSchema(role="user", content="hi")
    tool = OpenAIChatToolSchema(
        type="function",
        function=OpenAIChatToolFunctionDefSchema(
            name="read_shell_command",
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        ),
    )
    req = OpenAIChatRequestSchema(model="gpt-4o-mini", messages=[msg], tools=[tool], tool_choice="auto")
    payload = req.model_dump(exclude_none=True)

    assert payload["tool_choice"] == "auto"
    assert payload["tools"][0]["function"]["name"] == "read_shell_command"
