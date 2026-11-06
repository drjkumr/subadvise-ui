from pathlib import Path

from memory_manager import HybridChatMemory


def main() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    memory = HybridChatMemory.from_paths(
        project_dir / "data" / "demo_chat_history",
        project_dir / "data" / "demo_chroma_db",
    )
    session = memory.create_session(metadata={"source": "demo"})

    memory.append_message(
        session.session_id,
        "user",
        "I use a yearly music streaming subscription.",
    )
    memory.append_message(
        session.session_id,
        "assistant",
        "I will remember that for this conversation.",
    )
    memory.append_message(
        session.session_id,
        "user",
        "I also want to track my monthly grocery target.",
    )
    memory.append_message(
        session.session_id,
        "assistant",
        "You can review monthly expenses using your target categories.",
    )

    context = memory.get_context(
        session.session_id,
        query_text="What did I say about my streaming plan?",
        recent_turns=1,
        relevant_top_k=3,
    )
    print("Recent history:")
    for message in context.recent_history:
        print(f"{message.role}: {message.content}")

    print("\nSemantically relevant older messages:")
    for result in context.relevant_context:
        print(f"{result.message.role}: {result.message.content} ({result.distance:.3f})")


if __name__ == "__main__":
    main()
