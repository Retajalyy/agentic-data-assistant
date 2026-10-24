"""Interactive CLI:  python main.py"""
import uuid

from agent.graph import ask, build_agent


def main() -> None:
    agent = build_agent()
    thread = str(uuid.uuid4())
    print("Data assistant ready. Type 'exit' to quit.")
    while True:
        q = input("\nYou: ").strip()
        if q.lower() in {"exit", "quit", ""}:
            break
        res = ask(agent, q, thread_id=thread)
        print(f"\nAssistant: {res['answer']}\n[tools: {res['tools_used']} | {res['latency_s']}s]")


if __name__ == "__main__":
    main()
