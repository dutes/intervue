from sqlalchemy import Column, String, Float, Text, JSON
from .database import Base

class InterviewSession(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    created_at = Column(Float)
    status = Column(String)
    job_spec = Column(Text)
    cv_text = Column(Text)
    provider = Column(String)
    start_round = Column(Float, default=1)
    overall_score = Column(Float, nullable=True)
    
    # JSON columns for complex data
    rubric = Column(JSON, nullable=True)
    persona = Column(JSON, nullable=True)
    cv_analysis = Column(JSON, nullable=True)
    questions = Column(JSON, default=list)
    answers = Column(JSON, default=list)
    scores = Column(JSON, default=list)
    logs = Column(JSON, default=list)
