# from openai import AzureOpenAI
# from django.conf import settings
# import time  # ✅ added

# client = AzureOpenAI(
#     api_key=settings.AZURE_OPENAI_API_KEY,
#     azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
#     api_version=settings.AZURE_OPENAI_API_VERSION,
# )


# def generate_response(system_prompt, user_message):
#     llm_start = time.time()  # ✅ start timer

#     response = client.chat.completions.create(
#         model=settings.AZURE_OPENAI_DEPLOYMENT,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_message},
#         ],
#         temperature=0.3,
#         max_tokens=150,  # ⚡ Cap response length — voice replies should be 1-3 sentences
#     )

#     print("⏱ LLM Time:", time.time() - llm_start)  # ✅ log time

#     return response.choices[0].message.content


# def generate_response_streaming(system_prompt, user_message):
#     """
#     ⚡ Streaming variant — yields text chunks as they arrive from the LLM.
#     First tokens arrive in ~200-400ms instead of waiting 1.5s for full response.
#     Used by the streaming pipeline in consumers.py.
#     """
#     llm_start = time.time()
#     response = client.chat.completions.create(
#         model=settings.AZURE_OPENAI_DEPLOYMENT,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_message},
#         ],
#         temperature=0.3,
#         max_tokens=150,
#         stream=True,
#     )
#     for chunk in response:
#         if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
#             yield chunk.choices[0].delta.content
#     print("⏱ LLM Stream Time:", round(time.time() - llm_start, 3), "s")




































from openai import AzureOpenAI
from django.conf import settings
import time  # ✅ added

client = AzureOpenAI(
    api_key=settings.AZURE_OPENAI_API_KEY,
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    api_version=settings.AZURE_OPENAI_API_VERSION,
)


def generate_response(system_prompt, user_message):
    llm_start = time.time()  # ✅ start timer

    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=150,  # ⚡ Cap response length — voice replies should be 1-3 sentences
        frequency_penalty=0.3,   
    )

    usage = response.usage
    print(f"⏱ LLM Time: {round(time.time() - llm_start, 3)}s | "
          f"Prompt tokens: {usage.prompt_tokens} | "
          f"Reply tokens: {usage.completion_tokens}")

    return response.choices[0].message.content


def generate_response_streaming(system_prompt, user_message):
    """
    ⚡ Streaming variant — yields text chunks as they arrive from the LLM.
    First tokens arrive in ~200-400ms instead of waiting 1.5s for full response.
    Used by the streaming pipeline in consumers.py.
    """
    llm_start = time.time()
    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=150,
        stream=True,
        frequency_penalty=0.3
    )
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
    print("⏱ LLM Stream Time:", round(time.time() - llm_start, 3), "s")