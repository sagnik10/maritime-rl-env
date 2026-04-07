import asyncio
import httpx
import os

ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")
MAX_STEPS = 40

async def reset_env(client):
    try:
        r = await client.post(f"{ENV_URL}/reset")
        return r.json()
    except:
        return {}

async def step_env(client, action):
    try:
        r = await client.post(f"{ENV_URL}/step", json=action)
        return r.json()
    except:
        return {}

async def run_episode(client):
    obs = await reset_env(client)

    if not isinstance(obs, dict):
        obs = {}

    for _ in range(MAX_STEPS):
        action = {"action": "noop"}

        step = await step_env(client, action)

        if not isinstance(step, dict):
            continue

        obs = step.get("observation", {})
        done = step.get("done", False)

        if done:
            break

async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await run_episode(client)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=1500))
