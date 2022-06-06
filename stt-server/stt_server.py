#!/usr/bin/env python3

# Copyright 2020 Alpha Cephei Inc
# Copyright 2015 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The Python implementation of the gRPC route guide server."""

from concurrent import futures
import os
import sys
import time
import math
import logging
import json
import grpc
import gc

import stt_service_pb2
import stt_service_pb2_grpc
from google.protobuf import duration_pb2

from vosk import Model, KaldiRecognizer

ssl = False   # Use SSL for connection  
numb = True  # Convert numeral words to numbers
punct = True # Use punctuation marks

if numb:
   from numberator.text2numbers import TextToNumbers
   text2numbers = TextToNumbers()

if punct:
   from punctuator.recasepunc import CasePuncPredictor, WordpieceTokenizer, Config
   predictor = CasePuncPredictor('punctuator/checkpoint', lang="ru")

gc.set_threshold(0)

vosk_interface = os.environ.get('VOSK_SERVER_INTERFACE', '0.0.0.0')
vosk_port = int(os.environ.get('VOSK_SERVER_PORT', 5001))
vosk_model_path = os.environ.get('VOSK_MODEL_PATH', 'model')
vosk_sample_rate = float(os.environ.get('VOSK_SAMPLE_RATE', 16000))

if len(sys.argv) > 1:
   vosk_model_path = sys.argv[1]

class SttServiceServicer(stt_service_pb2_grpc.SttServiceServicer):
    """Provides methods that implement functionality of route guide server."""

    def __init__(self):
        self.model = Model(vosk_model_path)

    def get_duration(self, x):
        seconds = int(x)
        nanos = (int (x * 1000) % 1000) * 1000000;
        return duration_pb2.Duration(seconds = seconds, nanos=nanos)

    def get_word_info(self, x):
        return stt_service_pb2.WordInfo(start_time = self.get_duration(x['start']),
                                        end_time = self.get_duration(x['end']),
                                        word= x['word'], confidence = x.get('conf', 1.0))

    def get_alternative(self, x):
        results = ''
        words = [self.get_word_info(y) for y in x.get('result', [])]
        if 'confidence' in x:
            conf = x['confidence']
        elif len(words) > 0:
            confs = [w.confidence for w in words]
            conf = sum(confs) / len(confs)
        else:
            conf = 1.0

        # Convert numeral words to numbers
        if self.spec.raw_results and numb:
            numbertext = text2numbers.convert(x['text'])
        else:
            numbertext = x['text']
        
        # Punctuation marks
        if self.spec.automatic_punctuation and punct:
            tokens = list(enumerate(predictor.tokenize(numbertext)))
            for token, case_label, punc_label in predictor.predict(tokens, lambda x: x[1]):
                    prediction = predictor.map_punc_label(predictor.map_case_label(token[1], case_label), punc_label)
                    if token[1][0] != '#':
                       results = results + ' ' + prediction
                    else:
                       results = results + prediction
            resulttext = results.strip()
        else:
            resulttext = numbertext
        
        return stt_service_pb2.SpeechRecognitionAlternative(text=resulttext,
                                                            words=words, confidence=conf)

    def get_response(self, json_res):
        res = json.loads(json_res)

        if 'partial' in res:
             numbertext = text2numbers.convert(res['partial']) if self.spec.raw_results and numb else res['partial']
             alternatives = [stt_service_pb2.SpeechRecognitionAlternative(text=numbertext)]
             chunks = [stt_service_pb2.SpeechRecognitionChunk(alternatives=alternatives, final=False)]
             return stt_service_pb2.StreamingRecognitionResponse(chunks=chunks)
        elif 'alternatives' in res:
             alternatives = [self.get_alternative(x) for x in res['alternatives']]
             chunks = [stt_service_pb2.SpeechRecognitionChunk(alternatives=alternatives, final=True)]
             return stt_service_pb2.StreamingRecognitionResponse(chunks=chunks)
        else:
             alternatives = [self.get_alternative(res)]
             chunks = [stt_service_pb2.SpeechRecognitionChunk(alternatives=alternatives, final=True)]
             return stt_service_pb2.StreamingRecognitionResponse(chunks=chunks)

    def StreamingRecognize(self, request_iterator, context):
        request = next(request_iterator)
        self.spec = request.config.specification
        partial = request.config.specification.partial_results
        recognizer = KaldiRecognizer(self.model, request.config.specification.sample_rate_hertz)
        recognizer.SetMaxAlternatives(request.config.specification.max_alternatives)
        recognizer.SetWords(request.config.specification.enable_word_time_offsets)

        for request in request_iterator:
            res = recognizer.AcceptWaveform(request.audio_content)
            if res:
                yield self.get_response(recognizer.Result())
            elif partial:
                yield self.get_response(recognizer.PartialResult())
        yield self.get_response(recognizer.FinalResult())

def serve():
    server = grpc.server(futures.ThreadPoolExecutor((os.cpu_count() or 1)))
    stt_service_pb2_grpc.add_SttServiceServicer_to_server(
        SttServiceServicer(), server)
    
    if ssl:
       with open('certificate/key.pem') as f:
           private_key = f.read().encode()
       with open('certificate/certificate.pem') as f:
           certificate_chain = f.read().encode()
       server_creds = grpc.ssl_server_credentials (((private_key, certificate_chain,),))
       server.add_secure_port('{}:{}'.format(vosk_interface, vosk_port), server_creds)
    else:
       server.add_insecure_port('{}:{}'.format(vosk_interface, vosk_port))
    
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig()
    serve()