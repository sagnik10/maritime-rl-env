from env.environment import MaritimeEnv

env=MaritimeEnv()
scores=[]
for i in range(10):
    s=env.reset()
    total=0
    for _ in range(50):
        _,r,d,_=env.step()
        total+=r
        if d:
            break
    scores.append(total)

print(sum(scores)/len(scores))
