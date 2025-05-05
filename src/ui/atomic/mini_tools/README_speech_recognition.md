# Speech Recognition Module User Guide

## Overview

The Speech Recognition module allows users to record audio and convert it to text using the Baidu Speech Recognition API. This module supports the following features:

- Record audio up to 60 seconds
- Support for 16kHz and 8kHz sampling rates
- Support for mono, 16-bit audio
- Support for WAV, PCM, and AMR formats
- Copy recognition results to clipboard
- Language selection (Mandarin or English)
- Automatic saving of API configuration
- Microphone device selection

## Prerequisites

1. Ensure necessary dependencies are installed:
   - baidu-aip (Baidu AI Platform SDK)
   - pyaudio (Audio recording library)

2. Obtain Baidu Speech Recognition API credentials:
   - Visit [Baidu AI Platform](https://ai.baidu.com/)
   - Register and create a speech recognition application
   - Get your APP ID, API Key, and Secret Key

## Usage Instructions

1. Click "Speech Recognition" in the application sidebar
2. Click the "API Settings" button to configure your Baidu API credentials:
   - APP ID
   - API Key
   - Secret Key
3. Select your preferred language (Mandarin or English)
4. Select the sampling rate (16000Hz or 8000Hz)
5. Select your preferred microphone from the dropdown list
   - The system automatically detects all available microphones
   - You can refresh the microphone list by clicking the "刷新麦克风" button
6. Click the "Start Recording" button to begin recording
7. The progress bar will show the recording time
8. Click the "Stop Recording" button to end recording (or wait for the 60-second automatic cutoff)
9. The system will automatically send the recording to the Baidu API for recognition
10. The recognition result will be displayed in the text box
11. Use the "Copy Result" button to copy the recognition result to the clipboard
12. Use the "Clear Result" button to clear the current recognition result

## Notes

- API credentials are saved automatically after first configuration
- Your settings (API credentials, language preference, sample rate, and microphone selection) are preserved between sessions
- Ensure your network connection is stable for communication with the Baidu API
- Record in a quiet environment for better recognition accuracy
- Recording is limited to 60 seconds maximum
- Supports both Mandarin Chinese and English recognition
- Configuration is stored in the user's home directory under `.speech_recognition/config.json`