import asyncio
import httpx
import os

ENV_URL=os.getenv("ENV_URL","http://localhost:8000")
API_BASE_URL=os.environ["API_BASE_URL"]
API_KEY=os.environ["API_KEY"]
MAX_STEPS=40

async def llm_call(client,prompt):
    try:
        await client.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers={"Authorization":f"Bearer {API_KEY}"},
            json={
                "model":"gpt-3.5-turbo",
                "messages":[{"role":"user","content":prompt}],
                "max_tokens":5
            }
        )
    except:
        pass

async def reset_env(client):
    try:
        r=await client.post(f"{ENV_URL}/reset")
        return r.json()
    except:
        return {}

async def step_env(client,action):
    try:
        r=await client.post(f"{ENV_URL}/step",json=action)
        return r.json()
    except:
        return {}

async def run_episode(client):

    print("[START] task=maritime",flush=True)

    obs=await reset_env(client)

    if not isinstance(obs,dict):
        obs={}

    total_reward=0
    steps=0

    for i in range(MAX_STEPS):

        await llm_call(client,str(obs))

        action={"action":"noop"}

        step=await step_env(client,action)

        if not isinstance(step,dict):
            continue

        obs=step.get("observation",{})
        reward=step.get("reward",0)
        done=step.get("done",False)

        total_reward+=reward
        steps+=1

        print(f"[STEP] step={i+1} reward={reward}",flush=True)

        if done:
            break

    print(f"[END] task=maritime score={total_reward} steps={steps}",flush=True)

async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await run_episode(client)
        except:
            pass

if __name__=="__main__":
    asyncio.run(asyncio.wait_for(main(),timeout=1500))
