import grpc
from concurrent import futures
import threading
import queue
import sounddevice as sd
import numpy as np
import voip_separate_pb2
import voip_separate_pb2_grpc
import time

event_queue = queue.Queue()  # Queue for sending events from CLI

class AudioService(voip_separate_pb2_grpc.AudioServiceServicer):
    def StreamAudio(self, request_iterator, context):
        for chunk in request_iterator:
            yield voip_separate_pb2.AudioChunk(
                data=chunk.data,
                sample_rate=chunk.sample_rate,
                channels=chunk.channels
            )

class EventService(voip_separate_pb2_grpc.EventServiceServicer):
    def StreamEvents(self, request_iterator, context):
        def send_cli_events():
            while True:
                evt = event_queue.get()
                yield evt

        # Start sending CLI events in another thread
        threading.Thread(target=send_cli_events, daemon=True).start()

        for event in request_iterator:
            print(f"[CLIENT EVENT RECEIVED] {event.type}: {event.data}")
            # Echo back the same event
            yield voip_separate_pb2.Event(type=event.type, data=event.data)

def cli_input_thread():
    while True:
        cmd = input("SERVER CLI EVENT> ")
        event_queue.put(voip_separate_pb2.Event(type=cmd, data="From server CLI"))

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
