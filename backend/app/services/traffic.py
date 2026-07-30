from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import CommunityReport, EnforcementCamera, DuiNotice
from app.providers.base import DemoTrafficProvider

provider = DemoTrafficProvider()


async def build_traffic_reply(db: Session, area: str) -> str:
    incidents = await provider.incidents_for(area)
    now = datetime.utcnow()
    police = db.scalars(
        select(CommunityReport)
        .where(CommunityReport.area_label.ilike(f"%{area}%"))
        .where(CommunityReport.expires_at > now)
        .where(CommunityReport.report_type.in_(["police_visible", "police_hidden", "police_other_side", "mobile_camera"]))
        .order_by(CommunityReport.reported_at.desc())
        .limit(2)
    ).all()
    cameras = db.scalars(
        select(EnforcementCamera)
        .where(EnforcementCamera.area_label.ilike(f"%{area}%"))
        .where(EnforcementCamera.active.is_(True))
        .limit(2)
    ).all()
    dui_notices = db.scalars(
        select(DuiNotice)
        .where(DuiNotice.area_label.ilike(f"%{area}%"))
        .where(DuiNotice.starts_at <= now)
        .where(DuiNotice.ends_at >= now)
        .limit(1)
    ).all()

    lines = [f"TrafficSMS - {area}"]
    for i, incident in enumerate(incidents[:2], 1):
        delay = f", {incident.delay_minutes}-min delay" if incident.delay_minutes else ""
        lines.append(f"{i}. {incident.road_name}: {incident.description}{delay}.")
    for report in police:
        age = max(0, int((now - report.reported_at).total_seconds() // 60))
        lines.append(f"Police peer report #{report.id}: {report.road_name} near {report.area_label}, {age}m ago. Reply P{report.id} YES/NO/UNSURE.")
    for camera in cameras:
        label = "verified" if camera.verified else "community-reported"
        lines.append(f"Camera: {camera.road_name} near {camera.area_label} ({label}).")
    for notice in dui_notices:
        lines.append(f"Official DUI notice: {notice.agency}, {notice.area_label}. Source published by agency.")
    lines.append("Do not text while driving. Obey posted limits.")
    return "\n".join(lines)[:1500]
