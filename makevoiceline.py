from pipeline import voiceResponse

if __name__ == "__main__":
    while True:
        prompt = str(input("Enter input for AI voice, q to quit: "))
        if prompt == "q":
            break
        file = str(input("Enter name for file: "))

        audio = voiceResponse(prompt)
        with open(f"Assets/voice/voicelines/{file}.wav", "wb") as f:
            f.write(audio)
