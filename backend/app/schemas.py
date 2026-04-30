from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentSummary(BaseModel):
    id: int
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    summary: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentDetail(DocumentSummary):
    extracted_text: str | None


class DocumentStatus(BaseModel):
    id: int
    status: str
    error: str | None


class SearchHit(BaseModel):
    document_id: int
    filename: str
    snippet: str
    score: float


class ChatSummary(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class Citation(BaseModel):
    document_id: int
    filename: str
    chunk_ordinal: int
    snippet: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    citations: list[Citation] = []
    created_at: datetime


class ChatDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: list[MessageResponse]


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class CreateChatRequest(BaseModel):
    title: str | None = None


class TransactionLineResponse(BaseModel):
    id: int
    ordinal: int
    posted_date: str | None
    description: str
    category: str | None
    direction: str
    amount: float
    balance_after: float | None
    source_format: str

    class Config:
        from_attributes = True


class TransactionExtreme(BaseModel):
    description: str
    posted_date: str | None
    amount: float


class TransactionStats(BaseModel):
    count_total: int
    count_debits: int
    count_credits: int
    total_debits: float
    total_credits: float
    net: float
    max_debit: TransactionExtreme | None
    max_credit: TransactionExtreme | None
    min_debit: TransactionExtreme | None
    min_credit: TransactionExtreme | None


class TransactionsResponse(BaseModel):
    document_id: int
    source_format: str | None
    stats: TransactionStats
    lines: list[TransactionLineResponse]
