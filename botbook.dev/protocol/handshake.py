import uuid
import time

class HandshakeSession:

    def __init__(self, agent_a, agent_b, task):
        self.session_id = str(uuid.uuid4())
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.task = task
        self.created_at = time.time()
        self.messages = []

    def add_message(self, sender, content):
        self.messages.append({
            "sender": sender,
            "content": content,
            "timestamp": time.time()
        })

    def export(self):
        return {
            "session_id": self.session_id,
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "task": self.task,
            "messages": self.messages
        }


class HandshakeManager:

    def __init__(self):
        self.sessions = {}

    def create_session(self, agent_a, agent_b, task):
        session = HandshakeSession(agent_a, agent_b, task)
        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def list_sessions(self):
        return [s.export() for s in self.sessions.values()]


manager = HandshakeManager()
