import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from database import SessionLocal
from models.models import POSSale, Restaurant, Company, User
import uuid

def test_duplicate_prevention():
    db = SessionLocal()
    try:
        # 1. Setup mock data
        company = db.query(Company).first()
        if not company:
            print("No company found, create one first.")
            return
            
        restaurant = db.query(Restaurant).filter(Restaurant.company_id == company.id).first()
        if not restaurant:
            print("No restaurant found.")
            return

        order_ref = f"TEST-DUP-{uuid.uuid4().hex[:6]}"
        print(f"Using Order Ref: {order_ref}")

        # 2. Insert initial data (Simulation of first upload)
        sale1 = POSSale(
            restaurant_id=restaurant.id,
            company_id=company.id,
            order_ref=order_ref,
            product_name="Pizza Test",
            quantity=1,
            price_with_tax=10.5
        )
        db.add(sale1)
        db.commit()
        print("Initial sale inserted.")

        # 3. Simulate "Clear and Replace" logic from upload_sales
        # (This is the code we are validating)
        order_refs_to_clear = {order_ref}
        
        print(f"Simulating re-upload. Clearing orders: {order_refs_to_clear}")
        
        # This is the exact query from admin.py
        db.query(POSSale).filter(
            POSSale.restaurant_id == restaurant.id,
            POSSale.order_ref.in_(list(order_refs_to_clear))
        ).delete(synchronize_session=False)
        
        # 4. Insert "new" data (Simulation of second upload)
        sale2 = POSSale(
            restaurant_id=restaurant.id,
            company_id=company.id,
            order_ref=order_ref, # Same ref
            product_name="Pizza Test (Updated)",
            quantity=2,
            price_with_tax=21.0
        )
        db.add(sale2)
        db.commit()
        print("Replacement sale inserted.")

        # 5. Validate
        count = db.query(POSSale).filter(
            POSSale.restaurant_id == restaurant.id,
            POSSale.order_ref == order_ref
        ).count()
        
        print(f"Found {count} records with ref {order_ref}")
        if count == 1:
            print("SUCCESS: Old data was cleared, only 1 record exists.")
            # Check if it's the new one
            latest = db.query(POSSale).filter(POSSale.order_ref == order_ref).first()
            if latest.quantity == 2:
                print("SUCCESS: The existing record is the NEW one.")
            else:
                print("FAILURE: The existing record is the OLD one!")
        else:
            print(f"FAILURE: Expected 1 record, found {count}. Duplicates exist!")

    finally:
        # Cleanup
        db.query(POSSale).filter(POSSale.order_ref.like("TEST-DUP-%")).delete(synchronize_session=False)
        db.commit()
        db.close()

if __name__ == "__main__":
    test_duplicate_prevention()
