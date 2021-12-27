from threading import Lock
from flask import Flask, render_template, session, request, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from ml_gym.backend.messaging.event_storage import ListEventStorage
from typing import List
from collections import defaultdict


class WebSocketServer:

    def __init__(self, port: int, async_mode: str, app: Flask):
        """[summary]

        Args:
            port (int): [description]
            async_mode (str): Set this variable to "threading", "eventlet" or "gevent" to test the
                              different async modes, or leave it set to None for the application to choose
                              the best option based on installed packages.
        """
        self._port = port
        self._socketio = SocketIO(app, async_mode=async_mode)
        self._client_sids = []
        self._room_event_storage = {}
        self._init_call_backs()

    def _register_callback_funs(self):
        self._socketio.on("join", self.on_join)
        self._socketio.on("leave", self.on_leave)
        self._socketio.on("mlgym_event", self.on_mlgym_event)
        self._socketio.on("ping", self.on_ping)
        self._socketio.on("client_connected", self.on_client_connected)
        self._socketio.on("client_disconnected", self.on_client_disconnected)

    def emit_server_log_message(self, data):
        emit("server_log_message", data)

    @property
    def client_sids(self) -> List[str]:
        return self._client_sids

    def _init_call_backs(self):

        @self._socketio.on("join")
        def on_join(data):
            self._client_sids.append(request.sid)
            if 'client_id' in data:
                client_id = data['client_id']
            else:
                client_id = "<unknown>"
            rooms_to_join = data['rooms']
            for room in rooms_to_join:
                if room not in self._room_event_storage:
                    self._room_event_storage[room] = ListEventStorage()
                join_room(room)
            print(f"Client {client_id} joined rooms: {rooms()}")
            self.emit_server_log_message(f"Client {client_id} joined rooms: {rooms()}")

        @self._socketio.on("leave")
        def on_leave():
            self._client_sids.remove(request.sid)
            # TODO  leave all rooms
            # leave_room(message['room'])
            self.emit_server_log_message("You are now disconnected.")
            disconnect()

        @self._socketio.on("mlgym_event")
        def on_mlgym_event(data):
            print("mlgym_event: " + str(data))
            emit('mlgym_event',
                 {'data': data},
                 to="mlgym_event_subscribers")

    # @socketio.event
    # def disconnect_request():
    #     @copy_current_request_context
    #     def can_disconnect():
    #         disconnect()

    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     # for this emit we use a callback function
    #     # when the callback function is invoked we know that the message has been
    #     # received and it is safe to disconnect
    #     emit('my_response',
    #          {'data': 'Disconnected!', 'count': session['receive_count']},
    #          callback=can_disconnect)

        @self._socketio.on("ping")
        def on_ping():
            emit('pong')

        @self._socketio.on("client_connected")
        def on_client_connected():
            print(f"Client with SID {request.sid} connnected.")
            self.emit_server_log_message(f"Client with SID {request.sid} connnected.")

        @self._socketio.on("client_disconnected")
        def on_client_disconnected():
            print('Client disconnected', request.sid)
            self._client_sids.remove(request.sid)

    def run(self, app: Flask):
        self._socketio.run(app)


if __name__ == '__main__':
    async_mode = None

    app = Flask(__name__, template_folder="/home/mluebberin/repositories/github/private_workspace/mlgym/src/ml_gym/backend/streaming/template")
    app.config['SECRET_KEY'] = 'secret!'

    # thread = socketio.start_background_task(background_thread, )
    port = 5000
    async_mode = None

    ws = WebSocketServer(port=port, async_mode=async_mode, app=app)

    @app.route('/')
    def index():
        return render_template('index.html', async_mode=ws._socketio.async_mode)

    @app.route('/status')
    def status():
        return render_template('status.html', async_mode=ws._socketio.async_mode)

    @app.route('/api/status')
    def api_status():
        client_sids = ws.client_sids
        room_key_to_sid = defaultdict(list)
        for client_sid in client_sids:
            room_keys = rooms(client_sid, "/")
            for room_key in room_keys:
                room_key_to_sid[room_key].append(client_sid)

        return {"clients": client_sids, "rooms": room_key_to_sid}

    ws.run(app)