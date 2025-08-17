import re

def format_plans_to_markdown(plans):
    markdown_output = []

    for plan in plans:
        # Normalize: remove extra spaces and unify newlines
        plan = plan.strip().replace('\\n', '\n').replace('\r', '')

        # Try to extract Reasoning and Step using regex (case insensitive)
        reasoning_match = re.search(r"(?i)reasoning\s*:\s*(.*?)(?=\n|\bstep\s*:|$)", plan, re.IGNORECASE)
        step_match = re.search(r"(?i)step\s*:\s*(.*)", plan, re.IGNORECASE)

        reasoning = reasoning_match.group(1).strip() if reasoning_match else "N/A"
        step = step_match.group(1).strip() if step_match else "N/A"

        formatted = f"**Reasoning**: {reasoning}\n**Step**: {step}"
        markdown_output.append(formatted)

    return "\n\n".join(markdown_output)