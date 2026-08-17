from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.refresh_token import RefreshToken


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user: User,
    ) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def save(
        self,
        user: User,
    ) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(
        self,
        user_id: int,
    ) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(
        self,
        email: str,
    ) -> User | None:
        normalized = email.strip().lower()
        return self.db.scalar(
            select(User).where(
                func.lower(User.email) == normalized
            )
        )

    def get_by_phone(
        self,
        phone_number: str,
    ) -> User | None:
        return self.db.scalar(
            select(User).where(
                User.phone_e164 == phone_number
            )
        )

    def get_by_identifier(
        self,
        identifier: str,
    ) -> User | None:
        normalized = identifier.strip().lower()

        return self.db.scalar(
            select(User).where(
                or_(
                    func.lower(User.email) == normalized,
                    User.phone_e164 == identifier,
                )
            )
        )

    def get_by_verification_token(
        self,
        token: str,
    ) -> User | None:
        return self.db.scalar(
            select(User).where(
                User.verification_token == token
            )
        )

    def get_by_password_reset_token(
        self,
        token: str,
    ) -> User | None:
        return self.db.scalar(
            select(User).where(
                User.password_reset_token == token
            )
        )

    def phone_exists(
        self,
        phone_number: str,
        *,
        exclude_user_id: int | None = None,
    ) -> bool:
        user = self.get_by_phone(phone_number)
        if user is None:
            return False
        if exclude_user_id is None:
            return True
        return user.id != exclude_user_id

    def store_refresh_token(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> RefreshToken:
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_refresh_token(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        return self.db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash
            )
        )

    def revoke_refresh_token(
        self,
        record: RefreshToken,
        *,
        revoked_at: datetime,
        replaced_by_token_id: UUID | None = None,
    ) -> RefreshToken:
        record.revoked = True
        record.revoked_at = revoked_at
        record.replaced_by_token_id = replaced_by_token_id
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def revoke_user_refresh_tokens(
        self,
        user_id: int,
        *,
        revoked_at: datetime,
    ) -> None:
        records = self.db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
        ).all()

        for record in records:
            record.revoked = True
            record.revoked_at = revoked_at
            self.db.add(record)

        self.db.commit()
