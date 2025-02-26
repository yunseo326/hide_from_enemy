# 라이브러리 불러오기
import torch
import torch.nn.functional as F

state_size = 96
action_size = 3

class ActorCritic(torch.nn.Module):
    def __init__(self, **kwargs):
        super(ActorCritic, self).__init__(**kwargs)
        self.d1 = torch.nn.Linear(state_size, 128)
        self.d2 = torch.nn.Linear(128, 128)
        self.pi = torch.nn.Linear(128, action_size)
        self.v = torch.nn.Linear(128, 1)
        
    def forward(self, x):
        x = F.relu(self.d1(x))
        x = F.relu(self.d2(x))
        return F.softmax(self.pi(x), dim=-1), self.v(x)
