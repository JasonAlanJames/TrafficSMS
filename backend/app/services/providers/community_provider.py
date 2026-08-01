from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    CommunityReport,
    DuiNotice,
    EnforcementCamera,
)


class CommunityProvider:
    """
    Retrieves community and local intelligence
    from the TrafficSMS database.

    Responsibilities:

    - Community police reports
    - Enforcement cameras
    - Official DUI notices
    """

    async def get_reports(
        self,
        db: Session,
        area: str,
        limit: int = 5,
    ) -> list[CommunityReport]:

        return (
            db.scalars(
                select(CommunityReport)
                .where(
                    CommunityReport.area_label.ilike(
                        f"%{area}%"
                    )
                )
                .where(
                    CommunityReport.expires_at > datetime.utcnow()
                )
                .order_by(
                    CommunityReport.reported_at.desc()
                )
                .limit(limit)
            )
            .all()
        )

    async def get_cameras(
        self,
        db: Session,
        area: str,
        limit: int = 5,
    ) -> list[EnforcementCamera]:

        return (
            db.scalars(
                select(EnforcementCamera)
                .where(
                    EnforcementCamera.area_label.ilike(
                        f"%{area}%"
                    )
                )
                .where(
                    EnforcementCamera.active.is_(True)
                )
                .limit(limit)
            )
            .all()
        )

    async def get_dui_notices(
        self,
        db: Session,
        area: str,
        limit: int = 3,
    ) -> list[DuiNotice]:

        now = datetime.utcnow()

        return (
            db.scalars(
                select(DuiNotice)
                .where(
                    DuiNotice.area_label.ilike(
                        f"%{area}%"
                    )
                )
                .where(
                    DuiNotice.starts_at <= now
                )
                .where(
                    DuiNotice.ends_at >= now
                )
                .limit(limit)
            )
            .all()
        )


community_provider = CommunityProvider()