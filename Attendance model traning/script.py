import cv2
import numpy as np
import mediapipe as mp
import json
from insightface.app import FaceAnalysis
import math
import os

# -----------------------------
# Configuration
# -----------------------------
STUDENT_NAME = "Yash"
STUDENT_ID = "S001"
EMBEDDING_FILE = "Yash_embeddings.npy"
METADATA_FILE = "Yash_metadata.json"
MODEL_ROOT = './antelopev'  # Local path to antelopev2 models
TEACHER_IMAGE_PATH = "teacher/class_photo.jpg"
SIMILARITY_THRESHOLD = 0.35  # Cosine similarity threshold for recognition

YAW_THRESHOLD = 15
PITCH_THRESHOLD = 10

# -----------------------------
# Initialize InsightFace
# -----------------------------
# Using buffalo_l model which is more stable and reliable
print("Initializing InsightFace with buffalo_l model...")
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
print("InsightFace initialized successfully!")

# -----------------------------
# Initialize MediaPipe FaceMesh
# -----------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False,
                                  max_num_faces=1,
                                  refine_landmarks=True,
                                  min_detection_confidence=0.5,
                                  min_tracking_confidence=0.5)

# -----------------------------
# Utility functions
# -----------------------------
def calculate_head_pose(landmarks, image_shape):
    image_h, image_w = image_shape[:2]
    nose = np.array([landmarks[1].x * image_w, landmarks[1].y * image_h])
    left_eye = np.array([landmarks[33].x * image_w, landmarks[33].y * image_h])
    right_eye = np.array([landmarks[263].x * image_w, landmarks[263].y * image_h])

    eye_dx = right_eye[0] - left_eye[0]
    eye_dy = right_eye[1] - left_eye[1]
    yaw = math.degrees(math.atan2(eye_dy, eye_dx))

    eye_center = (left_eye + right_eye) / 2
    nose_dy = nose[1] - eye_center[1]
    nose_dx = nose[0] - eye_center[0]
    pitch = math.degrees(math.atan2(nose_dy, nose_dx))

    return yaw, pitch

def detect_orientation(yaw, pitch):
    if yaw < -YAW_THRESHOLD:
        return "left"
    elif yaw > YAW_THRESHOLD:
        return "right"
    elif pitch < -PITCH_THRESHOLD:
        return "up"
    elif pitch > PITCH_THRESHOLD:
        return "down"
    else:
        return "front"

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# -----------------------------
# Capture embeddings
# -----------------------------
collected_embeddings = {}
angles_captured = set()
angle_order = ["front", "left", "right", "up", "down"]

cap = cv2.VideoCapture(0)
capture_started = False

print("Press 'c' to start capturing your face embeddings")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    display_frame = frame.copy()
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    mp_results = face_mesh.process(rgb_frame)
    current_orientation = None

    if mp_results.multi_face_landmarks:
        landmarks = mp_results.multi_face_landmarks[0].landmark
        yaw, pitch = calculate_head_pose(landmarks, frame.shape)
        current_orientation = detect_orientation(yaw, pitch)
        if capture_started and current_orientation not in angles_captured:
            faces = app.get(frame)
            if len(faces) > 0:
                embedding = faces[0].normed_embedding
                collected_embeddings[current_orientation] = embedding
                angles_captured.add(current_orientation)
                print(f"Captured {current_orientation} embedding")

        # Draw bounding box
        for face in app.get(frame):
            x1, y1, x2, y2 = map(int, face.bbox)
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, f"{current_orientation if current_orientation else ''}", (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # Display instructions
    if not capture_started:
        cv2.putText(display_frame, "Press 'c' to START capturing", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
    else:
        cv2.putText(display_frame, f"Please turn your face: {','.join([a for a in angle_order if a not in angles_captured])}",
                    (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

    cv2.imshow("Face Capture & Recognition", display_frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'):
        capture_started = True
        print("Capture started...")

    if capture_started and len(angles_captured) == 5:
        print("All orientations captured!")
        break

cap.release()
cv2.destroyAllWindows()

# -----------------------------
# Save embeddings and metadata
# -----------------------------
emb_list = []
for angle in angle_order:
    if angle in collected_embeddings:
        emb_list.append(collected_embeddings[angle])
    else:
        emb_list.append(np.zeros(512))  # placeholder if missing

emb_array = np.array(emb_list)
np.save(EMBEDDING_FILE, emb_array)

metadata = {
    "name": STUDENT_NAME,
    "student_id": STUDENT_ID,
    "angles": angle_order,
    "embedding_file": EMBEDDING_FILE
}

with open(METADATA_FILE, "w") as f:
    json.dump(metadata, f, indent=4)

print(f"Saved embeddings to {EMBEDDING_FILE} and metadata to {METADATA_FILE}")

# -----------------------------
# Recognition
# -----------------------------
teacher_img = cv2.imread(TEACHER_IMAGE_PATH)
teacher_faces = app.get(teacher_img)
if len(teacher_faces) == 0:
    print("No face detected in teacher image")
else:
    teacher_embedding = teacher_faces[0].normed_embedding
    # Compare with student embedding (average of 5 angles)
    student_avg_embedding = np.mean(emb_array, axis=0)
    similarity = cosine_similarity(student_avg_embedding, teacher_embedding)
    print(f"Similarity with student {STUDENT_NAME}: {similarity:.3f}")
    if similarity > SIMILARITY_THRESHOLD:
        print(f"{STUDENT_NAME} is present in teacher image!")
    else:
        print(f"{STUDENT_NAME} not recognized in teacher image.")
