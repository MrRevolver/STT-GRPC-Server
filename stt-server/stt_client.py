#!/usr/bin/env python3

import argparse
import grpc

import stt_service_pb2
import stt_service_pb2_grpc

server  = 'localhost:5001'

ssl = True # Use SSL for connection  

CHUNK_SIZE = 4000

def gen(audio_file_name):

    specification = stt_service_pb2.RecognitionSpec(
        partial_results=True,          # Get partial results
        audio_encoding='LINEAR16_PCM',
        sample_rate_hertz=16000,
        enable_word_time_offsets=True,
        max_alternatives=5,
        automatic_punctuation=True,    # Use punctuation marks
        raw_results=True,              # Convert numeral words to numbers
    )
    streaming_config = stt_service_pb2.RecognitionConfig(specification=specification)

    yield stt_service_pb2.StreamingRecognitionRequest(config=streaming_config)

    with open(audio_file_name, 'rb') as f:
        data = f.read(CHUNK_SIZE)
        while data != b'':
            yield stt_service_pb2.StreamingRecognitionRequest(audio_content=data)
            data = f.read(CHUNK_SIZE)


def run(audio_file_name):

    if ssl:
        with open('certificate.pem') as f:
           certificate_chain = f.read().encode()
        client_creds = grpc.ssl_channel_credentials (certificate_chain)
        channel = grpc.secure_channel(server, client_creds)
    else:
        channel = grpc.insecure_channel(server)
        
    stub = stt_service_pb2_grpc.SttServiceStub(channel)
    it = stub.StreamingRecognize(gen(audio_file_name))

    try:
        for r in it:
            try:
                print('Start chunk: ')
                for alternative in r.chunks[0].alternatives:
                    print('alternative: ', alternative.text)
                    print('alternative_confidence: ', alternative.confidence)
                    for word in alternative.words:
                       print('words: ', word.word)
                print('Is final: ', r.chunks[0].final)
                print('')
            except LookupError:
                print('No available chunks')
    except grpc._channel._Rendezvous as err:
        print('Error code %s, message: %s' % (err._state.code, err._state.details))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True, help='audio file path')
    args = parser.parse_args()

    run(args.path)
