import os

def explain(msg):
    try:
        from openai import OpenAI
        client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise Exception()

        r=client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":msg}]
        )
        return r.choices[0].message.content

    except:
        return "Routes are optimized globally by minimizing distance, avoiding weather disturbances, and reducing conflict exposure while balancing fuel consumption and ETA."
