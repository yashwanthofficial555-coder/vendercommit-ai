from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

T = TypeVar('T')
class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class APIResponse(BaseModel, Generic[T]):
    data: T
    meta: dict = Field(default_factory=dict)

class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(default='viewer', pattern='^(admin|procurement|viewer)$')

class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

class SupplierBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(default='', max_length=100)
    contact_name: str = Field(default='', max_length=120)
    email: EmailStr | str = Field(default='')
    phone: str = Field(default='', max_length=40)
    location: str = Field(default='', max_length=200)
    status: str = Field(default='active', pattern='^(active|inactive|onboarding|suspended)$')

    @field_validator('name', 'category', 'contact_name', 'phone', 'location')
    @classmethod
    def strip_text(cls, value): return value.strip()

class SupplierCreate(SupplierBase): pass
class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    contact_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | str | None = None
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, pattern='^(active|inactive|onboarding|suspended)$')

class SupplierOut(ORMModel):
    id: int
    name: str
    category: str
    contact_name: str
    email: str
    phone: str
    location: str
    status: str
    created_at: datetime
    updated_at: datetime
    reliability_score: float | None = None
    delivery_score: float | None = None
    risk_level: str = 'unknown'
    active_commitments: int = 0

class StatusUpdate(BaseModel):
    status: str = Field(pattern='^(active|inactive|onboarding|suspended)$')

class CommitmentBase(BaseModel):
    supplier_id: int = Field(gt=0)
    commitment_type: str = Field(pattern='^(price|delivery|quantity|quality|sla)$')
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(default='', max_length=10000)
    previous_value: Decimal | None = Field(default=None, ge=0)
    current_value: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default='USD', min_length=3, max_length=3)
    previous_quantity: Decimal | None = Field(default=None, ge=0)
    current_quantity: Decimal | None = Field(default=None, ge=0)
    unit: str = Field(default='', max_length=30)
    deadline: datetime | None = None
    previous_promise: str = Field(default='', max_length=10000)
    updated_promise: str = Field(default='', max_length=10000)
    quality_terms: str = Field(default='', max_length=10000)
    sla_target: float | None = Field(default=None, ge=0)
    sla_actual: float | None = Field(default=None, ge=0)
    status: str = Field(default='pending', pattern='^(pending|fulfilled|overdue|breached)$')

    @field_validator('currency')
    @classmethod
    def uppercase_currency(cls, value): return value.upper()

    @model_validator(mode='after')
    def validate_type_values(self):
        if self.commitment_type == 'price' and self.current_value is None:
            raise ValueError('current_value is required for price commitments')
        if self.commitment_type == 'quantity' and self.current_quantity is None:
            raise ValueError('current_quantity is required for quantity commitments')
        if self.commitment_type == 'delivery' and self.deadline is None:
            raise ValueError('deadline is required for delivery commitments')
        return self

class CommitmentCreate(CommitmentBase): pass
class CommitmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    previous_value: Decimal | None = Field(default=None, ge=0)
    current_value: Decimal | None = Field(default=None, ge=0)
    previous_quantity: Decimal | None = Field(default=None, ge=0)
    current_quantity: Decimal | None = Field(default=None, ge=0)
    deadline: datetime | None = None
    previous_promise: str | None = Field(default=None, max_length=10000)
    updated_promise: str | None = Field(default=None, max_length=10000)
    quality_terms: str | None = Field(default=None, max_length=10000)
    sla_target: float | None = Field(default=None, ge=0)
    sla_actual: float | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, pattern='^(pending|fulfilled|overdue|breached)$')

class CommitmentOut(ORMModel):
    id: int
    supplier_id: int
    commitment_type: str
    title: str
    description: str
    previous_value: Decimal | None
    current_value: Decimal | None
    currency: str
    previous_quantity: Decimal | None
    current_quantity: Decimal | None
    unit: str
    deadline: datetime | None
    previous_promise: str
    updated_promise: str
    quality_terms: str
    sla_target: float | None
    sla_actual: float | None
    status: str
    verified_at: datetime | None
    fulfilled_at: datetime | None
    verification_note: str
    created_by_id: int | None
    verified_by_id: int | None
    created_at: datetime
    updated_at: datetime
    savings: Decimal | None = None
    savings_percentage: float | None = None
    is_breached: bool = False

class VerificationRequest(BaseModel):
    note: str = Field(min_length=3, max_length=5000)

class InteractionBase(BaseModel):
    supplier_id: int = Field(gt=0)
    interaction_type: str = Field(pattern='^(call|email|meeting|delivery|note|negotiation)$')
    subject: str = Field(min_length=2, max_length=240)
    content: str = Field(min_length=1, max_length=50000)
    occurred_at: datetime | None = None

class InteractionCreate(InteractionBase): pass
class InteractionUpdate(BaseModel):
    interaction_type: str | None = Field(default=None, pattern='^(call|email|meeting|delivery|note|negotiation)$')
    subject: str | None = Field(default=None, min_length=2, max_length=240)
    content: str | None = Field(default=None, min_length=1, max_length=50000)
    occurred_at: datetime | None = None

class InteractionOut(ORMModel):
    id: int
    supplier_id: int
    author_id: int | None
    interaction_type: str
    subject: str
    content: str
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime

class MemoryCreate(BaseModel):
    supplier_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=50000)
    provenance: dict = Field(default_factory=dict)

class MemoryOut(ORMModel):
    id: int
    supplier_id: int
    content: str
    provenance: str
    sync_status: str
    retry_count: int
    last_error: str
    external_id: str
    created_at: datetime

class PerformanceOut(ORMModel):
    id: int
    supplier_id: int
    recorded_at: datetime
    reliability_score: float
    delivery_score: float | None
    risk_level: str
    fulfilled_count: int
    breached_count: int
