import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# --- 1. 定数と初期設定 ---

TOTAL_MINUTES_IN_DAY = 1440  # 24時間 = 1440分
MINUTES_IN_HOUR = 60

def init_session_state():
    """セッションステート（アプリの状態を保持する領域）を初期化する"""
    if 'schedule_df' not in st.session_state:
        # スケジュールを保存するDataFrameを作成
        st.session_state.schedule_df = pd.DataFrame(
            columns=['活動名', '開始時刻', '終了時刻', '所要時間 (分)']
        )

st.set_page_config(
    page_title="24時間フルカバー可視化",
    layout="wide"
)

init_session_state()
st.title("📅 24時間フルカバー スケジュール可視化アプリ")

# --- 2. データ入力エリア (サイドバー) ---

st.sidebar.header("📝 時間帯指定で活動を記録")

with st.sidebar.form(key='schedule_form', clear_on_submit=True):
    activity_name = st.text_input("活動名 (例: 昼食、仕事、睡眠)")

    # 開始時刻と終了時刻の入力（初期値は1時間）
    col_start, col_end = st.sidebar.columns(2)
    start_time = col_start.time_input("開始時刻", datetime.time(12, 0))
    end_time = col_end.time_input("終了時刻", datetime.time(13, 0))

    submit_button = st.form_submit_button("活動を追加")

    if submit_button:
        if not activity_name:
            st.sidebar.error("活動名を入力してください。")
        else:
            # 日付情報をつけてDurationを計算
            today = datetime.date.today()
            start_dt = datetime.datetime.combine(today, start_time)
            end_dt = datetime.datetime.combine(today, end_time)
            
            # 日をまたぐ入力（例: 23:00から01:00）に対応
            if start_dt >= end_dt:
                # 終了時刻に1日加算して計算
                if start_time != end_time: # ぴったり24時間は除外
                     end_dt += datetime.timedelta(days=1)
                else:
                    st.sidebar.error("開始時刻と終了時刻が同じか、または不適切な入力です。開始時刻より後に終了時刻を設定してください。")
                    st.stop() # 処理を中断

            duration = end_dt - start_dt
            duration_minutes = int(duration.total_seconds() / 60)
            
            # 24時間を超える活動のチェック
            if duration_minutes > TOTAL_MINUTES_IN_DAY:
                st.sidebar.error("活動の所要時間が24時間（1440分）を超えています。")
                st.stop()

            # 新しい行を作成
            new_entry = pd.DataFrame(
                [[activity_name, start_time.strftime("%H:%M"), end_time.strftime("%H:%M"), duration_minutes]],
                columns=['活動名', '開始時刻', '終了時刻', '所要時間 (分)']
            )
            
            st.session_state.schedule_df = pd.concat(
                [st.session_state.schedule_df, new_entry],
                ignore_index=True
            )
            st.toast(f"'{activity_name}' を {duration_minutes}分 追加しました！", icon='✅')

# --- 3. メイン処理：活動データと「予定なし」を結合する関数 ---

def get_full_day_schedule(df):
    """記録された活動と「予定なし」の時間を計算してDataFrameを統合する"""
    if df.empty:
        # 活動が一つもなければ、すべて「予定なし」
        return pd.DataFrame({
            '活動名': ['予定なし'],
            '所要時間 (分)': [TOTAL_MINUTES_IN_DAY]
        })

    # 活動名ごとに時間を合計
    grouped_df = df.groupby('活動名')['所要時間 (分)'].sum().reset_index(name='所要時間 (分)')
    
    # 記録された活動の合計時間を計算
    recorded_minutes = grouped_df['所要時間 (分)'].sum()
    
    # 残りの時間（予定なし）を計算
    unplanned_minutes = TOTAL_MINUTES_IN_DAY - recorded_minutes
    
    if unplanned_minutes < 0:
        # 合計時間が24時間を超えている場合は警告を出す（Streamlit表示で別途対応）
        pass
    
    elif unplanned_minutes > 0:
        # 残りの時間があれば「予定なし」として追加
        unplanned_entry = pd.DataFrame({
            '活動名': ['予定なし'],
            '所要時間 (分)': [unplanned_minutes]
        })
        grouped_df = pd.concat([grouped_df, unplanned_entry], ignore_index=True)

    return grouped_df

# --- 4. データ表示エリア ---

st.subheader("現在のスケジュール内訳 (24時間)")

# 24時間対応の統合済みデータを取得
full_schedule_df = get_full_day_schedule(st.session_state.schedule_df)
total_minutes_displayed = full_schedule_df['所要時間 (分)'].sum()

if st.session_state.schedule_df.empty:
    st.info("👈 サイドバーから活動を入力すると、24時間の円グラフが作成されます。")
else:
    # グラフタイトル用に実際の合計時間を再計算
    recorded_minutes = st.session_state.schedule_df['所要時間 (分)'].sum()

    if recorded_minutes > TOTAL_MINUTES_IN_DAY:
        st.error(f"⚠️ **合計時間が24時間（1,440分）を超過しています！** 現在 **{recorded_minutes}分**です。")
        # 超過時は「予定なし」を含まない、記録された活動のみを表示
        display_df = st.session_state.schedule_df.groupby('活動名')['所要時間 (分)'].sum().reset_index(name='所要時間 (分)')
        chart_title = f"📅 記録された活動の時間配分（超過あり: {recorded_minutes}分）"
    else:
        # 正常な場合は「予定なし」を含むフルスケジュールを表示
        display_df = full_schedule_df
        chart_title = f"📅 24時間の時間配分"


    # --- 5. 円グラフの生成と表示 ---
    
    # 円グラフを Plotly で作成
    fig = px.pie(
        display_df,
        values='所要時間 (分)',
        names='活動名',
        title=chart_title,
        hole=.3 # ドーナツ型にする
    )

    # グラフを24分割の円グラフのように見せるための工夫（時間表示のヒント）
    fig.update_traces(textinfo='percent+label') # 割合とラベルを表示
    
    # グラフの表示 
    st.plotly_chart(fig, use_container_width=True)

    # 詳細データ
    st.subheader("詳細データテーブル")
    # 入力詳細
    st.markdown("##### 記録された活動リスト")
    st.dataframe(st.session_state.schedule_df, use_container_width=True, hide_index=True)
    # 集計結果
    st.markdown("##### 24時間集計結果")
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# --- 6. データクリア機能 (サイドバー) ---

st.sidebar.markdown("---")
if st.sidebar.button("全データをクリア", help="記録したスケジュールデータをすべて削除します。"):
    # session_stateをリセット
    st.session_state.schedule_df = pd.DataFrame(
        columns=['活動名', '開始時刻', '終了時刻', '所要時間 (分)']
    )
    st.rerun()