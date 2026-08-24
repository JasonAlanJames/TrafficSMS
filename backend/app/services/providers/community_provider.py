from datetime import UTC, datetime

from sqlalchemy import or_, select
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

    async def get_active_reports(self, db: Session, terms: tuple[str, ...], limit: int = 12) -> list[CommunityReport]:
        statement = select(CommunityReport).where(CommunityReport.expires_at > self._naive_utc_now())
        if terms:
            statement = statement.where(or_(*[
                CommunityReport.area_label.ilike(f"%{term}%") | CommunityReport.road_name.ilike(f"%{term}%")
                for term in terms
            ]))
        return list(db.scalars(statement.order_by(CommunityReport.reported_at.desc()).limit(limit)))

    async def get_active_cameras(self, db: Session, terms: tuple[str, ...], limit: int = 8) -> list[EnforcementCamera]:
        statement = select(EnforcementCamera).where(EnforcementCamera.active.is_(True))
        if terms:
            statement = statement.where(or_(*[
                EnforcementCamera.area_label.ilike(f"%{term}%") | EnforcementCamera.road_name.ilike(f"%{term}%")
                for term in terms
            ]))
        return list(db.scalars(statement.limit(limit)))

    async def get_active_dui_notices(self, db: Session, terms: tuple[str, ...], limit: int = 5) -> list[DuiNotice]:
        now = self._naive_utc_now()
        statement = select(DuiNotice).where(DuiNotice.starts_at <= now, DuiNotice.ends_at >= now)
        if terms:
            statement = statement.where(or_(*[DuiNotice.area_label.ilike(f"%{term}%") for term in terms]))
        return list(db.scalars(statement.limit(limit)))

    @staticmethod
    def _naive_utc_now() -> datetime:
        """Match existing naive UTC database columns without deprecated APIs."""

        return datetime.now(UTC).replace(tzinfo=None)

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
