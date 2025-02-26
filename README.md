pt 파일 사용시 model.py 를 참고하여 model의 사전 구성을 동일하게 해주어야 합니다.


학습 환경 

state 96   
90 라이더 센서 (최대거리 10, 장애물만 탐지 나머지는 10으로 설정해줌) -  추후 변경후 학습 예정 
3  적과 agent간의 상대적 거리 x,y,z 3개
3  agent와 시작지점 간 상대적 거리 x,y,z 3개
data type : float 32

action 3      
[정지, 좌 0.3f, 우 0.3f]



