from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='viewer', index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Supplier(Base, TimestampMixin):
    __tablename__ = 'suppliers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    normalized_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(100), default='', index=True)
    contact_name: Mapped[str] = mapped_column(String(120), default='')
    email: Mapped[str] = mapped_column(String(320), default='', index=True)
    phone: Mapped[str] = mapped_column(String(40), default='')
    location: Mapped[str] = mapped_column(String(200), default='')
    status: Mapped[str] = mapped_column(String(20), default='active', index=True)
    commitments: Mapped[list['Commitment']] = relationship(back_populates='supplier', cascade='all, delete-orphan')
    interactions: Mapped[list['Interaction']] = relationship(back_populates='supplier', cascade='all, delete-orphan')

class Commitment(Base, TimestampMixin):
    __tablename__ = 'commitments'
    __table_args__ = (Index('ix_commitment_supplier_status', 'supplier_id', 'status'), Index('ix_commitment_deadline_status', 'deadline', 'status'))
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id', ondelete='CASCADE'), index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    verified_by_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    commitment_type: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default='')
    previous_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    current_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default='USD')
    previous_quantity: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    current_quantity: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str] = mapped_column(String(30), default='')
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    previous_promise: Mapped[str] = mapped_column(Text, default='')
    updated_promise: Mapped[str] = mapped_column(Text, default='')
    quality_terms: Mapped[str] = mapped_column(Text, default='')
    sla_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    sla_actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_note: Mapped[str] = mapped_column(Text, default='')
    supplier: Mapped[Supplier] = relationship(back_populates='commitments')

class Interaction(Base, TimestampMixin):
    __tablename__ = 'interactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id', ondelete='CASCADE'), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    interaction_type: Mapped[str] = mapped_column(String(20), index=True)
    subject: Mapped[str] = mapped_column(String(240))
    content: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    supplier: Mapped[Supplier] = relationship(back_populates='interactions')

class PerformanceHistory(Base):
    __tablename__ = 'supplier_performance_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id', ondelete='CASCADE'), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    reliability_score: Mapped[float] = mapped_column(Float)
    delivery_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20))
    fulfilled_count: Mapped[int] = mapped_column(Integer, default=0)
    breached_count: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint('supplier_id', 'recorded_at', name='uq_performance_snapshot'),)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(60), default='')
    details: Mapped[str] = mapped_column(Text, default='{}')
    ip_address: Mapped[str] = mapped_column(String(64), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class MemoryItem(Base, TimestampMixin):
    __tablename__ = 'memory_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id', ondelete='CASCADE'), index=True)
    content: Mapped[str] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(Text, default='{}')
    sync_status: Mapped[str] = mapped_column(String(20), default='local_only', index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default='')
    external_id: Mapped[str] = mapped_column(String(200), default='')
