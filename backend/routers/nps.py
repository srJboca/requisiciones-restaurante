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

@router.get("/report")
def get_nps_report(
    restaurant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["CompanyAdmin", "Admin", "SuperAdmin"]:
        raise HTTPException(403, "Not authorized to view reports")

    query = db.query(NPSSurveyResponse).join(Restaurant).filter(Restaurant.company_id == current_user.company_id)
    
    if restaurant_id:
        query = query.filter(NPSSurveyResponse.restaurant_id == restaurant_id)
    
    responses = query.order_by(NPSSurveyResponse.created_at.desc()).all()
    
    # Calculate stats
    total = len(responses)
    promoters = 0
    passives = 0
    detractors = 0
    
    # Get all questions for this company to headers
    questions_meta = db.query(NPSQuestion).filter(
        NPSQuestion.company_id == current_user.company_id
    ).order_by(NPSQuestion.display_order).all()
    
    score_q_ids = [q.id for q in questions_meta if q.question_type == 'score']
    
    # Map results
    results = []
    for r in responses:
        ans_data = {}
        score_val = None
        for a in r.answers:
            ans_data[str(a.question_id)] = a.answer_text
            if a.question_id in score_q_ids:
                try:
                    # Take the first score question found as the NPS score
                    if score_val is None:
                        score_val = int(a.answer_text)
                except:
                    pass
        
        if score_val is not None:
            if score_val >= 9: promoters += 1
            elif score_val >= 7: passives += 1
            else: detractors += 1
            
        results.append({
            "id": r.id,
            "restaurant_name": r.restaurant.name,
            "receipt_ref": r.receipt_ref,
            "created_at": r.created_at,
            "score": score_val,
            "answers": ans_data
        })

    nps_score = 0
    if total > 0:
        nps_score = ((promoters / total) - (detractors / total)) * 100

    return {
        "summary": {
            "total": total,
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors,
            "nps_score": round(nps_score, 1)
        },
        "questions": [
            {"id": q.id, "text": q.question_text, "type": q.question_type} 
            for q in questions_meta
        ],
        "responses": results
    }
