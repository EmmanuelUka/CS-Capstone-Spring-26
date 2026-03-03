# generate a professional looking summery of a few word scouting report.
# example report: "Fast, explosive first step, undersized, struggles vs press"
# example output: "John Smith is a fast athlete with an explosive first step, but his undersized frame limits his effectiveness against press coverage. While his speed can create separation, he consistently struggles when confronted by press defenders."
import argparse
from typing import Iterable, Optional, Tuple
from groq import Groq


def _build_prompt(name: str, pos: str, prev: str, notes: str) -> str:
    return f"""
You are a scout report writer.

INPUT
Name: {name}
Role/Pos: {pos}
PrevSummary: {prev}
NewNotes: {notes}

TASK
1) Write a concise American football scouting report (2–3 sentences).
2) Use ONLY facts supported by PrevSummary + NewNotes.
3) No headings. No lists.
"""

def generate_scout_report(
    name: str,
    pos: str = "",
    prev: str = "",
    notes: str = "",
    client: Optional[Groq] = None,
    stream: bool = True,
    suppress_stream_output: bool = False,
) -> str:
    """Return a scouting report for the provided player inputs.

    The report is streamed to stdout by default for parity with the previous
    script behavior, but the complete text is always returned.
    """

    client = client or Groq()
    prompt = _build_prompt(name, pos, prev, notes)
    completion = client.chat.completions.create(
        model="groq/compound-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_completion_tokens=300,
        top_p=1,
        stream=stream,
    )

    report_parts: list[str] = []
    for chunk in completion:
        content = chunk.choices[0].delta.content
        if not content:
            continue
        report_parts.append(content)
        if stream and not suppress_stream_output:
            print(content, end="")

    return "".join(report_parts)

def _cli_args() -> Tuple[str, str, str, str]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--pos", default="")
    parser.add_argument("--prev", default="")
    parser.add_argument("--notes", required=True)
    args = parser.parse_args()
    return args.name, args.pos, args.prev, args.notes


def main() -> None:
    name, pos, prev, notes = _cli_args()
    generate_scout_report(name=name, pos=pos, prev=prev, notes=notes)


if __name__ == "__main__":
    main()
