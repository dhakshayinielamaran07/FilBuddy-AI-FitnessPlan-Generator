from typing import Literal

from pydantic import BaseModel, Field, field_validator

Goal = Literal["weight loss", "muscle gain", "general wellness", "flexibility"]
Intensity = Literal["low", "medium", "high"]


class UserInput(BaseModel):
    user_id: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=13, le=100)
    weight: float = Field(gt=20, le=400)
    goal: Goal
    intensity: Intensity

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Name cannot be empty")
        return value


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    feedback: str = Field(min_length=3, max_length=2000)


class PlanResponse(BaseModel):
    user_id: str
    name: str
    goal: str
    intensity: str
    workout_plan: str
    nutrition_tip: str
