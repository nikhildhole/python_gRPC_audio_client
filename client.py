import grpc
import threading
import queue
import sounddevice as sd
import numpy as np
import voip_separate_pb2
import voip_separate_pb2_grpc

RATE = 16000
CHANNELS = 1
CHUNK = 1024

audio_queue = queue.Queue()
event_queue = queue.Queue()

def record_audio():
    with sd.InputStream(samplerate=RATE, channels=CHANNELS, blocksize=CHUNK, dtype='int16') as mic:
        while True:
            data, _ = mic.read(CHUNK)
            audio_queue.put(data)

def audio_stream(stub):
    def gen_audio():
        while True:
            chunk = audio_queue.get()
            yield voip_separate_pb2.AudioChunk(
                data=chunk.tobytes(),
                sample_rate=RATE,
                channels=CHANNELS
            )

    try:
        responses = stub.StreamAudio(gen_audio())
        with sd.OutputStream(samplerate=RATE, channels=CHANNELS, blocksize=CHUNK, dtype='int16') as speaker:
            for chunk in responses:
                speaker.write(np.frombuffer(chunk.data, dtype='int16').reshape(-1, CHANNELS))
    except grpc.RpcError as e:
        print("Audio stream disconnected:", e)

def event_stream(stub):
    def gen_events():
        while True:
            evt = event_queue.get()
            yield evt

    try:
        responses = stub.StreamEvents(gen_events())
        for evt in responses:
            print(f"[SERVER EVENT] {evt.type}: {evt.data}")
    except grpc.RpcError as e:
        print("Event stream disconnected:", e)

def main():
    channel = grpc.insecure_channel('localhost:50051')
    audio_stub = voip_separate_pb2_grpc.AudioServiceStub(channel)
    event_stub = voip_separate_pb2_grpc.EventServiceStub(channel)

    threading.Thread(target=record_audio, daemon=True).start()
    threading.Thread(target=audio_stream, args=(audio_stub,), daemon=True).start()
    threading.Thread(target=event_stream, args=(event_stub,), daemon=True).start()

    try:
        while True:
            cmd = input("CLIENT CLI EVENT> ")
            event_queue.put(voip_separate_pb2.Event(type=cmd, data="From client CLI"))
    except EOFError:
        print("Input closed, exiting...")
    except KeyboardInterrupt:
        print("Exiting client...")

if __name__ == "__main__":
    main()
