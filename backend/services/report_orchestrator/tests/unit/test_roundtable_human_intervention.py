import pytest

from app.core.roundtable.agent import Agent
from app.core.roundtable.meeting import Meeting
from app.core.roundtable.message import Message
from app.core.roundtable.message import MessageType


@pytest.mark.asyncio
async def test_inject_human_input_appends_broadcast_message():
    meeting = Meeting(agents=[])

    user_input = "请优先评估稳定币脱锚风险与交易所流动性冲击"
    await meeting.inject_human_input(user_input)

    assert meeting.message_bus.message_history, "message history should not be empty"
    human_message = meeting.message_bus.message_history[-1]
    assert human_message.sender == "Human"
    assert human_message.recipient == "ALL"
    assert human_message.message_type == MessageType.BROADCAST
    assert user_input in human_message.content


@pytest.mark.asyncio
async def test_pause_then_continue_without_input_resumes_without_human_message():
    meeting = Meeting(agents=[])

    paused = await meeting.pause_for_human_intervention()
    assert paused is True
    assert meeting.waiting_for_human is True

    await meeting.inject_human_input("")
    assert meeting.waiting_for_human is True  # cleared when waiter consumes the event
    assert meeting.human_intervention_event is not None
    assert meeting.human_intervention_event.is_set() is True
    assert meeting.last_human_intervention_content == ""
    assert meeting.message_bus.message_history == []


@pytest.mark.asyncio
async def test_inject_human_input_with_anchor_discards_future_history():
    agent = Agent(name="ExpertA", role_prompt="test")
    meeting = Meeting(agents=[agent])

    msg1 = Message(sender="Host", recipient="ALL", content="m1")
    msg2 = Message(sender="ExpertA", recipient="ALL", content="m2")
    msg3 = Message(sender="Host", recipient="ALL", content="m3")
    await meeting.message_bus.send(msg1)
    await meeting.message_bus.send(msg2)
    await meeting.message_bus.send(msg3)
    # Simulate local agent memory that also contains future messages.
    agent.message_history = [msg1, msg2, msg3]

    await meeting.pause_for_human_intervention()
    await meeting.inject_human_input("从这里重新开始", anchor_message_id=msg1.message_id)

    history = meeting.message_bus.message_history
    assert [m.content for m in history] == ["m1", history[-1].content]
    assert history[0].message_id == msg1.message_id
    assert history[-1].sender == "Human"
    assert all(m.content != "m2" for m in history)
    assert all(m.content != "m3" for m in history)
    assert all(m.content != "m2" for m in agent.message_history)
    assert all(m.content != "m3" for m in agent.message_history)
