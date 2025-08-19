import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("env/cloud-crypto-access-firebase-adminsdk-fbsvc-cb0114721f.json")
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