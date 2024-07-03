# Curse Word Bleeper

This is a Mac application that automatically detects curse words in video or audio files and bleeps them out.

## Features

- Detects curse words in audio and video files using advanced speech recognition
- Automatically bleeps out detected curse words with adjustable volume
- Handles misrecognized words (e.g., "con" for "cunt")
- Extends bleep duration for specific words for extra safety
- Preserves original video content for MP4 files, only modifying the audio track
- Simple graphical user interface for easy use
- Supports various audio and video file formats

## Requirements

- Python 3.7+
- FFmpeg (for audio and video processing)
- PyQt6
- whisper (OpenAI's speech recognition model)
- pydub

## Installation

1. Clone this repository or download the source code.
2. Install the required Python packages:

```
pip install PyQt6 openai-whisper pydub
```

3. Make sure FFmpeg is installed on your system. If not, you can install it using Homebrew:

```
brew install ffmpeg
```

## Usage

1. Run the application:

```
python main.py
```

2. Click the "Select Audio/Video File" button to choose a file for processing.
3. Wait for the processing to complete. The progress bar will show the current status.
4. Once finished, the application will save a new file with "_bleeped" appended to the original filename.

## Customizing Curse Words

You can modify the list of curse words by editing the `curse_words.txt` file. Add or remove words as needed, with one word per line.

## Adjusting Bleep Settings

You can customize the bleep settings by modifying the following variables in the `BleepWorker` class:

- `bleep_volume_reduction`: Adjust the volume of the bleep sound (in dB).
- `extended_bleep_words`: Extend the bleep duration for specific words.

Example:

```python
self.bleep_volume_reduction = 6  # Reduce bleep volume by 6 dB
self.extended_bleep_words = {"cunt": 0.2, "fuck": 0.1}  # Extend bleep by 0.2s for "cunt" and 0.1s for "fuck"
```

## Handling Misrecognized Words

The application includes a dictionary to map commonly misrecognized words to their intended curse words. You can modify this in the `BleepWorker` class:

```python
self.misrecognized_words = {
    "con": "cunt",
    # Add more misrecognized words here if needed
}
```

## Note

This application uses the Whisper speech recognition model, which may require a significant amount of processing power and time depending on the length of the audio/video file. The accuracy of curse word detection depends on the quality of the audio and the accuracy of the speech recognition.

## License

This project is open-source and available under the MIT License.
