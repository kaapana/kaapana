from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import UniqueConstraint

class Base(SQLModel):
    pass


class DataSource(SQLModel, table=True):
    __tablename__ = "DataSources"

    id: Optional[int] = Field(default=None, primary_key=True)
    dcmweb_endpoint: str = Field(..., max_length=255)
    opensearch_index: str = Field(..., max_length=255)

    __table_args__ = (
        UniqueConstraint(
            "dcmweb_endpoint", "opensearch_index", name="uq_endpoint_project"
        ),
    )

