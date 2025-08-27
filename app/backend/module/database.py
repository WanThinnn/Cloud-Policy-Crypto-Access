import firebase_admin
from firebase_admin import credentials, firestore
import os

# Get the directory of this file and construct path to the Firebase key
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
firebase_key_path = os.path.join(backend_dir, "env", "cloud-firestore-crypto-access.json")

cred = credentials.Certificate(firebase_key_path)
firebase_admin.initialize_app(cred)
# Kết nối tới Firestore
db = firestore.client()

for collection in db.collections():
    print(collection.id)
