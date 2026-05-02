from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
from models.models import User, Restaurant, NPSQuestion, NPSSurveyResponse, NPSSurveyAnswer, SystemSetting
from dependencies import get_current_user

router = APIRouter(prefix="/nps", tags=["nps"])

class AnswerItem(BaseModel):
    question_id: int
    answer_text: str

class SurveySubmission(BaseModel):
    receipt_ref: str
    answers: List[AnswerItem]

@router.get("/survey-questions")
def get_survey_questions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "Restaurant":
        raise HTTPException(403, "Only restaurant users can access surveys")
    
    # Get active questions for the company
    questions = db.query(NPSQuestion).filter(
        NPSQuestion.company_id == current_user.company_id,
        NPSQuestion.is_active == True
    ).order_by(NPSQuestion.display_order).all()

    # Fetch settings
    ty_msg = db.query(SystemSetting).filter(SystemSetting.company_id == current_user.company_id, SystemSetting.setting_key == "nps_thank_you_message").first()
    brand_name = db.query(SystemSetting).filter(SystemSetting.company_id == current_user.company_id, SystemSetting.setting_key == "brand_name").first()
    primary_color = db.query(SystemSetting).filter(SystemSetting.company_id == current_user.company_id, SystemSetting.setting_key == "primary_color").first()
    logo_url = db.query(SystemSetting).filter(SystemSetting.company_id == current_user.company_id, SystemSetting.setting_key == "logo_url").first()

    return {
        "questions": questions,
        "thank_you_message": ty_msg.setting_value if ty_msg else "Your feedback has been successfully recorded.",
        "branding": {
            "brand_name": brand_name.setting_value if brand_name else "",
            "primary_color": primary_color.setting_value if primary_color else "#2563eb",
            "logo_url": logo_url.setting_value if logo_url else ""
        }
    }

@router.post("/submit-survey")
def submit_survey(payload: SurveySubmission, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "Restaurant":
        raise HTTPException(403, "Only restaurant users can submit surveys")
    
    if not current_user.restaurant_id:
        raise HTTPException(400, "User not assigned to a restaurant")

    # 1. Create response
    response = NPSSurveyResponse(
        restaurant_id=current_user.restaurant_id,
        receipt_ref=payload.receipt_ref
    )
    db.add(response)
    db.flush() # Get response.id

    # 2. Create answers
    for item in payload.answers:
        ans = NPSSurveyAnswer(
            response_id=response.id,
            question_id=item.question_id,
            answer_text=item.answer_text
        )
        db.add(ans)
    
    db.commit()
    return {"status": "success", "message": "Survey submitted"}
