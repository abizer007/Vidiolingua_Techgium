# VidioLingua Architecture Documentation

## High-Level Architecture Overview

VidioLingua follows a modular pipeline architecture where video processing flows through four independent stages: Automatic Speech Recognition (ASR), Machine Translation (MT), Text-to-Speech (TTS), and Lip Synchronization. Each stage operates as a self-contained module with dedicated input/output folders, communicating through file-based interfaces. The pipeline enforces unidirectional data flow—each stage reads from the previous stage's output and writes to its own output folder, ensuring clear separation of concerns and enabling parallel development. A shared contracts file defines the data format specifications between stages, maintaining consistency across the pipeline. The architecture is designed for Windows environments with beginner-friendly, low-risk modularity.

## Complete Folder Structure

```
C:\vidiolingua\
│
├── asr\
│   ├── input\
│   ├── output\
│   └── run_asr.py
│
├── translation\
│   ├── input\
│   ├── output\
│   └── run_translate.py
│
├── tts\
│   ├── input\
│   ├── output\
│   └── run_tts.py
│
├── lipsync\
│   ├── input\
│   ├── output\
│   └── run_lipsync.py
│
├── demo_inputs\
│   └── sample_video.mp4
│
├── demo_outputs\
│
├── shared\
│   └── contracts.json
│
├── requirements.txt
└── README.md
```



## Folder and File Descriptions

### Root Directory: `C:\vidiolingua\`

The main project root containing all pipeline modules and shared resources.

### `asr\`

**Purpose:** Automatic Speech Recognition module that extracts spoken text from video files.

- **`asr\input\`**: Receives video files from the demo_inputs folder or previous pipeline stages.
- **`asr\output\`**: Contains transcribed text output (typically JSON or text files with timestamps and transcriptions).
- **`run_asr.py`**: Entry point script that processes video files in the input folder and generates transcriptions in the output folder.

### `translation\`

**Purpose:** Machine Translation module that translates transcribed text into target languages (Hindi, Spanish, French).

- **`translation\input\`**: Receives transcription files from the ASR module's output.
- **`translation\output\`**: Contains translated text files for each target language, maintaining timing information.
- **`run_translate.py`**: Entry point script that reads transcriptions and generates translations for all target languages.

### `tts\`

**Purpose:** Text-to-Speech module that converts translated text into speech audio files.

- **`tts\input\`**: Receives translated text files from the translation module's output.
- **`tts\output\`**: Contains generated audio files (one per target language) with speech synthesized from translated text.
- **`run_tts.py`**: Entry point script that processes translated text and generates audio files for each language.

### `lipsync\`

**Purpose:** Lip Synchronization module that synchronizes generated audio with video lip movements.

- **`lipsync\input\`**: Receives both the original video file and generated audio files from TTS output.
- **`lipsync\output\`**: Contains final dubbed video files with lip-synced audio for each target language.
- **`run_lipsync.py`**: Entry point script that combines video and audio to produce lip-synced dubbed videos.

### `demo_inputs\`

**Purpose:** Storage location for sample input videos used for testing and demonstration.

- **`demo_inputs\sample_video.mp4`**: Placeholder for a sample English video file (1-3 minutes) used for POC testing.

### `demo_outputs\`

**Purpose:** Storage location for final processed videos after the complete pipeline execution.

- Empty folder where final dubbed videos (one per target language) will be placed after successful pipeline completion.

### `shared\`

**Purpose:** Contains shared configuration and contract definitions used across all pipeline stages.

- **`shared\contracts.json`**: Defines data format specifications, file naming conventions, and interface contracts between pipeline stages to ensure consistent communication.

### `requirements.txt`

**Purpose:** Python dependency manifest listing all required packages and libraries for the entire pipeline.

