from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class ChannelVisits(Base):
    __tablename__ = 'channelVisits'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_te: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    user_actions: Mapped[int] = mapped_column(Integer, nullable=False)
