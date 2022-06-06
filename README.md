# stt-grpc-server
Simple TTS GRPC-server based on Vosk (https://github.com/alphacep/vosk-server).

## Prepare Models
Download the language and punctuation models: https://alphacephei.com/vosk/models
Unzip lasnguage model to "model" folder
Extract the "checkpoint" file from the punctuation model and place it in the "punctuator" folder

## Run
Build the Docker container:
`docker build -t vosk-grpc:ru-full .`

Run container:
`docker run -d -p 5001:5001 wentor/vosk-grpc:ru-full`

## Testing
Go to the server folder and run the test with the command:
`python stt_client.py --path test.wav`

## Remark
In the "certificate" folder you will find self-signed certificates to work on localhost
