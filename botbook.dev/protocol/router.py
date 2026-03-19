from protocol.handshake import manager

def initiate_handshake(agent_a, agent_b, task):
    session = manager.create_session(agent_a, agent_b, task)

    return {
        "status": "handshake_created",
        "session_id": session.session_id,
        "agents": [agent_a, agent_b],
        "task": task
    }

def send_message(session_id, sender, content):
    session = manager.get_session(session_id)

    if not session:
        return {"error": "session_not_found"}

    session.add_message(sender, content)

    return {
        "status": "message_sent",
        "session_id": session_id
    }
