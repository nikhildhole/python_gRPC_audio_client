import grpc
from concurrent import futures
import threading
import queue
import time
import voip_separate_pb2
import voip_separate_pb2_grpc
import uuid  # for unique client IDs

# -------------------------
# Global client management
# -------------------------
connected_clients = {}  # key: client_id (str), value: client_queue
client_lock = threading.Lock()  # for thread-safe access

# -------------------------
# Audio Service
# -------------------------
class AudioService(voip_separate_pb2_grpc.AudioServiceServicer):
    def StreamAudio(self, request_iterator, context):
        """Echo back audio to the same client"""
        for chunk in request_iterator:
            yield chunk  # simply echo back

# -------------------------
# Event Service
# -------------------------
class EventService(voip_separate_pb2_grpc.EventServiceServicer):
    def StreamEvents(self, request_iterator, context):
        client_id = str(uuid.uuid4())
        client_queue = queue.Queue()

        # Register client
        with client_lock:
            connected_clients[client_id] = client_queue
            print(f"[SERVER] Client connected: {client_id}")

        # Send initial CLIENT_ID event
        client_queue.put(voip_separate_pb2.Event(type="CLIENT_ID", data=client_id))

        # Thread to read client events
        def read_client_events():
            try:
                for evt in request_iterator:
                    print(f"[CLIENT EVENT] {client_id} - {evt.type}: {evt.data}")
            except Exception:
                pass
            finally:
                with client_lock:
                    connected_clients.pop(client_id, None)
                    print(f"[SERVER] Client disconnected: {client_id}")

        threading.Thread(target=read_client_events, daemon=True).start()

        # Yield events to client
        while True:
            evt = client_queue.get()
            yield evt


# -------------------------
# Send event to a specific client
# -------------------------
def send_event_to_client(target_client_id, event_type, event_data):
    evt = voip_separate_pb2.Event(type=event_type, data=event_data)
    with client_lock:
        client_queue = connected_clients.get(target_client_id)
        if client_queue:
            client_queue.put(evt)
            print(f"[SERVER] Sent event to {target_client_id}")
        else:
            print(f"[SERVER] Client {target_client_id} not connected")

# -------------------------
# CLI Thread
# -------------------------
def cli_input_thread():
    while True:
        print("\n--- Connected Clients ---")
        with client_lock:
            if connected_clients:
                for cid in connected_clients:
                    print(f"  {cid}")
            else:
                print("  No clients connected")

        cmd = input("Enter event type to send> ")
        target_client_id = input("Enter target client ID> ")
        send_event_to_client(target_client_id, cmd, "From server CLI")

# -------------------------
# Serve gRPC Server
# -------------------------
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    voip_separate_pb2_grpc.add_AudioServiceServicer_to_server(AudioService(), server)
    voip_separate_pb2_grpc.add_EventServiceServicer_to_server(EventService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server running on port 50051")

    # Start CLI thread
    threading.Thread(target=cli_input_thread, daemon=True).start()

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)
        print("Server stopped")

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    serve()
