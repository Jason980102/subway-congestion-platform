from datetime import date, datetime, time, timedelta

import streamlit as st
from sqlalchemy import distinct, func, select

from database import SessionLocal
from models import Ridership, Station
from prediction_service import predict_and_save
from recommendation_service import generate_and_save
from user_decision_service import save_user_decision


st.set_page_config(
    page_title="NYU Subway Congestion Advisor",
    page_icon="🚇",
    layout="centered",
)


@st.cache_data(ttl=300)
def get_stations() -> list[tuple[int, str]]:
    with SessionLocal() as session:
        return list(
            session.execute(
                select(Station.station_id, Station.station_name).order_by(
                    Station.station_name
                )
            ).all()
        )


@st.cache_data(ttl=300)
def get_training_coverage() -> tuple[date, date, tuple[int, ...]]:
    with SessionLocal() as session:
        minimum_date, maximum_date = session.execute(
            select(
                func.min(Ridership.record_date),
                func.max(Ridership.record_date),
            )
        ).one()
        months = tuple(
            session.scalars(
                select(distinct(Ridership.month)).order_by(Ridership.month)
            ).all()
        )

    if minimum_date is None or maximum_date is None or not months:
        raise RuntimeError("No training coverage is available in RIDERSHIP")
    return minimum_date, maximum_date, months


def next_supported_future_date(today: date, supported_months: tuple[int, ...]) -> date:
    candidate = today
    for _ in range(730):
        if candidate.month in supported_months:
            return candidate
        candidate += timedelta(days=1)
    raise RuntimeError("Unable to find a supported future prediction date")


def congestion_icon(level: str) -> str:
    return {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(level, "⚪")


st.title("🚇 NYU Subway Congestion Advisor")
st.caption(
    "Select a station and travel time to receive a congestion prediction "
    "and an actionable recommendation."
)

stations = get_stations()
station_labels = {station_id: name for station_id, name in stations}
training_start, training_end, supported_months = get_training_coverage()
today = date.today()
default_prediction_date = next_supported_future_date(today, supported_months)

# Remove an old historical integration-test result after the app is upgraded
# to future-only predictions.
old_workflow = st.session_state.get("workflow")
if old_workflow and old_workflow["prediction_time"].date() < today:
    st.session_state.pop("workflow", None)
    st.session_state.pop("decision", None)

if not stations:
    st.error("No stations are available in the database.")
    st.stop()

with st.form("prediction_form"):
    station_id = st.selectbox(
        "Station",
        options=list(station_labels),
        format_func=lambda value: station_labels[value],
    )
    travel_date = st.date_input(
        "Future travel date",
        value=default_prediction_date,
        min_value=today,
    )
    travel_time = st.time_input("Travel time", value=time(18, 0))
    submitted = st.form_submit_button(
        "Check congestion",
        type="primary",
        use_container_width=True,
    )

if submitted:
    if travel_date.month not in supported_months:
        supported_names = ", ".join(
            date(2000, month, 1).strftime("%B") for month in supported_months
        )
        st.error(
            "This month is outside the current model's training coverage. "
            f"Please choose a future date in: {supported_names}."
        )
    else:
        requested_datetime = datetime.combine(travel_date, travel_time)
        try:
            with st.spinner("Calculating future congestion and recommendation..."):
                prediction = predict_and_save(station_id, requested_datetime)
                recommendation = generate_and_save(prediction.prediction_id)

            st.session_state["workflow"] = {
                "prediction_id": prediction.prediction_id,
                "station_name": prediction.station_name,
                "prediction_time": prediction.prediction_time,
                "congestion_level": prediction.congestion_level,
                "confidence_score": prediction.confidence_score,
                "estimated_transfers": prediction.estimated_transfers,
                "model_version": prediction.model_version,
                "recommendation_id": recommendation.recommendation_id,
                "recommended_route": recommendation.recommended_route,
                "suggested_departure_time": recommendation.suggested_departure_time,
                "incentive": recommendation.incentive,
            }
            st.session_state.pop("decision", None)
        except Exception as exc:
            st.error(f"Unable to complete the prediction: {exc}")

st.caption(
    f"Future estimates use recurring station-hour patterns learned from "
    f"{training_start:%B %Y}–{training_end:%B %Y} ridership data."
)

workflow = st.session_state.get("workflow")

if workflow:
    st.divider()
    st.subheader("Predicted future congestion")

    metric_col, confidence_col = st.columns(2)
    metric_col.metric(
        "Congestion level",
        f"{congestion_icon(workflow['congestion_level'])} "
        f"{workflow['congestion_level']}",
    )
    confidence_col.metric(
        "Model confidence",
        f"{workflow['confidence_score']:.1%}",
    )

    st.write(
        f"**Station:** {workflow['station_name']}  \n"
        f"**Requested time:** {workflow['prediction_time']:%Y-%m-%d %I:%M %p}  \n"
        f"**Estimated transfers:** {workflow['estimated_transfers']:.2f}"
    )

    st.subheader("Recommended action")
    st.info(workflow["recommended_route"])
    st.write(
        f"**Suggested departure:** "
        f"{workflow['suggested_departure_time']:%Y-%m-%d %I:%M %p}  \n"
        f"**Incentive:** {workflow['incentive']}"
    )

    decision = st.session_state.get("decision")
    if decision:
        st.success(
            f"Decision saved: {decision['user_action']} "
            f"(Decision ID {decision['decision_id']})"
        )
    else:
        accept_col, keep_col = st.columns(2)

        if accept_col.button(
            "Accept recommendation",
            type="primary",
            use_container_width=True,
        ):
            saved = save_user_decision(
                workflow["recommendation_id"],
                "ACCEPTED",
            )
            st.session_state["decision"] = {
                "decision_id": saved.decision_id,
                "user_action": saved.user_action,
            }
            st.rerun()

        if keep_col.button(
            "Keep original plan",
            use_container_width=True,
        ):
            saved = save_user_decision(
                workflow["recommendation_id"],
                "KEPT_ORIGINAL_PLAN",
            )
            st.session_state["decision"] = {
                "decision_id": saved.decision_id,
                "user_action": saved.user_action,
            }
            st.rerun()

    st.caption(
        f"Prediction ID {workflow['prediction_id']} · "
        f"Recommendation ID {workflow['recommendation_id']} · "
        f"Model {workflow['model_version']}"
    )
