from typing import List

def aggregate_responses(responses: List[str], task_type: str = "general") -> str:
    if not responses:
        return "No responses to aggregate."
        
    if len(responses) == 1:
        return responses[0]
        
    if task_type == "summary":
        # Formats separate chunk summaries into a cohesive report outline
        aggregated = "### Combined Summary Report\n\n"
        for i, res in enumerate(responses, 1):
            aggregated += f"#### Part {i}\n{res.strip()}\n\n"
        return aggregated.strip()
        
    # Default clean concatenation for code generation, reviews, or general analysis
    return "\n\n".join(res.strip() for res in responses)