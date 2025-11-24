import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 页面配置 ---
st.set_page_config(page_title="Momo的全域内容数据台", layout="wide", page_icon="📊")

# --- 核心逻辑：数据标准化适配器 ---
def standardize_data(df):
    """
    识别是小红书还是视频号，并重命名为标准字段。
    标准字段：'标题', '曝光', '观看', '点赞', '评论', '收藏', '分享', '涨粉', 'CTR'
    """
    columns = df.columns.tolist()
    platform = "Unknown"
    
    # 清理列名中的空格
    df.columns = [c.strip() for c in df.columns]
    columns = df.columns.tolist()

    # 1. 识别小红书 (特征列：笔记标题)
    if any("笔记标题" in col for col in columns):
        platform = "小红书 (Xiaohongshu)"
        rename_map = {
            '笔记标题': '标题',
            '曝光': '曝光',
            '观看量': '观看',
            '封面点击率': 'CTR', 
            '点赞': '点赞',
            '评论': '评论',
            '收藏': '收藏',
            '分享': '分享',
            '涨粉': '涨粉'
        }
        df_std = df.rename(columns=rename_map)

    # 2. 识别视频号 (特征列：视频描述 或 动态描述)
    elif any(x in columns for x in ["视频描述", "动态描述", "内容"]):
        platform = "视频号 (WeChat Channels)"
        # 建立映射字典
        rename_map = {
            '视频描述': '标题',
            '动态描述': '标题',
            '内容': '标题',
            '播放量': '观看',     # 适配你的文件
            '浏览次数': '观看',
            '观看次数': '观看',
            '喜欢': '点赞',       # 视频号叫“喜欢”
            '点赞次数': '点赞',
            '评论量': '评论',
            '评论次数': '评论',
            '收藏次数': '收藏',   # 你的文件可能没有收藏列，没关系，下面会补0
            '分享量': '分享',
            '转发次数': '分享',
            '分享次数': '分享',
            '关注量': '涨粉',     # 适配你的文件
            '净增关注': '涨粉',
            '推荐': '曝光',       # 注意：视频号的推荐通常指推荐次数，不完全等于曝光，但可作参考
            '推荐次数': '曝光'
        }
        df_std = df.rename(columns=rename_map)
        
        # 特殊处理：合并分享数据
        # 视频号有时会区分 "分享量" 和 "转发聊天和朋友圈"
        if '转发聊天和朋友圈' in df.columns and '分享' in df_std.columns:
            # 确保是数字类型
            share_1 = pd.to_numeric(df_std['分享'], errors='coerce').fillna(0)
            share_2 = pd.to_numeric(df['转发聊天和朋友圈'], errors='coerce').fillna(0)
            df_std['分享'] = share_1 + share_2

    else:
        return df, "Unknown", []

    # --- 统一清洗逻辑 ---
    
    # 确保所有标准列都存在，不存在的补0
    needed_cols = ['标题', '曝光', '观看', '点赞', '评论', '收藏', '分享', '涨粉', 'CTR']
    for col in needed_cols:
        if col not in df_std.columns:
            df_std[col] = 0 
            
    # 数据类型转换 (强制转为数字)
    for col in needed_cols[1:]: # 跳过标题
        df_std[col] = pd.to_numeric(df_std[col], errors='coerce').fillna(0)

    # 视频号特殊处理：如果没有CTR，且有曝光和观看，尝试计算；否则为0
    if df_std['CTR'].sum() == 0 and df_std['曝光'].sum() > 0 and df_std['观看'].sum() > 0:
         # 只有当曝光大于观看时，计算CTR才有意义 (避免CTR > 100% 的异常情况)
         if df_std['曝光'].sum() > df_std['观看'].sum():
            df_std['CTR'] = df_std['观看'] / df_std['曝光']
    
    # 计算互动总量
    df_std['互动总量'] = df_std['点赞'] + df_std['评论'] + df_std['收藏'] + df_std['分享']
    
    return df_std, platform, needed_cols

def load_data(file):
    try:
        if file.name.endswith('.csv'):
            try:
                df = pd.read_csv(file, encoding='utf-8')
            except:
                try:
                    df = pd.read_csv(file, encoding='gbk')
                except:
                    df = pd.read_csv(file, encoding='utf-16') # 视频号有时用utf-16
        else:
            df = pd.read_excel(file)
        return df
    except Exception as e:
        st.error(f"读取文件失败: {e}")
        return None

# --- 主界面 ---
st.title("📊 Momo的全域内容数据台 (Pro版)")
st.markdown("### 兼容：小红书笔记列表 & 视频号动态明细")

# 侧边栏上传
st.sidebar.header("📂 数据导入")
uploaded_file = st.sidebar.file_uploader("上传 Excel/CSV 文件", type=['csv', 'xlsx'])

if uploaded_file is not None:
    raw_df = load_data(uploaded_file)
    
    if raw_df is not None:
        # 数据标准化
        df, platform_name, _ = standardize_data(raw_df)
        
        if platform_name == "Unknown":
            st.error("无法识别文件格式。请确保上传的是小红书或视频号的官方导出表格。")
            st.write("检测到的列名:", raw_df.columns.tolist())
        else:
            st.success(f"✅ 已成功识别平台：**{platform_name}**")
            
            # --- 顶部 KPI ---
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("总观看/浏览", f"{df['观看'].sum():,.0f}")
            col2.metric("总互动量", f"{df['互动总量'].sum():,.0f}")
            col3.metric("总涨粉", f"{df['涨粉'].sum():,.0f}")
            
            # 判断是否有有效的曝光数据
            # 很多视频号数据曝光列全是0，或者极小(仅推荐数)，这种情况下不显示CTR
            has_valid_exposure = df['曝光'].sum() > df['观看'].sum()
            
            if has_valid_exposure:
                col4.metric("总曝光", f"{df['曝光'].sum():,.0f}")
                avg_ctr = df['CTR'].mean() * 100 if df['CTR'].max() <= 1 else df['CTR'].mean()
                col5.metric("平均点击率 (CTR)", f"{avg_ctr:.2f}%")
            else:
                col4.metric("互动率", f"{(df['互动总量'].sum() / df['观看'].sum() * 100):.2f}%", help="总互动/总观看")
                col5.metric("点击率", "无曝光数据", help="视频号通常不提供总曝光量，无法计算点击率")

            st.markdown("---")

            # -------------------------------------------------------
            # 1. 流量漏斗
            # -------------------------------------------------------
            st.header("1. 🌪️ 流量漏斗全景")
            
            funnel_stages = ["观看 (点击进来)", "互动 (赞藏评转)", "转化 (关注)"]
            funnel_values = [df['观看'].sum(), df['互动总量'].sum(), df['涨粉'].sum()]
            
            if has_valid_exposure:
                funnel_stages.insert(0, "曝光 (展现)")
                funnel_values.insert(0, df['曝光'].sum())
            else:
                st.caption("⚠️ 注：检测到该平台未提供完整的曝光数据（或曝光量小于播放量），漏斗将从【观看】开始展示。")

            fig_funnel = go.Figure(go.Funnel(
                y=funnel_stages,
                x=funnel_values,
                textinfo="value+percent previous"
            ))
            st.plotly_chart(fig_funnel, use_container_width=True)

            # -------------------------------------------------------
            # 2. 涨粉效率榜单
            # -------------------------------------------------------
            st.header("2. 🚀 涨粉效率榜单")
            top_n = st.slider("显示前多少名？", 5, 20, 10)
            
            df_fans = df[df['涨粉'] > 0].sort_values(by='涨粉', ascending=False).head(top_n)
            
            if not df_fans.empty:
                # 截断太长的标题
                df_fans['短标题'] = df_fans['标题'].apply(lambda x: str(x)[:20] + '...' if len(str(x)) > 20 else str(x))
                
                fig_fans = px.bar(
                    df_fans, 
                    x='涨粉', 
                    y='短标题', 
                    orientation='h',
                    text='涨粉',
                    color='涨粉',
                    color_continuous_scale='Bluered',
                    hover_data=['标题', '观看', '互动总量']
                )
                fig_fans.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_fans, use_container_width=True)
            else:
                st.info("数据中没有显示任何涨粉记录。")

            # -------------------------------------------------------
            # 3. 象限图 (智能切换)
            # -------------------------------------------------------
            st.header("3. 🎯 内容质量象限图")
            
            if has_valid_exposure:
                # 模式 A: CTR vs 观看
                x_axis = 'CTR'
                y_axis = '观看'
                title_text = "封面点击率 (CTR) vs 观看量"
                x_mean = df['CTR'].mean()
                help_msg = "右侧代表点击率高（标题党/封面好），上方代表流量大。"
            else:
                # 模式 B: 互动率 vs 观看 (视频号模式)
                # 计算互动率 = 互动总量 / 观看
                df['互动率'] = df.apply(lambda row: row['互动总量'] / row['观看'] if row['观看'] > 0 else 0, axis=1)
                x_axis = '互动率'
                y_axis = '观看'
                title_text = "互动率 (内容质量) vs 观看量 (算法推流)"
                x_mean = df['互动率'].mean()
                help_msg = "💡 **视频号专属模式**：X轴改为**互动率**。\n- **右下角**：小众精品（流量一般，但看的人都喜欢/收藏/转发）。\n- **右上角**：大爆款（流量大，互动也高）。"

            st.caption(help_msg)
            y_mean = df['观看'].mean()

            fig_scatter = px.scatter(
                df, 
                x=x_axis, 
                y=y_axis, 
                size='涨粉', 
                color='涨粉', 
                hover_name='标题',
                size_max=60,
                template='plotly_white',
                title=f"气泡大小 = 涨粉数"
            )
            
            # 辅助线
            fig_scatter.add_vline(x=x_mean, line_width=1, line_dash="dash", line_color="grey")
            fig_scatter.add_hline(y=y_mean, line_width=1, line_dash="dash", line_color="grey")
            
            st.plotly_chart(fig_scatter, use_container_width=True)

            # -------------------------------------------------------
            # 4. 热力图
            # -------------------------------------------------------
            st.header("4. 🔥 关键指标相关性")
            
            corr_cols = ['曝光', '观看', 'CTR', '点赞', '评论', '收藏', '分享', '涨粉', '互动总量']
            valid_cols = [c for c in corr_cols if c in df.columns and df[c].sum() != 0]
            
            if len(valid_cols) > 1:
                corr_matrix = df[valid_cols].corr()
                fig_corr = px.imshow(
                    corr_matrix, 
                    text_auto=".2f", 
                    aspect="auto", 
                    color_continuous_scale="RdBu_r",
                    origin='lower'
                )
                st.plotly_chart(fig_corr, use_container_width=True)
                
                if '涨粉' in valid_cols:
                    correlations = corr_matrix['涨粉'].drop('涨粉')
                    best_indicator = correlations.idxmax()
                    st.success(f"💡 **AI洞察：** 在【{platform_name}】平台，与涨粉最相关的指标是【{best_indicator}】(相关系数 {correlations.max():.2f})。这提示你应重点优化该指标。")

else:
    st.info("👆 请在左侧上传数据文件。支持：小红书后台导出表、视频号助手导出表。")