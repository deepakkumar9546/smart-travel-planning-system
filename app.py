
import streamlit as st
from datetime import date, timedelta

from crew import plan_trip


st.set_page_config(
    page_title="Smart Travel Planner",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Smart Travel Planning System")
st.write(
    "Plan a personalized trip with collaborating AI agents, "
    "travel research, and budget analysis."
)

with st.form("travel_form"):
    st.subheader("Tell us about your trip")

    col1, col2 = st.columns(2)

    with col1:
        destination = st.text_input(
            "Travel destination",
            placeholder="e.g. Jaipur, India",
        )
        starting_location = st.text_input(
            "Starting location",
            placeholder="e.g. Bengaluru, India",
        )
        start_date = st.date_input(
            "Departure date",
            value=date.today() + timedelta(days=30),
            min_value=date.today(),
        )
        travelers = st.number_input(
            "Number of travelers",
            min_value=1,
            max_value=20,
            value=1,
            step=1,
        )

    with col2:
        end_date = st.date_input(
            "Return date",
            value=date.today() + timedelta(days=33),
            min_value=date.today(),
        )
        budget = st.number_input(
            "Total budget (₹)",
            min_value=1000,
            max_value=10000000,
            value=25000,
            step=1000,
        )
        activities = st.multiselect(
            "Preferred activities",
            [
                "Sightseeing",
                "Local food",
                "Shopping",
                "Adventure",
                "Relaxation",
                "Nature",
                "Culture and history",
                "Nightlife",
            ],
            default=["Sightseeing", "Local food", "Shopping"],
        )

    submitted = st.form_submit_button(
        "Generate my travel plan",
        type="primary",
        use_container_width=True,
    )

if submitted:
    if not destination.strip() or not starting_location.strip():
        st.error("Please enter both your destination and starting location.")
    elif end_date < start_date:
        st.error("Return date must be on or after the departure date.")
    elif not activities:
        st.error("Please select at least one preferred activity.")
    else:
        requirements = {
            "destination": destination.strip(),
            "starting_location": starting_location.strip(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "duration": (end_date - start_date).days + 1,
            "budget": float(budget),
            "travelers": int(travelers),
            "activities": activities,
        }

        try:
            with st.spinner(
                "Our AI travel agents are researching and planning your trip..."
            ):
                result = plan_trip(requirements)

            st.success("Your travel plan is ready!")
            st.markdown(result)

            st.download_button(
                "Download travel plan",
                data=str(result),
                file_name="smart_travel_plan.md",
                mime="text/markdown",
            )

        except Exception as exc:
            st.error(
                "The travel planning process failed. "
                "Check the VS Code terminal for diagnostic details."
            )
            print(f"Travel planning error: {exc}")
