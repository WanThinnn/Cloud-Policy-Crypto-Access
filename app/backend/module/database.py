import firebase_admin
from firebase_admin import credentials, firestore
import os

# Get the directory of this file and construct path to the Firebase key
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
firebase_key_path = os.path.join(backend_dir, "env", "cloud-crypto-access-firebase-adminsdk-fbsvc-cb0114721f.json")

cred = credentials.Certificate(firebase_key_path)
firebase_admin.initialize_app(cred)
# Kết nối tới Firestore
db = firestore.client()

# Ví dụ: thêm một document
doc_ref = db.collection("users").document("user_001")
doc_ref.set({
    "name": "Thiên",
    "age": 21,
    "email": "thien@example.com"
})

# Ví dụ: đọc document
user_doc = db.collection("users").document("user_001").get()
if user_doc.exists:
    print(user_doc.to_dict())
else:
    print("Document không tồn tại")