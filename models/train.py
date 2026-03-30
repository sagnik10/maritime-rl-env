import torch
import torch.nn as nn
import torch.optim as optim

class PPO(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(
            nn.Linear(4,64),
            nn.ReLU(),
            nn.Linear(64,2)
        )

    def forward(self,x):
        return self.net(x)

model=PPO()
opt=optim.Adam(model.parameters(),lr=1e-3)

for _ in range(1000):
    x=torch.randn(32,4)
    y=model(x)
    loss=y.mean()
    opt.zero_grad()
    loss.backward()
    opt.step()

print("RL training running")
