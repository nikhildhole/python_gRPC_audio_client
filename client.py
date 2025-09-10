import grpc
import chat_pb2
import chat_pb2_grpc

def chat():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = chat_pb2_grpc.ChatServiceStub(channel)

        def generate_messages():
            while True:
                msg = input("You: ")
                yield chat_pb2.ChatMessage(user="Client", message=msg)

        responses = stub.ChatStream(generate_messages())
        for response in responses:
            print(f"{response.user}: {response.message}")

if __name__ == "__main__":
    chat()
