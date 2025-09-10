import grpc
import voip_pb2
import voip_pb2_grpc
import threading
import pyaudio

# Audio config
RATE = 16000
CHUNK = 1024
CHANNELS = 1

def stream_audio(stub):
    audio = pyaudio.PyAudio()
    # Input stream (mic)
    stream_in = audio.open(format=pyaudio.paInt16,
                           channels=CHANNELS,
                           rate=RATE,
                           input=True,
                           frames_per_buffer=CHUNK)
    # Output stream (speaker)
    stream_out = audio.open(format=pyaudio.paInt16,
                            channels=CHANNELS,
                            rate=RATE,
                            output=True,
                            frames_per_buffer=CHUNK)

    def request_generator():
        while True:
            data = stream_in.read(CHUNK, exception_on_overflow=False)
            yield voip_pb2.VoIPMessage(audio=voip_pb2.AudioChunk(data=data, sample_rate=RATE, channels=CHANNELS))

    responses = stub.Stream(request_generator())

    for response in responses:
        if response.HasField("audio"):
            stream_out.write(response.audio.data)
        elif response.HasField("event"):
            print(f"Received event: {response.event.type} - {response.event.data}")

def send_events(stub):
    # Example: sending events from another thread
    while True:
        cmd = input("Event (END_CALL/ABC_EVENT): ")
        yield voip_pb2.VoIPMessage(event=voip_pb2.Event(type=cmd, data="Some data"))

def main():
    channel = grpc.insecure_channel('localhost:50051')
    stub = voip_pb2_grpc.VoIPServiceStub(channel)

    # Start audio streaming in thread
    threading.Thread(target=stream_audio, args=(stub,), daemon=True).start()

    # Start event sending in main thread
    for event_msg in send_events(stub):
        stub.Stream(iter([event_msg]))  # Send event to server

if __name__ == "__main__":
    main()
