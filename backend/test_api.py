import requests
import json

API_URL = "http://localhost:8000"

def test_products():
    # We need a token. Let's try to login as admin@lacesta
    try:
        res = requests.post(f"{API_URL}/auth/login", data={"username": "restaurante@lacestalocal", "password": "restaurante"})
        if res.status_code != 200:
            print(f"Login failed: {res.text}")
            return
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        res = requests.get(f"{API_URL}/requisitions/products", headers=headers)
        if res.status_code == 200:
            products = res.json()
            print(f"Total products: {len(products)}")
            if products:
                print("First product keys:", products[0].keys())
                print("First product group_id:", products[0].get("group_id"))
                groups = {p.get("group_id") for p in products}
                print("Unique group_ids in products:", groups)
        else:
            print(f"Failed to get products: {res.text}")
            
        res = requests.get(f"{API_URL}/requisitions/product-groups", headers=headers)
        if res.status_code == 200:
            groups = res.json()
            print(f"Total groups: {len(groups)}")
            if groups:
                print("First group keys:", groups[0].keys())
                print("Group IDs:", [g.get("id") for g in groups])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_products()
