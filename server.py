import grpc
from concurrent import futures
import threading
import queue
import time
import voip_separate_pb2
import voip_separate_pb2_grpc

server_event_queue = queue.Queue()  # For CLI events

class AudioService(voip_separate_pb2_grpc.AudioServiceServicer):
    def StreamAudio(self, request_iterator, context):
        """Echo back audio to the same client"""
        for chunk in request_iterator:
            yield chunk  # simply echo back

class EventService(voip_separate_pb2_grpc.EventServiceServicer):
    def StreamEvents(self, request_iterator, context):
        client_queue = queue.Queue()

        def send_server_events():
            while True:
                evt = server_event_queue.get()
                client_queue.put(evt)

        threading.Thread(target=send_server_events, daemon=True).start()

        # Thread to read client events
        def read_client_events():
            try:
                for evt in request_iterator:
                    print(f"[CLIENT EVENT] {evt.type}: {evt.data}")
            except grpc.RpcError:
                pass

        threading.Thread(target=read_client_events, daemon=True).start()

        # Yield server events to the client
        while True:
            evt = client_queue.get()
            yield evt

def cli_input_thread():
    while True:
        cmd = input("SERVER CLI EVENT> ")
        evt = voip_separate_pb2.Event(type=cmd, data="From server CLI")
        server_event_queue.put(evt)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    voip_separate_pb2_grpc.add_AudioServiceServicer_to_server(AudioService(), server)
    voip_separate_pb2_grpc.add_EventServiceServicer_to_server(EventService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server running on port 50051")

    threading.Thread(target=cli_input_thread, daemon=True).start()

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == "__main__":
    serve()
