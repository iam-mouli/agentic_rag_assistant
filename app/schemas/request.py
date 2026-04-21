from pydantic import BaseModel, Field
from config.constants import MIN_QUERY_LENGTH, MAX_QUERY_LENGTH


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=MIN_QUERY_LENGTH, max_length=MAX_QUERY_LENGTH)
