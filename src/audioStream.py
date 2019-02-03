from __future__ import division

import re
import sys

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from six.moves import queue
import os
import time
import threading

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r"/Users/jnaylor/Documents/QHacks2019Local/gcpcredentialsnaylor.json"

WORD_LIST = ['like', ' so', ' you know', 'basically', ' cuz', 'things', 'stuff', 'yeah']


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


class AudioGenerator(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True  # OK for main to exit even if instance still running
        self.lock = threading.Lock()
        self.wpm = 0
        self.t = ''
        self.crutch = {}

    start_stream = threading.Thread.start  # an alias for starting thread


    def get_wpm(self):
        return self.wpm

    def get_crutch(self):
        with self.lock:
            return self.crutch

    def get_transcript(self):
        with self.lock:
            return self.t

    def run(self):


            # See http://g.co/cloud/speech/docs/languages
        # for a list of supported languages.
        language_code = 'en-US'  # a BCP-47 language tag

        client = speech.SpeechClient()
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code=language_code)
        streaming_config = types.StreamingRecognitionConfig(
            config=config,
            interim_results=True)

        with MicrophoneStream(RATE, CHUNK) as stream:
            audio_generator = stream.generator()
            requests = (types.StreamingRecognizeRequest(audio_content=content)
                        for content in audio_generator)

            responses = client.streaming_recognize(streaming_config, requests)

            # Now, put the transcription responses to use.

            num_chars_printed = 0
            WORD_COUNT = 0
            cur_bad_words = {}
            total_bad_words = {}
            start = time.time()
            old_start = time.time()
            words = 0
            old_words = 0

            for word in WORD_LIST:
                cur_bad_words[word] = 0
                total_bad_words[word] = 0
            try:
                for response in responses:
                    if not response.results:
                        continue

                    # The `results` list is consecutive. For streaming, we only care about
                    # the first result being considered, since once it's `is_final`, it
                    # moves on to considering the next utterance.
                    result = response.results[0]
                    if not result.alternatives:
                        continue

                    # Display the transcription of the top alternative.
                    transcript = result.alternatives[0].transcript

                    # Display interim results, but with a carriage return at the end of the
                    # line, so subsequent lines will overwrite them.
                    #
                    # If the previous result was longer than this one, we need to print
                    # some extra spaces to overwrite the previous result
                    overwrite_chars = ' ' * (num_chars_printed - len(transcript))

                    # In the middle on a sentence
                    if not result.is_final:
                        # sys.stdout.write(transcript + overwrite_chars + '\r')
                        # sys.stdout.flush()


                        num_chars_printed = len(transcript)
                        for word in WORD_LIST:
                            cur_bad_words[word] = transcript.count(word) + total_bad_words[word]

                        words = len(transcript.split(' '))
                        total_time = time.time() - old_start
                        total_words = words + old_words

                        
                        # with self.lock:
                        self.wpm =  total_words / (total_time / 60)
                        self.t = transcript
                        self.crutch = cur_bad_words

                    # End of sentence
                    else:
                        old_words = words
                        old_start = start
                        start = time.time()
                        total_bad_words = cur_bad_words

            except:
                pass


def main():
        # See http://g.co/cloud/speech/docs/languages
    # for a list of supported languages.
    language_code = 'en-US'  # a BCP-47 language tag

    client = speech.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=True)

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)

        # Now, put the transcription responses to use.

        num_chars_printed = 0
        WORD_COUNT = 0
        cur_bad_words = {}
        total_bad_words = {}
        start = time.time()
        old_start = time.time()
        words = 0
        old_words = 0

        for word in WORD_LIST:
            cur_bad_words[word] = 0
            total_bad_words[word] = 0
        try:
            for response in responses:
                if not response.results:
                    continue

                # The `results` list is consecutive. For streaming, we only care about
                # the first result being considered, since once it's `is_final`, it
                # moves on to considering the next utterance.
                result = response.results[0]
                if not result.alternatives:
                    continue

                # Display the transcription of the top alternative.
                transcript = result.alternatives[0].transcript

                # Display interim results, but with a carriage return at the end of the
                # line, so subsequent lines will overwrite them.
                #
                # If the previous result was longer than this one, we need to print
                # some extra spaces to overwrite the previous result
                overwrite_chars = ' ' * (num_chars_printed - len(transcript))

                # In the middle on a sentence
                if not result.is_final:
                    # sys.stdout.write(transcript + overwrite_chars + '\r')
                    # sys.stdout.flush()


                    num_chars_printed = len(transcript)
                    for word in WORD_LIST:
                        cur_bad_words[word] = transcript.count(word) + total_bad_words[word]

                    words = len(transcript.split(' '))
                    total_time = time.time() - old_start
                    total_words = words + old_words

                    
                    # with self.lock:
                    wpm =  total_words / (total_time / 60)
                    t = transcript
                    crutch = cur_bad_words

                    print("WPM: {}  Transcript:{}".format(wmp, transcript))
                    print(crutch)

                # End of sentence
                else:
                    old_words = words
                    old_start = start
                    start = time.time()
                    total_bad_words = cur_bad_words

        except:
            pass




if __name__ == '__main__':
    main()
    # ag = AudioGenerator()
    # ag.start_stream()
    # while True:
    #     print("WPM: {}  Transcript:{}".format(ag.get_wpm, ag.get_transcript))