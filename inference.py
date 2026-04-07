import asyncio
import httpx
import os

ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")
LLM_URL = os.getenv("LLM_URL", "http://localhost:8001/generate")
MAX_STEPS = 40


async def call_llm(obs):
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(LLM_URL, json={"observation": obs})
            return r.json()
        except:
            return {"action": "noop"}


async def reset_env(client):
    r = await client.post(f"{ENV_URL}/reset")
    return r.json()


async def step_env(client, action):
    r = await client.post(f"{ENV_URL}/step", json={"action": action})
    return r.json()


async def run_episode(client):
    obs = await reset_env(client)

    for _ in range(MAX_STEPS):
        try:
            action = await asyncio.wait_for(call_llm(obs), timeout=20)
        except:
            action = {"action": "noop"}

        step = await step_env(client, action)

        obs = step.get("observation", {})
        done = step.get("done", False)

        if done:
            break


async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        await run_episode(client)


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=1500))
