from typing import List
from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str = Field(
        description="The name of the entity, capitalized and standardized."
    )
    type: str = Field(
        description="The type of the entity (e.g., PERSON, ORGANIZATION, LOCATION, CONCEPT)."
    )
    description: str = Field(
        description="A brief description of the entity based on the text."
    )


class Relationship(BaseModel):
    source: str = Field(description="The name of the source entity.")
    target: str = Field(description="The name of the target entity.")
    predicate: str = Field(
        description="The relationship label/predicate connecting source to target (e.g., FOUNDED, LOCATED_IN)."
    )
    description: str = Field(
        description="Explanation of the relationship as supported by the text."
    )


class GraphExtractionResult(BaseModel):
    """The complete set of entities and relationships extracted from the document."""

    entities: List[Entity] = Field(
        description="List of all distinct entities found in the text."
    )
    relationships: List[Relationship] = Field(
        description="List of relationships connecting the extracted entities."
    )


class Quad(BaseModel):
    subject: str
    predicate: str
    object: str
    graph: str  # The context, document ID, or source chunk ID
