from argus_review.services.review.service import ReviewService


async def run_agent_review_command():
    review_service = ReviewService()
    # Single combined agent session (summary + inline together) instead of
    # chaining the two standalone agent-light flows, which would explore the
    # diff/conventions twice and roughly double the quota cost.
    await review_service.run_agent_review()
    review_service.report_total_cost()
