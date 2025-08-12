import os
import uuid
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room

# ---------------- App Setup ---------------- #
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# ---------------- Homepage Route ---------------- #
@app.route("/")
def home():
    return jsonify({
        "status": "🔥 Student Video Room Backend is Running!",
        "socket": "Connected via Socket.IO",
        "api_test": "/api/test"
    })

# ---------------- Test API ---------------- #
@app.route("/api/test", methods=["GET"])
def test_api():
    return jsonify({"message": "✅ API is working!"})

# ---------------- Verify Token API (Dummy for now) ---------------- #
@app.route("/api/verify-token", methods=["POST"])
def verify_token():
    data = request.get_json()
    token = data.get("token")

    # Temporarily skip Firebase validation
    if not token:
        return jsonify({"error": "No token provided"}), 400

    return jsonify({"message": "Token received (dummy verify)", "token": token})

# ---------------- Matchmaking Logic ---------------- #
waiting_users = []
rooms = {}  # room_id: [user1, user2]

@socketio.on("join_queue")
def handle_join(data=None):
    user_id = request.sid
    waiting_users.append(user_id)
    print(f"User {user_id} joined queue")

    # If 2+ users waiting, match them
    if len(waiting_users) >= 2:
        user1 = waiting_users.pop(0)
        user2 = waiting_users.pop(0)

        room_id = str(uuid.uuid4())
        rooms[room_id] = [user1, user2]

        join_room(room_id, sid=user1)
        join_room(room_id, sid=user2)

        emit("matched", {"room_id": room_id}, to=user1)
        emit("matched", {"room_id": room_id}, to=user2)

@socketio.on("offer")
def handle_offer(data):
    room_id = data.get("room_id")
    emit("offer", data, room=room_id, include_self=False)

@socketio.on("answer")
def handle_answer(data):
    room_id = data.get("room_id")
    emit("answer", data, room=room_id, include_self=False)

@socketio.on("ice-candidate")
def handle_ice_candidate(data):
    room_id = data.get("room_id")
    emit("ice-candidate", data, room=room_id, include_self=False)

@socketio.on("disconnect")
def handle_disconnect():
    user_id = request.sid
    if user_id in waiting_users:
        waiting_users.remove(user_id)

    for room_id, users in list(rooms.items()):
        if user_id in users:
            users.remove(user_id)
            emit("partner_left", room=room_id)
            if not users:
                del rooms[room_id]
            break

# ---------------- Server Start ---------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🔥 Starting Student Video Room Backend on port {port}...")
    socketio.run(app, host="0.0.0.0", port=port)
