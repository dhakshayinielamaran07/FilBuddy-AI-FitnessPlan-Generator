from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import get_settings
from .database import get_db
from .models import User, WorkoutPlan
from .schemas import FeedbackRequest, UserInput
from .services.gemini_service import (
    GeminiServiceError,
    generate_nutrition_tip_with_flash,
    generate_workout_gemini,
    update_workout_plan,
)

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
settings = get_settings()


def _get_user(db: Session, user_code: str) -> User | None:
    return db.scalar(select(User).where(User.user_code == user_code).options(selectinload(User.plans)))


def _get_or_create_user(db: Session, data: UserInput) -> User:
    user = _get_user(db, data.user_id)
    if user:
        user.name = data.name
        user.age = data.age
        user.weight_kg = data.weight
        user.goal = data.goal
        user.intensity = data.intensity
    else:
        user = User(
            user_code=data.user_id,
            name=data.name,
            age=data.age,
            weight_kg=data.weight,
            goal=data.goal,
            intensity=data.intensity,
        )
        db.add(user)
        db.flush()
    return user


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"error": None})


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout(
    request: Request,
    user_id: str = Form(...),
    name: str = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        data = UserInput(user_id=user_id, name=name, age=age, weight=weight, goal=goal, intensity=intensity)
        user = _get_or_create_user(db, data)
        workout = generate_workout_gemini(**data.model_dump(exclude={"user_id"}, by_alias=False))
        tip = generate_nutrition_tip_with_flash(data.goal)
        plan = WorkoutPlan(user_id=user.id, original_plan=workout, nutrition_tip=tip)
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "user": user,
                "plan": plan,
                "workout_plan": workout,
                "nutrition_tip": tip,
                "error": None,
                "message": None,
            },
        )
    except (ValueError, GeminiServiceError) as exc:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"error": str(exc)},
            status_code=400 if isinstance(exc, ValueError) else 503,
        )


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db),
):
    feedback = feedback.strip()
    if not feedback or len(feedback) > settings.max_feedback_length:
        raise HTTPException(status_code=400, detail=f"Feedback must be 3–{settings.max_feedback_length} characters.")

    user = _get_user(db, user_id)
    if not user or not user.plans:
        raise HTTPException(status_code=404, detail="User or workout plan not found.")

    plan = user.plans[-1]
    try:
        revised = update_workout_plan(plan.original_plan, feedback, user.goal, user.intensity)
        plan.updated_plan = revised
        plan.feedback = feedback
        plan.nutrition_tip = generate_nutrition_tip_with_flash(user.goal)
        db.commit()
        db.refresh(plan)
    except GeminiServiceError as exc:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={"user": user, "plan": plan, "workout_plan": plan.original_plan, "nutrition_tip": plan.nutrition_tip, "error": str(exc), "message": None},
            status_code=503,
        )

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={"user": user, "plan": plan, "workout_plan": revised, "nutrition_tip": plan.nutrition_tip, "error": None, "message": "Your plan was updated successfully."},
    )


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request, db: Session = Depends(get_db)):
    users = db.scalars(select(User).options(selectinload(User.plans)).order_by(User.created_at.desc())).unique().all()
    return templates.TemplateResponse(request=request, name="all_users.html", context={"users": users})


@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "mock_ai": settings.mock_ai}


@router.post("/api/plans")
def api_generate_plan(data: UserInput, db: Session = Depends(get_db)):
    try:
        user = _get_or_create_user(db, data)
        workout = generate_workout_gemini(data.name, data.age, data.weight, data.goal, data.intensity)
        tip = generate_nutrition_tip_with_flash(data.goal)
        plan = WorkoutPlan(user_id=user.id, original_plan=workout, nutrition_tip=tip)
        db.add(plan)
        db.commit()
        return {"user_id": data.user_id, "name": data.name, "goal": data.goal, "intensity": data.intensity, "workout_plan": workout, "nutrition_tip": tip}
    except GeminiServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/plans/{user_id}/feedback")
def api_update_plan(user_id: str, data: FeedbackRequest, db: Session = Depends(get_db)):
    if data.user_id != user_id:
        raise HTTPException(status_code=400, detail="Path user_id and body user_id must match")
    user = _get_user(db, user_id)
    if not user or not user.plans:
        raise HTTPException(status_code=404, detail="User or workout plan not found")
    plan = user.plans[-1]
    try:
        revised = update_workout_plan(plan.original_plan, data.feedback, user.goal, user.intensity)
        plan.updated_plan = revised
        plan.feedback = data.feedback
        plan.nutrition_tip = generate_nutrition_tip_with_flash(user.goal)
        db.commit()
        return {"user_id": user.user_code, "updated_plan": revised, "nutrition_tip": plan.nutrition_tip}
    except GeminiServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/users")
def api_users(db: Session = Depends(get_db)):
    users = db.scalars(select(User).options(selectinload(User.plans)).order_by(User.created_at.desc())).unique().all()
    return [
        {
            "id": user.id,
            "user_id": user.user_code,
            "name": user.name,
            "age": user.age,
            "weight_kg": user.weight_kg,
            "goal": user.goal,
            "intensity": user.intensity,
            "plans": [
                {"id": p.id, "original_plan": p.original_plan, "updated_plan": p.updated_plan, "feedback": p.feedback, "nutrition_tip": p.nutrition_tip}
                for p in user.plans
            ],
        }
        for user in users
    ]


@router.get("/api/users/{user_id}")
def api_user(user_id: str, db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "user_id": user.user_code,
        "name": user.name,
        "age": user.age,
        "weight_kg": user.weight_kg,
        "goal": user.goal,
        "intensity": user.intensity,
        "plans": [
            {"id": p.id, "original_plan": p.original_plan, "updated_plan": p.updated_plan, "feedback": p.feedback, "nutrition_tip": p.nutrition_tip}
            for p in user.plans
        ],
    }


@router.delete("/api/users/{user_id}")
def api_delete_user(user_id: str, db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
