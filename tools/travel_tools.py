import json
import os
import requests
from datetime import datetime
from crewai.tools import tool
from dotenv import load_dotenv
import streamlit as st
def get_secret(key):
    value = os.getenv(key)

    if value:
        return value

    try:
        return st.secrets.get(key)
    except Exception:
        return None
load_dotenv()


@tool("Search Travel Information")
def search_travel_information(query: str) -> str:
    """Search the web for attractions, local experiences, hotels, and travel information."""
    api_key = get_secret("SERPER_API_KEY")
    if not api_key:
        return "Web search unavailable: SERPER_API_KEY is not configured."

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json={"q": query},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("organic", [])[:5]:
            results.append(
                f"Title: {item.get('title', 'N/A')}\n"
                f"Snippet: {item.get('snippet', 'N/A')}\n"
                f"Source: {item.get('link', 'N/A')}"
            )

        return "\n\n".join(results) or "No search results found."
    except requests.RequestException as exc:
        return f"Web search failed: {exc}"


@tool("Get Destination Weather")
def get_destination_weather(city: str) -> str:
    """Retrieve current weather and conditions for a destination city."""
    api_key = get_secret("OPENWEATHER_API_KEY")
    if not api_key:
        return "Weather unavailable: OPENWEATHER_API_KEY is not configured."

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        return (
            f"Weather for {data.get('name', city)}: "
            f"{data['main']['temp']}°C, "
            f"{data['weather'][0]['description']}; "
            f"humidity {data['main']['humidity']}%."
        )
    except requests.RequestException as exc:
        return f"Weather lookup failed: {exc}"



@tool("Calculate Travel Budget")
def calculate_travel_budget(
    hotel_cost: float,
    transport_cost: float,
    food_cost: float,
    activities_cost: float,
    miscellaneous_cost: float,
    total_budget: float,
) -> str:
    """Calculate travel expenses, remaining budget, and budget status."""

    costs = {
        "Hotel": hotel_cost,
        "Transport": transport_cost,
        "Food": food_cost,
        "Activities": activities_cost,
        "Miscellaneous": miscellaneous_cost,
    }

    values = list(costs.values()) + [total_budget]

    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not __import__("math").isfinite(value)
            or value < 0
        ):
            return "Error: all costs and the budget must be finite, non-negative numbers."

    total = sum(costs.values())
    remaining = total_budget - total
    status = "WITHIN BUDGET" if remaining >= 0 else "OVER BUDGET"

    breakdown = "\n".join(
        f"{category} cost: ₹{amount:,.2f}"
        for category, amount in costs.items()
    )

    result = {
        "expenses": costs,
        "total": round(total, 2),
        "budget": round(total_budget, 2),
        "remaining": round(remaining, 2),
        "status": status,
    }

    return (
        f"EXPENSE BREAKDOWN\n{breakdown}\n"
        f"Estimated total: INR {total:,.2f}\n"
        f"Total budget: INR {total_budget:,.2f}\n"
        f"Remaining budget: INR {remaining:,.2f}\n"
        f"Budget status: {status}\n"
        f"STRUCTURED_RESULT: {json.dumps(result)}"
    )


@tool("Calculate Trip Duration")
def calculate_trip_duration(start_date: str, end_date: str) -> str:
    """Calculate the number of travel days between YYYY-MM-DD dates, inclusive."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if end < start:
            return "Error: end date must be on or after start date."

        return f"Trip duration: {(end - start).days + 1} days."
    except ValueError:
        return "Error: provide dates in YYYY-MM-DD format."
