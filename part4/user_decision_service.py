from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from database import SessionLocal
from models import Recommendation, UserDecision


ACTION_MAPPING = {
    "ACCEPTED": "Accepted",
    "ACCEPT": "Accepted",
    "FOLLOWED": "Followed",
    "REJECTED": "Rejected",
    "REJECT": "Rejected",
    "KEPT_ORIGINAL_PLAN": "Ignored",
    "IGNORED": "Ignored",
}


@dataclass(frozen=True)
class UserDecisionResult:
    decision_id: int
    recommendation_id: int
    user_action: str
    decision_time: datetime


def save_user_decision(
    recommendation_id: int,
    user_action: str,
) -> UserDecisionResult:
    requested_action = user_action.strip().upper()
    if requested_action not in ACTION_MAPPING:
        raise ValueError(
            "Unsupported user action"
        )
    database_action = ACTION_MAPPING[requested_action]

    with SessionLocal.begin() as session:
        recommendation = session.get(Recommendation, recommendation_id)
        if recommendation is None:
            raise ValueError(f"Unknown recommendation_id: {recommendation_id}")

        existing = session.scalar(
            select(UserDecision).where(
                UserDecision.recommendation_id == recommendation_id
            )
        )
        if existing is not None:
            return UserDecisionResult(
                decision_id=existing.decision_id,
                recommendation_id=existing.recommendation_id,
                user_action=str(existing.user_action),
                decision_time=existing.decision_time,
            )

        decision_time = datetime.now()
        decision = UserDecision(
            recommendation_id=recommendation_id,
            user_action=database_action,
            decision_time=decision_time,
        )
        session.add(decision)
        session.flush()

        result = UserDecisionResult(
            decision_id=decision.decision_id,
            recommendation_id=recommendation_id,
            user_action=database_action,
            decision_time=decision_time,
        )

    return result
