import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, Text

from app.db.database import Base


class ProcessedDocument(Base):
    __tablename__ = "processed_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, index=True, nullable=False)
    document_type = Column(String, nullable=False)
    status = Column(String, nullable=False)  # SUCCESS | FAILED
    file_validation = Column(JSON, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    validations = Column(JSON, nullable=True)
    processing_metadata = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    processed_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
