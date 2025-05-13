from openai import OpenAI
# Replace 'your-api-key' with your actual OpenAI API key
client = OpenAI(api_key = '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')
# client = OpenAI()
def test_openai_api():
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", #"text-davinci-003"
            messages=[{"role": "user", "content": "Say hello to the world!"}],#["Say hello to the world!"],
            max_tokens=10
        )
        print("Response from OpenAI API:", response.choices[0].message.content)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_openai_api()