
from crewai import Agent, Crew, Process, Task
import re
from math import isfinite
from config import LLM_MODEL, OPENROUTER_API_KEY
from crewai import LLM
from pydantic import BaseModel, Field, ConfigDict

class TravelBudgetOutput(BaseModel):
    """Structured expense estimates returned by the Budget Analyst."""

    model_config = ConfigDict(extra="forbid")

    hotel_cost: float = Field(ge=0)
    transport_cost: float = Field(ge=0)
    food_cost: float = Field(ge=0)
    activities_cost: float = Field(ge=0)
    miscellaneous_cost: float = Field(ge=0)
    total_budget: float = Field(ge=0)
    assumptions: str
    cheaper_alternatives: str

from tools.travel_tools import (
    search_travel_information,
    get_destination_weather,
    calculate_travel_budget,
    calculate_trip_duration,
)


llm = LLM(
    model=LLM_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=0.2,
)


# -------------------- AGENTS --------------------

travel_coordinator = Agent(
    role="Travel Coordinator",
    goal="Understand customer requirements and coordinate a complete, "
         "personalized travel plan.",
    backstory="You are an experienced travel coordinator who ensures "
              "every agent's work aligns with the customer's requirements.",
    llm=llm,
    allow_delegation=False,
    verbose=True,
)

destination_researcher = Agent(
    role="Destination Research Specialist",
    goal="Research suitable attractions, local experiences, and practical "
         "destination information using web search.",
    backstory="You are a destination expert who prioritizes relevant, "
              "verifiable travel information and source links.",
    tools=[search_travel_information, get_destination_weather],
    llm=llm,
    allow_delegation=False,
    verbose=True,
)

hotel_transport_agent = Agent(
    role="Hotel and Transport Specialist",
    goal="Research accommodation and transport options with realistic "
         "cost estimates and source links.",
    backstory="You compare options based on location, convenience, "
              "customer preferences, and affordability.",
    tools=[search_travel_information],
    llm=llm,
    allow_delegation=False,
    verbose=True,
)

budget_analyst = Agent(
    role="Travel Budget Analyst",
    goal="Estimate trip expenses, calculate totals, and identify "
         "ways to stay within the customer's budget.",
    backstory="You are a careful financial planner who separates "
              "verified prices from estimates and avoids hidden costs.",
    tools=[calculate_travel_budget],
    llm=llm,
    allow_delegation=False,
    verbose=True,
)

itinerary_planner = Agent(
    role="Itinerary Planner",
    goal="Create a practical day-by-day travel schedule based on "
         "research, duration, interests, and the approved budget.",
    backstory="You design realistic travel schedules with sensible "
              "activity groupings, breaks, and travel-time considerations.",
    tools=[calculate_trip_duration],
    llm=llm,
    allow_delegation=False,
    verbose=True,
)


# -------------------- TASKS --------------------

requirements_task = Task(
    description=(
        "Organize the customer's requirements into a concise travel brief. "
        "Identify destination, starting location, dates, duration, total "
        "budget, number of travelers, and preferred activities. "
        "Flag missing or inconsistent information. "
        "Customer details: {travel_requirements}"
    ),
    expected_output="A structured customer travel brief with dates, "
                    "duration, budget, traveler count, and interests.",
    agent=travel_coordinator,
)

destination_task = Task(
    description=(
        "Research attractions and local experiences for the destination "
        "using your search tool. Retrieve current weather information "
        "where possible, but do not present current conditions as a future "
        "forecast. Include source URLs, suitability for the customer's "
        "interests, practical notes, and any relevant admission costs. "
        "Customer brief: {travel_requirements}"
    ),
    expected_output="Destination research with attraction descriptions, "
                    "source URLs, practical notes, and cost estimates.",
    agent=destination_researcher,
    context=[requirements_task],
)

hotel_transport_task = Task(
    description=(
        "Use web search to investigate accommodation and transport options "
        "for this trip. Consider the starting location, destination, travel "
        "dates, traveler count, and budget. Provide source URLs and prices "
        "when available. Clearly label unverified prices as estimates. "
        "Never claim a booking or live availability has been confirmed "
        "unless the source actually confirms it."
    ),
    expected_output="A comparison of accommodation and transport options "
                    "with source URLs, estimated prices, and caveats.",
    agent=hotel_transport_agent,
    context=[requirements_task, destination_task],
)

budget_task = Task(
    description=(
        "Build a realistic itemized budget using the customer brief and "
        "research from the previous tasks. Account for transport, hotel, "
        "food, activities, and miscellaneous expenses. Use the budget "
        "calculator tool to calculate the total and remaining budget. "
        "If costs are missing, state your assumptions explicitly. "
        "If the estimate exceeds the budget, propose specific cheaper "
        "alternatives and recalculate the revised estimate."
    ),
    
    expected_output=(
        "Return an itemized budget with these exact expense categories "
        "and numeric values in INR: accommodation, transport, food, "
        "activities, and miscellaneous. Include a machine-readable JSON "
        "object with keys hotel_cost, transport_cost, food_cost, "
        "activities_cost, miscellaneous_cost, and total_budget. All "
        "values must be numbers, not strings. Also include assumptions, "
        "whether the trip is within budget, and cheaper alternatives "
        "if the estimate exceeds the budget."
    ),

    agent=budget_analyst,
    context=[requirements_task, destination_task, hotel_transport_task],
    output_pydantic=TravelBudgetOutput,
)

itinerary_task = Task(
    description=(
        "Create an achievable day-by-day itinerary using the customer brief, "
        "destination research, hotel and transport findings, and budget "
        "analysis. Cover every travel day, group nearby attractions where "
        "practical, allow meal and rest breaks, and avoid exceeding the "
        "approved budget. Include useful source URLs and distinguish "
        "estimates from confirmed information."
    ),
    expected_output="A complete daily itinerary, accommodation and "
                    "transport recommendations, cost breakdown, budget "
                    "status, sources, and alternatives.",
    agent=itinerary_planner,
    context=[
        requirements_task,
        destination_task,
        hotel_transport_task,
        budget_task,
    ],
)


final_review_task = Task(
    description=(
        "Produce the final customer-ready travel plan using all previous "
        "task outputs and the customer requirements.\n\n"
        "MANDATORY BUDGET VALIDATION:\n"
        "1. Use the Budget Analyst task's calculator-generated expense "
        "total, budget, and remaining balance as the authoritative "
        "budget figures whenever those results are available.\n"
        "2. Do not invent, independently recalculate, or contradict "
        "the verified calculator output.\n"
        "3. Ensure the final expense categories reconcile with the "
        "reported total. If they do not reconcile, clearly flag the "
        "inconsistency instead of claiming the figures are verified.\n"
        "4. Clearly distinguish estimated prices from confirmed prices.\n"
        "5. If the available budget analysis exceeds the budget, explain "
        "the shortfall and recommend specific cost-saving alternatives. "
        "Do not claim the revised budget is verified unless the calculator "
        "has actually calculated it.\n\n"
        "Also check that every travel day is covered, the requested "
        "activities are addressed, source URLs are included, and current "
        "weather is not presented as a future forecast. Do not invent "
        "live prices, bookings, availability, or sources.\n\n"
        "Customer requirements: {travel_requirements}"
    ),
    expected_output=(
        "A final customer-ready travel plan containing daily activities, "
        "accommodation and transport recommendations, itemized expenses, "
        "the Budget Analyst's verified budget figures, alternatives, "
        "source URLs, and clear caveats for estimates or unavailable data."
    ),
    agent=travel_coordinator,
    context=[
        requirements_task,
        destination_task,
        hotel_transport_task,
        budget_task,
        itinerary_task,
    ],
)


# -------------------- CREW --------------------

travel_crew = Crew(
    agents=[
        travel_coordinator,
        destination_researcher,
        hotel_transport_agent,
        budget_analyst,
        itinerary_planner,
    ],
    tasks=[
        requirements_task,
        destination_task,
        hotel_transport_task,
        budget_task,
        itinerary_task,
        final_review_task,
    ],
    process=Process.sequential,
    verbose=True,
)



def verify_budget(
    hotel_cost: float,
    transport_cost: float,
    food_cost: float,
    activities_cost: float,
    miscellaneous_cost: float,
    total_budget: float,
) -> str:
    """Calculate trip expenses and budget status using Python."""
    costs = {
        "Accommodation": hotel_cost,
        "Transport": transport_cost,
        "Food": food_cost,
        "Activities": activities_cost,
        "Local transport and miscellaneous": miscellaneous_cost,
    }

    for name, amount in costs.items():
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not isfinite(amount)
            or amount < 0
        ):
            raise ValueError(
                f"{name} must be a finite, non-negative number."
            )

    if (
        isinstance(total_budget, bool)
        or not isinstance(total_budget, (int, float))
        or not isfinite(total_budget)
        or total_budget < 0
    ):
        raise ValueError(
            "Budget must be a finite, non-negative number."
        )

    total = round(sum(costs.values()), 2)
    remaining = round(total_budget - total, 2)
    status = "WITHIN BUDGET" if remaining >= 0 else "OVER BUDGET"

    lines = [
        "## Python-Verified Budget",
        "",
        "| Expense category | Amount (INR) |",
        "|---|---:|",
    ]

    for category, amount in costs.items():
        lines.append(f"| {category} | INR {amount:,.2f} |")

    lines.extend([
        f"| **Total estimated cost** | **INR {total:,.2f}** |",
        f"| **Total budget** | **INR {total_budget:,.2f}** |",
        f"| **Remaining budget** | **INR {remaining:,.2f}** |",
        "",
        f"**Budget status: {status}**",
        "",
        "Python calculated these figures from the expense inputs. "
        "This calculation does not independently verify market prices.",
    ])

    return "\n".join(lines)



def plan_trip(travel_requirements: dict) -> str:
    """Run CrewAI and verify the Budget Analyst's expense arithmetic."""
    result = travel_crew.kickoff(
        inputs={"travel_requirements": travel_requirements}
    )

    report = str(result)
    budget_output = budget_task.output

    if budget_output is None or budget_output.pydantic is None:
        return (
            report
            + "\n\n---\n\n"
            + "## Budget Verification Status\n\n"
            + "Python verification could not run because the Budget "
              "Analyst did not return a valid structured budget. "
              "Treat the report's cost figures as unverified estimates."
        )

    data = budget_output.pydantic

    try:
        verified_budget = verify_budget(
            hotel_cost=data.hotel_cost,
            transport_cost=data.transport_cost,
            food_cost=data.food_cost,
            activities_cost=data.activities_cost,
            miscellaneous_cost=data.miscellaneous_cost,
            total_budget=float(travel_requirements["budget"]),
        )
    except (ValueError, TypeError, AttributeError) as exc:
        return (
            report
            + "\n\n---\n\n"
            + "## Budget Verification Status\n\n"
            + f"Python budget verification failed: {exc}\n\n"
            + "Treat the expense figures as unverified estimates."
        )

    notes = (
        "\n\n---\n\n"
        + verified_budget
        + "\n\n**Budget assumptions:** "
        + data.assumptions
        + "\n\n**Cost-saving alternatives:** "
        + data.cheaper_alternatives
        + "\n\n*Prices are estimates; Python verifies arithmetic, "
        "not real-world price or availability.*"
    )

    return report + notes

    verified_budget = verify_budget(
        hotel_cost=data.hotel_cost,
        transport_cost=data.transport_cost,
        food_cost=data.food_cost,
        activities_cost=data.activities_cost,
        miscellaneous_cost=data.miscellaneous_cost,
        total_budget=float(travel_requirements["budget"]),
    )

    notes = (
        "\n\n---\n\n"
        + verified_budget
        + "\n\n**Budget assumptions:** "
        + data.assumptions
        + "\n\n**Cost-saving alternatives:** "
        + data.cheaper_alternatives
        + "\n\n*Prices are estimates; Python verifies arithmetic, "
          "not real-world price or availability.*"
    )

    return report + notes




if __name__ == "__main__":
    sample_requirements = {
        "destination": "Jaipur, India",
        "starting_location": "Bengaluru, India",
        "start_date": "2026-11-10",
        "end_date": "2026-11-13",
        "duration": 4,
        "budget": 25000,
        "travelers": 1,
        "activities": ["sightseeing", "local food", "shopping"],
    }

    print("\nStarting Smart Travel Planning System...\n")
    print(plan_trip(sample_requirements))
