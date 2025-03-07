# 라이브러리 불러오기
import numpy as np
import datetime
import platform
import torch
import torch.nn.functional as F
from torch.utils.tensorboard import SummaryWriter
from mlagents_envs.environment import UnityEnvironment, ActionTuple
from mlagents_envs.side_channel.engine_configuration_channel\
                             import EngineConfigurationChannel
import threading
# 파라미터 값 세팅 
state_size = 96
action_size = 3

load_model = True
train_mode = False
inference = False

discount_factor = 0.99
learning_rate = 1e-5
n_step = 256
batch_size = 256
n_epoch = 3
_lambda = 0.95
epsilon = 0.3

run_step = 20000 if train_mode else 0
test_step = 10000

print_interval = 10
save_interval = 10

# 유니티 환경 경로
game = "hiderobot"
os_name = platform.system()
if os_name == 'Windows':
    env_name = "C:/5 colledge file/2024-1/hands/ml-agents-release_17/Project2/Env/hiderobot_small_discrete10/hiderobot.exe"  # 성공한거 5
    # 디버깅 용도 
    #env_name = "C:/5 colledge file/2024-1/hands/ml-agents-release_17/Project2/Env/hiderobot_discrete_dubugging/hiderobot.exe"  # 성공한거 5
elif os_name == 'Darwin':
    env_name = f"../envs/{game}_{os_name}"

# 모델 저장 및 불러오기 경로
date_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
save_path = f"C:/5 colledge file/2024-1/hands/ml-agents-release_17/Project2/saved_models/hiderobot_discrete/ppo/{date_time}"
load_path = "C:/5 colledge file/2024-1/hands/ml-agents-release_17/Project2/saved_models/hiderobot_discrete/ppo/20250226195313"

# 연산 장치
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ActorCritic 클래스 -> Actor Network, Critic Network 정의 
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

# PPOAgent 클래스 -> PPO 알고리즘을 위한 다양한 함수 정의 
class PPOAgent:
    def __init__(self):
        self.network = ActorCritic().to(device)
        self.optimizer = torch.optim.Adam(self.network.parameters(), lr=learning_rate)
        self.memory = list()
        self.writer = SummaryWriter(save_path)

        if load_model == True:
            print(f"... Load Model from {load_path}/ckpt ...")
            checkpoint = torch.load(load_path+'/ckpt', map_location=device)
            self.network.load_state_dict(checkpoint["network"])
            self.optimizer.load_state_dict(checkpoint["optimizer"])

    # 정책을 통해 행동 결정 
    def get_action(self, state, training=True):
        # 네트워크 모드 설정
        self.network.train(training)

        # 네트워크 연산에 따라 행동 결정
        pi, _ = self.network(torch.FloatTensor(state).to(device))
        action = torch.multinomial(pi, num_samples=1).cpu().numpy()
        return action

    # 리플레이 메모리에 데이터 추가 (상태, 행동, 보상, 다음 상태, 게임 종료 여부)
    def append_sample(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    # 학습 수행
    def train_model(self):
        self.network.train()

        state      = np.stack([m[0] for m in self.memory], axis=0)
        action     = np.stack([m[1] for m in self.memory], axis=0)
        reward     = np.stack([m[2] for m in self.memory], axis=0)
        next_state = np.stack([m[3] for m in self.memory], axis=0)
        done       = np.stack([m[4] for m in self.memory], axis=0)
        self.memory.clear()

        state, action, reward, next_state, done = map(lambda x: torch.FloatTensor(x).to(device),
                                                        [state, action, reward, next_state, done])
        # prob_old, adv, ret 계산 
        with torch.no_grad():
            pi_old, value = self.network(state)
            prob_old = pi_old.gather(1, action.long())

            _, next_value = self.network(next_state)
            delta = reward + (1 - done) * discount_factor * next_value - value
            adv = delta.clone()
            adv, done = map(lambda x: x.view(n_step, -1).transpose(0,1).contiguous(), [adv, done])
            for t in reversed(range(n_step-1)):
                adv[:, t] += (1 - done[:, t]) * discount_factor * _lambda * adv[:, t+1]
            adv = adv.transpose(0,1).contiguous().view(-1, 1)
            
            ret = adv + value

        # 학습 이터레이션 시작
        actor_losses, critic_losses = [], []
        idxs = np.arange(len(reward))
        for _ in range(n_epoch):
            np.random.shuffle(idxs)
            for offset in range(0, len(reward), batch_size):
                idx = idxs[offset : offset + batch_size]

                _state, _action, _ret, _adv, _prob_old =\
                    map(lambda x: x[idx], [state, action, ret, adv, prob_old])
                
                pi, value = self.network(_state)
                prob = pi.gather(1, _action.long())

                # 정책신경망 손실함수 계산
                ratio = prob / (_prob_old + 1e-7)
                surr1 = ratio * _adv
                surr2 = torch.clamp(ratio, min=1-epsilon, max=1+epsilon) * _adv
                actor_loss = -torch.min(surr1, surr2).mean()

                # 가치신경망 손실함수 계산
                critic_loss = F.mse_loss(value, _ret).mean()

                total_loss = actor_loss + critic_loss

                self.optimizer.zero_grad()
                total_loss.backward()
                self.optimizer.step()

                actor_losses.append(actor_loss.item())
                critic_losses.append(critic_loss.item())

        return np.mean(actor_losses), np.mean(critic_losses)

    # 네트워크 모델 저장
    def save_model(self):
        print(f"... Save Model to {save_path}/ckpt ...")
        torch.save({
            "network" : self.network.state_dict(),
            "optimizer" : self.optimizer.state_dict(),
        }, save_path+'/ckpt')

        # pt 파일 만을 저장 하는것
        #torch.save(self.network.state_dict(), save_path + '/model.pt')

    # 학습 기록 
    def write_summary(self, score, actor_loss, critic_loss, step):
        self.writer.add_scalar("run/score", score, step)
        self.writer.add_scalar("model/actor_loss", actor_loss, step)
        self.writer.add_scalar("model/critic_loss", critic_loss, step)


user_input = None
def get_user_input():
    global user_input
    user_input = input("추론을 시작하시려면 1, 리셋하려면 3을 눌러주세요: ")

def thread_start():
    input_thread = threading.Thread(target=get_user_input, daemon=True)
    input_thread.start()

# Main 함수 -> 전체적으로 DDPG 알고리즘을 진행
if __name__ == '__main__':
    # 유니티 환경 경로 설정 (file_name)
    engine_configuration_channel = EngineConfigurationChannel()
    env = UnityEnvironment(file_name=env_name,
                           side_channels=[engine_configuration_channel])
    env.reset()
    count = 0
    # 유니티 브레인 설정
    behavior_name = list(env.behavior_specs.keys())[0]
    spec = env.behavior_specs[behavior_name]
    # 시뮬레이션 속도 설정
    if train_mode:
        engine_configuration_channel.set_configuration_parameters(time_scale=1.0)
    elif train_mode is False:
        engine_configuration_channel.set_configuration_parameters(time_scale=1.0)
    dec, term = env.get_steps(behavior_name)
    num_worker = len(dec)

    agent = PPOAgent()

    actor_losses, critic_losses, scores, episode, score = [], [], [], 0, 0
    if train_mode is False and inference is False:
        thread_start()
    for step in range(run_step + test_step):
        if step == run_step:
            if train_mode:
                agent.save_model()
            print("TEST START")
            if inference is True:
                thread_start()
            train_mode = False
            engine_configuration_channel.set_configuration_parameters(time_scale=12.0)
        
        state = dec.obs[0]

        if train_mode:
            action = agent.get_action(state, train_mode)
        elif train_mode is False and inference is False:
            action = agent.get_action(state, train_mode)
        elif user_input is not None and inference is True and train_mode is False:
            # 모든 값을 0으로 해서 선택하지 않게끔
            if user_input == "1":
                action = agent.get_action(state, train_mode)
                print(action,2)
                user_input = None
                thread_start()

            elif user_input == "3":
                print("reset")
                env.reset()
                user_input = None
                thread_start()
            else:
                user_input = None
                thread_start()
        elif train_mode is False:
            action = np.zeros((1, 1), dtype=np.float32)

        action_tuple = ActionTuple()
        action_tuple.add_discrete(action)
        env.set_actions(behavior_name, action_tuple)
        env.step()

        # 환경으로부터 얻는 정보
        dec, term = env.get_steps(behavior_name)
        done = [False] * num_worker
        next_state = dec.obs[0]
        reward = dec.reward
        for id in term.agent_id:
            _id = list(term.agent_id).index(id)
            done[id] = True
            next_state[id] = term.obs[0][_id]
            reward[id] = term.reward[_id]
            if done[id] == True and train_mode is False:
                print(reward[id])
        score += reward[0]

        if train_mode:
            for id in range(num_worker):
                agent.append_sample(state[id], action[id], [reward[id]], next_state[id], [done[id]])
            # 학습수행
            if (step+1) % n_step == 0:
                actor_loss, critic_loss = agent.train_model()
                actor_losses.append(actor_loss)
                critic_losses.append(critic_loss)

        if done[0]:
            episode +=1
            scores.append(score)
            score = 0

            # 게임 진행 상황 출력 및 텐서 보드에 보상과 손실함수 값 기록 
            if episode % print_interval == 0:
                mean_score = np.mean(scores)
                mean_actor_loss = np.mean(actor_losses) if len(actor_losses) > 0 else 0
                mean_critic_loss = np.mean(critic_losses)  if len(critic_losses) > 0 else 0
                agent.write_summary(mean_score, mean_actor_loss, mean_critic_loss, step)
                actor_losses, critic_losses, scores = [], [], []

                print(f"{episode} Episode / Step: {step} / Score: {mean_score:.2f} / " +\
                      f"Actor loss: {mean_actor_loss:.2f} / Critic loss: {mean_critic_loss:.4f}" )

            # 네트워크 모델 저장 
            if train_mode and episode % save_interval == 0:
                agent.save_model()

    env.close()
