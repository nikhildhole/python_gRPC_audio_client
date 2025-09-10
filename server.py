import grpc
from concurrent import futures
import voip_pb2
import voip_pb2_grpc
import time

class VoIPService(voip_pb2_grpc.VoIPServiceServicer):
    def Stream(self, request_iterator, context):
        for message in request_iterator:
            if message.HasField("audio"):
                # Echo back audio
                audio_chunk = message.audio
                yield voip_pb2.VoIPMessage(audio=audio_chunk)
            elif message.HasField("event"):
                event = message.event
                print(f"Received event: {event.type}, data: {event.data}")
                # Example: echo back the event
                yield voip_pb2.VoIPMessage(event=event)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    voip_pb2_grpc.add_VoIPServiceServicer_to_server(VoIPService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("VoIP Server running on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == "__main__":
    serve()
