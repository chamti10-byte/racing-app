import streamlit as st
import pandas as pd
import random

# ==========================================
# 1. 데이터 구조 (리스트 & 딕셔너리)
# ==========================================
sectors = ["직선 고속구간", "급커브 헤어핀", "빗길 슬릭", "최종 결승 직선"]
parts = ["구동 모터", "고전압 배터리", "인버터/제어기"]

# 개러지 부품 데이터 (전기전자공학 스펙 반영)
motors_spec = {
    "IPMSM (영구자석 동기모터)": {"accel": 1.00, "max_spd": 310, "heat": 1.00, "desc": "균형 잡힌 고효율 표준 레이싱 모터"},
    "IM (유도전동기)": {"accel": 0.92, "max_spd": 335, "heat": 0.80, "desc": "발열이 적고 초고속 직선 주행에 강함"},
    "AFPM (축방향 자속 모터)": {"accel": 1.20, "max_spd": 295, "heat": 1.25, "desc": "폭발적인 초반 가속력, 빠른 온도 상승"}
}

batteries_spec = {
    "NCM 811 (고출력 리튬이온)": {"cap": 100.0, "drain": 1.00, "regen": 1.00, "heat_stab": 1.00, "desc": "높은 방전 출력의 표준 레이싱 배터리"},
    "LFP (리튬인산철)": {"cap": 95.0, "drain": 0.95, "regen": 0.95, "heat_stab": 0.75, "desc": "열 안정성이 뛰어나 과열에 매우 강함"},
    "Solid-State (전고체 배터리)": {"cap": 115.0, "drain": 0.85, "regen": 1.40, "heat_stab": 0.85, "desc": "대용량(115%) 및 회생제동 충전 효율 극대화"}
}

inverters_spec = {
    "Si-IGBT (표준 인버터)": {"power": 1.00, "heat_red": 1.00, "regen_boost": 1.00, "desc": "안정적인 기본 스위칭 전력 제어기"},
    "SiC-MOSFET (실리콘카바이드)": {"power": 1.08, "heat_red": 0.72, "regen_boost": 1.20, "desc": "전력 손실 및 발열 약 30% 감소"},
    "Dual-Inverter 800V": {"power": 1.22, "heat_red": 1.12, "regen_boost": 1.10, "desc": "800V 고전압 승압으로 최고 출력 +22%"}
}

# random 라이브러리를 활용한 트랙 돌발 변수 (메시지, 속도변화, 온도변화, 배터리변화, 점수변화)
track_events = [
    ("순풍이 불어 공기저항이 감소했습니다!", 12, -1.5, 0.5, 2),
    ("노면 온도가 최상이라 타이어 접지력이 완벽합니다!", 10, 0.0, 0.0, 3),
    ("강한 맞바람으로 전력 소모가 소폭 증가했습니다.", -10, 1.5, -1.5, -1),
    ("앞선 차량의 난기류(더티 에어)로 냉각 효율이 떨어졌습니다.", -5, 3.0, -0.5, -1),
    ("완벽한 레코드 라인으로 코너를 공략했습니다!", 15, -1.0, 1.0, 4)
]

# ==========================================
# 2. 상태 초기화 및 엔지니어 무전 가이드 함수 (def)
# ==========================================
def init_game():
    st.session_state.started = False
    st.session_state.finished = False
    st.session_state.distance = 0          # 총 1200m (150m씩 8구간 진행)
    st.session_state.total_time = 0.0      # 누적 랩타임(초)
    st.session_state.speed = 0             # 현재 속도(km/h)
    st.session_state.motor_temp = 45.0     # 구동 모터 온도(℃)
    st.session_state.battery = 100.0       # 배터리 잔량(%)
    st.session_state.score = 100           # 레이싱 점수
    st.session_state.logs = []             # 주행 기록 로그
    st.session_state.last_msg = "개러지에서 파워트레인 부품을 세팅한 뒤 '레이스 스타트!'를 누르세요."
    st.session_state.last_event = "대기 중 (주행 시작 시 실시간 텔레메트리가 수신됩니다)"
    st.session_state.msg_type = "info"

def get_engineer_radio(distance, temp, battery):
    """현재 트랙 구간과 차량 상태에 따라 실시간 전략 무전을 반환하는 함수"""
    if temp >= 88:
        return "🚨 [긴급 무전] 모터 과열 임박! 지금 즉시 냉각 시스템을 '3: MAX'로 올리고 토크 상한을 낮추세요!", "error"
    if battery <= 18:
        return "🪫 [긴급 무전] 배터리 잔량 위험! 냉각을 '1: ECO'로 내리고 회생제동으로 에너지를 회수하세요!", "error"
    
    if distance < 300:
        return "📡 [직선 고속구간 0~300m] 추천 세팅: 토크 상한 85~100% + '가속 주행'으로 최고 속도를 끌어올리세요!", "info"
    elif distance < 600:
        return "📡 [급커브 헤어핀 300~600m] 추천 세팅: 회생제동 강도 70% 이상 + '회생제동 감속'으로 코너 안정성과 배터리를 확보하세요!", "warning"
    elif distance < 900:
        return "📡 [빗길 슬릭 600~900m] 추천 세팅: 노면이 미끄럽습니다! 휠스핀 방지를 위해 토크 상한을 75% 이하로 낮추세요!", "warning"
    else:
        return "📡 [최종 결승 직선 900~1200m] 추천 세팅: 회생제동 20% 이하 + '오버부스트 가속'으로 마지막 스퍼트를 내세요!", "success"

# ==========================================
# 3. 핵심 시뮬레이션 로직 함수 (def)
# ==========================================
def run_sector_step(action, torque_limit, regen_level, cooling_mode):
    m_spec = motors_spec[st.session_state.selected_motor]
    b_spec = batteries_spec[st.session_state.selected_battery]
    i_spec = inverters_spec[st.session_state.selected_inverter]
    
    dist = st.session_state.distance
    sector_idx = min(3, dist // 300)
    current_sector = sectors[sector_idx]
    
    # 냉각 시스템 단계별 파라미터 설정
    if "1: ECO" in cooling_mode:
        cool_power, cool_drain = 2.0, 0.3
    elif "2: NORMAL" in cooling_mode:
        cool_power, cool_drain = 5.5, 1.0
    else:  # 3: MAX
        cool_power, cool_drain = 11.5, 2.5

    # random 돌발 변수 1개 추첨
    ev_msg, ev_spd, ev_temp, ev_bat, ev_score = random.choice(track_events)
    
    penalty_time = 0.0
    score_change = ev_score
    status_msg = ""
    msg_type = "success"
    
    # 주행 페달 조작(가속 / 회생제동 / 오버부스트) 계산
    if "가속 주행" in action:
        effective_torque = torque_limit * m_spec["accel"] * i_spec["power"]
        target_speed = min(m_spec["max_spd"], 150 + effective_torque * 1.65) + ev_spd
        temp_delta = (torque_limit * 0.14 * m_spec["heat"] * i_spec["heat_red"] * b_spec["heat_stab"]) - cool_power + ev_temp
        bat_delta = -(torque_limit * 0.08 * b_spec["drain"] + cool_drain) + ev_bat
        status_msg = f"⚡ {current_sector} 가속 주행 완료! 인버터 출력 {torque_limit}% 가동."
        
    elif "회생제동 감속" in action:
        target_speed = max(110, st.session_state.speed * (1.0 - regen_level * 0.0045)) + ev_spd
        recovered = (regen_level * 0.095 * b_spec["regen"] * i_spec["regen_boost"])
        temp_delta = -(cool_power * 0.9) + (regen_level * 0.03) + ev_temp
        bat_delta = recovered - cool_drain + ev_bat
        status_msg = f"🔋 회생제동 작동! 운동 에너지를 전기로 변환하여 배터리를 {round(recovered, 1)}% 충전했습니다."
        
    else:  # 오버부스트 가속
        effective_torque = min(130, torque_limit * 1.2) * m_spec["accel"] * i_spec["power"]
        target_speed = min(m_spec["max_spd"] + 25, 180 + effective_torque * 1.75) + ev_spd
        temp_delta = (18.0 * m_spec["heat"] * i_spec["heat_red"]) - cool_power + ev_temp
        bat_delta = -(12.5 * b_spec["drain"] + cool_drain) + ev_bat
        status_msg = "🔥 오버부스트 발동! 인버터 최대 전류 공급으로 폭발적인 가속!"

    # 조건문 (if-elif-else): 트랙 구간별 공학 규칙 판정
    if current_sector == "급커브 헤어핀":
        if "회생제동" in action and regen_level >= 65:
            bat_delta += 4.5
            score_change += 8
            status_msg = "🏁 완벽한 헤어핀 공략! 회생제동으로 코너를 안정적으로 탈출하고 배터리를 크게 회복했습니다!"
        elif target_speed > 215:
            penalty_time += 1.3
            score_change -= 10
            status_msg = "⚠️ 헤어핀 진입 속도 초과! 회생제동 감속이 부족해 코너 바깥으로 밀려났습니다."
            msg_type = "warning"
            
    elif current_sector == "빗길 슬릭":
        if "회생제동" not in action and torque_limit > 78:
            penalty_time += 1.6
            target_speed *= 0.72
            score_change -= 12
            status_msg = "⚠️ 빗길 휠스핀(슬립) 경고! 토크가 78%를 초과해 타이어가 헛돌며 기록이 지연되었습니다."
            msg_type = "error"
        else:
            score_change += 5
            status_msg = "✅ 빗길 트랙션 제어 성공! 적정 토크 유지로 미끄러짐 없이 통과했습니다."
            
    elif current_sector in ["직선 고속구간", "최종 결승 직선"]:
        if "회생제동" in action:
            penalty_time += 1.0
            score_change -= 6
            status_msg = "⚠️ 직선 구간에서 회생제동을 사용해 속도가 손실되었습니다!"
            msg_type = "warning"
        elif torque_limit >= 85 and regen_level <= 30:
            score_change += 6

    # 모터 과열(열화) 판정
    new_temp = max(35.0, st.session_state.motor_temp + temp_delta + random.uniform(-1.0, 1.5))
    if new_temp >= 95.0:
        target_speed *= 0.70
        penalty_time += 1.2
        score_change -= 10
        status_msg = "🔥 모터 과열(열화) 경고! 95℃ 돌파로 출력 제한(세이프티 모드)이 발동되었습니다!"
        msg_type = "error"

    # 구간(150m = 0.15km) 주행 시간 계산 + random 미세 오차
    avg_speed = max(70.0, (st.session_state.speed + target_speed) / 2.0)
    segment_time = (0.15 / avg_speed) * 3600.0 + penalty_time + random.uniform(-0.12, 0.12)
    
    # 상태 업데이트
    st.session_state.distance += 150
    st.session_state.total_time = round(st.session_state.total_time + segment_time, 2)
    st.session_state.speed = int(target_speed)
    st.session_state.motor_temp = round(new_temp, 1)
    st.session_state.battery = round(max(0.0, min(b_spec["cap"], st.session_state.battery + bat_delta)), 1)
    st.session_state.score = max(0, min(100, st.session_state.score + score_change))
    st.session_state.last_msg = status_msg
    st.session_state.last_event = ev_msg
    st.session_state.msg_type = msg_type
    
    st.session_state.logs.append({
        "구간": f"{st.session_state.distance - 150}~{st.session_state.distance}m ({current_sector})",
        "조작": action.split(" ")[1],
        "속도": f"{st.session_state.speed} km/h",
        "구간기록": f"{round(segment_time, 2)}초",
        "모터온도": f"{st.session_state.motor_temp}℃",
        "배터리": f"{st.session_state.battery}%"
    })

    # 완주 또는 배터리 방전 종료 판정
    if st.session_state.battery <= 0:
        st.session_state.finished = True
        st.session_state.last_msg = "🪫 배터리 완전 방전(DNF)! 에너지 관리 실패로 레이스를 완주하지 못했습니다."
        st.session_state.msg_type = "error"
    elif st.session_state.distance >= 1200:
        st.session_state.finished = True
        st.session_state.last_msg = f"🏆 1,200m 완주 성공! 최종 기록 {st.session_state.total_time}초 / 레이싱 점수 {st.session_state.score}점!"
        st.session_state.msg_type = "success"


# ==========================================
# 4. Streamlit 웹 앱 UI 구성
# ==========================================
st.set_page_config(page_title="하이퍼 EV 레이싱: 파워트레인 마스터", page_icon="🏎️", layout="wide")

if "started" not in st.session_state:
    init_game()

st.title("🏎️⚡ 하이퍼 EV 레이싱: 파워트레인 마스터")
st.caption("전기전자공학 진로 연계 시뮬레이션 | 개러지 부품 세팅 + 실시간 ECU 및 냉각 시스템 제어")

# ------------------------------------------
# [1단계] 개러지: 파워트레인 부품 세팅 (주행 시작 시 잠금)
# ------------------------------------------
lock_badge = "🔒 LOCKED (주행 중 부품 교체 불가)" if st.session_state.started else "🔓 OPEN (레이스 시작 전 세팅 가능)"
st.subheader(f"🛠️ 1. 개러지 파워트레인 세팅 — `{lock_badge}`")

g_col1, g_col2, g_col3 = st.columns(3)
with g_col1:
    st.selectbox(
        "구동 모터 선택",
        list(motors_spec.keys()),
        key="selected_motor",
        disabled=st.session_state.started
    )
    st.caption(motors_spec[st.session_state.selected_motor]["desc"])

with g_col2:
    st.selectbox(
        "고전압 배터리 선택",
        list(batteries_spec.keys()),
        key="selected_battery",
        disabled=st.session_state.started
    )
    st.caption(batteries_spec[st.session_state.selected_battery]["desc"])

with g_col3:
    st.selectbox(
        "인버터 제어기 선택",
        list(inverters_spec.keys()),
        key="selected_inverter",
        disabled=st.session_state.started
    )
    st.caption(inverters_spec[st.session_state.selected_inverter]["desc"])

st.divider()

# ------------------------------------------
# [2단계] 트랙 진행 상황 & 레이스 엔지니어 실시간 무전 가이드
# ------------------------------------------
st.subheader("📡 2. 트랙 현황 및 레이스 엔지니어 전략 무전")

progress_ratio = min(1.0, st.session_state.distance / 1200.0)
current_sec_name = sectors[min(3, st.session_state.distance // 300)] if st.session_state.distance < 1200 else "결승선 통과!"
st.progress(progress_ratio, text=f"주행 거리: {st.session_state.distance}m / 1,200m  |  현재 구간: **{current_sec_name}**")

# 트랙이 바뀔 때마다 추천 조작을 알려주는 엔지니어 무전 배너
radio_text, radio_level = get_engineer_radio(
    st.session_state.distance,
    st.session_state.motor_temp,
    st.session_state.battery
)
if radio_level == "error":
    st.error(radio_text)
elif radio_level == "warning":
    st.warning(radio_text)
elif radio_level == "success":
    st.success(radio_text)
else:
    st.info(radio_text)

# ------------------------------------------
# [3단계] 실시간 주행 제어판 & 냉각 시스템 안내
# ------------------------------------------
ctrl_col, dash_col = st.columns([1.1, 1.2])

with ctrl_col:
    st.subheader("🎛️ 3. 실시간 ECU 및 주행 제어")
    
    # 냉각 시스템이 무엇인지 설명해주는 안내 박스
    with st.expander("❄️ 냉각 시스템(Cooling System)이 무엇인가요? (클릭하여 원리 보기)", expanded=False):
        st.markdown("""
        - **작동 원리:** 모터와 배터리에 큰 전류가 흐르면 줄열($P = I^2R$)이 발생해 온도가 오릅니다. **95℃**를 넘기면 부품 보호를 위해 강제로 출력이 제한됩니다.
        - **1: ECO (절전):** 냉각 펌프를 최소로 돌려 배터리를 아끼지만 온도가 빨리 오릅니다.
        - **2: NORMAL (표준):** 일반적인 주행에 맞춘 기본 냉각 모드입니다.
        - **3: MAX (최대냉각):** 냉각 팬과 워터펌프를 최대로 돌려 온도를 빠르게 식히지만, **냉각기 가동으로 배터리가 조금 더 빨리 소모**됩니다.
        """)

    action = st.radio(
        "주행 페달 조작 선택",
        ["⚡ 가속 주행 (W)", "🔋 회생제동 감속 (S)", "🔥 오버부스트 가속 (Space)"],
        horizontal=True
    )
    
    torque_limit = st.slider("모터 토크 상한 (%)", min_value=20, max_value=100, value=80, step=5)
    regen_level = st.slider("회생제동 강도 (%)", min_value=0, max_value=100, value=40, step=5)
    cooling_mode = st.radio(
        "❄️ 냉각 시스템 출력 단계",
        ["1: ECO (절전)", "2: NORMAL (표준)", "3: MAX (최대냉각)"],
        index=1,
        horizontal=True
    )
    
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if not st.session_state.started:
            if st.button("🏁 레이스 스타트! (부품 잠금)", type="primary", use_container_width=True):
                st.session_state.started = True
                st.session_state.battery = batteries_spec[st.session_state.selected_battery]["cap"]
                st.session_state.last_msg = "🚦 레이스 시작! 개러지 부품이 잠금 처리되었습니다. 첫 150m 구간을 주행하세요!"
                st.rerun()
        elif not st.session_state.finished:
            if st.button("▶️ 다음 150m 구간 주행!", type="primary", use_container_width=True):
                run_sector_step(action, torque_limit, regen_level, cooling_mode)
                st.rerun()
        else:
            st.button("🏁 레이스 종료됨", disabled=True, use_container_width=True)
            
    with btn_col2:
        if st.button("🔄 개러지로 복귀 (리셋)", use_container_width=True):
            init_game()
            st.rerun()

# ------------------------------------------
# [4단계] 결과 출력 및 전장 부품 상태 진단표 (for문 + DataFrame)
# ------------------------------------------
with dash_col:
    st.subheader("📊 4. 실시간 텔레메트리 & 전장 부품 진단")
    
    # 주행 피드백 및 random 트랙 변수 출력
    if st.session_state.msg_type == "error":
        st.error(st.session_state.last_msg)
    elif st.session_state.msg_type == "warning":
        st.warning(st.session_state.last_msg)
    elif st.session_state.msg_type == "success":
        st.success(st.session_state.last_msg)
    else:
        st.info(st.session_state.last_msg)
        
    st.caption(f"🎲 **트랙 환경 변수 (random):** {st.session_state.last_event}")
    
    # 강조 수치 (Metric) 4종
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("⏱️ 누적 기록", f"{st.session_state.total_time} 초")
    m2.metric("🏎️ 현재 속도", f"{st.session_state.speed} km/h")
    m3.metric("🌡️ 모터 온도", f"{st.session_state.motor_temp} ℃")
    m4.metric("🏆 레이싱 점수", f"{st.session_state.score} 점")
    
    # 반복문 (for): 전장 부품 리스트를 순회하며 상태 진단 테이블 생성
    diagnostics = []
    for part in parts:
        if part == "구동 모터":
            load_val = f"{torque_limit}%"
            temp_volt = f"{st.session_state.motor_temp}℃"
            if st.session_state.motor_temp >= 95:
                state = "🔥 과열(출력제한)"
            elif st.session_state.motor_temp >= 85:
                state = "⚠️ 고온주의"
            elif torque_limit >= 85:
                state = "⚡ 고출력 가동"
            else:
                state = "✅ 정상"
                
        elif part == "고전압 배터리":
            load_val = f"{st.session_state.battery}%"
            # random.randint로 실시간 고전압 배터리 전압(V) 변동 표현
            volt = random.randint(355, 370) if st.session_state.battery < 20 else random.randint(396, 405)
            if "800V" in st.session_state.selected_inverter:
                volt *= 2
            temp_volt = f"{volt}V"
            if "회생제동" in action:
                state = "🔋 회생충전 중"
            elif st.session_state.battery < 20:
                state = "🪫 저전압 경고"
            else:
                state = "✅ 정상"
                
        elif part == "인버터/제어기":
            cool_tag = cooling_mode.split(":")[1].strip()
            load_val = f"냉각 {cool_tag}"
            temp_volt = "정상 스위칭"
            if "MAX" in cooling_mode:
                state = "❄️ 최대 냉각 가동"
            elif "오버부스트" in action:
                state = "⚡ 부스트 제어"
            else:
                state = "✅ 안정"
                
        diagnostics.append({
            "전장 부품": part,
            "세팅/부하": load_val,
            "온도/전압": temp_volt,
            "주행 상태": state
        })
        
    df = pd.DataFrame(diagnostics)
    st.table(df)

# 구간별 주행 로그 표시
if st.session_state.logs:
    with st.expander("📜 구간별 상세 주행 로그 보기", expanded=False):
        st.dataframe(pd.DataFrame(st.session_state.logs), use_container_width=True)
