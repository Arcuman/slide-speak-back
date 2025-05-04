# SlideSpeak Backend

Backend service for the SlideSpeak application, which processes and indexes slide content.

![slidespeak-banner-github](https://github.com/SlideSpeak/slidespeak-backend/assets/5519740/6dba254f-abdd-40fd-a647-59ec2b41e0fb)

[SlideSpeak](https://slidespeak.co): The ultimate AI presentation maker. Summarize PowerPoint files with AI or create entire PowerPoint presentations. Upload your PowerPoint files and use SlideSpeak to get the information you need.

SlideSpeak was built with:

- [Llama Index](https://github.com/jerryjliu/llama_index) and uses the OpenAI [GPT 3.5 Turbo](https://platform.openai.com/docs/models/gpt-3-5) Mobel
- [PineCone](https://www.pinecone.io/) as the primary vector storage
- [MongoDB](https://mongodb.com/) as the Index Store and Document Store
- AWS S3 as the blob file storage

The frontend for this project is available here: [https://github.com/SlideSpeak/slidespeak-webapp](https://github.com/SlideSpeak/slidespeak-webapp)

## Requirements

- Python3
- Pinecone
- MongoDB
- S3 with AWS credentials
- OpenAI API credentials

## Setup

### Environment Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables by copying `.env.example` to `.env` and filling in your values.

### Running the Application

_Please note:_ Both the index server and the flask backend need to run in parallel.

- Start index server `python3 index_server.py`
- Start Flask Backend `python3 flask_demo.py`

## License

See LICENSE file.
