"""
SQLAlchemy ORM models for the public Steam schema.

Schema reference: back_end/SCHEMA_DOCUMENTATION.md (section 1).

The column names and types mirror the Supabase tables exactly so that
the existing schema (managed via SQL scripts) continues to work without
modification. These classes are read-only from the AI's perspective:
the model can query through `db_service` but must not mutate data.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Game(Base):
    """
    Maps to the public.games table (Steam game metadata).

    Array-like data (publishers, developers, genres, ...) is stored as a
    flattened comma-separated text string in the database, matching the
    schema documentation.
    """

    __tablename__ = "games"

    steam_appid: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    supported_languages: Mapped[Optional[str]] = mapped_column(Text)
    required_age: Mapped[int] = mapped_column(Integer, default=0)
    release_date: Mapped[Optional[date]] = mapped_column(Date)
    publishers: Mapped[Optional[str]] = mapped_column(Text)
    developers: Mapped[Optional[str]] = mapped_column(Text)
    categories: Mapped[Optional[str]] = mapped_column(Text)
    genres: Mapped[Optional[str]] = mapped_column(Text)
    price_text: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )

    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="game", cascade="all, delete-orphan"
    )


class SteamUser(Base):
    """
    Maps to the public.users table (Steam users extracted from reviews).

    Note: named SteamUser to avoid clashing with the application's own
    user/auth tables (app_users).
    """

    __tablename__ = "users"

    steamid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    personaname: Mapped[Optional[str]] = mapped_column(Text)
    num_games_owned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )

    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="user", cascade="all, delete-orphan"
    )


class Review(Base):
    """Maps to the public.reviews table (user reviews and playtime stats)."""

    __tablename__ = "reviews"

    recommendationid: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    steam_appid: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.steam_appid", ondelete="CASCADE"),
        nullable=False,
    )
    steamid: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.steamid", ondelete="CASCADE"),
        nullable=False,
    )
    language: Mapped[Optional[str]] = mapped_column(Text)
    review_text: Mapped[Optional[str]] = mapped_column(Text)
    timestamp_created: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    timestamp_updated: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    refunded: Mapped[bool] = mapped_column(Boolean, default=False)
    received_for_free: Mapped[bool] = mapped_column(Boolean, default=False)
    written_during_early_access: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    primarily_steam_deck: Mapped[bool] = mapped_column(Boolean, default=False)
    playtime_at_review: Mapped[int] = mapped_column(Integer, default=0)
    playtime_last_two_weeks: Mapped[int] = mapped_column(Integer, default=0)
    playtime_forever: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )

    game: Mapped["Game"] = relationship("Game", back_populates="reviews")
    user: Mapped["SteamUser"] = relationship("SteamUser", back_populates="reviews")
