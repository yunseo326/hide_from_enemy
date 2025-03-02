아직 미완입니다! 업데이트되는 대로 올리겠습니다.

pt 파일 사용시 model.py 를 참고하여 model의 사전 구성을 동일하게 해주어야 합니다.

```
2action_pt      :   좌우2개 액션      state ver1  장애물 ver1
4action_0_ckpt  :   상하좌우 4개 액션 state ver1  장애물 ver2
4action_1_ckpt  :   상하좌우 4개 액션 state ver1  장애물 ver3
4action_2_ckpt  :   상하좌우 4개 액션 state ver1  장애물 ver3
4action_3_ckpt  :   상하좌우 4개 액션 state ver2  장애물 ver3

학습중...
4action_4_ckpt  :   상하좌우 4개 액션 state ver2  장애물 ver4
4action_5_ckpt  :   좌우회전 + 앞뒤 이동 4개 액션 state ver2  장애물 ver4
```
```
학습 환경 
ppo 
learning rate 1e-5
env           400
step          20000
episilon      0.2
```

```
state 버전 
1. state 96 라이더 90 + 6(적과의 상대거리 + 처음시작지점과의 상대거리)
2. state 93 라이더 90 + 3(적과의 상대거리)
```

```
장애물 버전 
1. 장애물 1개 좌우로만 배치
2. 장애물 3개 좌우로만 배치
3. 장애물 3개 상하좌우로 배치
4. 장애물 3개 상하좌우로 배치 + 장애물과 가까워야 성공하는 조건 추가
```